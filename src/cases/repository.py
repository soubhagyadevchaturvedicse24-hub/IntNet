"""
Repository Pattern Abstraction for Case Management Domain.
Provides Abstract Base Class CaseRepository, SQLiteCaseRepository, and InMemoryCaseRepository implementations.
"""

from abc import ABC, abstractmethod
import json
import sqlite3
import threading
from typing import List, Optional, Dict, Any

from src.cases.models import Case, CaseStatus, JudicialCaseContext, CaseAnchor


class CaseRepository(ABC):
    @abstractmethod
    def save(self, case: Case) -> Case:
        """Saves or updates a Case entity."""
        pass

    @abstractmethod
    def get_by_id(self, case_id: str) -> Optional[Case]:
        """Retrieves a Case by its unique case_id."""
        pass

    @abstractmethod
    def list_all(self) -> List[Case]:
        """Lists all registered cases."""
        pass

    @abstractmethod
    def delete(self, case_id: str) -> bool:
        """Deletes a Case by case_id."""
        pass

    @abstractmethod
    def get_evidence_count(self, case_id: str) -> int:
        """Gets count of evidence assigned to case."""
        pass


class InMemoryCaseRepository(CaseRepository):
    def __init__(self):
        self._cases: Dict[str, Case] = {}

    def save(self, case: Case) -> Case:
        self._cases[case.case_id] = case
        return case

    def get_by_id(self, case_id: str) -> Optional[Case]:
        return self._cases.get(case_id)

    def list_all(self) -> List[Case]:
        return list(self._cases.values())

    def delete(self, case_id: str) -> bool:
        if case_id in self._cases:
            del self._cases[case_id]
            return True
        return False

    def get_evidence_count(self, case_id: str) -> int:
        return 0


class SQLiteCaseRepository(CaseRepository):
    def __init__(self, db_path: str = "DATA/cases.db"):
        import os
        if db_path != ":memory:" and "/" in db_path:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
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
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    case_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    judicial_context_json TEXT,
                    assigned_investigators_json TEXT,
                    integrity_audit_references_json TEXT,
                    anchor_json TEXT
                )
            """)
            try:
                cursor.execute("ALTER TABLE cases ADD COLUMN anchor_json TEXT")
            except Exception:
                pass
            self._conn.commit()

    def save(self, case: Case) -> Case:
        with self._lock:
            cursor = self._conn.cursor()

            jud_json = json.dumps(case.judicial_context.model_dump()) if case.judicial_context else None
            inv_json = json.dumps(case.assigned_investigators)
            audit_json = json.dumps(case.integrity_audit_references)
            anchor_json = json.dumps(case.anchor.model_dump()) if hasattr(case, "anchor") and case.anchor else None

            cursor.execute("""
                INSERT OR REPLACE INTO cases (
                    case_id, case_name, description, status, created_by, created_at, updated_at,
                    judicial_context_json, assigned_investigators_json, integrity_audit_references_json, anchor_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case.case_id, case.case_name, case.description, case.status.value,
                case.created_by, case.created_at, case.updated_at,
                jud_json, inv_json, audit_json, anchor_json
            ))
            self._conn.commit()
            return case

    def get_by_id(self, case_id: str) -> Optional[Case]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_case(row)

    def list_all(self) -> List[Case]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM cases ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_case(row) for row in rows]

    def delete(self, case_id: str) -> bool:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
            affected = cursor.rowcount
            cursor.execute("DELETE FROM evidence WHERE case_id = ?", (case_id,))
            self._conn.commit()
            return affected > 0

    def get_evidence_count(self, case_id: str) -> int:
        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM evidence WHERE case_id = ?", (case_id,))
                row = cursor.fetchone()
                return row[0] if row else 0
            except Exception:
                return 0

    def _row_to_case(self, row: sqlite3.Row) -> Case:
        jud_context = None
        if row["judicial_context_json"]:
            jud_context = JudicialCaseContext(**json.loads(row["judicial_context_json"]))

        assigned_inv = json.loads(row["assigned_investigators_json"]) if row["assigned_investigators_json"] else []
        audit_refs = json.loads(row["integrity_audit_references_json"]) if row["integrity_audit_references_json"] else []

        anchor = None
        if "anchor_json" in row.keys() and row["anchor_json"]:
            anchor = CaseAnchor(**json.loads(row["anchor_json"]))

        ev_count = self.get_evidence_count(row["case_id"])

        return Case(
            case_id=row["case_id"],
            case_name=row["case_name"],
            description=row["description"],
            status=CaseStatus(row["status"]),
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            judicial_context=jud_context,
            assigned_investigators=assigned_inv,
            integrity_audit_references=audit_refs,
            anchor=anchor,
            evidence_count=ev_count
        )
