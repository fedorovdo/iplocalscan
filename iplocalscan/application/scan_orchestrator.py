from __future__ import annotations

from dataclasses import replace

from ..core.entities import ScanExecutionResult
from ..core.enums import ScanLifecycleStatus
from ..services.contracts import (
    HostDiscoveryService,
    HostnameResolver,
    MacVendorLookup,
    PortScanner,
    ServiceDetector,
)


class ScanOrchestrator:
    """Coordinates the scan pipeline independently from the Qt UI layer."""

    def __init__(
        self,
        host_discovery: HostDiscoveryService,
        hostname_resolver: HostnameResolver,
        port_scanner: PortScanner,
        service_detector: ServiceDetector,
        mac_vendor_lookup: MacVendorLookup,
    ) -> None:
        self._host_discovery = host_discovery
        self._hostname_resolver = hostname_resolver
        self._port_scanner = port_scanner
        self._service_detector = service_detector
        self._mac_vendor_lookup = mac_vendor_lookup
        self._stop_requested = False

    def execute(self, network_range: str) -> ScanExecutionResult:
        results = []
        discovered_hosts = self._host_discovery.discover_hosts(network_range)

        for discovered_host in discovered_hosts:
            if self._stop_requested:
                self._stop_requested = False
                return ScanExecutionResult(
                    results=results,
                    status=ScanLifecycleStatus.STOPPED,
                    note="scan.note.stop_requested",
                )

            open_ports = self._port_scanner.scan_open_ports(discovered_host.ip_address)
            detected_services = self._service_detector.detect_services(
                discovered_host.ip_address,
                open_ports,
            )
            hostname = self._hostname_resolver.resolve_hostname(
                discovered_host.ip_address
            )
            vendor = self._mac_vendor_lookup.lookup_vendor(
                discovered_host.mac_address
            )
            results.append(
                replace(
                    discovered_host,
                    hostname=hostname or discovered_host.hostname,
                    mac_vendor=vendor or discovered_host.mac_vendor,
                    open_ports=open_ports,
                    detected_services=detected_services,
                )
            )

        final_status = (
            ScanLifecycleStatus.STOPPED
            if self._stop_requested
            else ScanLifecycleStatus.COMPLETED
        )
        self._stop_requested = False
        return ScanExecutionResult(
            results=results,
            status=final_status,
            note="scan.note.stub",
        )

    def request_stop(self) -> None:
        self._stop_requested = True

    def clear_stop_request(self) -> None:
        self._stop_requested = False

