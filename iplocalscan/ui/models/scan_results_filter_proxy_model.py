from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt

from ...core.enums import HostStatus


class ScanResultsFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._search_text = ""
        self._online_only = False
        self._has_open_ports_only = False
        self._has_services_only = False
        self.setDynamicSortFilter(True)
        self.setSortRole(int(Qt.ItemDataRole.UserRole))

    def set_search_text(self, text: str) -> None:
        normalized_text = text.strip().casefold()
        if normalized_text == self._search_text:
            return

        self._search_text = normalized_text
        self.invalidateFilter()

    def set_online_only(self, enabled: bool) -> None:
        if enabled == self._online_only:
            return

        self._online_only = enabled
        self.invalidateFilter()

    def set_has_open_ports_only(self, enabled: bool) -> None:
        if enabled == self._has_open_ports_only:
            return

        self._has_open_ports_only = enabled
        self.invalidateFilter()

    def set_has_services_only(self, enabled: bool) -> None:
        if enabled == self._has_services_only:
            return

        self._has_services_only = enabled
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        model = self.sourceModel()
        if (
            model is None
            or not hasattr(model, "search_text_for_row")
            or not hasattr(model, "result_at")
        ):
            return True

        result = model.result_at(source_row)
        if result is None:
            return True
        if self._online_only and result.status is not HostStatus.UP:
            return False
        if self._has_open_ports_only and not result.open_ports:
            return False
        if self._has_services_only and not result.detected_services:
            return False
        if not self._search_text:
            return True

        return self._search_text in model.search_text_for_row(source_row)

    def lessThan(self, left, right) -> bool:
        left_value = left.data(self.sortRole())
        right_value = right.data(self.sortRole())

        try:
            return left_value < right_value
        except TypeError:
            return str(left_value) < str(right_value)
