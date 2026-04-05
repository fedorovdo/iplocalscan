from __future__ import annotations

from PySide6.QtCore import QObject, QLocale, Signal

from .strings import TRANSLATIONS


class LocalizationManager(QObject):
    locale_changed = Signal(str)

    def __init__(self, locale_code: str | None = None) -> None:
        super().__init__()
        self._locale_code = self._normalize_locale(
            locale_code or QLocale.system().name()
        )

    @property
    def locale_code(self) -> str:
        return self._locale_code

    def set_locale(self, locale_code: str) -> None:
        normalized_locale = self._normalize_locale(locale_code)
        if normalized_locale == self._locale_code:
            return

        self._locale_code = normalized_locale
        self.locale_changed.emit(self._locale_code)

    def text(self, key: str, **params: object) -> str:
        template = TRANSLATIONS.get(self._locale_code, {}).get(
            key,
            TRANSLATIONS["en"].get(key, key),
        )
        return template.format(**params)

    def _normalize_locale(self, locale_code: str) -> str:
        language = locale_code.replace("-", "_").split("_", maxsplit=1)[0].lower()
        return language if language in TRANSLATIONS else "en"

