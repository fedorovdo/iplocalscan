from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..application.controller import ScanController
from ..config import DEFAULT_HISTORY_LIMIT
from ..localization.manager import LocalizationManager
from .models.scan_results_table_model import ScanResultsTableModel


class HistoryDialog(QDialog):
    def __init__(
        self,
        controller: ScanController,
        localizer: LocalizationManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._localizer = localizer
        self._sessions = []
        self._results_model = ScanResultsTableModel(localizer=localizer, parent=self)

        self._description_label = QLabel(self)
        self._saved_scans_label = QLabel(self)
        self._history_list = QListWidget(self)
        self._preview_label = QLabel(self)
        self._preview_table = QTableView(self)
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            parent=self,
        )

        self._build_ui()
        self._connect_signals()
        self._load_history()
        self._retranslate_ui()

    def _build_ui(self) -> None:
        self.setModal(True)
        self.resize(900, 620)

        self._preview_table.setModel(self._results_model)
        self._preview_table.setSortingEnabled(True)
        self._preview_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._preview_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._preview_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.horizontalHeader().setStretchLastSection(True)
        self._preview_table.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        layout = QVBoxLayout(self)
        layout.addWidget(self._description_label)
        layout.addWidget(self._saved_scans_label)
        layout.addWidget(self._history_list, stretch=2)
        layout.addWidget(self._preview_label)
        layout.addWidget(self._preview_table, stretch=3)
        layout.addWidget(self._button_box)

    def _connect_signals(self) -> None:
        self._history_list.currentRowChanged.connect(self._handle_history_selected)
        self._button_box.rejected.connect(self.reject)
        self._localizer.locale_changed.connect(self._retranslate_ui)

    def _load_history(self) -> None:
        self._sessions = self._controller.list_recent_scans(DEFAULT_HISTORY_LIMIT)
        self._populate_history_list()

    def _populate_history_list(self) -> None:
        current_scan_id = None
        current_item = self._history_list.currentItem()
        if current_item is not None:
            current_scan_id = current_item.data(Qt.ItemDataRole.UserRole)

        self._history_list.clear()
        self._results_model.clear()

        for session in self._sessions:
            started_at = self._format_timestamp(session.started_at)
            status_text = self._localizer.text(f"status.scan.{session.status.value}")
            item_text = self._localizer.text(
                "history.scan_item",
                started_at=started_at,
                network_range=session.network_range,
                status=status_text,
                result_count=session.result_count,
            )
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, session.id)
            self._history_list.addItem(item)

        if not self._sessions:
            self._description_label.setText(self._localizer.text("history.empty"))
            return

        self._description_label.setText(
            self._localizer.text(
                "history.description",
                limit=DEFAULT_HISTORY_LIMIT,
            )
        )

        for row_index in range(self._history_list.count()):
            list_item = self._history_list.item(row_index)
            if list_item.data(Qt.ItemDataRole.UserRole) == current_scan_id:
                self._history_list.setCurrentRow(row_index)
                break
        else:
            self._history_list.setCurrentRow(0)

    def _handle_history_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._sessions):
            self._results_model.clear()
            return

        selected_session = self._sessions[row]
        if selected_session.id is None:
            self._results_model.clear()
            return

        scan_results = self._controller.list_results_for_scan(selected_session.id)
        self._results_model.set_results(scan_results)
        header = self._preview_table.horizontalHeader()
        self._results_model.sort(
            header.sortIndicatorSection(),
            header.sortIndicatorOrder(),
        )

    def _retranslate_ui(self, _locale_code: str | None = None) -> None:
        self.setWindowTitle(self._localizer.text("history.title"))
        self._saved_scans_label.setText(
            self._localizer.text("history.saved_scans_label")
        )
        self._preview_label.setText(self._localizer.text("history.preview_label"))
        self._button_box.button(QDialogButtonBox.StandardButton.Close).setText(
            self._localizer.text("history.close_button")
        )
        self._populate_history_list()

    def _format_timestamp(self, timestamp: datetime) -> str:
        return timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S")
