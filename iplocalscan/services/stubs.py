from __future__ import annotations

from collections.abc import Sequence
from threading import Event
from typing import Callable

from ..core.entities import ScanProgress, ScanResult, ServiceRecord


class StubHostDiscoveryService:
    """Placeholder host discovery implementation for the first scaffold step."""

    def discover_hosts(
        self,
        network_range: str,
        *,
        stop_event: Event | None = None,
        on_host_discovered: Callable[[ScanResult], None] | None = None,
        on_progress: Callable[[ScanProgress], None] | None = None,
    ) -> list[ScanResult]:
        _ = network_range
        _ = stop_event
        _ = on_host_discovered
        _ = on_progress
        return []


class StubHostnameResolver:
    def resolve_hostname(self, ip_address: str) -> str | None:
        _ = ip_address
        return None


class StubMacAddressResolver:
    def resolve_mac_address(self, ip_address: str) -> str | None:
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
