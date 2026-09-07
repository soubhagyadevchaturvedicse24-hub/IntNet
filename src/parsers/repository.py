"""
Parsed Artifact Repository for CRIMENET (Slice 8A).
Persists parsed artifact observations, structured metadata, and integrity results in SQLite.
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.parsers.models import (
    ParsedArtifact,
    ParserMetadata,
    ParserType,
    ParsingStatus,
    ExtractedObservation,
)


class SQLiteParsedArtifactRepository:
    """
    SQLite persistence layer for deep parsed artifact observations.
    Stores records in DATA/parsed_artifacts.db.
    """

    def __init__(self, db_path: str = "DATA/parsed_artifacts.db"):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS parsed_artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    parser_type TEXT NOT NULL,
                    parser_name TEXT NOT NULL,
                    parser_version TEXT NOT NULL,
                    parsed_at TEXT NOT NULL,
                    execution_duration_ms REAL NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    configured_size_ceiling_bytes INTEGER NOT NULL,
                    computed_sha256 TEXT NOT NULL,
                    integrity_verified INTEGER NOT NULL,
                    structured_metadata TEXT NOT NULL,
                    observations TEXT NOT NULL,
                    error_message TEXT
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_parsed_case ON parsed_artifacts(case_id);")
            conn.commit()

    def save(self, parsed: ParsedArtifact) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO parsed_artifacts (
                    artifact_id, case_id, status, parser_type, parser_name, parser_version,
                    parsed_at, execution_duration_ms, file_size_bytes, configured_size_ceiling_bytes,
                    computed_sha256, integrity_verified, structured_metadata, observations, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    case_id = excluded.case_id,
                    status = excluded.status,
                    parser_type = excluded.parser_type,
                    parser_name = excluded.parser_name,
                    parser_version = excluded.parser_version,
                    parsed_at = excluded.parsed_at,
                    execution_duration_ms = excluded.execution_duration_ms,
                    file_size_bytes = excluded.file_size_bytes,
                    configured_size_ceiling_bytes = excluded.configured_size_ceiling_bytes,
                    computed_sha256 = excluded.computed_sha256,
                    integrity_verified = excluded.integrity_verified,
                    structured_metadata = excluded.structured_metadata,
                    observations = excluded.observations,
                    error_message = excluded.error_message;
            """, (
                parsed.artifact_id,
                parsed.case_id,
                parsed.status.value,
                parsed.parser_metadata.parser_type.value,
                parsed.parser_metadata.parser_name,
                parsed.parser_metadata.parser_version,
                parsed.parser_metadata.parsed_at,
                parsed.parser_metadata.execution_duration_ms,
                parsed.parser_metadata.file_size_bytes,
                parsed.parser_metadata.configured_size_ceiling_bytes,
                parsed.computed_sha256,
                1 if parsed.integrity_verified else 0,
                json.dumps(parsed.structured_metadata),
                json.dumps([obs.model_dump() for obs in parsed.observations]),
                parsed.error_message,
            ))
            conn.commit()

    def get_by_id(self, artifact_id: str) -> Optional[ParsedArtifact]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM parsed_artifacts WHERE artifact_id = ?;", (artifact_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_model(row)

    def list_by_case(self, case_id: str) -> List[ParsedArtifact]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM parsed_artifacts WHERE case_id = ? ORDER BY parsed_at DESC;", (case_id,))
            rows = cursor.fetchall()
            return [self._row_to_model(r) for r in rows]

    def delete_by_id(self, artifact_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM parsed_artifacts WHERE artifact_id = ?;", (artifact_id,))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> ParsedArtifact:
        raw_meta = json.loads(row["structured_metadata"]) if row["structured_metadata"] else {}
        raw_obs = json.loads(row["observations"]) if row["observations"] else []

        observations = [ExtractedObservation(**o) for o in raw_obs]

        parser_meta = ParserMetadata(
            parser_type=ParserType(row["parser_type"]),
            parser_name=row["parser_name"],
            parser_version=row["parser_version"],
            parsed_at=row["parsed_at"],
            execution_duration_ms=row["execution_duration_ms"],
            file_size_bytes=row["file_size_bytes"],
            configured_size_ceiling_bytes=row["configured_size_ceiling_bytes"],
        )

        return ParsedArtifact(
            artifact_id=row["artifact_id"],
            case_id=row["case_id"],
            status=ParsingStatus(row["status"]),
            parser_metadata=parser_meta,
            computed_sha256=row["computed_sha256"],
            integrity_verified=bool(row["integrity_verified"]),
            structured_metadata=raw_meta,
            observations=observations,
            error_message=row["error_message"],
        )
