"""
Repository Abstraction for Processing Domain (Slice 4).
Provides ProcessingRepository interface, SQLiteProcessingRepository, and InMemoryProcessingRepository.
"""

from abc import ABC, abstractmethod
import json
import sqlite3
import threading
from typing import List, Optional, Dict, Any

from src.processing.models import ProcessingJob, JobStatus


class ProcessingRepository(ABC):
    @abstractmethod
    def save(self, job: ProcessingJob) -> ProcessingJob:
        """Saves or updates a ProcessingJob entity."""
        pass

    @abstractmethod
    def get_by_id(self, job_id: str) -> Optional[ProcessingJob]:
        """Retrieves a ProcessingJob by job_id."""
        pass

    @abstractmethod
    def list_by_evidence(self, evidence_id: str) -> List[ProcessingJob]:
        """Lists processing jobs associated with an evidence_id."""
        pass

    @abstractmethod
    def list_by_case(self, case_id: str) -> List[ProcessingJob]:
        """Lists processing jobs associated with a case_id."""
        pass


class InMemoryProcessingRepository(ProcessingRepository):
    def __init__(self):
        self._jobs: Dict[str, ProcessingJob] = {}

    def save(self, job: ProcessingJob) -> ProcessingJob:
        self._jobs[job.job_id] = job
        return job

    def get_by_id(self, job_id: str) -> Optional[ProcessingJob]:
        return self._jobs.get(job_id)

    def list_by_evidence(self, evidence_id: str) -> List[ProcessingJob]:
        return [j for j in self._jobs.values() if j.evidence_id == evidence_id]

    def list_by_case(self, case_id: str) -> List[ProcessingJob]:
        return [j for j in self._jobs.values() if j.case_id == case_id]


class SQLiteProcessingRepository(ProcessingRepository):
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
                CREATE TABLE IF NOT EXISTS processing_jobs (
                    job_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    engine_name TEXT NOT NULL,
                    engine_version TEXT NOT NULL,
                    image_format TEXT NOT NULL,
                    observed_filesystem TEXT,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    requested_by TEXT NOT NULL,
                    output_directory TEXT NOT NULL,
                    evidence_contract_ref TEXT,
                    pre_processing_sha256 TEXT NOT NULL,
                    post_processing_sha256 TEXT,
                    error_message TEXT,
                    audit_references_json TEXT
                )
            """)
            self._conn.commit()

    def save(self, job: ProcessingJob) -> ProcessingJob:
        with self._lock:
            cursor = self._conn.cursor()
            audit_json = json.dumps(job.audit_references)

            cursor.execute("""
                INSERT OR REPLACE INTO processing_jobs (
                    job_id, case_id, evidence_id, status, engine_name, engine_version,
                    image_format, observed_filesystem, created_at, started_at, completed_at,
                    requested_by, output_directory, evidence_contract_ref, pre_processing_sha256,
                    post_processing_sha256, error_message, audit_references_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id, job.case_id, job.evidence_id, job.status.value,
                job.engine_name, job.engine_version, job.image_format, job.observed_filesystem,
                job.created_at, job.started_at, job.completed_at, job.requested_by,
                job.output_directory, job.evidence_contract_ref, job.pre_processing_sha256,
                job.post_processing_sha256, job.error_message, audit_json
            ))
            self._conn.commit()
            return job

    def get_by_id(self, job_id: str) -> Optional[ProcessingJob]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM processing_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def list_by_evidence(self, evidence_id: str) -> List[ProcessingJob]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM processing_jobs WHERE evidence_id = ? ORDER BY created_at DESC", (evidence_id,))
            rows = cursor.fetchall()
            return [self._row_to_job(row) for row in rows]

    def list_by_case(self, case_id: str) -> List[ProcessingJob]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT * FROM processing_jobs WHERE case_id = ? ORDER BY created_at DESC", (case_id,))
            rows = cursor.fetchall()
            return [self._row_to_job(row) for row in rows]

    def _row_to_job(self, row: sqlite3.Row) -> ProcessingJob:
        audit_refs = json.loads(row["audit_references_json"]) if row["audit_references_json"] else []
        return ProcessingJob(
            job_id=row["job_id"],
            case_id=row["case_id"],
            evidence_id=row["evidence_id"],
            status=JobStatus(row["status"]),
            engine_name=row["engine_name"],
            engine_version=row["engine_version"],
            image_format=row["image_format"],
            observed_filesystem=row["observed_filesystem"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            requested_by=row["requested_by"],
            output_directory=row["output_directory"],
            evidence_contract_ref=row["evidence_contract_ref"],
            pre_processing_sha256=row["pre_processing_sha256"],
            post_processing_sha256=row["post_processing_sha256"],
            error_message=row["error_message"],
            audit_references=audit_refs
        )
