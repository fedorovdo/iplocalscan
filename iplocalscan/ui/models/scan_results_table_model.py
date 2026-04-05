from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any, Callable

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from ...core.entities import ScanResult
from ...localization.manager import LocalizationManager


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    header_key: str
    display_value: Callable[[ScanResult], str]
    sort_value: Callable[[ScanResult], Any]


def _sort_ip(result: ScanResult) -> int:
    try:
        return int(ip_address(result.ip_address))
    except ValueError:
        return -1


def _sort_mac(result: ScanResult) -> str:
    raw_value = result.mac_address or ""
    return "".join(character for character in raw_value if character.isalnum()).lower()


def _sort_hostname(result: ScanResult) -> str:
    return (result.hostname or "").casefold()


def _sort_status(result: ScanResult) -> int:
    return result.status.sort_order


def _format_open_ports(result: ScanResult) -> str:
    return ",".join(str(port) for port in result.open_ports)


def _sort_open_ports(result: ScanResult) -> str:
    return ",".join(f"{port:05d}" for port in result.open_ports)


def _format_services(result: ScanResult) -> str:
    return ", ".join(service.name for service in result.detected_services)


def _sort_services(result: ScanResult) -> str:
    return _format_services(result).casefold()


class ScanResultsTableModel(QAbstractTableModel):
    def __init__(
        self,
        localizer: LocalizationManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._localizer = localizer
        self._results: list[ScanResult] = []
        self._result_index_by_key: dict[tuple[int | None, str], int] = {}
        self._columns = (
            ColumnSpec(
                header_key="table.ip_address",
                display_value=lambda result: result.ip_address,
                sort_value=_sort_ip,
            ),
            ColumnSpec(
                header_key="table.mac_address",
                display_value=lambda result: result.mac_address
                or self._localizer.text("common.not_available"),
                sort_value=_sort_mac,
            ),
            ColumnSpec(
                header_key="table.hostname",
                display_value=lambda result: result.hostname
                or self._localizer.text("common.not_available"),
                sort_value=_sort_hostname,
            ),
            ColumnSpec(
                header_key="table.status",
                display_value=lambda result: self._localizer.text(
                    f"status.host.{result.status.value}"
                ),
                sort_value=_sort_status,
            ),
            ColumnSpec(
                header_key="table.open_ports",
                display_value=lambda result: _format_open_ports(result)
                or self._localizer.text("common.not_available"),
                sort_value=_sort_open_ports,
            ),
            ColumnSpec(
                header_key="table.services",
                display_value=lambda result: _format_services(result)
                or self._localizer.text("common.not_available"),
                sort_value=_sort_services,
            ),
        )
        self._localizer.locale_changed.connect(self._handle_locale_changed)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._results)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        result = self._results[index.row()]
        column = self._columns[index.column()]

        if role == Qt.ItemDataRole.DisplayRole:
            return column.display_value(result)
        if role == Qt.ItemDataRole.UserRole:
            return column.sort_value(result)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if orientation == Qt.Orientation.Horizontal:
            return self._localizer.text(self._columns[section].header_key)

        return str(section + 1)

    def set_results(self, results: list[ScanResult]) -> None:
        self.beginResetModel()
        self._results = list(results)
        self._rebuild_result_index()
        self.endResetModel()

    def clear(self) -> None:
        self.set_results([])

    def append_result(self, result: ScanResult) -> None:
        row_index = len(self._results)
        self.beginInsertRows(QModelIndex(), row_index, row_index)
        self._results.append(result)
        self._rebuild_result_index()
        self.endInsertRows()

    def upsert_result(self, result: ScanResult) -> None:
        key = self._result_key(result)
        existing_row = self._result_index_by_key.get(key)
        if existing_row is None:
            self.append_result(result)
            return

        self._results[existing_row] = result
        top_left = self.index(existing_row, 0)
        bottom_right = self.index(existing_row, self.columnCount() - 1)
        self.dataChanged.emit(
            top_left,
            bottom_right,
            [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.UserRole],
        )

    def search_text_for_row(self, row: int) -> str:
        result = self._results[row]
        parts = [
            result.ip_address,
            result.mac_address or "",
            result.mac_vendor or "",
            result.hostname or "",
            result.status.value,
            self._localizer.text(f"status.host.{result.status.value}"),
            _format_open_ports(result),
            _format_services(result),
        ]
        return " ".join(parts).casefold()

    def _rebuild_result_index(self) -> None:
        self._result_index_by_key = {
            self._result_key(result): index
            for index, result in enumerate(self._results)
        }

    def _result_key(self, result: ScanResult) -> tuple[int | None, str]:
        return (result.scan_id, result.ip_address)

    def _handle_locale_changed(self, _locale_code: str) -> None:
        if self._results:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, self.columnCount() - 1),
                [Qt.ItemDataRole.DisplayRole],
            )
        if self.columnCount() > 0:
            self.headerDataChanged.emit(
                Qt.Orientation.Horizontal,
                0,
                self.columnCount() - 1,
            )
