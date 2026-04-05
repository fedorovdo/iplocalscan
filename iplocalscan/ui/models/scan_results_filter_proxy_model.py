from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt


class ScanResultsFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._search_text = ""
        self.setDynamicSortFilter(True)
        self.setSortRole(int(Qt.ItemDataRole.UserRole))

    def set_search_text(self, text: str) -> None:
        normalized_text = text.strip().casefold()
        if normalized_text == self._search_text:
            return

        self._search_text = normalized_text
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        if not self._search_text:
            return True

        model = self.sourceModel()
        if model is None or not hasattr(model, "search_text_for_row"):
            return True

        return self._search_text in model.search_text_for_row(source_row)

