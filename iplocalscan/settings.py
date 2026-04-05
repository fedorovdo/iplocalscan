from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ApplicationSettings:
    locale_code: str | None = None


class SettingsManager:
    def __init__(self, settings_path: Path) -> None:
        self._settings_path = settings_path

    @property
    def settings_path(self) -> Path:
        return self._settings_path

    def load(self) -> ApplicationSettings:
        if not self._settings_path.exists():
            return ApplicationSettings()

        try:
            payload = json.loads(self._settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception(
                "Failed to load application settings.",
                extra={
                    "event": "settings_load_failed",
                    "settings_path": str(self._settings_path),
                },
            )
            return ApplicationSettings()

        locale_code = payload.get("locale_code")
        if locale_code is not None and not isinstance(locale_code, str):
            locale_code = None
        return ApplicationSettings(locale_code=locale_code)

    def save(self, settings: ApplicationSettings) -> None:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"locale_code": settings.locale_code}
        temp_path = self._settings_path.with_suffix(".tmp")

        try:
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temp_path.replace(self._settings_path)
        except OSError:
            logger.exception(
                "Failed to save application settings.",
                extra={
                    "event": "settings_save_failed",
                    "settings_path": str(self._settings_path),
                },
            )
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def save_locale(self, locale_code: str) -> None:
        self.save(ApplicationSettings(locale_code=locale_code))
