from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any, Callable

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QBrush, QColor

from ...core.entities import ScanResult
from ...core.enums import ChangeStatus
from ...core.mac import normalize_mac_address
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


def _sort_optional_text(value: str | None) -> tuple[int, str]:
    normalized_value = (value or "").casefold()
    return (0, normalized_value) if normalized_value else (1, "")


def _sort_mac(result: ScanResult) -> tuple[int, str]:
    normalized_mac = normalize_mac_address(result.mac_address)
    if normalized_mac is None:
        return (1, "")
    return (0, normalized_mac.replace(":", ""))


def _sort_hostname(result: ScanResult) -> tuple[int, str]:
    return _sort_optional_text(result.hostname)


def _sort_vendor(result: ScanResult) -> tuple[int, str]:
    return _sort_optional_text(result.vendor)


def _sort_status(result: ScanResult) -> int:
    return result.status.sort_order


def _sort_change_status(result: ScanResult) -> int:
    return result.change_status.sort_order


def _format_open_ports(result: ScanResult) -> str:
    return ",".join(str(port) for port in result.open_ports)


def _sort_open_ports(result: ScanResult) -> tuple[int, int, int, tuple[int, ...]]:
    if not result.open_ports:
        return (1, 0, 0, ())
    sorted_ports = tuple(sorted(result.open_ports))
    return (0, sorted_ports[0], len(sorted_ports), sorted_ports)


def _format_services(result: ScanResult) -> str:
    return ", ".join(service.name for service in result.detected_services)


def _sort_services(result: ScanResult) -> tuple[int, tuple[str, ...]]:
    if not result.detected_services:
        return (1, ())
    return (
        0,
        tuple(
            service.name.casefold()
            for service in sorted(
                result.detected_services,
                key=lambda service: (service.port or -1, service.name.casefold()),
            )
        ),
    )


def _background_brush(result: ScanResult) -> QBrush | None:
    color_map = {
        ChangeStatus.NEW: QColor("#e6f4ea"),
        ChangeStatus.CHANGED: QColor("#fff4ce"),
        ChangeStatus.REMOVED: QColor("#fde7e9"),
    }
    color = color_map.get(result.change_status)
    return QBrush(color) if color is not None else None


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
                header_key="table.vendor",
                display_value=lambda result: result.vendor
                or self._localizer.text("common.not_available"),
                sort_value=_sort_vendor,
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
                header_key="table.change_status",
                display_value=lambda result: self._localizer.text(
                    f"status.change.{result.change_status.value}"
                ),
                sort_value=_sort_change_status,
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
        if role == Qt.ItemDataRole.BackgroundRole:
            return _background_brush(result)
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
            [
                Qt.ItemDataRole.DisplayRole,
                Qt.ItemDataRole.UserRole,
                Qt.ItemDataRole.BackgroundRole,
            ],
        )

    def search_text_for_row(self, row: int) -> str:
        result = self._results[row]
        normalized_mac = normalize_mac_address(result.mac_address) or ""
        parts = [
            result.ip_address,
            result.mac_address or "",
            normalized_mac,
            normalized_mac.replace(":", ""),
            result.vendor or "",
            result.hostname or "",
            result.device_model or "",
            result.serial_number or "",
            result.snmp_name or "",
            result.snmp_description or "",
            result.snmp_object_id or "",
            result.status.value,
            self._localizer.text(f"status.host.{result.status.value}"),
            result.change_status.value,
            self._localizer.text(f"status.change.{result.change_status.value}"),
            _format_open_ports(result),
            _format_services(result),
        ]
        return " ".join(parts).casefold()

    def result_at(self, row: int) -> ScanResult | None:
        if row < 0 or row >= len(self._results):
            return None
        return self._results[row]

    def sort(
        self,
        column: int,
        order: Qt.SortOrder = Qt.SortOrder.AscendingOrder,
    ) -> None:
        if column < 0 or column >= len(self._columns):
            return

        self.layoutAboutToBeChanged.emit()
        self._results.sort(
            key=self._columns[column].sort_value,
            reverse=order == Qt.SortOrder.DescendingOrder,
        )
        self._rebuild_result_index()
        self.layoutChanged.emit()

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
