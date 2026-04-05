from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from threading import Event

from ..core.entities import ScanExecutionResult, ScanProgress, ScanResult
from ..core.enums import ScanLifecycleStatus
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
            results.append(enriched_host)
            if on_result_discovered is not None:
                on_result_discovered(enriched_host)

        self._host_discovery.discover_hosts(
            network_range,
            stop_event=self._stop_requested,
            on_host_discovered=handle_host_discovered,
            on_progress=on_progress_updated,
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
