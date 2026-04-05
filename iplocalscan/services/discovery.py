from __future__ import annotations

import logging
import math
import subprocess
import sys
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from ipaddress import ip_network
from threading import Event
from typing import Callable

from ..core.entities import ScanProgress, ScanResult
from ..core.enums import HostStatus, ScanStage

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProbeResult:
    ip_address: str
    is_online: bool


class SubprocessPingHostDiscovery:
    def __init__(
        self,
        *,
        timeout_ms: int = 300,
        max_workers: int = 32,
    ) -> None:
        self._timeout_ms = timeout_ms
        self._max_workers = max_workers

    def discover_hosts(
        self,
        network_range: str,
        *,
        stop_event: Event | None = None,
        on_host_discovered: Callable[[ScanResult], None] | None = None,
        on_progress: Callable[[ScanProgress], None] | None = None,
    ) -> list[ScanResult]:
        network = ip_network(network_range, strict=True)
        if network.version != 4:
            raise ValueError("Only IPv4 networks are supported.")

        host_addresses = [str(address) for address in network.hosts()]
        total_hosts = len(host_addresses)
        max_workers = max(1, min(self._max_workers, total_hosts or 1))
        results: list[ScanResult] = []
        scanned_hosts = 0
        discovered_hosts = 0

        logger.info(
            "Starting ping-based host discovery.",
            extra={
                "event": "host_discovery_started",
                "network_range": network_range,
                "total_hosts": total_hosts,
                "max_workers": max_workers,
                "timeout_ms": self._timeout_ms,
            },
        )

        if total_hosts == 0:
            if on_progress is not None:
                on_progress(
                    ScanProgress(
                        network_range=network_range,
                        stage=ScanStage.DISCOVERY,
                        total_hosts=0,
                        completed_hosts=0,
                        discovered_hosts=0,
                    )
                )
            return results

        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="iplocalscan-ping",
        ) as executor:
            host_iter = iter(host_addresses)
            pending_futures: dict[Future[ProbeResult], str] = {}

            def submit_next() -> bool:
                if stop_event is not None and stop_event.is_set():
                    return False
                try:
                    ip_address = next(host_iter)
                except StopIteration:
                    return False

                future = executor.submit(self._probe_host, ip_address)
                pending_futures[future] = ip_address
                return True

            for _ in range(max_workers):
                if not submit_next():
                    break

            while pending_futures:
                if stop_event is not None and stop_event.is_set():
                    for future in pending_futures:
                        future.cancel()
                    logger.info(
                        "Stopping host discovery after cancellation request.",
                        extra={
                            "event": "host_discovery_stopping",
                            "network_range": network_range,
                            "scanned_hosts": scanned_hosts,
                            "discovered_hosts": discovered_hosts,
                        },
                    )
                    break

                done_futures, _ = wait(
                    tuple(pending_futures),
                    return_when=FIRST_COMPLETED,
                )
                for completed_future in done_futures:
                    ip_address = pending_futures.pop(completed_future)
                    try:
                        probe_result = completed_future.result()
                    except Exception:
                        logger.exception(
                            "Ping probe failed unexpectedly.",
                            extra={
                                "event": "ping_probe_failed",
                                "ip_address": ip_address,
                            },
                        )
                        probe_result = ProbeResult(ip_address=ip_address, is_online=False)

                    scanned_hosts += 1
                    if probe_result.is_online:
                        discovered_hosts += 1
                        discovered_result = ScanResult(
                            ip_address=probe_result.ip_address,
                            status=HostStatus.UP,
                        )
                        results.append(discovered_result)
                        logger.info(
                            "Discovered online host.",
                            extra={
                                "event": "host_discovered",
                                "ip_address": probe_result.ip_address,
                                "network_range": network_range,
                                "discovered_hosts": discovered_hosts,
                            },
                        )
                        if on_host_discovered is not None:
                            on_host_discovered(discovered_result)

                    if on_progress is not None:
                        on_progress(
                            ScanProgress(
                                network_range=network_range,
                                stage=ScanStage.DISCOVERY,
                                total_hosts=total_hosts,
                                completed_hosts=scanned_hosts,
                                discovered_hosts=discovered_hosts,
                                current_ip=probe_result.ip_address,
                            )
                        )

                    submit_next()

        logger.info(
            "Completed ping-based host discovery.",
            extra={
                "event": "host_discovery_completed",
                "network_range": network_range,
                "scanned_hosts": scanned_hosts,
                "discovered_hosts": discovered_hosts,
            },
        )
        return results

    def _probe_host(self, ip_address: str) -> ProbeResult:
        command = self._build_ping_command(ip_address)
        run_kwargs = {
            "args": command,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "check": False,
            "timeout": max(2, math.ceil(self._timeout_ms / 1000) + 1),
        }
        creation_flags = self._subprocess_creation_flags()
        if creation_flags:
            run_kwargs["creationflags"] = creation_flags

        try:
            completed_process = subprocess.run(**run_kwargs)
        except (subprocess.TimeoutExpired, OSError):
            logger.debug(
                "Ping probe returned no response.",
                extra={
                    "event": "ping_probe_timeout",
                    "ip_address": ip_address,
                },
            )
            return ProbeResult(ip_address=ip_address, is_online=False)

        return ProbeResult(
            ip_address=ip_address,
            is_online=completed_process.returncode == 0,
        )

    def _build_ping_command(self, ip_address: str) -> list[str]:
        if sys.platform.startswith("win"):
            return ["ping", "-n", "1", "-w", str(self._timeout_ms), ip_address]

        timeout_seconds = max(1, math.ceil(self._timeout_ms / 1000))
        return ["ping", "-c", "1", "-W", str(timeout_seconds), ip_address]

    def _subprocess_creation_flags(self) -> int:
        if hasattr(subprocess, "CREATE_NO_WINDOW") and sys.platform.startswith("win"):
            return int(subprocess.CREATE_NO_WINDOW)
        return 0
