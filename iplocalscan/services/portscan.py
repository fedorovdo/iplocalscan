from __future__ import annotations

import logging
import socket
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from threading import Event
from typing import Final, Sequence

from ..core.entities import ServiceRecord

logger = logging.getLogger(__name__)

DEFAULT_TCP_PORTS: Final[tuple[int, ...]] = (
    21,
    22,
    23,
    25,
    53,
    80,
    110,
    123,
    135,
    139,
    143,
    161,
    389,
    443,
    445,
    465,
    515,
    587,
    631,
    636,
    993,
    995,
    1433,
    3306,
    3389,
    5357,
    5432,
    5985,
    5986,
    6379,
    8080,
    8443,
    9100,
)

KNOWN_TCP_SERVICES: Final[dict[int, str]] = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    123: "NTP",
    135: "RPC",
    139: "NetBIOS",
    143: "IMAP",
    161: "SNMP",
    389: "LDAP",
    443: "HTTPS",
    445: "SMB",
    465: "SMTPS",
    515: "LPD",
    587: "SMTP Submission",
    631: "IPP",
    636: "LDAPS",
    993: "IMAPS",
    995: "POP3S",
    1433: "MSSQL",
    3306: "MySQL",
    3389: "RDP",
    5357: "WSD",
    5432: "PostgreSQL",
    5985: "WinRM",
    5986: "WinRM HTTPS",
    6379: "Redis",
    8080: "HTTP Alt",
    8443: "HTTPS Alt",
    9100: "JetDirect",
}


class SocketTcpConnectPortScanner:
    def __init__(
        self,
        *,
        ports: Sequence[int] = DEFAULT_TCP_PORTS,
        timeout_seconds: float = 0.3,
        max_workers: int = 12,
    ) -> None:
        self._ports = tuple(dict.fromkeys(int(port) for port in ports))
        self._timeout_seconds = timeout_seconds
        self._max_workers = max_workers

    def scan_open_ports(
        self,
        ip_address: str,
        *,
        stop_event: Event | None = None,
    ) -> list[int]:
        if not self._ports:
            return []

        max_workers = max(1, min(self._max_workers, len(self._ports)))
        open_ports: list[int] = []

        logger.info(
            "Starting TCP connect scan for host.",
            extra={
                "event": "port_scan_started",
                "ip_address": ip_address,
                "port_count": len(self._ports),
                "timeout_seconds": self._timeout_seconds,
                "max_workers": max_workers,
            },
        )

        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="iplocalscan-port",
        ) as executor:
            port_iter = iter(self._ports)
            pending_futures: dict[Future[int | None], int] = {}

            def submit_next() -> bool:
                if stop_event is not None and stop_event.is_set():
                    return False
                try:
                    port = next(port_iter)
                except StopIteration:
                    return False

                future = executor.submit(self._probe_port, ip_address, port)
                pending_futures[future] = port
                return True

            for _ in range(max_workers):
                if not submit_next():
                    break

            while pending_futures:
                if stop_event is not None and stop_event.is_set():
                    for future in pending_futures:
                        future.cancel()
                    logger.info(
                        "Stopping TCP connect scan after cancellation request.",
                        extra={
                            "event": "port_scan_stopping",
                            "ip_address": ip_address,
                            "open_ports": open_ports,
                        },
                    )
                    break

                completed_futures, _ = wait(
                    tuple(pending_futures),
                    return_when=FIRST_COMPLETED,
                )
                for completed_future in completed_futures:
                    port = pending_futures.pop(completed_future)
                    try:
                        maybe_open_port = completed_future.result()
                    except Exception:
                        logger.exception(
                            "Port probe failed unexpectedly.",
                            extra={
                                "event": "port_probe_failed",
                                "ip_address": ip_address,
                                "port": port,
                            },
                        )
                        maybe_open_port = None

                    if maybe_open_port is not None:
                        open_ports.append(maybe_open_port)

                    submit_next()

        unique_open_ports = sorted(set(open_ports))
        logger.info(
            "Completed TCP connect scan for host.",
            extra={
                "event": "port_scan_completed",
                "ip_address": ip_address,
                "open_ports": unique_open_ports,
            },
        )
        return unique_open_ports

    def _probe_port(self, ip_address: str, port: int) -> int | None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_socket:
                probe_socket.settimeout(self._timeout_seconds)
                result = probe_socket.connect_ex((ip_address, port))
        except OSError:
            return None

        return port if result == 0 else None


class StaticPortServiceDetector:
    def __init__(self, service_map: dict[int, str] | None = None) -> None:
        self._service_map = dict(service_map or KNOWN_TCP_SERVICES)

    def detect_services(
        self,
        ip_address: str,
        open_ports: Sequence[int],
    ) -> list[ServiceRecord]:
        logger.debug(
            "Inferring services from open ports.",
            extra={
                "event": "service_detection_started",
                "ip_address": ip_address,
                "open_ports": list(open_ports),
            },
        )
        detected_services = [
            ServiceRecord(
                name=self._service_map[port],
                protocol="tcp",
                port=port,
            )
            for port in sorted(set(open_ports))
            if port in self._service_map
        ]
        logger.debug(
            "Completed service inference.",
            extra={
                "event": "service_detection_completed",
                "ip_address": ip_address,
                "service_count": len(detected_services),
            },
        )
        return detected_services
