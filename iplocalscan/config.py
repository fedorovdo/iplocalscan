from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "iplocalscan"
APP_DISPLAY_NAME = "IP Local Scan"
DEFAULT_HISTORY_LIMIT = 3
DEFAULT_WINDOW_WIDTH = 1080
DEFAULT_WINDOW_HEIGHT = 680


@dataclass(frozen=True, slots=True)
class ApplicationPaths:
    data_dir: Path
    database_path: Path
    settings_path: Path

    @classmethod
    def detect(cls, app_name: str = APP_NAME) -> "ApplicationPaths":
        if sys.platform.startswith("win"):
            base_dir = Path(
                os.getenv(
                    "LOCALAPPDATA",
                    Path.home() / "AppData" / "Local",
                )
            )
        elif sys.platform.startswith("linux"):
            base_dir = Path(
                os.getenv(
                    "XDG_DATA_HOME",
                    Path.home() / ".local" / "share",
                )
            )
        elif sys.platform == "darwin":
            base_dir = Path.home() / "Library" / "Application Support"
        else:
            base_dir = Path.home()

        data_dir = base_dir / app_name
        data_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            data_dir=data_dir,
            database_path=data_dir / f"{app_name}.db",
            settings_path=data_dir / "settings.json",
        )
