from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from threading import Event

from ..core.entities import (
    DeviceIdentity,
    ScanExecutionResult,
    ScanProgress,
    ScanResult,
    ServiceRecord,
)
from ..core.enums import ScanLifecycleStatus, ScanStage
from ..services.contracts import (
    DeviceIdentityService,
    HostDiscoveryService,
    HostnameResolver,
    MacAddressResolver,
    MacVendorLookup,
    PortScanner,
    ServiceDetector,
)

logger = logging.getLogger(__name__)

_PRINTER_PORTS = {515, 631, 9100, 5357}
_PRINTER_VENDOR_TERMS = (
    "canon",
    "epson",
    "xerox",
    "ricoh",
    "kyocera",
    "brother",
    "lexmark",
    "zebra",
    "pantum",
)
_PRINTER_HOSTNAME_TERMS = (
    "npi",
    "imagerunner",
    "pantum",
)


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
        device_identity_service: DeviceIdentityService | None = None,
    ) -> None:
        self._host_discovery = host_discovery
        self._hostname_resolver = hostname_resolver
        self._mac_address_resolver = mac_address_resolver
        self._port_scanner = port_scanner
        self._service_detector = service_detector
        self._mac_vendor_lookup = mac_vendor_lookup
        self._device_identity_service = device_identity_service
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
                "stop_requested": self._stop_requested.is_set(),
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
        logger.info(
            "Host discovery stage returned results to orchestrator.",
            extra={
                "event": "scan_discovery_results_ready",
                "network_range": network_range,
                "result_count": len(results),
                "stop_requested": self._stop_requested.is_set(),
            },
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
                "stop_requested": self._stop_requested.is_set(),
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
            vendor=vendor or discovered_host.vendor,
            open_ports=[],
            detected_services=[],
            ports_scanned=False,
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
            logger.info(
                "Skipping port scan stage because discovery returned no hosts.",
                extra={
                    "event": "port_stage_skipped_no_hosts",
                    "network_range": network_range,
                    "stop_requested": self._stop_requested.is_set(),
                },
            )
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
                ports_scanned=True,
            )
            updated_host = self._retry_missing_mac_vendor(updated_host)
            updated_host = self._enrich_printer_identity(updated_host)
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

    def _retry_missing_mac_vendor(self, result: ScanResult) -> ScanResult:
        if result.mac_address and result.vendor:
            return result

        mac_address = result.mac_address
        if mac_address is None:
            mac_address = self._mac_address_resolver.resolve_mac_address(
                result.ip_address
            )

        vendor = result.vendor
        if vendor is None:
            vendor = self._mac_vendor_lookup.lookup_vendor(mac_address)

        if mac_address == result.mac_address and vendor == result.vendor:
            return result

        logger.debug(
            "Updated host identity after port scan.",
            extra={
                "event": "post_port_identity_updated",
                "ip_address": result.ip_address,
                "mac_address": mac_address,
                "vendor": vendor,
            },
        )
        return replace(
            result,
            mac_address=mac_address or result.mac_address,
            vendor=vendor or result.vendor,
        )

    def _enrich_printer_identity(self, result: ScanResult) -> ScanResult:
        if self._device_identity_service is None:
            return result
        if not self._is_likely_printer_candidate(result):
            return result

        identity = self._device_identity_service.query_identity(result.ip_address)
        if identity is None or not identity.has_data():
            return result

        updated_services = self._services_with_snmp(result.detected_services)
        hostname = result.hostname or self._hostname_from_identity(identity)
        updated_result = replace(
            result,
            hostname=hostname,
            device_model=identity.device_model or result.device_model,
            serial_number=identity.serial_number or result.serial_number,
            snmp_name=identity.snmp_name or result.snmp_name,
            snmp_description=identity.snmp_description or result.snmp_description,
            snmp_object_id=identity.snmp_object_id or result.snmp_object_id,
            detected_services=updated_services,
        )
        logger.debug(
            "Updated host identity from SNMP.",
            extra={
                "event": "snmp_host_identity_updated",
                "ip_address": result.ip_address,
                "hostname": updated_result.hostname,
                "device_model": updated_result.device_model,
                "serial_number": updated_result.serial_number,
            },
        )
        return updated_result

    def _is_likely_printer_candidate(self, result: ScanResult) -> bool:
        if _PRINTER_PORTS.intersection(result.open_ports):
            return True

        vendor = (result.vendor or "").casefold()
        if vendor and any(term in vendor for term in _PRINTER_VENDOR_TERMS):
            return True

        hostname = (result.hostname or "").casefold()
        if not hostname:
            return False
        if any(term in hostname for term in _PRINTER_HOSTNAME_TERMS):
            return True
        if hostname.startswith("mf") and any(
            character.isdigit() for character in hostname
        ):
            return True
        return hostname.startswith("hp") and any(
            character.isdigit() for character in hostname
        )

    def _services_with_snmp(
        self,
        detected_services: list[ServiceRecord],
    ) -> list[ServiceRecord]:
        if any(
            service.port == 161 and (service.protocol or "").casefold() == "udp"
            for service in detected_services
        ):
            return detected_services

        return [
            *detected_services,
            ServiceRecord(name="SNMP", protocol="udp", port=161),
        ]

    def _hostname_from_identity(self, identity: DeviceIdentity) -> str | None:
        if identity.snmp_name:
            return identity.snmp_name
        if identity.device_model and len(identity.device_model) <= 80:
            return identity.device_model
        return None
