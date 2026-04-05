from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ..core.entities import ScanResult, ServiceRecord


class HostDiscoveryService(Protocol):
    def discover_hosts(self, network_range: str) -> list[ScanResult]:
        ...


class HostnameResolver(Protocol):
    def resolve_hostname(self, ip_address: str) -> str | None:
        ...


class PortScanner(Protocol):
    def scan_open_ports(self, ip_address: str) -> list[int]:
        ...


class ServiceDetector(Protocol):
    def detect_services(
        self,
        ip_address: str,
        open_ports: Sequence[int],
    ) -> list[ServiceRecord]:
        ...


class MacVendorLookup(Protocol):
    def lookup_vendor(self, mac_address: str | None) -> str | None:
        ...

