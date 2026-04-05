from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .enums import HostStatus, ScanLifecycleStatus


@dataclass(slots=True)
class ServiceRecord:
    name: str
    protocol: str | None = None
    port: int | None = None


@dataclass(slots=True)
class ScanResult:
    ip_address: str
    mac_address: str | None = None
    mac_vendor: str | None = None
    hostname: str | None = None
    status: HostStatus = HostStatus.UNKNOWN
    open_ports: list[int] = field(default_factory=list)
    detected_services: list[ServiceRecord] = field(default_factory=list)
    scan_id: int | None = None


@dataclass(slots=True)
class ScanSession:
    network_range: str
    started_at: datetime
    status: ScanLifecycleStatus
    id: int | None = None
    finished_at: datetime | None = None
    result_count: int = 0
    note: str | None = None


@dataclass(slots=True)
class ScanExecutionResult:
    results: list[ScanResult] = field(default_factory=list)
    status: ScanLifecycleStatus = ScanLifecycleStatus.COMPLETED
    note: str | None = None


@dataclass(slots=True)
class ScanProgress:
    network_range: str
    total_hosts: int
    scanned_hosts: int
    discovered_hosts: int
    current_ip: str | None = None
