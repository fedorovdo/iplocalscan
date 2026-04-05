from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from .application.controller import ScanController
from .application.scan_orchestrator import ScanOrchestrator
from .config import APP_DISPLAY_NAME, APP_NAME, ApplicationPaths
from .logging_config import configure_logging
from .localization.manager import LocalizationManager
from .persistence.database import DatabaseManager
from .persistence.repositories import ScanResultRepository, ScanSessionRepository
from .services.discovery import SubprocessPingHostDiscovery
from .services.portscan import (
    SocketTcpConnectPortScanner,
    StaticPortServiceDetector,
)
from .services.resolvers import (
    SocketHostnameResolver,
    WindowsArpTableMacAddressResolver,
)
from .services.stubs import StubMacVendorLookup
from .ui.main_window import MainWindow


def create_application(
    argv: Sequence[str] | None = None,
) -> tuple[QApplication, MainWindow]:
    configure_logging()
    app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setOrganizationName(APP_NAME)

    paths = ApplicationPaths.detect()
    database_manager = DatabaseManager(paths.database_path)
    database_manager.initialize()

    localization = LocalizationManager()
    orchestrator = ScanOrchestrator(
        host_discovery=SubprocessPingHostDiscovery(),
        hostname_resolver=SocketHostnameResolver(),
        mac_address_resolver=WindowsArpTableMacAddressResolver(),
        port_scanner=SocketTcpConnectPortScanner(),
        service_detector=StaticPortServiceDetector(),
        mac_vendor_lookup=StubMacVendorLookup(),
    )
    controller = ScanController(
        orchestrator=orchestrator,
        session_repository=ScanSessionRepository(database_manager),
        result_repository=ScanResultRepository(database_manager),
    )
    window = MainWindow(controller=controller, localizer=localization)
    return app, window


def main() -> int:
    app, window = create_application()
    window.show()
    return app.exec()
