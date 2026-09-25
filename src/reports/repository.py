"""
SQLite Repository for CRIMENET Report Subsystem.
Persists generated reports, version lineage, cryptographic digests, and scope envelopes.
Zero mock data — strictly empty until real case reports are generated.
"""

import json
import sqlite3
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.reports.models import ReportDetail, ReportSummaryItem


class SQLiteReportRepository:
    def __init__(self, db_path: str = "DATA/reports.db"):
        self.db_path = db_path
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL;")
        self._conn.execute("PRAGMA synchronous = NORMAL;")
        self._init_db()

    def _init_db(self):
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS case_reports (
                    report_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    previous_version_id TEXT,
                    is_current INTEGER NOT NULL DEFAULT 1,
                    title TEXT NOT NULL,
                    template_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    author TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    created_at_iso TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    content_html TEXT NOT NULL,
                    content_markdown TEXT NOT NULL,
                    stats_json TEXT NOT NULL,
                    source_scope_json TEXT NOT NULL,
                    legal_draft_json TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reports_case_id ON case_reports(case_id);
            """)
            self._conn.commit()

    def save(self, report: ReportDetail) -> ReportDetail:
        with self._lock:
            cursor = self._conn.cursor()
            # If this report is set as current, mark previous reports for this case as not current
            if report.is_current:
                cursor.execute("""
                    UPDATE case_reports SET is_current = 0 WHERE case_id = ?
                """, (report.case_id,))

            cursor.execute("""
                INSERT INTO case_reports (
                    report_id, case_id, version, version_number, previous_version_id,
                    is_current, title, template_type, status, author,
                    created_at, created_at_iso, sha256, summary,
                    content_html, content_markdown, stats_json,
                    source_scope_json, legal_draft_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(report_id) DO UPDATE SET
                    title = excluded.title,
                    status = excluded.status,
                    is_current = excluded.is_current,
                    summary = excluded.summary,
                    content_html = excluded.content_html,
                    content_markdown = excluded.content_markdown,
                    stats_json = excluded.stats_json,
                    source_scope_json = excluded.source_scope_json,
                    legal_draft_json = excluded.legal_draft_json;
            """, (
                report.report_id,
                report.case_id,
                report.version,
                report.version_number,
                report.previous_version_id,
                1 if report.is_current else 0,
                report.title,
                report.template_type,
                report.status,
                report.author,
                report.created_at,
                report.created_at_iso,
                report.sha256,
                report.summary,
                report.content_html,
                report.content_markdown,
                json.dumps(report.stats),
                json.dumps(report.source_scope),
                json.dumps(report.legal_draft),
            ))
            self._conn.commit()
            return report

    def list_by_case(self, case_id: str) -> List[ReportSummaryItem]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                SELECT report_id, case_id, version, version_number, previous_version_id,
                       is_current, title, template_type, status, author,
                       created_at, created_at_iso, sha256, summary, stats_json
                FROM case_reports
                WHERE case_id = ?
                ORDER BY created_at DESC
            """, (case_id,))
            rows = cursor.fetchall()
            items: List[ReportSummaryItem] = []
            for row in rows:
                stats = {}
                try:
                    stats = json.loads(row["stats_json"]) if row["stats_json"] else {}
                except Exception:
                    pass
                items.append(ReportSummaryItem(
                    report_id=row["report_id"],
                    case_id=row["case_id"],
                    version=row["version"],
                    version_number=row["version_number"],
                    previous_version_id=row["previous_version_id"],
                    is_current=bool(row["is_current"]),
                    title=row["title"],
                    template_type=row["template_type"],
                    status=row["status"],
                    author=row["author"],
                    created_at=row["created_at"],
                    created_at_iso=row["created_at_iso"],
                    sha256=row["sha256"],
                    summary=row["summary"],
                    artifact_count=stats.get("total_artifacts", 0),
                    entity_count=stats.get("total_entities", 0),
                    relationship_count=stats.get("total_relationships", 0)
                ))
            return items

    def list_by_cases(self, case_ids: List[str]) -> List[ReportSummaryItem]:
        if not case_ids:
            return []
        with self._lock:
            cursor = self._conn.cursor()
            placeholders = ",".join(["?"] * len(case_ids))
            cursor.execute(f"""
                SELECT report_id, case_id, version, version_number, previous_version_id,
                       is_current, title, template_type, status, author,
                       created_at, created_at_iso, sha256, summary, stats_json
                FROM case_reports
                WHERE case_id IN ({placeholders})
                ORDER BY created_at DESC
            """, tuple(case_ids))
            rows = cursor.fetchall()
            items: List[ReportSummaryItem] = []
            for row in rows:
                stats = {}
                try:
                    stats = json.loads(row["stats_json"]) if row["stats_json"] else {}
                except Exception:
                    pass
                items.append(ReportSummaryItem(
                    report_id=row["report_id"],
                    case_id=row["case_id"],
                    version=row["version"],
                    version_number=row["version_number"],
                    previous_version_id=row["previous_version_id"],
                    is_current=bool(row["is_current"]),
                    title=row["title"],
                    template_type=row["template_type"],
                    status=row["status"],
                    author=row["author"],
                    created_at=row["created_at"],
                    created_at_iso=row["created_at_iso"],
                    sha256=row["sha256"],
                    summary=row["summary"],
                    artifact_count=stats.get("total_artifacts", 0),
                    entity_count=stats.get("total_entities", 0),
                    relationship_count=stats.get("total_relationships", 0)
                ))
            return items

    def get_by_id(self, case_id: str, report_id: str) -> Optional[ReportDetail]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                SELECT * FROM case_reports
                WHERE case_id = ? AND report_id = ?
            """, (case_id, report_id))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_detail(row)

    def get_latest_for_case(self, case_id: str) -> Optional[ReportDetail]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                SELECT * FROM case_reports
                WHERE case_id = ?
                ORDER BY version_number DESC, created_at DESC
                LIMIT 1
            """, (case_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_detail(row)

    def get_version_count(self, case_id: str) -> int:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM case_reports WHERE case_id = ?", (case_id,))
            row = cursor.fetchone()
            return row["c"] if row else 0

    def _row_to_detail(self, row: sqlite3.Row) -> ReportDetail:
        return ReportDetail(
            report_id=row["report_id"],
            case_id=row["case_id"],
            version=row["version"],
            version_number=row["version_number"],
            previous_version_id=row["previous_version_id"],
            is_current=bool(row["is_current"]),
            title=row["title"],
            template_type=row["template_type"],
            status=row["status"],
            author=row["author"],
            created_at=row["created_at"],
            created_at_iso=row["created_at_iso"],
            sha256=row["sha256"],
            summary=row["summary"],
            content_html=row["content_html"],
            content_markdown=row["content_markdown"],
            stats=json.loads(row["stats_json"]) if row["stats_json"] else {},
            source_scope=json.loads(row["source_scope_json"]) if row["source_scope_json"] else {},
            legal_draft=json.loads(row["legal_draft_json"]) if row["legal_draft_json"] else {}
        )
