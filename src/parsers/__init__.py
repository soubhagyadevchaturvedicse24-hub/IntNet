"""
Deep Artifact Parsing Subsystem for CRIMENET (Slice 8A).
Exposes modular parsers for PDF, Image, and SQLite database artifacts.
"""

from src.parsers.models import (
    ParsingStatus,
    ParserType,
    ObservationType,
    ExtractedObservation,
    ParserMetadata,
    ParsedArtifact,
)
from src.parsers.base import ArtifactParser
from src.parsers.pdf_parser import PdfParser
from src.parsers.image_parser import ImageParser
from src.parsers.sqlite_parser import SqliteParser
from src.parsers.registry import ParserRegistry
from src.parsers.repository import SQLiteParsedArtifactRepository
from src.parsers.service import DeepParsingService

__all__ = [
    "ParsingStatus",
    "ParserType",
    "ObservationType",
    "ExtractedObservation",
    "ParserMetadata",
    "ParsedArtifact",
    "ArtifactParser",
    "PdfParser",
    "ImageParser",
    "SqliteParser",
    "ParserRegistry",
    "SQLiteParsedArtifactRepository",
    "DeepParsingService",
]
