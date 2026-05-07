from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    network_range TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    result_count INTEGER NOT NULL DEFAULT 0,
    note TEXT
);

CREATE TABLE IF NOT EXISTS scan_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL,
    ip_address TEXT NOT NULL,
    mac_address TEXT,
    vendor TEXT,
    hostname TEXT,
    device_model TEXT,
    serial_number TEXT,
    snmp_name TEXT,
    snmp_description TEXT,
    snmp_object_id TEXT,
    status TEXT NOT NULL,
    change_status TEXT NOT NULL DEFAULT 'unchanged',
    open_ports_json TEXT NOT NULL DEFAULT '[]',
    detected_services_json TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scans_started_at ON scans(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_scan_results_scan_id ON scan_results(scan_id);
"""


class DatabaseManager:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    @property
    def database_path(self) -> Path:
        return self._database_path

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.executescript(SCHEMA_SQL)
            self._apply_migrations(connection)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _apply_migrations(self, connection: sqlite3.Connection) -> None:
        scan_result_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(scan_results)")
        }
        if "vendor" not in scan_result_columns:
            connection.execute("ALTER TABLE scan_results ADD COLUMN vendor TEXT")
        if "change_status" not in scan_result_columns:
            connection.execute(
                """
                ALTER TABLE scan_results
                ADD COLUMN change_status TEXT NOT NULL DEFAULT 'unchanged'
                """
            )
        for column_name in (
            "device_model",
            "serial_number",
            "snmp_name",
            "snmp_description",
            "snmp_object_id",
        ):
            if column_name not in scan_result_columns:
                connection.execute(
                    f"ALTER TABLE scan_results ADD COLUMN {column_name} TEXT"
                )
        if "mac_vendor" in scan_result_columns:
            connection.execute(
                """
                UPDATE scan_results
                SET vendor = COALESCE(vendor, mac_vendor)
                WHERE mac_vendor IS NOT NULL
                """
            )
        connection.execute(
            """
            UPDATE scan_results
            SET change_status = COALESCE(change_status, 'unchanged')
            WHERE change_status IS NULL
            """
        )
