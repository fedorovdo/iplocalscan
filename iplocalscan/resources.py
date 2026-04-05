from __future__ import annotations

import sys
from pathlib import Path


def package_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "iplocalscan"

    return Path(__file__).resolve().parent


def resource_path(*relative_parts: str) -> Path:
    return package_root().joinpath(*relative_parts)
