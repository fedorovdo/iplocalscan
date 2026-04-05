from __future__ import annotations

from collections.abc import Callable, Sequence
from threading import Event
from typing import Protocol

from ..core.entities import ScanProgress, ScanResult, ServiceRecord


class HostDiscoveryService(Protocol):
    def discover_hosts(
        self,
        network_range: str,
        *,
        stop_event: Event | None = None,
        on_host_discovered: Callable[[ScanResult], None] | None = None,
        on_progress: Callable[[ScanProgress], None] | None = None,
    ) -> list[ScanResult]:
        ...


class HostnameResolver(Protocol):
    def resolve_hostname(self, ip_address: str) -> str | None:
        ...


class MacAddressResolver(Protocol):
    def resolve_mac_address(self, ip_address: str) -> str | None:
        ...


class PortScanner(Protocol):
    def scan_open_ports(
        self,
        ip_address: str,
        *,
        stop_event: Event | None = None,
    ) -> list[int]:
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
