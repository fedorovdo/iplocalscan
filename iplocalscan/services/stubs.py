from __future__ import annotations

from collections.abc import Sequence

from ..core.entities import ScanResult, ServiceRecord


class StubHostDiscoveryService:
    """Placeholder host discovery implementation for the first scaffold step."""

    def discover_hosts(self, network_range: str) -> list[ScanResult]:
        _ = network_range
        return []


class StubHostnameResolver:
    def resolve_hostname(self, ip_address: str) -> str | None:
        _ = ip_address
        return None


class StubPortScanner:
    def scan_open_ports(self, ip_address: str) -> list[int]:
        _ = ip_address
        return []


class StubServiceDetector:
    def detect_services(
        self,
        ip_address: str,
        open_ports: Sequence[int],
    ) -> list[ServiceRecord]:
        _ = ip_address
        _ = open_ports
        return []


class StubMacVendorLookup:
    def lookup_vendor(self, mac_address: str | None) -> str | None:
        _ = mac_address
        return None

