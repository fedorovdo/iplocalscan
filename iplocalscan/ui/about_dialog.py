from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from ..about_info import AboutInfo, collect_about_info
from ..localization.manager import LocalizationManager


class AboutDialog(QDialog):
    def __init__(
        self,
        localizer: LocalizationManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._localizer = localizer
        self._about_info = collect_about_info()

        self._icon_label = QLabel(self)
        self._app_name_label = QLabel(self)
        self._description_label = QLabel(self)
        self._version_label = QLabel(self)
        self._version_value = QLabel(self)
        self._author_label = QLabel(self)
        self._author_value = QLabel(self)
        self._github_label = QLabel(self)
        self._github_value = QLabel(self)
        self._python_label = QLabel(self)
        self._python_value = QLabel(self)
        self._os_label = QLabel(self)
        self._os_value = QLabel(self)
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            parent=self,
        )
        self._copy_button = QPushButton(self)

        self._build_ui()
        self._connect_signals()
        self._retranslate_ui()

    def _build_ui(self) -> None:
        self.setModal(True)
        self.resize(520, 340)

        about_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self._icon_label.setPixmap(about_icon.pixmap(48, 48))
        self._app_name_label.setObjectName("aboutAppNameLabel")
        self._description_label.setWordWrap(True)
        self._github_value.setOpenExternalLinks(True)
        self._github_value.setTextFormat(Qt.TextFormat.RichText)
        self._os_value.setWordWrap(True)
        self._python_value.setWordWrap(True)
        self._version_value.setWordWrap(True)
        self._author_value.setWordWrap(True)

        details_form = QFormLayout()
        details_form.addRow(self._version_label, self._version_value)
        details_form.addRow(self._author_label, self._author_value)
        details_form.addRow(self._github_label, self._github_value)
        details_form.addRow(self._python_label, self._python_value)
        details_form.addRow(self._os_label, self._os_value)
        self._details_form = details_form

        header_layout = QHBoxLayout()
        header_layout.addWidget(self._icon_label, 0)

        header_text_layout = QVBoxLayout()
        header_text_layout.addWidget(self._app_name_label)
        header_text_layout.addWidget(self._description_label)
        header_layout.addLayout(header_text_layout, 1)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self._copy_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self._button_box)

        layout = QVBoxLayout(self)
        layout.addLayout(header_layout)
        layout.addSpacing(8)
        layout.addLayout(self._details_form)
        layout.addStretch(1)
        layout.addLayout(buttons_layout)

        self.setStyleSheet(
            "QLabel#aboutAppNameLabel { font-size: 22px; font-weight: 600; }"
        )

    def _connect_signals(self) -> None:
        self._button_box.rejected.connect(self.reject)
        self._copy_button.clicked.connect(self._copy_info_to_clipboard)
        self._localizer.locale_changed.connect(self._retranslate_ui)

    def _retranslate_ui(self, _locale_code: str | None = None) -> None:
        self.setWindowTitle(self._localizer.text("about.title"))
        self._app_name_label.setText(self._about_info.app_name)
        self._description_label.setText(self._localizer.text("about.description"))
        self._version_label.setText(self._localizer.text("about.version_label"))
        self._author_label.setText(self._localizer.text("about.author_label"))
        self._github_label.setText(self._localizer.text("about.github_label"))
        self._python_label.setText(self._localizer.text("about.python_label"))
        self._os_label.setText(self._localizer.text("about.os_label"))
        self._copy_button.setText(self._localizer.text("about.copy_button"))
        self._button_box.button(QDialogButtonBox.StandardButton.Close).setText(
            self._localizer.text("about.close_button")
        )

        self._version_value.setText(self._about_info.version)
        self._author_value.setText(self._about_info.author)
        self._github_value.setText(
            f'<a href="{self._about_info.github_url}">{self._about_info.github_url}</a>'
        )
        self._python_value.setText(self._about_info.python_version)
        self._os_value.setText(self._about_info.operating_system)

    def _copy_info_to_clipboard(self) -> None:
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self._build_copy_payload())
        QMessageBox.information(
            self,
            self._localizer.text("about.copy_success_title"),
            self._localizer.text("about.copy_success_message"),
        )

    def _build_copy_payload(self) -> str:
        return "\n".join(
            [
                f"{self._localizer.text('about.name_label')}: {self._about_info.app_name}",
                f"{self._localizer.text('about.version_label')}: {self._about_info.version}",
                f"{self._localizer.text('about.author_label')}: {self._about_info.author}",
                f"{self._localizer.text('about.description_label')}: {self._localizer.text('about.description')}",
                f"{self._localizer.text('about.github_label')}: {self._about_info.github_url}",
                f"{self._localizer.text('about.python_label')}: {self._about_info.python_version}",
                f"{self._localizer.text('about.os_label')}: {self._about_info.operating_system}",
            ]
        )
