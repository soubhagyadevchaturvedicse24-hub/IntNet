"""
Repository Pattern Abstraction for Evidence Domain (Slice 3).
Provides EvidenceRepository interface, SQLiteEvidenceRepository, and InMemoryEvidenceRepository implementations.
"""

from abc import ABC, abstractmethod
import json
import sqlite3
import threading
from typing import List, Optional, Dict, Any

from src.evidence.models import Evidence, EvidenceType, PreservationStatus, IntegrityStatus


class EvidenceRepository(ABC):
    @abstractmethod
    def save(self, evidence: Evidence) -> Evidence:
        """Saves or updates an Evidence entity."""
        pass

    @abstractmethod
    def get_by_id(self, evidence_id: str) -> Optional[Evidence]:
        """Retrieves an Evidence record by evidence_id."""
        pass

    @abstractmethod
    def list_by_case(self, case_id: str) -> List[Evidence]:
        """Lists all evidence registered under a given case_id."""
        pass

    @abstractmethod
    def delete(self, evidence_id: str) -> bool:
        """Deletes evidence metadata record (forensic audit logged)."""
        pass


class InMemoryEvidenceRepository(EvidenceRepository):
    def __init__(self):
        self._store: Dict[str, Evidence] = {}

    def save(self, evidence: Evidence) -> Evidence:
        self._store[evidence.evidence_id] = evidence
        return evidence

    def get_by_id(self, evidence_id: str) -> Optional[Evidence]:
        return self._store.get(evidence_id)

    def list_by_case(self, case_id: str) -> List[Evidence]:
        return [ev for ev in self._store.values() if ev.case_id == case_id]

    def delete(self, evidence_id: str) -> bool:
        if evidence_id in self._store:
            del self._store[evidence_id]
            return True
        return False


class SQLiteEvidenceRepository(EvidenceRepository):
    def __init__(self, db_path: str = "DATA/cases.db"):
        import os
        if db_path != ":memory:" and "/" in db_path:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    evidence_name TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    original_size_bytes INTEGER NOT NULL,
                    storage_reference TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    md5 TEXT,
                    registered_at REAL NOT NULL,
                    registered_by TEXT NOT NULL,
                    source_description TEXT,
                    preservation_status TEXT NOT NULL,
                    integrity_status TEXT NOT NULL,
                    evidence_contract_ref TEXT,
                    audit_references_json TEXT
                )
            """)
            self._conn.commit()

    def save(self, evidence: Evidence) -> Evidence:
        with self._lock:
            cursor = self._conn.cursor()
            audit_json = json.dumps(evidence.audit_references)

            cursor.execute("""
                INSERT OR REPLACE INTO evidence (
                    evidence_id, case_id, evidence_name, evidence_type, original_filename,
                    original_size_bytes, storage_reference, sha256, md5, registered_at,
                    registered_by, source_description, preservation_status, integrity_status,
                    evidence_contract_ref, audit_references_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                evidence.evidence_id, evidence.case_id, evidence.evidence_name, evidence.evidence_type.value,
                evidence.original_filename, evidence.original_size_bytes, evidence.storage_reference,
                evidence.sha256, evidence.md5, evidence.registered_at, evidence.registered_by,
                evidence.source_description, evidence.preservation_status.value, evidence.integrity_status.value,
                evidence.evidence_contract_ref, audit_json
            ))
            self._conn.commit()
            return evidence

    def get_by_id(self, evidence_id: str) -> Optional[Evidence]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_evidence(row)

    def list_by_case(self, case_id: str) -> List[Evidence]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM evidence WHERE case_id = ? ORDER BY registered_at DESC", (case_id,))
            rows = cursor.fetchall()
            return [self._row_to_evidence(row) for row in rows]

    def delete(self, evidence_id: str) -> bool:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM evidence WHERE evidence_id = ?", (evidence_id,))
            affected = cursor.rowcount
            self._conn.commit()
            return affected > 0

    def _row_to_evidence(self, row: sqlite3.Row) -> Evidence:
        audit_refs = json.loads(row["audit_references_json"]) if row["audit_references_json"] else []
        return Evidence(
            evidence_id=row["evidence_id"],
            case_id=row["case_id"],
            evidence_name=row["evidence_name"],
            evidence_type=EvidenceType(row["evidence_type"]),
            original_filename=row["original_filename"],
            original_size_bytes=row["original_size_bytes"],
            storage_reference=row["storage_reference"],
            sha256=row["sha256"],
            md5=row["md5"],
            registered_at=row["registered_at"],
            registered_by=row["registered_by"],
            source_description=row["source_description"],
            preservation_status=PreservationStatus(row["preservation_status"]),
            integrity_status=IntegrityStatus(row["integrity_status"]),
            evidence_contract_ref=row["evidence_contract_ref"],
            audit_references=audit_refs
        )
