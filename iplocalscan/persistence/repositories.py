from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import datetime
from sqlite3 import Row
from typing import Sequence

from ..core.entities import ScanResult, ScanSession, ServiceRecord
from ..core.enums import HostStatus, ScanLifecycleStatus
from .database import DatabaseManager


class ScanSessionRepository:
    def __init__(self, database_manager: DatabaseManager) -> None:
        self._database_manager = database_manager

    def create(self, session: ScanSession) -> ScanSession:
        with self._database_manager.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO scans (
                    network_range,
                    started_at,
                    finished_at,
                    status,
                    result_count,
                    note
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session.network_range,
                    session.started_at.isoformat(),
                    session.finished_at.isoformat() if session.finished_at else None,
                    session.status.value,
                    session.result_count,
                    session.note,
                ),
            )
            session_id = int(cursor.lastrowid)
        return replace(session, id=session_id)

    def finalize(
        self,
        session_id: int,
        status: ScanLifecycleStatus,
        finished_at: datetime,
        result_count: int,
        note: str | None = None,
    ) -> None:
        with self._database_manager.connection() as connection:
            connection.execute(
                """
                UPDATE scans
                SET finished_at = ?, status = ?, result_count = ?, note = ?
                WHERE id = ?
                """,
                (
                    finished_at.isoformat(),
                    status.value,
                    result_count,
                    note,
                    session_id,
                ),
            )

    def list_recent(self, limit: int = 3) -> list[ScanSession]:
        with self._database_manager.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, network_range, started_at, finished_at, status, result_count, note
                FROM scans
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def trim_history(self, keep_last: int = 3) -> None:
        with self._database_manager.connection() as connection:
            stale_rows = connection.execute(
                """
                SELECT id
                FROM scans
                ORDER BY started_at DESC
                LIMIT -1 OFFSET ?
                """,
                (keep_last,),
            ).fetchall()
            stale_ids = [int(row["id"]) for row in stale_rows]
            if not stale_ids:
                return

            placeholders = ",".join("?" for _ in stale_ids)
            connection.execute(
                f"DELETE FROM scans WHERE id IN ({placeholders})",
                stale_ids,
            )

    def _row_to_session(self, row: Row) -> ScanSession:
        finished_at = row["finished_at"]
        return ScanSession(
            id=int(row["id"]),
            network_range=row["network_range"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(finished_at) if finished_at else None,
            status=ScanLifecycleStatus(row["status"]),
            result_count=int(row["result_count"]),
            note=row["note"],
        )


class ScanResultRepository:
    def __init__(self, database_manager: DatabaseManager) -> None:
        self._database_manager = database_manager

    def replace_for_scan(self, scan_id: int, results: Sequence[ScanResult]) -> None:
        with self._database_manager.connection() as connection:
            connection.execute(
                "DELETE FROM scan_results WHERE scan_id = ?",
                (scan_id,),
            )

            if not results:
                return

            connection.executemany(
                """
                INSERT INTO scan_results (
                    scan_id,
                    ip_address,
                    mac_address,
                    mac_vendor,
                    hostname,
                    status,
                    open_ports_json,
                    detected_services_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        scan_id,
                        result.ip_address,
                        result.mac_address,
                        result.mac_vendor,
                        result.hostname,
                        result.status.value,
                        json.dumps(result.open_ports),
                        json.dumps(
                            [asdict(service) for service in result.detected_services]
                        ),
                    )
                    for result in results
                ],
            )

    def list_for_scan(self, scan_id: int) -> list[ScanResult]:
        with self._database_manager.connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    scan_id,
                    ip_address,
                    mac_address,
                    mac_vendor,
                    hostname,
                    status,
                    open_ports_json,
                    detected_services_json
                FROM scan_results
                WHERE scan_id = ?
                ORDER BY ip_address ASC
                """,
                (scan_id,),
            ).fetchall()
        return [self._row_to_result(row) for row in rows]

    def _row_to_result(self, row: Row) -> ScanResult:
        service_payload = json.loads(row["detected_services_json"])
        services = [
            ServiceRecord(
                name=service_data["name"],
                protocol=service_data.get("protocol"),
                port=service_data.get("port"),
            )
            for service_data in service_payload
        ]
        return ScanResult(
            scan_id=int(row["scan_id"]),
            ip_address=row["ip_address"],
            mac_address=row["mac_address"],
            mac_vendor=row["mac_vendor"],
            hostname=row["hostname"],
            status=HostStatus(row["status"]),
            open_ports=list(json.loads(row["open_ports_json"])),
            detected_services=services,
        )
