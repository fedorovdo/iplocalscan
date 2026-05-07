from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .enums import ChangeStatus, HostStatus, ScanLifecycleStatus, ScanStage


@dataclass(slots=True)
class ServiceRecord:
    name: str
    protocol: str | None = None
    port: int | None = None


@dataclass(slots=True)
class DeviceIdentity:
    device_model: str | None = None
    serial_number: str | None = None
    snmp_name: str | None = None
    snmp_description: str | None = None
    snmp_object_id: str | None = None

    def has_data(self) -> bool:
        return any(
            (
                self.device_model,
                self.serial_number,
                self.snmp_name,
                self.snmp_description,
                self.snmp_object_id,
            )
        )


@dataclass(slots=True)
class ScanResult:
    ip_address: str
    mac_address: str | None = None
    vendor: str | None = None
    hostname: str | None = None
    device_model: str | None = None
    serial_number: str | None = None
    snmp_name: str | None = None
    snmp_description: str | None = None
    snmp_object_id: str | None = None
    status: HostStatus = HostStatus.UNKNOWN
    change_status: ChangeStatus = ChangeStatus.UNCHANGED
    open_ports: list[int] = field(default_factory=list)
    detected_services: list[ServiceRecord] = field(default_factory=list)
    ports_scanned: bool = False
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
    stage: ScanStage
    total_hosts: int
    completed_hosts: int
    discovered_hosts: int = 0
    current_ip: str | None = None
