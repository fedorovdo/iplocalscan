from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QThread, Signal

from ..config import DEFAULT_HISTORY_LIMIT
from ..core.entities import ScanExecutionResult, ScanProgress, ScanResult, ScanSession
from ..core.enums import ScanLifecycleStatus, ScanStage
from ..core.networking import normalize_network_range
from ..persistence.repositories import ScanResultRepository, ScanSessionRepository
from .scan_orchestrator import ScanOrchestrator
from .scan_worker import ScanWorker

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class StatusEvent:
    key: str
    params: dict[str, object] = field(default_factory=dict)


class ScanController(QObject):
    status_event = Signal(object)
    results_replaced = Signal(object)
    result_discovered = Signal(object)
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
        self._current_session: ScanSession | None = None
        self._current_results: list[ScanResult] = []
        self._scan_thread: QThread | None = None
        self._scan_worker: ScanWorker | None = None

    @property
    def is_busy(self) -> bool:
        return self._busy

    def start_scan(self, network_range: str) -> None:
        if self._busy:
            self._emit_status("status.scan_already_running")
            return
        if self._scan_thread is not None and self._scan_thread.isRunning():
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
        self._orchestrator.clear_stop_request()
        self._current_results = []
        self.results_replaced.emit([])

        try:
            session = self._session_repository.create(
                ScanSession(
                    network_range=normalized_range,
                    started_at=datetime.now(timezone.utc),
                    status=ScanLifecycleStatus.RUNNING,
                )
            )
        except Exception as exc:
            logger.exception(
                "Failed to create scan session.",
                extra={
                    "event": "scan_session_create_failed",
                    "network_range": normalized_range,
                },
            )
            self._set_busy(False)
            self._emit_status("status.scan_failed", reason=str(exc))
            return

        self._current_session = session
        self._emit_status(
            "status.scan_started",
            network_range=normalized_range,
        )
        logger.info(
            "Scan started.",
            extra={
                "event": "scan_started",
                "network_range": normalized_range,
                "scan_id": session.id,
            },
        )
        self._start_worker(normalized_range)

    def request_stop(self) -> None:
        if not self._busy:
            self._emit_status("status.no_active_scan")
            return

        self._orchestrator.request_stop()
        self._emit_status("status.stop_requested")
        logger.info(
            "Stop requested for active scan.",
            extra={
                "event": "scan_stop_requested",
                "scan_id": self._current_session.id if self._current_session else None,
            },
        )

    def list_recent_scans(self, limit: int = DEFAULT_HISTORY_LIMIT) -> list[ScanSession]:
        return self._session_repository.list_recent(limit=limit)

    def list_results_for_scan(self, scan_id: int) -> list[ScanResult]:
        return self._result_repository.list_for_scan(scan_id)

    def _start_worker(self, network_range: str) -> None:
        self._scan_thread = QThread(self)
        self._scan_worker = ScanWorker(
            orchestrator=self._orchestrator,
            network_range=network_range,
        )
        self._scan_worker.moveToThread(self._scan_thread)

        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.result_discovered.connect(self._handle_result_discovered)
        self._scan_worker.progress_updated.connect(self._handle_progress_updated)
        self._scan_worker.scan_completed.connect(self._handle_scan_completed)
        self._scan_worker.scan_failed.connect(self._handle_scan_failed)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_worker.finished.connect(self._scan_worker.deleteLater)
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)
        self._scan_thread.finished.connect(self._handle_thread_finished)
        self._scan_thread.start()

    def _handle_result_discovered(self, result: ScanResult) -> None:
        session_id = self._current_session.id if self._current_session else None
        persisted_result = replace(result, scan_id=session_id)
        self._upsert_current_result(persisted_result)
        self.result_discovered.emit(persisted_result)
        logger.info(
            "Result updated during scan.",
            extra={
                "event": "scan_result_updated",
                "scan_id": session_id,
                "ip_address": persisted_result.ip_address,
                "hostname": persisted_result.hostname,
                "mac_address": persisted_result.mac_address,
                "open_ports": persisted_result.open_ports,
                "service_count": len(persisted_result.detected_services),
            },
        )

    def _handle_progress_updated(self, progress: ScanProgress) -> None:
        if progress.stage is ScanStage.DISCOVERY:
            self._emit_status(
                "status.scan_progress.discovery",
                network_range=progress.network_range,
                completed_hosts=progress.completed_hosts,
                total_hosts=progress.total_hosts,
                discovered_hosts=progress.discovered_hosts,
            )
            return

        self._emit_status(
            "status.scan_progress.ports",
            completed_hosts=progress.completed_hosts,
            total_hosts=progress.total_hosts,
            current_ip=progress.current_ip or "",
            hosts_with_open_ports=progress.discovered_hosts,
        )

    def _handle_scan_completed(self, execution: ScanExecutionResult) -> None:
        result_count, persisted = self._persist_results(
            status=execution.status,
            note=execution.note,
            results=execution.results,
        )
        session = self._current_session
        network_range = session.network_range if session is not None else ""

        if not persisted:
            self._emit_status("status.scan_failed", reason="Database write failed.")
            logger.error(
                "Scan completed but persistence failed.",
                extra={
                    "event": "scan_completed_persist_failed",
                    "scan_id": session.id if session else None,
                    "network_range": network_range,
                },
            )
            self._current_session = None
            self._set_busy(False)
            return

        if execution.status is ScanLifecycleStatus.STOPPED:
            self._emit_status(
                "status.scan_stopped",
                network_range=network_range,
                result_count=result_count,
            )
        else:
            self._emit_status(
                "status.scan_completed",
                network_range=network_range,
                result_count=result_count,
            )

        logger.info(
            "Scan completed.",
            extra={
                "event": "scan_completed",
                "scan_id": session.id if session else None,
                "network_range": network_range,
                "status": execution.status.value,
                "result_count": result_count,
            },
        )
        self._current_session = None
        self._set_busy(False)

    def _handle_scan_failed(self, reason: str) -> None:
        session = self._current_session
        network_range = session.network_range if session is not None else None
        logger.error(
            "Scan failed.",
            extra={
                "event": "scan_failed",
                "scan_id": session.id if session else None,
                "network_range": network_range,
                "reason": reason,
            },
        )
        _, persisted = self._persist_results(
            status=ScanLifecycleStatus.FAILED,
            note=reason,
            results=self._current_results,
        )
        if not persisted:
            reason = "Database write failed."
        self._emit_status("status.scan_failed", reason=reason)
        self._current_session = None
        self._set_busy(False)

    def _persist_results(
        self,
        *,
        status: ScanLifecycleStatus,
        note: str | None,
        results: list[ScanResult],
    ) -> tuple[int, bool]:
        session = self._current_session
        if session is None or session.id is None:
            logger.warning(
                "Skipping scan persistence because the session is missing.",
                extra={"event": "scan_persist_skipped"},
            )
            return 0, False

        persisted_results = [
            replace(result, scan_id=session.id)
            for result in results
        ]
        self._current_results = persisted_results

        try:
            self._result_repository.replace_for_scan(session.id, persisted_results)
            self._session_repository.finalize(
                session_id=session.id,
                status=status,
                finished_at=datetime.now(timezone.utc),
                result_count=len(persisted_results),
                note=note,
            )
            self._session_repository.trim_history(DEFAULT_HISTORY_LIMIT)
        except Exception:
            logger.exception(
                "Failed to persist scan results.",
                extra={
                    "event": "scan_persist_failed",
                    "scan_id": session.id,
                    "status": status.value,
                },
            )
            return len(persisted_results), False

        return len(persisted_results), True

    def _upsert_current_result(self, updated_result: ScanResult) -> None:
        for index, existing_result in enumerate(self._current_results):
            if (
                existing_result.scan_id == updated_result.scan_id
                and existing_result.ip_address == updated_result.ip_address
            ):
                self._current_results[index] = updated_result
                return

        self._current_results.append(updated_result)

    def _handle_thread_finished(self) -> None:
        finished_thread = self.sender()
        if finished_thread is self._scan_thread:
            self._scan_worker = None
            self._scan_thread = None

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.busy_state_changed.emit(busy)

    def _emit_status(self, key: str, **params: object) -> None:
        self.status_event.emit(StatusEvent(key=key, params=params))
