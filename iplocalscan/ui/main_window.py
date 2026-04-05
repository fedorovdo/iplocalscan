from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..application.controller import ScanController, StatusEvent
from ..config import DEFAULT_WINDOW_HEIGHT, DEFAULT_WINDOW_WIDTH
from ..localization.manager import LocalizationManager
from .history_dialog import HistoryDialog
from .models.scan_results_filter_proxy_model import ScanResultsFilterProxyModel
from .models.scan_results_table_model import ScanResultsTableModel


class MainWindow(QMainWindow):
    def __init__(
        self,
        controller: ScanController,
        localizer: LocalizationManager,
    ) -> None:
        super().__init__()
        self._controller = controller
        self._localizer = localizer

        self._results_model = ScanResultsTableModel(localizer=localizer, parent=self)
        self._proxy_model = ScanResultsFilterProxyModel(parent=self)
        self._proxy_model.setSourceModel(self._results_model)

        self._network_label = QLabel(self)
        self._network_input = QLineEdit(self)
        self._scan_button = QPushButton(self)
        self._stop_button = QPushButton(self)
        self._history_button = QPushButton(self)
        self._filter_label = QLabel(self)
        self._filter_input = QLineEdit(self)
        self._online_only_checkbox = QCheckBox(self)
        self._has_open_ports_checkbox = QCheckBox(self)
        self._has_services_checkbox = QCheckBox(self)
        self._results_table = QTableView(self)

        self._build_ui()
        self._connect_signals()
        self._retranslate_ui()
        self._set_busy_state(False)
        self.statusBar().showMessage(self._localizer.text("status.ready"))

    def _build_ui(self) -> None:
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self._results_table.setModel(self._proxy_model)
        self._results_table.setSortingEnabled(True)
        self._results_table.setAlternatingRowColors(True)
        self._results_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._results_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._results_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._results_table.horizontalHeader().setStretchLastSection(True)
        self._results_table.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        layout = QVBoxLayout(central_widget)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self._network_label)
        controls_layout.addWidget(self._network_input, stretch=1)
        controls_layout.addWidget(self._scan_button)
        controls_layout.addWidget(self._stop_button)
        controls_layout.addWidget(self._history_button)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self._filter_label)
        filter_layout.addWidget(self._filter_input, stretch=1)
        filter_layout.addWidget(self._online_only_checkbox)
        filter_layout.addWidget(self._has_open_ports_checkbox)
        filter_layout.addWidget(self._has_services_checkbox)

        layout.addLayout(controls_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self._results_table, stretch=1)

    def _connect_signals(self) -> None:
        self._scan_button.clicked.connect(self._handle_scan_clicked)
        self._stop_button.clicked.connect(self._controller.request_stop)
        self._history_button.clicked.connect(self._open_history_dialog)
        self._filter_input.textChanged.connect(self._proxy_model.set_search_text)
        self._online_only_checkbox.toggled.connect(self._proxy_model.set_online_only)
        self._has_open_ports_checkbox.toggled.connect(
            self._proxy_model.set_has_open_ports_only
        )
        self._has_services_checkbox.toggled.connect(
            self._proxy_model.set_has_services_only
        )
        self._network_input.returnPressed.connect(self._handle_scan_clicked)

        self._controller.status_event.connect(self._show_status_event)
        self._controller.results_replaced.connect(self._results_model.set_results)
        self._controller.result_discovered.connect(self._results_model.upsert_result)
        self._controller.busy_state_changed.connect(self._set_busy_state)
        self._localizer.locale_changed.connect(self._retranslate_ui)

    def _handle_scan_clicked(self) -> None:
        self._controller.start_scan(self._network_input.text())

    def _open_history_dialog(self) -> None:
        dialog = HistoryDialog(
            controller=self._controller,
            localizer=self._localizer,
            parent=self,
        )
        dialog.exec()

    def _show_status_event(self, event: StatusEvent) -> None:
        self.statusBar().showMessage(self._localizer.text(event.key, **event.params))

    def _set_busy_state(self, busy: bool) -> None:
        self._scan_button.setEnabled(not busy)
        self._stop_button.setEnabled(busy)
        self._history_button.setEnabled(not busy)
        self._network_input.setReadOnly(busy)

    def _retranslate_ui(self, _locale_code: str | None = None) -> None:
        self.setWindowTitle(self._localizer.text("app.title"))
        self._network_label.setText(self._localizer.text("main.network_range_label"))
        self._network_input.setPlaceholderText(
            self._localizer.text("main.network_range_placeholder")
        )
        self._scan_button.setText(self._localizer.text("main.scan_button"))
        self._stop_button.setText(self._localizer.text("main.stop_button"))
        self._history_button.setText(self._localizer.text("main.history_button"))
        self._filter_label.setText(self._localizer.text("main.filter_label"))
        self._filter_input.setPlaceholderText(
            self._localizer.text("main.filter_placeholder")
        )
        self._online_only_checkbox.setText(
            self._localizer.text("main.online_only_checkbox")
        )
        self._has_open_ports_checkbox.setText(
            self._localizer.text("main.has_open_ports_checkbox")
        )
        self._has_services_checkbox.setText(
            self._localizer.text("main.has_services_checkbox")
        )
