"""
Artifact Repository Abstraction and SQLite Persistence for CRIMENET (Slice 6).
Provides storage for observed file artifacts with case isolation and indexing.
"""

from abc import ABC, abstractmethod
import json
import sqlite3
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.artifacts.models import (
    Artifact,
    ArtifactCategory,
    AllocationStatus,
    RecoveryStatus,
    ViewerType,
    ProvenanceEnvelope,
    ArtifactFilterParams
)


class ArtifactRepository(ABC):
    @abstractmethod
    def save(self, artifact: Artifact) -> None:
        pass

    @abstractmethod
    def get_by_id(self, artifact_id: str) -> Optional[Artifact]:
        pass

    @abstractmethod
    def list_by_case(
        self,
        case_id: str,
        filters: Optional[ArtifactFilterParams] = None
    ) -> List[Artifact]:
        pass

    @abstractmethod
    def delete_by_job(self, processing_job_id: str) -> None:
        pass


class SQLiteArtifactRepository(ArtifactRepository):
    def __init__(self, db_path: str = "DATA/cases.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -32000;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA mmap_size = 134217728;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    processing_job_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    path_within_source TEXT NOT NULL,
                    category TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    file_extension TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT,
                    created_at_observed TEXT,
                    modified_at_observed TEXT,
                    accessed_at_observed TEXT,
                    allocation_status TEXT NOT NULL,
                    recovery_status TEXT NOT NULL,
                    observation_method TEXT NOT NULL,
                    recommended_viewer TEXT NOT NULL,
                    provenance_chain TEXT NOT NULL,
                    content_reference TEXT
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_art_case ON artifacts(case_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_art_ev ON artifacts(evidence_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_art_job ON artifacts(processing_job_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_art_cat ON artifacts(category);")
            conn.commit()

    def _row_to_artifact(self, row: sqlite3.Row) -> Artifact:
        provenance_dict = json.loads(row["provenance_chain"])
        provenance = ProvenanceEnvelope(**provenance_dict)
        return Artifact(
            artifact_id=row["artifact_id"],
            case_id=row["case_id"],
            evidence_id=row["evidence_id"],
            processing_job_id=row["processing_job_id"],
            filename=row["filename"],
            path_within_source=row["path_within_source"],
            category=ArtifactCategory(row["category"]),
            mime_type=row["mime_type"],
            file_extension=row["file_extension"],
            size_bytes=row["size_bytes"],
            sha256=row["sha256"],
            created_at_observed=row["created_at_observed"],
            modified_at_observed=row["modified_at_observed"],
            accessed_at_observed=row["accessed_at_observed"],
            allocation_status=AllocationStatus(row["allocation_status"]),
            recovery_status=RecoveryStatus(row["recovery_status"]),
            observation_method=row["observation_method"],
            recommended_viewer=ViewerType(row["recommended_viewer"]),
            provenance_chain=provenance,
            content_reference=row["content_reference"]
        )

    def save(self, artifact: Artifact) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO artifacts (
                    artifact_id, case_id, evidence_id, processing_job_id,
                    filename, path_within_source, category, mime_type,
                    file_extension, size_bytes, sha256, created_at_observed,
                    modified_at_observed, accessed_at_observed, allocation_status,
                    recovery_status, observation_method, recommended_viewer,
                    provenance_chain, content_reference
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    case_id=excluded.case_id,
                    evidence_id=excluded.evidence_id,
                    processing_job_id=excluded.processing_job_id,
                    filename=excluded.filename,
                    path_within_source=excluded.path_within_source,
                    category=excluded.category,
                    mime_type=excluded.mime_type,
                    file_extension=excluded.file_extension,
                    size_bytes=excluded.size_bytes,
                    sha256=excluded.sha256,
                    created_at_observed=excluded.created_at_observed,
                    modified_at_observed=excluded.modified_at_observed,
                    accessed_at_observed=excluded.accessed_at_observed,
                    allocation_status=excluded.allocation_status,
                    recovery_status=excluded.recovery_status,
                    observation_method=excluded.observation_method,
                    recommended_viewer=excluded.recommended_viewer,
                    provenance_chain=excluded.provenance_chain,
                    content_reference=excluded.content_reference
            """, (
                artifact.artifact_id,
                artifact.case_id,
                artifact.evidence_id,
                artifact.processing_job_id,
                artifact.filename,
                artifact.path_within_source,
                artifact.category.value,
                artifact.mime_type,
                artifact.file_extension,
                artifact.size_bytes,
                artifact.sha256,
                artifact.created_at_observed,
                artifact.modified_at_observed,
                artifact.accessed_at_observed,
                artifact.allocation_status.value,
                artifact.recovery_status.value,
                artifact.observation_method,
                artifact.recommended_viewer.value,
                json.dumps(artifact.provenance_chain.model_dump()),
                artifact.content_reference
            ))
            conn.commit()

    def get_by_id(self, artifact_id: str) -> Optional[Artifact]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM artifacts WHERE artifact_id = ?;", (artifact_id,)).fetchone()
            if not row:
                return None
            return self._row_to_artifact(row)

    def list_by_case(
        self,
        case_id: str,
        filters: Optional[ArtifactFilterParams] = None
    ) -> List[Artifact]:
        with self._get_connection() as conn:
            query = "SELECT * FROM artifacts WHERE case_id = ?"
            params: List[Any] = [case_id]

            if filters:
                if filters.category:
                    query += " AND category = ?"
                    params.append(filters.category.value)
                if filters.mime_type:
                    query += " AND mime_type = ?"
                    params.append(filters.mime_type)
                if filters.filename:
                    query += " AND filename LIKE ?"
                    params.append(f"%{filters.filename}%")
                if filters.allocation_status:
                    query += " AND allocation_status = ?"
                    params.append(filters.allocation_status.value)
                if filters.recovery_status:
                    query += " AND recovery_status = ?"
                    params.append(filters.recovery_status.value)
                if filters.evidence_id:
                    query += " AND evidence_id = ?"
                    params.append(filters.evidence_id)
                if filters.processing_job_id:
                    query += " AND processing_job_id = ?"
                    params.append(filters.processing_job_id)

            query += " ORDER BY artifact_id ASC;"
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_artifact(r) for r in rows]

    def delete_by_job(self, processing_job_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM artifacts WHERE processing_job_id = ?;", (processing_job_id,))
            conn.commit()


class InMemoryArtifactRepository(ArtifactRepository):
    def __init__(self):
        self._artifacts: Dict[str, Artifact] = {}

    def save(self, artifact: Artifact) -> None:
        self._artifacts[artifact.artifact_id] = artifact

    def get_by_id(self, artifact_id: str) -> Optional[Artifact]:
        return self._artifacts.get(artifact_id)

    def list_by_case(
        self,
        case_id: str,
        filters: Optional[ArtifactFilterParams] = None
    ) -> List[Artifact]:
        results = [a for a in self._artifacts.values() if a.case_id == case_id]
        if filters:
            if filters.category:
                results = [a for a in results if a.category == filters.category]
            if filters.mime_type:
                results = [a for a in results if a.mime_type == filters.mime_type]
            if filters.filename:
                results = [a for a in results if filters.filename.lower() in a.filename.lower()]
            if filters.allocation_status:
                results = [a for a in results if a.allocation_status == filters.allocation_status]
            if filters.recovery_status:
                results = [a for a in results if a.recovery_status == filters.recovery_status]
            if filters.evidence_id:
                results = [a for a in results if a.evidence_id == filters.evidence_id]
            if filters.processing_job_id:
                results = [a for a in results if a.processing_job_id == filters.processing_job_id]
        return sorted(results, key=lambda x: x.artifact_id)

    def delete_by_job(self, processing_job_id: str) -> None:
        keys_to_del = [k for k, v in self._artifacts.items() if v.processing_job_id == processing_job_id]
        for k in keys_to_del:
            del self._artifacts[k]
