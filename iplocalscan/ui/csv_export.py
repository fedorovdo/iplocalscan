from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QTableView, QWidget

from ..localization.manager import LocalizationManager


def export_visible_table_to_csv(
    *,
    parent: QWidget,
    localizer: LocalizationManager,
    table_view: QTableView,
) -> None:
    model = table_view.model()
    if model is None:
        return

    visible_columns = [
        column
        for column in range(model.columnCount())
        if not table_view.isColumnHidden(column)
    ]
    visible_rows = model.rowCount()
    if visible_rows == 0 or not visible_columns:
        QMessageBox.information(
            parent,
            localizer.text("export.csv.title"),
            localizer.text("export.csv.no_rows"),
        )
        return

    dialog = QFileDialog(
        parent,
        localizer.text("export.csv.save_dialog_title"),
    )
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setNameFilter(localizer.text("export.csv.file_filter"))
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
            writer = csv.writer(
                handle,
                delimiter=";",
                quoting=csv.QUOTE_MINIMAL,
            )
            writer.writerow(
                [
                    str(
                        model.headerData(
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
                            model.index(row, column).data(Qt.ItemDataRole.DisplayRole)
                            or ""
                        )
                        for column in visible_columns
                    ]
                )
    except OSError as exc:
        QMessageBox.critical(
            parent,
            localizer.text("export.csv.title"),
            localizer.text("export.csv.failed", reason=str(exc)),
        )
        return

    QMessageBox.information(
        parent,
        localizer.text("export.csv.title"),
        localizer.text("export.csv.success", path=str(target_path)),
    )
