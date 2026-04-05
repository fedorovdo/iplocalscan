from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..application.controller import (
    ProgressEvent,
    ScanController,
    StageEvent,
    StatusEvent,
)
from ..config import DEFAULT_WINDOW_HEIGHT, DEFAULT_WINDOW_WIDTH
from ..localization.manager import LocalizationManager
from .about_dialog import AboutDialog
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
        self._language_label = QLabel(self)
        self._language_combo = QComboBox(self)
        self._filter_label = QLabel(self)
        self._filter_input = QLineEdit(self)
        self._online_only_checkbox = QCheckBox(self)
        self._has_open_ports_checkbox = QCheckBox(self)
        self._has_services_checkbox = QCheckBox(self)
        self._scan_stage_label = QLabel(self)
        self._scan_detail_label = QLabel(self)
        self._scan_progress_bar = QProgressBar(self)
        self._results_table = QTableView(self)
        self._file_menu = self.menuBar().addMenu("")
        self._export_csv_action = QAction(self)
        self._help_menu = self.menuBar().addMenu("")
        self._about_action = QAction(self)
        self._current_stage_event = StageEvent(key="progress.stage.ready")
        self._current_progress_event = ProgressEvent(
            minimum=0,
            maximum=1,
            value=0,
            indeterminate=False,
            detail_key="progress.detail.ready",
        )
        self._current_status_event = StatusEvent(key="status.ready")

        self._build_ui()
        self._connect_signals()
        self._retranslate_ui()
        self._set_busy_state(False)
        self._show_status_event(self._current_status_event)

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
        self._scan_stage_label.setObjectName("scanStageLabel")
        self._scan_detail_label.setObjectName("scanDetailLabel")
        self._scan_detail_label.setWordWrap(True)
        self._scan_progress_bar.setTextVisible(True)
        self._scan_progress_bar.setRange(0, 1)
        self._scan_progress_bar.setValue(0)

        layout = QVBoxLayout(central_widget)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self._network_label)
        controls_layout.addWidget(self._network_input, stretch=1)
        controls_layout.addWidget(self._scan_button)
        controls_layout.addWidget(self._stop_button)
        controls_layout.addWidget(self._history_button)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self._language_label)
        controls_layout.addWidget(self._language_combo)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self._filter_label)
        filter_layout.addWidget(self._filter_input, stretch=1)
        filter_layout.addWidget(self._online_only_checkbox)
        filter_layout.addWidget(self._has_open_ports_checkbox)
        filter_layout.addWidget(self._has_services_checkbox)

        layout.addLayout(controls_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self._scan_stage_label)
        layout.addWidget(self._scan_progress_bar)
        layout.addWidget(self._scan_detail_label)
        layout.addWidget(self._results_table, stretch=1)

    def _connect_signals(self) -> None:
        self._export_csv_action.triggered.connect(self._export_visible_results_to_csv)
        self._about_action.triggered.connect(self._open_about_dialog)
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
        self._language_combo.currentIndexChanged.connect(self._handle_language_changed)

        self._controller.status_event.connect(self._show_status_event)
        self._controller.stage_event.connect(self._show_stage_event)
        self._controller.progress_event.connect(self._show_progress_event)
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

    def _open_about_dialog(self) -> None:
        dialog = AboutDialog(
            localizer=self._localizer,
            parent=self,
        )
        dialog.exec()

    def _export_visible_results_to_csv(self) -> None:
        visible_columns = [
            column
            for column in range(self._proxy_model.columnCount())
            if not self._results_table.isColumnHidden(column)
        ]
        visible_rows = self._proxy_model.rowCount()
        if visible_rows == 0 or not visible_columns:
            QMessageBox.information(
                self,
                self._localizer.text("export.csv.title"),
                self._localizer.text("export.csv.no_rows"),
            )
            return

        dialog = QFileDialog(
            self,
            self._localizer.text("export.csv.save_dialog_title"),
        )
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilter(self._localizer.text("export.csv.file_filter"))
        dialog.setDefaultSuffix("csv")
        if dialog.exec() != QFileDialog.DialogCode.Accepted:
            return
        selected_files = dialog.selectedFiles()
        if not selected_files:
            return

        target_path = Path(selected_files[0])
        if target_path.suffix.lower() != ".csv":
            target_path = target_path.with_suffix(".csv")

        try:
            with target_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        str(
                            self._proxy_model.headerData(
                                column,
                                Qt.Orientation.Horizontal,
                                Qt.ItemDataRole.DisplayRole,
                            )
                            or ""
                        )
                        for column in visible_columns
                    ]
                )
                for row in range(visible_rows):
                    writer.writerow(
                        [
                            str(
                                self._proxy_model.index(row, column).data(
                                    Qt.ItemDataRole.DisplayRole
                                )
                                or ""
                            )
                            for column in visible_columns
                        ]
                    )
        except OSError as exc:
            QMessageBox.critical(
                self,
                self._localizer.text("export.csv.title"),
                self._localizer.text("export.csv.failed", reason=str(exc)),
            )
            return

        QMessageBox.information(
            self,
            self._localizer.text("export.csv.title"),
            self._localizer.text("export.csv.success", path=str(target_path)),
        )

    def _show_status_event(self, event: StatusEvent) -> None:
        self._current_status_event = event
        self.statusBar().showMessage(self._localizer.text(event.key, **event.params))

    def _handle_language_changed(self, index: int) -> None:
        locale_code = self._language_combo.itemData(index)
        if isinstance(locale_code, str):
            self._localizer.set_locale(locale_code)

    def _show_stage_event(self, event: StageEvent) -> None:
        self._current_stage_event = event
        self._scan_stage_label.setText(self._localizer.text(event.key, **event.params))
        self._apply_progress_visual_state(event.key)

    def _show_progress_event(self, event: ProgressEvent) -> None:
        self._current_progress_event = event
        if event.indeterminate:
            self._scan_progress_bar.setRange(0, 0)
            self._scan_progress_bar.setTextVisible(False)
        else:
            self._scan_progress_bar.setRange(event.minimum, event.maximum)
            self._scan_progress_bar.setValue(event.value)
            self._scan_progress_bar.setFormat("%p%")
            self._scan_progress_bar.setTextVisible(True)

        if event.detail_key is None:
            self._scan_detail_label.clear()
            return

        self._scan_detail_label.setText(
            self._localizer.text(event.detail_key, **event.params)
        )

    def _set_busy_state(self, busy: bool) -> None:
        self._scan_button.setEnabled(not busy)
        self._stop_button.setEnabled(busy)
        self._history_button.setEnabled(not busy)
        self._export_csv_action.setEnabled(not busy)
        self._network_input.setReadOnly(busy)

    def _retranslate_ui(self, _locale_code: str | None = None) -> None:
        self.setWindowTitle(self._localizer.text("app.title"))
        self._file_menu.setTitle(self._localizer.text("menu.file"))
        self._export_csv_action.setText(self._localizer.text("menu.export_csv"))
        if self._export_csv_action not in self._file_menu.actions():
            self._file_menu.addAction(self._export_csv_action)
        self._help_menu.setTitle(self._localizer.text("menu.help"))
        self._about_action.setText(self._localizer.text("menu.about"))
        if self._about_action not in self._help_menu.actions():
            self._help_menu.addAction(self._about_action)
        self._network_label.setText(self._localizer.text("main.network_range_label"))
        self._network_input.setPlaceholderText(
            self._localizer.text("main.network_range_placeholder")
        )
        self._scan_button.setText(self._localizer.text("main.scan_button"))
        self._stop_button.setText(self._localizer.text("main.stop_button"))
        self._history_button.setText(self._localizer.text("main.history_button"))
        self._language_label.setText(self._localizer.text("main.language_label"))
        self._refresh_language_selector()
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
        self._scan_stage_label.setText(
            self._localizer.text(
                self._current_stage_event.key,
                **self._current_stage_event.params,
            )
        )
        if self._current_progress_event.detail_key is None:
            self._scan_detail_label.clear()
        else:
            self._scan_detail_label.setText(
                self._localizer.text(
                    self._current_progress_event.detail_key,
                    **self._current_progress_event.params,
                )
            )
        self.statusBar().showMessage(
            self._localizer.text(
                self._current_status_event.key,
                **self._current_status_event.params,
            )
        )

    def _apply_progress_visual_state(self, stage_key: str) -> None:
        style_by_stage = {
            "progress.stage.completed": (
                "QProgressBar::chunk { background-color: #6aa84f; }",
                "QLabel#scanStageLabel { color: #2f6d2f; font-weight: 600; }",
            ),
            "progress.stage.stopped": (
                "QProgressBar::chunk { background-color: #d9a441; }",
                "QLabel#scanStageLabel { color: #8a6d1d; font-weight: 600; }",
            ),
            "progress.stage.failed": (
                "QProgressBar::chunk { background-color: #c0504d; }",
                "QLabel#scanStageLabel { color: #8f2f2c; font-weight: 600; }",
            ),
        }
        progress_style, label_style = style_by_stage.get(stage_key, ("", ""))
        self._scan_progress_bar.setStyleSheet(progress_style)
        self._scan_stage_label.setStyleSheet(label_style)

    def _refresh_language_selector(self) -> None:
        current_locale = self._localizer.locale_code
        blocker = QSignalBlocker(self._language_combo)
        self._language_combo.clear()
        self._language_combo.addItem(
            self._localizer.text("language.english"),
            "en",
        )
        self._language_combo.addItem(
            self._localizer.text("language.russian"),
            "ru",
        )
        current_index = self._language_combo.findData(current_locale)
        if current_index >= 0:
            self._language_combo.setCurrentIndex(current_index)
        del blocker
