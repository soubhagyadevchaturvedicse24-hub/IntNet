"""
Base Artifact Parser & Abstract Interface for CRIMENET (Slice 8A).
Provides core validation mechanisms:
- Header magic byte detection (never trusts file extensions or MIME types)
- Configurable size safeguard enforcement (prototype default 50 MB, recorded as configuration)
- Non-destructive streaming SHA-256 computation
- Graceful failure containment (isolated parser errors never cascade into pipeline failure)
"""

import abc
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from src.parsers.models import (
    ParsedArtifact,
    ParserMetadata,
    ParserType,
    ParsingStatus,
    ObservationType,
    ExtractedObservation,
)


class ArtifactParser(abc.ABC):
    """
    Abstract Base Class for modular deep artifact parsers.
    Subclasses implement format-specific decoding and observation extraction.
    """

    def __init__(self, max_file_size_bytes: int = 50 * 1024 * 1024):
        # Configurable prototype safeguard constraint (not a forensic limitation)
        self.max_file_size_bytes = max_file_size_bytes

    @abc.abstractmethod
    def get_parser_type(self) -> ParserType:
        """Returns the specific ParserType enum."""
        pass

    @abc.abstractmethod
    def get_parser_name(self) -> str:
        """Returns the name of the parser engine."""
        pass

    @abc.abstractmethod
    def get_parser_version(self) -> str:
        """Returns the parser engine version."""
        pass

    @abc.abstractmethod
    def can_parse(self, file_path: Path, header_bytes: bytes) -> bool:
        """
        Inspects header magic bytes to verify if this parser natively supports the format.
        Must NOT rely on file extensions.
        """
        pass

    @abc.abstractmethod
    def _execute_parse(
        self,
        file_path: Path,
        artifact_metadata: Dict[str, Any]
    ) -> tuple[Dict[str, Any], list[ExtractedObservation]]:
        """
        Performs format-specific parsing and returns (structured_metadata, observations).
        Subclasses implement this method.
        """
        pass

    @staticmethod
    def calculate_file_sha256(file_path: Path) -> str:
        """Computes SHA-256 hash in 2MB blocks without modifying file."""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(2 * 1024 * 1024):
                sha.update(chunk)
        return sha.hexdigest()

    @staticmethod
    def read_header_bytes(file_path: Path, num_bytes: int = 64) -> bytes:
        """Safely reads header magic bytes."""
        if not file_path.exists() or not file_path.is_file():
            return b""
        with open(file_path, "rb") as f:
            return f.read(num_bytes)

    def parse(self, file_path: Path, artifact_metadata: Dict[str, Any]) -> ParsedArtifact:
        """
        Main entry point for deep parsing.
        Wraps execution with integrity verification, size limits, and robust crash containment.
        """
        start_time = time.perf_counter()
        now_iso = datetime.now(timezone.utc).isoformat()

        artifact_id = artifact_metadata.get("artifact_id", "UNKNOWN_ARTIFACT")
        case_id = artifact_metadata.get("case_id", "UNKNOWN_CASE")
        expected_sha256 = artifact_metadata.get("sha256", "")

        # 1. Existence and size verification
        if not file_path.exists() or not file_path.is_file():
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ParsedArtifact(
                artifact_id=artifact_id,
                case_id=case_id,
                status=ParsingStatus.FAILED,
                parser_metadata=ParserMetadata(
                    parser_type=self.get_parser_type(),
                    parser_name=self.get_parser_name(),
                    parser_version=self.get_parser_version(),
                    parsed_at=now_iso,
                    execution_duration_ms=round(duration_ms, 2),
                    file_size_bytes=0,
                    configured_size_ceiling_bytes=self.max_file_size_bytes,
                ),
                computed_sha256="",
                integrity_verified=False,
                error_message=f"Target file does not exist: {file_path}",
            )

        file_size = file_path.stat().st_size

        # 2. Configurable size limit enforcement
        if file_size > self.max_file_size_bytes:
            duration_ms = (time.perf_counter() - start_time) * 1000
            computed_sha256 = self.calculate_file_sha256(file_path)
            integrity_verified = (computed_sha256.lower() == expected_sha256.lower()) if expected_sha256 else True
            return ParsedArtifact(
                artifact_id=artifact_id,
                case_id=case_id,
                status=ParsingStatus.OVERSIZED,
                parser_metadata=ParserMetadata(
                    parser_type=self.get_parser_type(),
                    parser_name=self.get_parser_name(),
                    parser_version=self.get_parser_version(),
                    parsed_at=now_iso,
                    execution_duration_ms=round(duration_ms, 2),
                    file_size_bytes=file_size,
                    configured_size_ceiling_bytes=self.max_file_size_bytes,
                ),
                computed_sha256=computed_sha256,
                integrity_verified=integrity_verified,
                error_message=(
                    f"File size ({file_size} bytes) exceeds configured prototype ceiling "
                    f"({self.max_file_size_bytes} bytes). Configurable constraint reached."
                ),
            )

        # 3. Cryptographic hash re-verification
        computed_sha256 = self.calculate_file_sha256(file_path)
        integrity_verified = (computed_sha256.lower() == expected_sha256.lower()) if expected_sha256 else True

        # 4. Header magic byte validation
        header = self.read_header_bytes(file_path, 64)
        if not self.can_parse(file_path, header):
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ParsedArtifact(
                artifact_id=artifact_id,
                case_id=case_id,
                status=ParsingStatus.UNSUPPORTED,
                parser_metadata=ParserMetadata(
                    parser_type=self.get_parser_type(),
                    parser_name=self.get_parser_name(),
                    parser_version=self.get_parser_version(),
                    parsed_at=now_iso,
                    execution_duration_ms=round(duration_ms, 2),
                    file_size_bytes=file_size,
                    configured_size_ceiling_bytes=self.max_file_size_bytes,
                ),
                computed_sha256=computed_sha256,
                integrity_verified=integrity_verified,
                error_message="Header magic byte signature does not match required format.",
            )

        # 5. Format-specific execution with crash isolation
        try:
            structured_meta, observations = self._execute_parse(file_path, artifact_metadata)
            status = ParsingStatus.SUCCESS
            error_message = None
        except Exception as e:
            # Isolated error containment — NEVER propagate exception to fail the pipeline
            structured_meta = {}
            observations = []
            status = ParsingStatus.CORRUPTED if "corrupt" in str(e).lower() or "malformed" in str(e).lower() else ParsingStatus.FAILED
            error_message = f"Parser execution caught error: {type(e).__name__}: {str(e)}"

        duration_ms = (time.perf_counter() - start_time) * 1000

        return ParsedArtifact(
            artifact_id=artifact_id,
            case_id=case_id,
            status=status,
            parser_metadata=ParserMetadata(
                parser_type=self.get_parser_type(),
                parser_name=self.get_parser_name(),
                parser_version=self.get_parser_version(),
                parsed_at=now_iso,
                execution_duration_ms=round(duration_ms, 2),
                file_size_bytes=file_size,
                configured_size_ceiling_bytes=self.max_file_size_bytes,
            ),
            computed_sha256=computed_sha256,
            integrity_verified=integrity_verified,
            structured_metadata=structured_meta,
            observations=observations,
            error_message=error_message,
        )
