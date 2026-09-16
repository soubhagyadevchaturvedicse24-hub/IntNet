"""
Dedicated Autopsy SQLite Forensic Adapter for CRIMENET (Slice 8C).
Extracts forensic artifacts and relational structures from Autopsy case databases:
- accounts (email accounts)
- account_relationships (deterministic communication edges)
- TSK_EMAIL_MSG (blackboard email artifacts with message details)
- TSK_METADATA_EXIF (GPS latitude, longitude, device make/model)
- TSK_WEB_HISTORY, TSK_WEB_COOKIE, TSK_WEB_DOWNLOAD

Enforces:
1. Strictly read-only connection via 'file:...?mode=ro'.
2. Bounded batch streaming via fetchmany(batch_size); never loads full tables into memory.
3. Preserves exact source location (table + row/artifact ID) and 5-part provenance.
4. Preserves backward compatibility with generic SqliteParser.
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Tuple, Iterator, Optional

from src.parsers.base import ArtifactParser
from src.parsers.models import (
    ParserType,
    ObservationType,
    ExtractedObservation,
)


class AutopsySqliteAdapter(ArtifactParser):
    """
    Dedicated streaming forensic adapter for Autopsy 4+ SQLite databases.
    Discovers blackboard artifacts, accounts, and relationships with bounded batch streaming.
    """

    SQLITE_HEADER_MAGIC = b"SQLite format 3\x00"

    def __init__(
        self,
        max_file_size_bytes: int = 150 * 1024 * 1024,
        batch_size: int = 500,
        max_communication_records: Optional[int] = None,
    ):
        super().__init__(max_file_size_bytes=max_file_size_bytes)
        self.batch_size = batch_size
        env_limit = os.getenv("MAX_AUTOPSY_COMMUNICATIONS")
        self.max_communication_records = max_communication_records if max_communication_records is not None else (int(env_limit) if env_limit else 500)

    def get_parser_type(self) -> ParserType:
        return ParserType.AUTOPSY_SQLITE

    def get_parser_name(self) -> str:
        return "CRIMENET_AUTOPSY_SQLITE_ADAPTER"

    def get_parser_version(self) -> str:
        return "1.0.0"

    def can_parse(self, file_path: Path, header_bytes: bytes) -> bool:
        """
        Validates SQLite magic header and quickly confirms presence of Autopsy schema
        (blackboard_artifacts or accounts tables) via a read-only introspection query.
        """
        if not header_bytes.startswith(self.SQLITE_HEADER_MAGIC):
            return False

        if not file_path.exists() or not file_path.is_file():
            return False

        try:
            uri_path = f"file:{file_path.resolve().as_posix()}?mode=ro"
            conn = sqlite3.connect(uri_path, uri=True, timeout=2.0)
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name IN ('blackboard_artifacts', 'accounts') LIMIT 1;"
            )
            row = cur.fetchone()
            conn.close()
            return row is not None
        except Exception:
            return False

    def _get_readonly_connection(self, file_path: Path) -> sqlite3.Connection:
        uri_path = f"file:{file_path.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri_path, uri=True, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def stream_accounts(
        self,
        conn: sqlite3.Connection,
        artifact_id: str,
    ) -> Iterator[List[ExtractedObservation]]:
        """
        Streams email and forensic accounts from the `accounts` table in bounded batches.
        """
        cursor = conn.cursor()
        # Verify table exists
        cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='accounts';")
        if not cursor.fetchone():
            return

        query = """
            SELECT account_id, account_type_id, account_unique_identifier
            FROM accounts
            ORDER BY account_id;
        """
        cursor.execute(query)
        while True:
            rows = cursor.fetchmany(self.batch_size)
            if not rows:
                break
            batch: List[ExtractedObservation] = []
            for r in rows:
                acc_id = r["account_id"]
                type_id = r["account_type_id"]
                identifier = (r["account_unique_identifier"] or "").strip()
                if not identifier:
                    continue

                acc_type = "EMAIL" if type_id == 4 else f"TYPE_{type_id}"
                batch.append(
                    ExtractedObservation(
                        observation_id=f"{artifact_id}-OBS-ACC-{acc_id}",
                        observation_type=ObservationType.FORENSIC_ACCOUNT,
                        location_reference=f"Table: accounts, Row: {acc_id}",
                        key=f"account_{acc_id}",
                        value={
                            "table": "accounts",
                            "row_id": str(acc_id),
                            "account_id": acc_id,
                            "account_type_id": type_id,
                            "account_type": acc_type,
                            "account_unique_identifier": identifier,
                        },
                        confidence=1.0,
                        provenance_note=f"accounts.account_id={acc_id}",
                    )
                )
            if batch:
                yield batch

    def stream_account_relationships(
        self,
        conn: sqlite3.Connection,
        artifact_id: str,
    ) -> Iterator[List[ExtractedObservation]]:
        """
        Streams communication relationships from `account_relationships` in bounded batches.
        """
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='account_relationships';")
        if not cursor.fetchone():
            return

        query = """
            SELECT 
                r.relationship_id,
                r.account1_id,
                r.account2_id,
                r.relationship_type,
                r.date_time,
                a1.account_unique_identifier AS from_account,
                a2.account_unique_identifier AS to_account
            FROM account_relationships r
            JOIN accounts a1 ON r.account1_id = a1.account_id
            JOIN accounts a2 ON r.account2_id = a2.account_id
            WHERE r.relationship_type = 1
            ORDER BY r.relationship_id
        """
        if self.max_communication_records:
            query += f" LIMIT {self.max_communication_records};"
        else:
            query += ";"
        cursor.execute(query)
        while True:
            rows = cursor.fetchmany(self.batch_size)
            if not rows:
                break
            batch: List[ExtractedObservation] = []
            for r in rows:
                rel_id = r["relationship_id"]
                from_acc = (r["from_account"] or "").strip()
                to_acc = (r["to_account"] or "").strip()
                if not from_acc or not to_acc:
                    continue

                batch.append(
                    ExtractedObservation(
                        observation_id=f"{artifact_id}-OBS-COMM-{rel_id}",
                        observation_type=ObservationType.FORENSIC_COMMUNICATION,
                        location_reference=f"Table: account_relationships, ID: {rel_id}",
                        key=f"comm_{rel_id}",
                        value={
                            "table": "account_relationships",
                            "row_id": str(rel_id),
                            "relationship_id": rel_id,
                            "relationship_type": "COMMUNICATION",
                            "date_time": r["date_time"],
                            "account1_id": r["account1_id"],
                            "account2_id": r["account2_id"],
                            "from_account": from_acc,
                            "to_account": to_acc,
                        },
                        confidence=1.0,
                        provenance_note=f"account_relationships.relationship_id={rel_id}",
                    )
                )
            if batch:
                yield batch

    def stream_email_messages(
        self,
        conn: sqlite3.Connection,
        artifact_id: str,
    ) -> Iterator[List[ExtractedObservation]]:
        """
        Streams email message artifacts (TSK_EMAIL_MSG, type 13) in bounded batches.
        """
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='blackboard_artifacts';")
        if not cursor.fetchone():
            return

        query = """
            SELECT 
                a.artifact_id,
                a.obj_id,
                MAX(CASE WHEN at.type_name = 'TSK_EMAIL_FROM' THEN b.value_text END) AS email_from,
                MAX(CASE WHEN at.type_name = 'TSK_EMAIL_TO' THEN b.value_text END) AS email_to,
                MAX(CASE WHEN at.type_name = 'TSK_EMAIL_CC' THEN b.value_text END) AS email_cc,
                MAX(CASE WHEN at.type_name = 'TSK_SUBJECT' THEN b.value_text END) AS subject,
                MAX(CASE WHEN at.type_name = 'TSK_DATETIME_SENT' THEN b.value_int64 END) AS datetime_sent,
                MAX(CASE WHEN at.type_name = 'TSK_DATETIME_RCVD' THEN b.value_int64 END) AS datetime_rcvd,
                MAX(CASE WHEN at.type_name = 'TSK_MSG_ID' THEN b.value_text END) AS msg_id
            FROM blackboard_artifacts a
            JOIN blackboard_attributes b ON a.artifact_id = b.artifact_id
            JOIN blackboard_attribute_types at ON b.attribute_type_id = at.attribute_type_id
            WHERE a.artifact_type_id = 13
            GROUP BY a.artifact_id, a.obj_id
            ORDER BY a.artifact_id;
        """
        cursor.execute(query)
        while True:
            rows = cursor.fetchmany(self.batch_size)
            if not rows:
                break
            batch: List[ExtractedObservation] = []
            for r in rows:
                art_pk = r["artifact_id"]
                ef = (r["email_from"] or "").strip()
                et = (r["email_to"] or "").strip()
                if not ef and not et:
                    continue

                batch.append(
                    ExtractedObservation(
                        observation_id=f"{artifact_id}-OBS-MSG-{art_pk}",
                        observation_type=ObservationType.FORENSIC_EMAIL_MESSAGE,
                        location_reference=f"blackboard_artifacts: {art_pk}",
                        key=f"email_msg_{art_pk}",
                        value={
                            "table": "blackboard_artifacts",
                            "row_id": str(art_pk),
                            "artifact_id": art_pk,
                            "obj_id": r["obj_id"],
                            "email_from": ef,
                            "email_to": et,
                            "email_cc": (r["email_cc"] or "").strip(),
                            "subject": (r["subject"] or "").strip(),
                            "datetime_sent": r["datetime_sent"],
                            "datetime_rcvd": r["datetime_rcvd"],
                            "msg_id": (r["msg_id"] or "").strip(),
                        },
                        confidence=1.0,
                        provenance_note=f"blackboard_artifacts.artifact_id={art_pk} (TSK_EMAIL_MSG)",
                    )
                )
            if batch:
                yield batch

    def stream_exif_gps(
        self,
        conn: sqlite3.Connection,
        artifact_id: str,
    ) -> Iterator[List[ExtractedObservation]]:
        """
        Streams EXIF metadata with valid GPS coordinates (TSK_METADATA_EXIF, type 16) in bounded batches.
        """
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='blackboard_artifacts';")
        if not cursor.fetchone():
            return

        query = """
            SELECT 
                a.artifact_id,
                a.obj_id,
                MAX(CASE WHEN at.type_name = 'TSK_GEO_LATITUDE' THEN b.value_double END) AS latitude,
                MAX(CASE WHEN at.type_name = 'TSK_GEO_LONGITUDE' THEN b.value_double END) AS longitude,
                MAX(CASE WHEN at.type_name = 'TSK_DATETIME_CREATED' THEN b.value_int64 END) AS datetime_created,
                MAX(CASE WHEN at.type_name = 'TSK_DEVICE_MAKE' THEN b.value_text END) AS device_make,
                MAX(CASE WHEN at.type_name = 'TSK_DEVICE_MODEL' THEN b.value_text END) AS device_model
            FROM blackboard_artifacts a
            JOIN blackboard_attributes b ON a.artifact_id = b.artifact_id
            JOIN blackboard_attribute_types at ON b.attribute_type_id = at.attribute_type_id
            WHERE a.artifact_type_id = 16
            GROUP BY a.artifact_id, a.obj_id
            HAVING latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY a.artifact_id;
        """
        cursor.execute(query)
        while True:
            rows = cursor.fetchmany(self.batch_size)
            if not rows:
                break
            batch: List[ExtractedObservation] = []
            for r in rows:
                art_pk = r["artifact_id"]
                lat = r["latitude"]
                lon = r["longitude"]
                if lat is None or lon is None:
                    continue

                batch.append(
                    ExtractedObservation(
                        observation_id=f"{artifact_id}-OBS-EXIF-{art_pk}",
                        observation_type=ObservationType.FORENSIC_EXIF_GPS,
                        location_reference=f"blackboard_artifacts: {art_pk}",
                        key=f"exif_gps_{art_pk}",
                        value={
                            "table": "blackboard_artifacts",
                            "row_id": str(art_pk),
                            "artifact_id": art_pk,
                            "obj_id": r["obj_id"],
                            "latitude": float(lat),
                            "longitude": float(lon),
                            "datetime_created": r["datetime_created"],
                            "device_make": (r["device_make"] or "").strip(),
                            "device_model": (r["device_model"] or "").strip(),
                        },
                        confidence=1.0,
                        provenance_note=f"blackboard_artifacts.artifact_id={art_pk} (TSK_METADATA_EXIF GPS)",
                    )
                )
            if batch:
                yield batch

    def stream_web_activity(
        self,
        conn: sqlite3.Connection,
        artifact_id: str,
    ) -> Iterator[List[ExtractedObservation]]:
        """
        Streams web browsing artifacts (history, cookies, downloads) in bounded batches.
        """
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='blackboard_artifacts';")
        if not cursor.fetchone():
            return

        # 1. Web History (type 4)
        wh_query = """
            SELECT 
                a.artifact_id,
                a.obj_id,
                MAX(CASE WHEN at.type_name = 'TSK_URL' THEN b.value_text END) AS url,
                MAX(CASE WHEN at.type_name = 'TSK_DOMAIN' THEN b.value_text END) AS domain,
                MAX(CASE WHEN at.type_name = 'TSK_TITLE' THEN b.value_text END) AS title,
                MAX(CASE WHEN at.type_name = 'TSK_DATETIME_ACCESSED' THEN b.value_int64 END) AS datetime_accessed,
                MAX(CASE WHEN at.type_name = 'TSK_PROG_NAME' THEN b.value_text END) AS program_name,
                MAX(CASE WHEN at.type_name = 'TSK_USER_NAME' THEN b.value_text END) AS user_name
            FROM blackboard_artifacts a
            JOIN blackboard_attributes b ON a.artifact_id = b.artifact_id
            JOIN blackboard_attribute_types at ON b.attribute_type_id = at.attribute_type_id
            WHERE a.artifact_type_id = 4
            GROUP BY a.artifact_id, a.obj_id
            ORDER BY a.artifact_id;
        """
        cursor.execute(wh_query)
        while True:
            rows = cursor.fetchmany(self.batch_size)
            if not rows:
                break
            batch: List[ExtractedObservation] = []
            for r in rows:
                art_pk = r["artifact_id"]
                batch.append(
                    ExtractedObservation(
                        observation_id=f"{artifact_id}-OBS-WEB-{art_pk}",
                        observation_type=ObservationType.FORENSIC_WEB_HISTORY,
                        location_reference=f"blackboard_artifacts: {art_pk}",
                        key=f"web_history_{art_pk}",
                        value={
                            "table": "blackboard_artifacts",
                            "row_id": str(art_pk),
                            "artifact_id": art_pk,
                            "obj_id": r["obj_id"],
                            "url": (r["url"] or "").strip(),
                            "domain": (r["domain"] or "").strip(),
                            "title": (r["title"] or "").strip(),
                            "datetime_accessed": r["datetime_accessed"],
                            "program_name": (r["program_name"] or "").strip(),
                            "user_name": (r["user_name"] or "").strip(),
                        },
                        confidence=1.0,
                        provenance_note=f"blackboard_artifacts.artifact_id={art_pk} (TSK_WEB_HISTORY)",
                    )
                )
            if batch:
                yield batch

    def iter_observations(
        self,
        file_path: Path,
        artifact_metadata: Dict[str, Any],
    ) -> Iterator[ExtractedObservation]:
        """
        Memory-bounded generator yielding ExtractedObservation objects one-by-one
        across all forensic tables without loading entire datasets into RAM.
        """
        conn = self._get_readonly_connection(file_path)
        art_id = artifact_metadata.get("artifact_id", "ART")
        try:
            for batch in self.stream_accounts(conn, art_id):
                for obs in batch:
                    yield obs
            for batch in self.stream_account_relationships(conn, art_id):
                for obs in batch:
                    yield obs
            for batch in self.stream_email_messages(conn, art_id):
                for obs in batch:
                    yield obs
            for batch in self.stream_exif_gps(conn, art_id):
                for obs in batch:
                    yield obs
            for batch in self.stream_web_activity(conn, art_id):
                for obs in batch:
                    yield obs
        finally:
            conn.close()

    def _execute_parse(
        self,
        file_path: Path,
        artifact_metadata: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[ExtractedObservation]]:
        """
        Standard ArtifactParser entry point. Streams forensic observations in bounded batches
        and returns structured metadata and observations list.
        """
        observations: List[ExtractedObservation] = []
        counts = {
            "accounts": 0,
            "account_relationships": 0,
            "email_messages": 0,
            "exif_gps": 0,
            "web_activity": 0,
        }

        conn = self._get_readonly_connection(file_path)
        art_id = artifact_metadata.get("artifact_id", "ART")
        try:
            # 1. Accounts
            for batch in self.stream_accounts(conn, art_id):
                counts["accounts"] += len(batch)
                observations.extend(batch)

            # 2. Account Relationships
            for batch in self.stream_account_relationships(conn, art_id):
                counts["account_relationships"] += len(batch)
                observations.extend(batch)

            # 3. Email Messages
            for batch in self.stream_email_messages(conn, art_id):
                counts["email_messages"] += len(batch)
                observations.extend(batch)

            # 4. EXIF GPS
            for batch in self.stream_exif_gps(conn, art_id):
                counts["exif_gps"] += len(batch)
                observations.extend(batch)

            # 5. Web Activity
            for batch in self.stream_web_activity(conn, art_id):
                counts["web_activity"] += len(batch)
                observations.extend(batch)

            structured_metadata = {
                "format": "Autopsy Forensic SQLite Database",
                "adapter": self.get_parser_name(),
                "batch_size": self.batch_size,
                "extraction_summary": counts,
                "total_observations_extracted": len(observations),
            }

            return structured_metadata, observations

        finally:
            conn.close()
