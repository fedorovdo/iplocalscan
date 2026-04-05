from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import replace

from ..core.entities import ScanResult, ServiceRecord
from ..core.enums import ChangeStatus, HostStatus
from ..core.mac import normalize_mac_address

logger = logging.getLogger(__name__)


class ScanComparisonService:
    """Compares the current scan against a previous stored baseline."""

    def prepare_baseline(self, results: Sequence[ScanResult]) -> list[ScanResult]:
        prepared_results = [
            result
            for result in results
            if result.change_status is not ChangeStatus.REMOVED
        ]
        logger.info(
            "Prepared scan comparison baseline.",
            extra={
                "event": "scan_comparison_baseline_prepared",
                "input_count": len(results),
                "baseline_count": len(prepared_results),
            },
        )
        return prepared_results

    def classify_result(
        self,
        current_result: ScanResult,
        previous_result: ScanResult | None,
    ) -> ScanResult:
        if previous_result is None:
            return replace(current_result, change_status=ChangeStatus.NEW)

        if self._result_has_changed(current_result, previous_result):
            return replace(current_result, change_status=ChangeStatus.CHANGED)

        return replace(current_result, change_status=ChangeStatus.UNCHANGED)

    def build_missing_results(
        self,
        current_results: Sequence[ScanResult],
        baseline_results: Sequence[ScanResult],
    ) -> list[ScanResult]:
        current_ips = {
            result.ip_address
            for result in current_results
            if result.change_status is not ChangeStatus.REMOVED
        }
        missing_results: list[ScanResult] = []

        for baseline_result in baseline_results:
            if baseline_result.ip_address in current_ips:
                continue

            missing_results.append(
                replace(
                    baseline_result,
                    status=HostStatus.DOWN,
                    change_status=ChangeStatus.REMOVED,
                )
            )

        logger.info(
            "Compared scan results against baseline.",
            extra={
                "event": "scan_comparison_completed",
                "current_count": len(current_results),
                "baseline_count": len(baseline_results),
                "missing_count": len(missing_results),
            },
        )
        return missing_results

    def _result_has_changed(
        self,
        current_result: ScanResult,
        previous_result: ScanResult,
    ) -> bool:
        if self._normalized_mac(current_result) != self._normalized_mac(previous_result):
            return True
        if (current_result.vendor or "").casefold() != (
            previous_result.vendor or ""
        ).casefold():
            return True
        if (current_result.hostname or "").casefold() != (
            previous_result.hostname or ""
        ).casefold():
            return True
        if current_result.status is not previous_result.status:
            return True
        if not current_result.ports_scanned:
            return False
        if tuple(sorted(current_result.open_ports)) != tuple(
            sorted(previous_result.open_ports)
        ):
            return True
        return self._service_signature(current_result.detected_services) != (
            self._service_signature(previous_result.detected_services)
        )

    def _normalized_mac(self, result: ScanResult) -> str:
        return normalize_mac_address(result.mac_address) or ""

    def _service_signature(
        self,
        services: Sequence[ServiceRecord],
    ) -> tuple[tuple[int, str, str], ...]:
        return tuple(
            sorted(
                (
                    service.port or -1,
                    (service.protocol or "").casefold(),
                    service.name.casefold(),
                )
                for service in services
            )
        )
