from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from PySide6.QtCore import QObject, Signal

from ..config import DEFAULT_HISTORY_LIMIT
from ..core.entities import ScanSession
from ..core.enums import ScanLifecycleStatus
from ..core.networking import normalize_network_range
from ..persistence.repositories import ScanResultRepository, ScanSessionRepository
from .scan_orchestrator import ScanOrchestrator


@dataclass(slots=True)
class StatusEvent:
    key: str
    params: dict[str, object] = field(default_factory=dict)


class ScanController(QObject):
    status_event = Signal(object)
    results_replaced = Signal(object)
    busy_state_changed = Signal(bool)

    def __init__(
        self,
        orchestrator: ScanOrchestrator,
        session_repository: ScanSessionRepository,
        result_repository: ScanResultRepository,
    ) -> None:
        super().__init__()
        self._orchestrator = orchestrator
        self._session_repository = session_repository
        self._result_repository = result_repository
        self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    def start_scan(self, network_range: str) -> None:
        if self._busy:
            self._emit_status("status.scan_already_running")
            return

        try:
            normalized_range = normalize_network_range(network_range)
        except ValueError:
            self._emit_status(
                "status.invalid_network",
                example="192.168.1.0/24",
            )
            return

        self._set_busy(True)
        self._emit_status(
            "status.scan_started",
            network_range=normalized_range,
        )

        session = self._session_repository.create(
            ScanSession(
                network_range=normalized_range,
                started_at=datetime.now(timezone.utc),
                status=ScanLifecycleStatus.RUNNING,
            )
        )

        try:
            self._orchestrator.clear_stop_request()
            execution = self._orchestrator.execute(normalized_range)
            if session.id is None:
                raise RuntimeError("A persisted scan session id was expected.")

            results = [
                replace(scan_result, scan_id=session.id)
                for scan_result in execution.results
            ]

            self._result_repository.replace_for_scan(session.id, results)
            self._session_repository.finalize(
                session_id=session.id,
                status=execution.status,
                finished_at=datetime.now(timezone.utc),
                result_count=len(results),
                note=execution.note,
            )
            self._session_repository.trim_history(DEFAULT_HISTORY_LIMIT)

            self.results_replaced.emit(results)
            if execution.status is ScanLifecycleStatus.STOPPED:
                self._emit_status(
                    "status.scan_stopped",
                    network_range=normalized_range,
                    result_count=len(results),
                )
            else:
                self._emit_status(
                    "status.scan_completed_stub",
                    network_range=normalized_range,
                    result_count=len(results),
                )
        except Exception as exc:
            if session.id is not None:
                self._session_repository.finalize(
                    session_id=session.id,
                    status=ScanLifecycleStatus.FAILED,
                    finished_at=datetime.now(timezone.utc),
                    result_count=0,
                    note=str(exc),
                )
            self.results_replaced.emit([])
            self._emit_status("status.scan_failed", reason=str(exc))
        finally:
            self._set_busy(False)

    def request_stop(self) -> None:
        if not self._busy:
            self._emit_status("status.no_active_scan")
            return

        self._orchestrator.request_stop()
        self._emit_status("status.stop_requested")

    def list_recent_scans(self, limit: int = DEFAULT_HISTORY_LIMIT) -> list[ScanSession]:
        return self._session_repository.list_recent(limit=limit)

    def list_results_for_scan(self, scan_id: int) -> list:
        return self._result_repository.list_for_scan(scan_id)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.busy_state_changed.emit(busy)

    def _emit_status(self, key: str, **params: object) -> None:
        self.status_event.emit(StatusEvent(key=key, params=params))

