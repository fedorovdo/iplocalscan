from __future__ import annotations

import logging

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
            self.scan_completed.emit(execution)
        except Exception as exc:
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
        self.progress_updated.emit(progress)
