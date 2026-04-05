from __future__ import annotations

from enum import StrEnum


class HostStatus(StrEnum):
    UNKNOWN = "unknown"
    UP = "up"
    DOWN = "down"

    @property
    def sort_order(self) -> int:
        return {
            HostStatus.UP: 0,
            HostStatus.UNKNOWN: 1,
            HostStatus.DOWN: 2,
        }[self]


class ScanLifecycleStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class ScanStage(StrEnum):
    DISCOVERY = "discovery"
    PORT_SCAN = "port_scan"
