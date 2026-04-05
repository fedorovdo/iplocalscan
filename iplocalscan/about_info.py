from __future__ import annotations

from dataclasses import dataclass
import platform

from .config import APP_DISPLAY_NAME
from .version import APP_AUTHOR, APP_GITHUB_URL, __version__


@dataclass(frozen=True, slots=True)
class AboutInfo:
    app_name: str
    version: str
    author: str
    github_url: str
    python_version: str
    operating_system: str


def collect_about_info() -> AboutInfo:
    return AboutInfo(
        app_name=APP_DISPLAY_NAME,
        version=__version__,
        author=APP_AUTHOR,
        github_url=APP_GITHUB_URL,
        python_version=_python_version_string(),
        operating_system=_os_info_string(),
    )


def _python_version_string() -> str:
    return (
        f"{platform.python_version()} "
        f"({platform.python_implementation()}, {platform.python_compiler()})"
    )


def _os_info_string() -> str:
    machine = platform.machine()
    os_name = platform.platform(aliased=True)
    if machine:
        return f"{os_name} [{machine}]"
    return os_name
