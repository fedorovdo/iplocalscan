from __future__ import annotations

import logging
import time

from PySide6.QtCore import QObject, Signal, Slot

from .scan_orchestrator import ScanOrchestrator
from ..core.entities import ScanProgress, ScanResult

logger = logging.getLogger(__name__)


class ScanWorker(QObject):
    result_discovered = Signal(object)
    progress_updated = Signal(object)
    scan_completed = Signal(object)
    scan_failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        orchestrator: ScanOrchestrator,
        network_range: str,
    ) -> None:
        super().__init__()
        self._orchestrator = orchestrator
        self._network_range = network_range
        self._pending_progress: ScanProgress | None = None
        self._last_progress_flush = 0.0
        self._last_progress_stage = None
        self._progress_flush_interval_seconds = 0.15

    @Slot()
    def run(self) -> None:
        logger.info(
            "Starting background scan worker.",
            extra={
                "event": "scan_worker_started",
                "network_range": self._network_range,
            },
        )
        try:
            execution = self._orchestrator.execute(
                self._network_range,
                on_result_discovered=self._emit_result_discovered,
                on_progress_updated=self._emit_progress_updated,
            )
            self._flush_pending_progress_update()
            self.scan_completed.emit(execution)
        except Exception as exc:
            self._flush_pending_progress_update()
            logger.exception(
                "Background scan worker failed.",
                extra={
                    "event": "scan_worker_failed",
                    "network_range": self._network_range,
                },
            )
            self.scan_failed.emit(str(exc))
        finally:
            self.finished.emit()

    def _emit_result_discovered(self, result: ScanResult) -> None:
        self.result_discovered.emit(result)

    def _emit_progress_updated(self, progress: ScanProgress) -> None:
        self._pending_progress = progress
        now = time.monotonic()
        stage_changed = progress.stage is not self._last_progress_stage
        stage_complete = progress.completed_hosts >= progress.total_hosts
        interval_elapsed = (
            now - self._last_progress_flush >= self._progress_flush_interval_seconds
        )
        if stage_changed or stage_complete or interval_elapsed:
            self._flush_pending_progress_update(now=now)

    def _flush_pending_progress_update(self, *, now: float | None = None) -> None:
        if self._pending_progress is None:
            return

        progress = self._pending_progress
        self.progress_updated.emit(progress)
        self._pending_progress = None
        self._last_progress_stage = progress.stage
        self._last_progress_flush = now if now is not None else time.monotonic()
