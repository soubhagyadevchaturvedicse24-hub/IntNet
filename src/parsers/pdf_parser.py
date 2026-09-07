"""
PDF Forensic Artifact Parser for CRIMENET (Slice 8A).
Extracts document metadata and bounded text observations from PDF files.
PDF text extraction is strictly treated as observed digital evidence with
page-level provenance, NEVER speculative intelligence.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple
from pypdf import PdfReader

from src.parsers.base import ArtifactParser
from src.parsers.models import (
    ParserType,
    ObservationType,
    ExtractedObservation,
)


class PdfParser(ArtifactParser):
    """
    Parser for Portable Document Format (PDF) files.
    Enforces %PDF- header magic check and bounded page/character extraction.
    """

    def __init__(
        self,
        max_file_size_bytes: int = 50 * 1024 * 1024,
        max_pages_extract: int = 20,
        max_chars_per_page: int = 5000,
    ):
        super().__init__(max_file_size_bytes=max_file_size_bytes)
        self.max_pages_extract = max_pages_extract
        self.max_chars_per_page = max_chars_per_page

    def get_parser_type(self) -> ParserType:
        return ParserType.PDF

    def get_parser_name(self) -> str:
        return "CRIMENET_PDF_OBSERVATION_PARSER"

    def get_parser_version(self) -> str:
        return "1.0.0"

    def can_parse(self, file_path: Path, header_bytes: bytes) -> bool:
        """Verifies %PDF- magic signature (25 50 44 46)."""
        return header_bytes.startswith(b"%PDF-")

    def _execute_parse(
        self,
        file_path: Path,
        artifact_metadata: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[ExtractedObservation]]:
        """
        Parses PDF using pypdf. Extracts metadata dict and bounded page text observations.
        """
        observations: List[ExtractedObservation] = []
        artifact_id = artifact_metadata.get("artifact_id", "ART")

        reader = PdfReader(str(file_path))

        # Check encryption / password protection
        is_encrypted = reader.is_encrypted
        if is_encrypted:
            try:
                # Attempt empty password decrypt
                reader.decrypt("")
            except Exception:
                pass

        total_pages = len(reader.pages)

        # 1. Document Metadata Extraction
        raw_meta = reader.metadata or {}
        meta_dict = {}
        for key in ["/Title", "/Author", "/Subject", "/Creator", "/Producer", "/CreationDate", "/ModDate"]:
            val = raw_meta.get(key)
            clean_key = key.lstrip("/").lower()
            if val is not None:
                meta_dict[clean_key] = str(val)
                observations.append(
                    ExtractedObservation(
                        observation_id=f"{artifact_id}-OBS-META-{clean_key}",
                        observation_type=ObservationType.DOCUMENT_METADATA,
                        location_reference="Document Information Dictionary",
                        key=clean_key,
                        value=str(val),
                        provenance_note=f"pypdf:metadata:{key}",
                    )
                )

        # 2. Bounded Page Text Extraction (Observation, not intelligence)
        pages_to_extract = min(total_pages, self.max_pages_extract)
        extracted_pages_data = []
        total_extracted_words = 0

        for page_idx in range(pages_to_extract):
            page_num = page_idx + 1
            page_obj = reader.pages[page_idx]
            try:
                text = page_obj.extract_text() or ""
            except Exception as pe:
                text = f"[Text extraction error on page {page_num}: {str(pe)}]"

            # Apply bounded length guard
            truncated = len(text) > self.max_chars_per_page
            bounded_text = text[:self.max_chars_per_page]
            word_count = len(bounded_text.split())
            total_extracted_words += word_count

            extracted_pages_data.append({
                "page_number": page_num,
                "character_count": len(bounded_text),
                "word_count": word_count,
                "truncated": truncated,
                "text_snippet": bounded_text[:300] + ("..." if len(bounded_text) > 300 else ""),
            })

            observations.append(
                ExtractedObservation(
                    observation_id=f"{artifact_id}-OBS-TEXT-P{page_num}",
                    observation_type=ObservationType.DOCUMENT_TEXT,
                    location_reference=f"Page {page_num} of {total_pages}",
                    key=f"page_{page_num}_text",
                    value=bounded_text,
                    confidence=1.0,
                    provenance_note=f"pypdf:page:{page_num} (chars: {len(bounded_text)}, truncated: {truncated})",
                )
            )

        structured_metadata = {
            "format": "PDF",
            "pdf_version": reader.pdf_header if hasattr(reader, "pdf_header") else "%PDF",
            "total_pages": total_pages,
            "pages_inspected": pages_to_extract,
            "max_pages_ceiling": self.max_pages_extract,
            "is_encrypted": is_encrypted,
            "document_info": meta_dict,
            "pages_summary": extracted_pages_data,
            "total_words_extracted": total_extracted_words,
        }

        return structured_metadata, observations
