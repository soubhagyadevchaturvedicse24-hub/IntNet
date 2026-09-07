"""
SQLite Forensic Database Parser for CRIMENET (Slice 8A).
Extracts database metadata, table schemas, bounded row counts, and bounded 10-row samples.
Connects strictly using read-only URI mode ('file:...?mode=ro') to prevent any mutation.

NOTE: In accordance with Slice 8A design constraints, row counts are NOT treated
as unconditionally free; a query bound (max 10,000) protects against expensive full table scans.
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Tuple

from src.parsers.base import ArtifactParser
from src.parsers.models import (
    ParserType,
    ObservationType,
    ExtractedObservation,
)


class SqliteParser(ArtifactParser):
    """
    Forensic parser for SQLite 3 database files.
    Enforces header magic verification, read-only connection, and bounded data reading.
    """

    SQLITE_HEADER_MAGIC = b"SQLite format 3\x00"

    def __init__(
        self,
        max_file_size_bytes: int = 50 * 1024 * 1024,
        sample_row_limit: int = 10,
        max_count_threshold: int = 10000,
    ):
        super().__init__(max_file_size_bytes=max_file_size_bytes)
        self.sample_row_limit = sample_row_limit
        self.max_count_threshold = max_count_threshold

    def get_parser_type(self) -> ParserType:
        return ParserType.SQLITE

    def get_parser_name(self) -> str:
        return "CRIMENET_SQLITE_FORENSIC_PARSER"

    def get_parser_version(self) -> str:
        return "1.0.0"

    def can_parse(self, file_path: Path, header_bytes: bytes) -> bool:
        """Validates SQLite format 3 magic signature (first 16 bytes)."""
        return header_bytes.startswith(self.SQLITE_HEADER_MAGIC)

    def _execute_parse(
        self,
        file_path: Path,
        artifact_metadata: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[ExtractedObservation]]:
        """
        Parses SQLite database in read-only mode, extracting schema,
        bounded counts, and bounded sample rows.
        """
        observations: List[ExtractedObservation] = []
        artifact_id = artifact_metadata.get("artifact_id", "ART")

        # Open in strictly read-only mode using URI
        uri_path = f"file:{file_path.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri_path, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row

        try:
            cursor = conn.cursor()

            # 1. Database-Level Statistics & PRAGMAs
            pragma_stats = {}
            for pragma_name in ["page_size", "page_count", "encoding", "freelist_count", "user_version", "schema_version"]:
                try:
                    cursor.execute(f"PRAGMA {pragma_name};")
                    row = cursor.fetchone()
                    pragma_stats[pragma_name] = row[0] if row else None
                except Exception:
                    pragma_stats[pragma_name] = None

            observations.append(
                ExtractedObservation(
                    observation_id=f"{artifact_id}-OBS-SQLITE-PRAGMAS",
                    observation_type=ObservationType.SQLITE_STATS,
                    location_reference="Database Header PRAGMAs",
                    key="pragma_metadata",
                    value=pragma_stats,
                    provenance_note="sqlite3:PRAGMA introspection",
                )
            )

            # 2. Schema Discovery (Tables, Views, Indexes)
            cursor.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name;"
            )
            schema_objects = cursor.fetchall()

            tables: List[str] = []
            views: List[str] = []
            indexes: List[str] = []

            for obj in schema_objects:
                obj_type = obj["type"]
                obj_name = obj["name"]
                if obj_type == "table":
                    tables.append(obj_name)
                elif obj_type == "view":
                    views.append(obj_name)
                elif obj_type == "index":
                    indexes.append(obj_name)

            # 3. Table Column Introspection, Bounded Counts, and Bounded Sample Rows
            table_details = {}

            for table_name in tables:
                # Sanitize table identifier for PRAGMA (avoid injection)
                clean_table = table_name.replace('"', '""')

                # Column info
                cursor.execute(f'PRAGMA table_info("{clean_table}");')
                col_rows = cursor.fetchall()
                columns = [
                    {
                        "cid": c["cid"],
                        "name": c["name"],
                        "type": c["type"],
                        "notnull": bool(c["notnull"]),
                        "dflt_value": c["dflt_value"],
                        "pk": bool(c["pk"]),
                    }
                    for c in col_rows
                ]

                # Schema observation
                observations.append(
                    ExtractedObservation(
                        observation_id=f"{artifact_id}-OBS-SCHEMA-{table_name}",
                        observation_type=ObservationType.SQLITE_SCHEMA,
                        location_reference=f"Table: {table_name}",
                        key=f"schema_{table_name}",
                        value={"columns": columns},
                        provenance_note=f"sqlite3:PRAGMA table_info({table_name})",
                    )
                )

                # Bounded row count check (Protection against expensive full-table scans)
                # Query up to threshold + 1
                cursor.execute(
                    f'SELECT COUNT(*) FROM (SELECT 1 FROM "{clean_table}" LIMIT {self.max_count_threshold + 1});'
                )
                count_check = cursor.fetchone()[0]

                if count_check > self.max_count_threshold:
                    row_count_display = f">{self.max_count_threshold} (bounded estimate)"
                    is_exact_count = False
                    approx_count = self.max_count_threshold
                else:
                    row_count_display = str(count_check)
                    is_exact_count = True
                    approx_count = count_check

                # Bounded sample rows (strictly capped at sample_row_limit)
                cursor.execute(f'SELECT * FROM "{clean_table}" LIMIT {self.sample_row_limit};')
                sample_rows = cursor.fetchall()
                sample_data = []
                for s_row in sample_rows:
                    row_dict = {}
                    for col in columns:
                        val = s_row[col["name"]]
                        # Ensure bytes or non-serializable objects are safe
                        if isinstance(val, bytes):
                            row_dict[col["name"]] = f"<BLOB {len(val)} bytes>"
                        else:
                            row_dict[col["name"]] = val
                    sample_data.append(row_dict)

                observations.append(
                    ExtractedObservation(
                        observation_id=f"{artifact_id}-OBS-SAMPLE-{table_name}",
                        observation_type=ObservationType.SQLITE_SAMPLE_ROWS,
                        location_reference=f"Table: {table_name}",
                        key=f"sample_rows_{table_name}",
                        value={
                            "row_count": approx_count,
                            "is_exact_count": is_exact_count,
                            "count_display": row_count_display,
                            "sample_limit": self.sample_row_limit,
                            "returned_rows": len(sample_data),
                            "rows": sample_data,
                        },
                        provenance_note=(
                            f"sqlite3:SELECT * FROM {table_name} LIMIT {self.sample_row_limit} "
                            f"(row count marked as {'exact' if is_exact_count else 'bounded estimate to avoid expensive scan'})"
                        ),
                    )
                )

                table_details[table_name] = {
                    "column_count": len(columns),
                    "columns": columns,
                    "row_count_display": row_count_display,
                    "is_exact_count": is_exact_count,
                    "sample_row_count": len(sample_data),
                    "sample_rows": sample_data,
                }

            structured_metadata = {
                "format": "SQLite 3",
                "pragma_stats": pragma_stats,
                "table_count": len(tables),
                "view_count": len(views),
                "index_count": len(indexes),
                "table_names": tables,
                "view_names": views,
                "index_names": indexes,
                "tables": table_details,
            }

            return structured_metadata, observations

        finally:
            conn.close()
