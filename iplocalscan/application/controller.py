from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QThread, Signal

from ..config import DEFAULT_HISTORY_LIMIT
from ..core.entities import ScanExecutionResult, ScanProgress, ScanResult, ScanSession
from ..core.enums import ChangeStatus, ScanLifecycleStatus, ScanStage
from ..core.networking import normalize_network_range
from ..persistence.repositories import ScanResultRepository, ScanSessionRepository
from .scan_comparison import ScanComparisonService
from .scan_orchestrator import ScanOrchestrator
from .scan_worker import ScanWorker

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class StatusEvent:
    key: str
    params: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class StageEvent:
    key: str
    params: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ProgressEvent:
    minimum: int = 0
    maximum: int = 1
    value: int = 0
    indeterminate: bool = False
    detail_key: str | None = None
    params: dict[str, object] = field(default_factory=dict)


class ScanController(QObject):
    status_event = Signal(object)
    stage_event = Signal(object)
    progress_event = Signal(object)
    results_replaced = Signal(object)
    result_discovered = Signal(object)
    busy_state_changed = Signal(bool)

    def __init__(
        self,
        orchestrator: ScanOrchestrator,
        session_repository: ScanSessionRepository,
        result_repository: ScanResultRepository,
        comparison_service: ScanComparisonService | None = None,
    ) -> None:
        super().__init__()
        self._orchestrator = orchestrator
        self._session_repository = session_repository
        self._result_repository = result_repository
        self._comparison_service = comparison_service or ScanComparisonService()
        self._busy = False
        self._current_session: ScanSession | None = None
        self._current_results: list[ScanResult] = []
        self._baseline_results: list[ScanResult] = []
        self._baseline_results_by_ip: dict[str, ScanResult] = {}
        self._last_stage: ScanStage | None = None
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
        self._load_comparison_baseline(normalized_range)
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
        self._emit_stage("progress.stage.discovery")
        self._emit_progress(
            indeterminate=True,
            detail_key="progress.detail.starting",
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
        baseline_result = self._baseline_results_by_ip.get(result.ip_address)
        compared_result = self._comparison_service.classify_result(
            replace(result, scan_id=session_id),
            baseline_result,
        )
        self._upsert_current_result(compared_result)
        self.result_discovered.emit(compared_result)
        logger.debug(
            "Result updated during scan.",
            extra={
                "event": "scan_result_updated",
                "scan_id": session_id,
                "ip_address": compared_result.ip_address,
                "hostname": compared_result.hostname,
                "mac_address": compared_result.mac_address,
                "vendor": compared_result.vendor,
                "change_status": compared_result.change_status.value,
                "open_ports": compared_result.open_ports,
                "service_count": len(compared_result.detected_services),
            },
        )

    def _handle_progress_updated(self, progress: ScanProgress) -> None:
        if progress.stage is not self._last_stage:
            self._last_stage = progress.stage
            if progress.stage is ScanStage.DISCOVERY:
                self._emit_stage("progress.stage.discovery")
            else:
                self._emit_stage("progress.stage.port_scan")

        if progress.stage is ScanStage.DISCOVERY:
            discovery_maximum = max(progress.total_hosts, 1)
            self._emit_progress(
                minimum=0,
                maximum=discovery_maximum,
                value=min(progress.completed_hosts, discovery_maximum),
                indeterminate=progress.total_hosts <= 0,
                detail_key="progress.detail.discovery",
                completed_hosts=progress.completed_hosts,
                total_hosts=progress.total_hosts,
                discovered_hosts=progress.discovered_hosts,
            )
            self._emit_status(
                "status.scan_progress.discovery",
                network_range=progress.network_range,
                completed_hosts=progress.completed_hosts,
                total_hosts=progress.total_hosts,
                discovered_hosts=progress.discovered_hosts,
            )
            return

        port_scan_maximum = max(progress.total_hosts, 1)
        self._emit_progress(
            minimum=0,
            maximum=port_scan_maximum,
            value=min(progress.completed_hosts, port_scan_maximum),
            indeterminate=progress.total_hosts <= 0,
            detail_key="progress.detail.ports",
            completed_hosts=progress.completed_hosts,
            total_hosts=progress.total_hosts,
            hosts_with_open_ports=progress.discovered_hosts,
            current_ip=progress.current_ip or "",
        )
        self._emit_status(
            "status.scan_progress.ports",
            completed_hosts=progress.completed_hosts,
            total_hosts=progress.total_hosts,
            current_ip=progress.current_ip or "",
            hosts_with_open_ports=progress.discovered_hosts,
        )

    def _handle_scan_completed(self, execution: ScanExecutionResult) -> None:
        self._emit_stage("progress.stage.finalizing")
        self._emit_progress(
            indeterminate=True,
            detail_key="progress.detail.finalizing",
        )
        if execution.status is ScanLifecycleStatus.COMPLETED:
            self._append_missing_results()

        result_count, persisted = self._persist_results(
            status=execution.status,
            note=execution.note,
            results=self._current_results,
        )
        session = self._current_session
        network_range = session.network_range if session is not None else ""

        if not persisted:
            self._emit_stage("progress.stage.failed")
            self._emit_progress(
                minimum=0,
                maximum=1,
                value=0,
                indeterminate=False,
                detail_key="progress.detail.failed",
                reason="Database write failed.",
            )
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
            self._emit_stage("progress.stage.stopped")
            self._emit_progress(
                minimum=0,
                maximum=1,
                value=0,
                indeterminate=False,
                detail_key="progress.detail.stopped",
                result_count=result_count,
            )
            self._emit_status(
                "status.scan_stopped",
                network_range=network_range,
                result_count=result_count,
            )
        else:
            self._emit_stage("progress.stage.completed")
            self._emit_progress(
                minimum=0,
                maximum=1,
                value=1,
                indeterminate=False,
                detail_key="progress.detail.completed",
                result_count=result_count,
            )
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
        self._reset_runtime_state()

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
        self._emit_stage("progress.stage.failed")
        self._emit_progress(
            minimum=0,
            maximum=1,
            value=0,
            indeterminate=False,
            detail_key="progress.detail.failed",
            reason=reason,
        )
        self._emit_status("status.scan_failed", reason=reason)
        self._reset_runtime_state()

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
        active_result_count = sum(
            1
            for result in persisted_results
            if result.change_status is not ChangeStatus.REMOVED
        )

        try:
            self._result_repository.replace_for_scan(session.id, persisted_results)
            self._session_repository.finalize(
                session_id=session.id,
                status=status,
                finished_at=datetime.now(timezone.utc),
                result_count=active_result_count,
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
            return active_result_count, False

        return active_result_count, True

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

    def _emit_stage(self, key: str, **params: object) -> None:
        self.stage_event.emit(StageEvent(key=key, params=params))

    def _emit_progress(
        self,
        *,
        minimum: int = 0,
        maximum: int = 1,
        value: int = 0,
        indeterminate: bool = False,
        detail_key: str | None = None,
        **params: object,
    ) -> None:
        if not indeterminate:
            safe_maximum = max(maximum, minimum + 1)
            safe_value = min(max(value, minimum), safe_maximum)
        else:
            safe_maximum = maximum
            safe_value = value

        self.progress_event.emit(
            ProgressEvent(
                minimum=minimum,
                maximum=safe_maximum,
                value=safe_value,
                indeterminate=indeterminate,
                detail_key=detail_key,
                params=params,
            )
        )

    def _load_comparison_baseline(self, network_range: str) -> None:
        self._baseline_results = []
        self._baseline_results_by_ip = {}

        try:
            baseline_session = self._session_repository.get_latest_completed_for_network(
                network_range
            )
            if baseline_session is None or baseline_session.id is None:
                return

            baseline_results = self._result_repository.list_for_scan(baseline_session.id)
            self._baseline_results = self._comparison_service.prepare_baseline(
                baseline_results
            )
            self._baseline_results_by_ip = {
                result.ip_address: result for result in self._baseline_results
            }
            logger.info(
                "Loaded comparison baseline for scan.",
                extra={
                    "event": "scan_comparison_baseline_loaded",
                    "network_range": network_range,
                    "baseline_scan_id": baseline_session.id,
                    "baseline_result_count": len(self._baseline_results),
                },
            )
        except Exception:
            logger.exception(
                "Failed to load comparison baseline.",
                extra={
                    "event": "scan_comparison_baseline_failed",
                    "network_range": network_range,
                },
            )

    def _append_missing_results(self) -> None:
        if not self._baseline_results:
            return

        session_id = self._current_session.id if self._current_session else None
        missing_results = self._comparison_service.build_missing_results(
            self._current_results,
            self._baseline_results,
        )
        for missing_result in missing_results:
            current_missing = replace(missing_result, scan_id=session_id)
            self._upsert_current_result(current_missing)
            self.result_discovered.emit(current_missing)

    def _reset_runtime_state(self) -> None:
        self._current_session = None
        self._baseline_results = []
        self._baseline_results_by_ip = {}
        self._last_stage = None
        self._set_busy(False)
