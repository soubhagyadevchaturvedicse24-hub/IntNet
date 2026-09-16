"""
Parser Registry for CRIMENET (Slice 8A).
Dynamically dispatches incoming artifacts to specialized parsers by validating
header magic signatures, strictly bypassing untrusted client extensions and MIME types.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from src.parsers.base import ArtifactParser
from src.parsers.models import (
    ParserType,
    ParsingStatus,
    ParsedArtifact,
    ParserMetadata,
    ExtractedObservation,
)
from src.parsers.pdf_parser import PdfParser
from src.parsers.image_parser import ImageParser
from src.parsers.sqlite_parser import SqliteParser
from src.parsers.autopsy_adapter import AutopsySqliteAdapter


class UnsupportedParser(ArtifactParser):
    """Fallback parser returned when header magic matches no registered decoder."""

    def get_parser_type(self) -> ParserType:
        return ParserType.UNSUPPORTED

    def get_parser_name(self) -> str:
        return "CRIMENET_UNSUPPORTED_FALLBACK_PARSER"

    def get_parser_version(self) -> str:
        return "1.0.0"

    def can_parse(self, file_path: Path, header_bytes: bytes) -> bool:
        return True

    def _execute_parse(
        self,
        file_path: Path,
        artifact_metadata: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[ExtractedObservation]]:
        return {"note": "Unsupported format for deep parsing in Slice 8A."}, []

    def parse(self, file_path: Path, artifact_metadata: Dict[str, Any]) -> ParsedArtifact:
        res = super().parse(file_path, artifact_metadata)
        res.status = ParsingStatus.UNSUPPORTED
        res.error_message = "File format is not supported for deep parsing in Slice 8A."
        return res


class ParserRegistry:
    """
    Registry managing specialized artifact parsers and dynamic dispatch.
    """

    def __init__(
        self,
        parsers: Optional[List[ArtifactParser]] = None,
        max_file_size_bytes: int = 50 * 1024 * 1024,
    ):
        self.max_file_size_bytes = max_file_size_bytes
        if parsers:
            self._parsers = parsers
        else:
            self._parsers = [
                PdfParser(max_file_size_bytes=max_file_size_bytes),
                ImageParser(max_file_size_bytes=max_file_size_bytes),
                AutopsySqliteAdapter(max_file_size_bytes=max(max_file_size_bytes, 150 * 1024 * 1024)),
                SqliteParser(max_file_size_bytes=max_file_size_bytes),
            ]
        self._fallback_parser = UnsupportedParser(max_file_size_bytes=max_file_size_bytes)

    def register_parser(self, parser: ArtifactParser):
        """Registers a new parser implementation."""
        self._parsers.append(parser)

    def get_parser_for_file(self, file_path: Path) -> ArtifactParser:
        """
        Inspects header magic bytes (first 64 bytes) to determine the appropriate parser.
        Never relies on client-supplied extension or MIME type.
        """
        if not file_path.exists() or not file_path.is_file():
            return self._fallback_parser

        header = ArtifactParser.read_header_bytes(file_path, 64)
        for parser in self._parsers:
            if parser.can_parse(file_path, header):
                return parser

        return self._fallback_parser

    def get_parser_by_type(self, p_type: ParserType) -> Optional[ArtifactParser]:
        """Looks up registered parser by ParserType."""
        for p in self._parsers:
            if p.get_parser_type() == p_type:
                return p
        return None
