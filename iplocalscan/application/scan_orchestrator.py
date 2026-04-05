from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from threading import Event

from ..core.entities import ScanExecutionResult, ScanProgress, ScanResult
from ..core.enums import ScanLifecycleStatus, ScanStage
from ..services.contracts import (
    HostDiscoveryService,
    HostnameResolver,
    MacAddressResolver,
    MacVendorLookup,
    PortScanner,
    ServiceDetector,
)

logger = logging.getLogger(__name__)


class ScanOrchestrator:
    """Coordinates the scan pipeline independently from the Qt UI layer."""

    def __init__(
        self,
        host_discovery: HostDiscoveryService,
        hostname_resolver: HostnameResolver,
        mac_address_resolver: MacAddressResolver,
        port_scanner: PortScanner,
        service_detector: ServiceDetector,
        mac_vendor_lookup: MacVendorLookup,
    ) -> None:
        self._host_discovery = host_discovery
        self._hostname_resolver = hostname_resolver
        self._mac_address_resolver = mac_address_resolver
        self._port_scanner = port_scanner
        self._service_detector = service_detector
        self._mac_vendor_lookup = mac_vendor_lookup
        self._stop_requested = Event()

    def execute(
        self,
        network_range: str,
        *,
        on_result_discovered: Callable[[ScanResult], None] | None = None,
        on_progress_updated: Callable[[ScanProgress], None] | None = None,
    ) -> ScanExecutionResult:
        logger.info(
            "Executing scan orchestration.",
            extra={
                "event": "scan_execute_started",
                "network_range": network_range,
            },
        )
        results: list[ScanResult] = []

        def handle_host_discovered(discovered_host: ScanResult) -> None:
            if self._stop_requested.is_set():
                return

            enriched_host = self._enrich_host(discovered_host)
            self._upsert_result(results, enriched_host)
            if on_result_discovered is not None:
                on_result_discovered(enriched_host)

        self._host_discovery.discover_hosts(
            network_range,
            stop_event=self._stop_requested,
            on_host_discovered=handle_host_discovered,
            on_progress=on_progress_updated,
        )

        self._scan_ports_for_discovered_hosts(
            network_range=network_range,
            results=results,
            on_result_discovered=on_result_discovered,
            on_progress_updated=on_progress_updated,
        )

        final_status = (
            ScanLifecycleStatus.STOPPED
            if self._stop_requested.is_set()
            else ScanLifecycleStatus.COMPLETED
        )
        note = (
            "scan.note.stop_requested"
            if final_status is ScanLifecycleStatus.STOPPED
            else "scan.note.completed"
        )
        logger.info(
            "Scan orchestration finished.",
            extra={
                "event": "scan_execute_finished",
                "network_range": network_range,
                "status": final_status.value,
                "result_count": len(results),
            },
        )
        self._stop_requested.clear()
        return ScanExecutionResult(
            results=results,
            status=final_status,
            note=note,
        )

    def request_stop(self) -> None:
        self._stop_requested.set()

    def clear_stop_request(self) -> None:
        self._stop_requested.clear()

    def _enrich_host(self, discovered_host: ScanResult) -> ScanResult:
        hostname = self._hostname_resolver.resolve_hostname(discovered_host.ip_address)
        mac_address = self._mac_address_resolver.resolve_mac_address(
            discovered_host.ip_address
        )
        vendor = self._mac_vendor_lookup.lookup_vendor(mac_address)
        return replace(
            discovered_host,
            hostname=hostname or discovered_host.hostname,
            mac_address=mac_address or discovered_host.mac_address,
            mac_vendor=vendor or discovered_host.mac_vendor,
            open_ports=[],
            detected_services=[],
        )

    def _scan_ports_for_discovered_hosts(
        self,
        *,
        network_range: str,
        results: list[ScanResult],
        on_result_discovered: Callable[[ScanResult], None] | None,
        on_progress_updated: Callable[[ScanProgress], None] | None,
    ) -> None:
        if self._stop_requested.is_set():
            return

        total_hosts = len(results)
        if total_hosts == 0:
            return

        logger.info(
            "Starting port scan stage for discovered hosts.",
            extra={
                "event": "port_stage_started",
                "network_range": network_range,
                "host_count": total_hosts,
            },
        )
        if on_progress_updated is not None:
            on_progress_updated(
                ScanProgress(
                    network_range=network_range,
                    stage=ScanStage.PORT_SCAN,
                    total_hosts=total_hosts,
                    completed_hosts=0,
                    discovered_hosts=0,
                )
            )

        hosts_with_open_ports = 0
        for index, discovered_host in enumerate(list(results), start=1):
            if self._stop_requested.is_set():
                break

            open_ports = self._port_scanner.scan_open_ports(
                discovered_host.ip_address,
                stop_event=self._stop_requested,
            )
            detected_services = self._service_detector.detect_services(
                discovered_host.ip_address,
                open_ports,
            )
            updated_host = replace(
                discovered_host,
                open_ports=open_ports,
                detected_services=detected_services,
            )
            if open_ports:
                hosts_with_open_ports += 1

            self._upsert_result(results, updated_host)
            if on_result_discovered is not None:
                on_result_discovered(updated_host)
            if on_progress_updated is not None:
                on_progress_updated(
                    ScanProgress(
                        network_range=network_range,
                        stage=ScanStage.PORT_SCAN,
                        total_hosts=total_hosts,
                        completed_hosts=index,
                        discovered_hosts=hosts_with_open_ports,
                        current_ip=updated_host.ip_address,
                    )
                )

        logger.info(
            "Completed port scan stage for discovered hosts.",
            extra={
                "event": "port_stage_completed",
                "network_range": network_range,
                "host_count": total_hosts,
                "hosts_with_open_ports": hosts_with_open_ports,
            },
        )

    def _upsert_result(
        self,
        results: list[ScanResult],
        updated_result: ScanResult,
    ) -> None:
        for index, existing_result in enumerate(results):
            if existing_result.ip_address == updated_result.ip_address:
                results[index] = updated_result
                return

        results.append(updated_result)
