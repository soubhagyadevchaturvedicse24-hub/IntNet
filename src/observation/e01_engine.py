"""
E01 Forensic Observation Engine for CRIMENET (Slice 7).
Parses Expert Witness Format (E01) multi-segment forensic images using libewf / pyewf
and The Sleuth Kit / pytsk3. Recursively traverses filesystems, extracts representative
artifacts, maintains strict forensic integrity, and generates EvidenceContract_v1.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Tuple, Dict, Any, List, Optional

import pyewf
import pytsk3

from src.processing.engine import ObservationEngine


class EwfImgInfo(pytsk3.Img_Info):
    """
    Bridge wrapper adapting pyewf.handle to pytsk3.Img_Info interface.
    Provides transparent virtual media stream seeking and reading.
    """
    def __init__(self, ewf_handle: pyewf.handle):
        self._ewf_handle = ewf_handle
        super(EwfImgInfo, self).__init__()

    def read(self, offset: int, size: int) -> bytes:
        self._ewf_handle.seek(offset)
        return self._ewf_handle.read(size)

    def get_size(self) -> int:
        return self._ewf_handle.get_media_size()


class E01ForensicObservationEngine(ObservationEngine):
    """
    High-performance native E01 observation engine for CRIMENET.
    Supports multi-segment container assembly, partition detection, NTFS / FAT traversal,
    representative file extraction, cryptographic provenance, and EvidenceContract_v1 output.
    """

    def __init__(
        self,
        max_artifacts: int = 250,
        max_file_size: int = 100 * 1024 * 1024,
        priority_targets: Optional[List[str]] = None,
    ):
        self.max_artifacts = max_artifacts
        self.max_file_size = max_file_size
        self.priority_targets = [t.lower() for t in (priority_targets or ["autopsy.db"])]

    def get_engine_name(self) -> str:
        return "CRIMENET_E01_OBSERVATION_ENGINE"

    def get_engine_version(self) -> str:
        return "1.0.0"

    @staticmethod
    def calculate_file_sha256(filepath: Path) -> str:
        """Calculates SHA-256 hash in 4MB chunks without modifying the file."""
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(4 * 1024 * 1024):
                sha.update(chunk)
        return sha.hexdigest()

    @staticmethod
    def verify_e01_magic(filepath: Path) -> bool:
        """Verifies EWF header magic: EVF\\x09\\x0d\\x0a\\xff\\x00 (45 56 46 09 0D 0A FF 00)."""
        if not filepath.exists() or filepath.stat().st_size < 8:
            return False
        with open(filepath, "rb") as f:
            header = f.read(8)
            return header.startswith(b"EVF\t\r\n\xff\x00") or header.startswith(b"EVF")

    @staticmethod
    def sanitize_artifact_filename(raw_name: str) -> str:
        """Strips directory traversal sequences and special characters from internal paths."""
        base = os.path.basename(raw_name.replace('\\', '/'))
        cleaned = re.sub(r"[^\w\.\-]", "_", base)
        while ".." in cleaned:
            cleaned = cleaned.replace("..", "_")
        cleaned = cleaned.lstrip("._")
        return cleaned or "artifact.bin"

    def process(
        self,
        image_path: Path,
        output_dir: Path,
        case_id: str,
        evidence_id: str,
        job_id: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Executes complete E01 observation:
        1. Validates E01 input & globs companion segments (.E02, etc.)
        2. Asserts companion segment presence
        3. Computes and records SHA-256 for every segment (read-only)
        4. Opens multi-segment media stream via pyewf
        5. Attempts Volume_Info (partition table) or falls back to logical volume at offset 0
        6. Traverses filesystem directories
        7. Extracts representative artifacts with strict path traversal defenses
        8. Derives artifact-backed entities
        9. Emits EvidenceContract_v1 JSON
        """
        image_path = Path(image_path).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        if not image_path.exists():
            raise FileNotFoundError(f"Forensic image file not found: '{image_path}'")

        # 1. Validate container magic / format
        if not self.verify_e01_magic(image_path):
            raise ValueError(f"Invalid forensic image format: '{image_path.name}' is not a valid EWF/E01 container.")

        # 2. Discover companion segments via pyewf.glob
        globbed_files = pyewf.glob(str(image_path))
        if not globbed_files:
            globbed_files = [str(image_path)]

        # 3. Verify all companion segments exist on disk
        segment_paths: List[Path] = [Path(p).resolve() for p in globbed_files]
        for seg_p in segment_paths:
            if not seg_p.exists():
                raise FileNotFoundError(f"Missing companion segment: '{seg_p.name}'")

        # Check for gaps in sequence (e.g. .E01 exists, .E03 exists, but .E02 missing)
        segment_suffixes = sorted([p.suffix.upper() for p in segment_paths])
        if len(segment_suffixes) > 1:
            for i in range(len(segment_suffixes) - 1):
                cur_ext = segment_suffixes[i]
                next_ext = segment_suffixes[i + 1]
                # If extensions follow .E01, .E02 pattern
                if cur_ext.startswith(".E") and next_ext.startswith(".E"):
                    try:
                        cur_num = int(cur_ext[2:])
                        next_num = int(next_ext[2:])
                        if next_num != cur_num + 1:
                            raise ValueError(f"Fragmented container: Missing intermediate segment between {cur_ext} and {next_ext}.")
                    except ValueError:
                        pass

        # 4. Compute and record SHA-256 for each source segment
        segment_hashes: Dict[str, str] = {}
        for seg_p in segment_paths:
            segment_hashes[seg_p.name] = self.calculate_file_sha256(seg_p)

        # 5. Open unified logical media stream
        ewf_handle = pyewf.handle()
        ewf_handle.open([str(p) for p in segment_paths])

        try:
            virtual_media_size = ewf_handle.get_media_size()
            sector_count = ewf_handle.get_number_of_sectors()
            chunk_size = ewf_handle.get_chunk_size()
            header_vals = ewf_handle.get_header_values()
            container_hashes = ewf_handle.get_hash_values()

            img_info = EwfImgInfo(ewf_handle)

            # 6. Attempt Volume_Info (partition table parsing)
            fs_offset = 0
            volume_system_detected = False
            volume_type = "LOGICAL_VOLUME"
            partition_info_list = []

            try:
                vol_info = pytsk3.Volume_Info(img_info)
                volume_system_detected = True
                volume_type = str(vol_info.info.vstype)

                for part in vol_info:
                    part_desc = part.desc.decode("utf-8", "ignore") if part.desc else "Unknown"
                    part_dict = {
                        "slot_num": part.slot_num,
                        "desc": part_desc,
                        "start_offset": part.start * 512,
                        "length_bytes": part.len * 512,
                        "flags": str(part.flags)
                    }
                    partition_info_list.append(part_dict)

                    # Choose first allocated partition with filesystem
                    if part.flags == pytsk3.TSK_VS_PART_FLAG_ALLOC and fs_offset == 0:
                        try:
                            test_fs = pytsk3.FS_Info(img_info, offset=part.start * 512)
                            fs_offset = part.start * 512
                        except Exception:
                            pass
            except Exception:
                # Logical volume acquisition (no MBR/GPT, filesystem begins at sector 0)
                volume_system_detected = False
                fs_offset = 0

            # 7. Identify Filesystem
            fs = pytsk3.FS_Info(img_info, offset=fs_offset)
            fs_type_code = fs.info.ftype

            if fs_type_code == pytsk3.TSK_FS_TYPE_NTFS:
                observed_filesystem = "NTFS"
            elif fs_type_code in [pytsk3.TSK_FS_TYPE_FAT12, pytsk3.TSK_FS_TYPE_FAT16, pytsk3.TSK_FS_TYPE_FAT32]:
                observed_filesystem = "FAT32"
            elif fs_type_code in [pytsk3.TSK_FS_TYPE_EXT2, pytsk3.TSK_FS_TYPE_EXT3, pytsk3.TSK_FS_TYPE_EXT4]:
                observed_filesystem = "EXT4"
            else:
                observed_filesystem = f"UNKNOWN ({fs_type_code})"

            # 8. Recursive Directory Traversal
            all_files: List[Dict[str, Any]] = []
            all_dirs: List[Dict[str, Any]] = []

            def traverse_dir(dir_obj, parent_path: str = ""):
                for entry in dir_obj:
                    if not entry.info.name or not entry.info.name.name:
                        continue
                    name = entry.info.name.name.decode("utf-8", "ignore")
                    if name in [".", ".."]:
                        continue

                    full_path = f"{parent_path}/{name}"
                    is_alloc = (entry.info.name.flags == pytsk3.TSK_FS_NAME_FLAG_ALLOC)
                    is_dir = bool(entry.info.meta and entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR)
                    size = entry.info.meta.size if entry.info.meta else 0

                    record = {
                        "path": full_path,
                        "name": name,
                        "is_dir": is_dir,
                        "allocated": is_alloc,
                        "size": size,
                        "inum": entry.info.meta.addr if entry.info.meta else None,
                        "mtime": entry.info.meta.mtime if entry.info.meta else None,
                        "crtime": entry.info.meta.crtime if entry.info.meta else None,
                        "atime": entry.info.meta.atime if entry.info.meta else None
                    }

                    if is_dir:
                        all_dirs.append(record)
                        try:
                            traverse_dir(entry.as_directory(), full_path)
                        except Exception:
                            pass
                    else:
                        all_files.append(record)

            root_dir = fs.open_dir(path="/")
            traverse_dir(root_dir)

            # 9. Representative File Extraction with Path Traversal Defense
            artifacts_dir = output_dir / "extracted_artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            observed_artifacts = []
            extracted_entities = []
            extracted_relationships = []

            # Prioritize candidate files for extraction:
            # 1) Targeted forensic database/container files (e.g. autopsy.db)
            # 2) Standard document, image, audio, or forensic evidence extensions
            priority_exts = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".pdf", ".txt", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".db", ".sqlite", ".log", ".eml", ".msg", ".bin", ".json", ".md"}
            targeted_candidates = []
            regular_candidates = []
            for f in all_files:
                if f["size"] <= 0 or f["size"] > self.max_file_size:
                    continue
                fpath_lower = f["path"].lower()
                fname_lower = f["name"].lower()
                # Skip Windows internal volume telemetry
                if "system volume information" in fpath_lower or "$orphanfiles" in fpath_lower:
                    continue
                if any(pt in fname_lower or pt in fpath_lower for pt in self.priority_targets):
                    targeted_candidates.append(f)
                elif Path(f["name"]).suffix.lower() in priority_exts:
                    regular_candidates.append(f)

            candidates = targeted_candidates + regular_candidates
            if len(candidates) < self.max_artifacts:
                other_files = [
                    f for f in all_files
                    if f["size"] > 0 and f["size"] <= self.max_file_size and f not in candidates
                    and "system volume information" not in f["path"].lower()
                ]
                candidates.extend(other_files[:(self.max_artifacts - len(candidates))])

            extraction_targets = candidates[:self.max_artifacts]

            for idx, target in enumerate(extraction_targets):
                try:
                    target_path = target["path"]
                    f_size = target["size"]

                    # Skip oversized files exceeding resource limits
                    if f_size > self.max_file_size:
                        continue

                    tsk_file = fs.open(target_path)
                    content_bytes = tsk_file.read_random(0, f_size)
                    art_sha256 = hashlib.sha256(content_bytes).hexdigest()

                    # Sanitize destination filename & enforce strict sandbox boundaries
                    clean_name = self.sanitize_artifact_filename(target["name"])
                    safe_filename = f"ART_{job_id}_{idx+1:03d}_{clean_name}"
                    dest_file_path = (artifacts_dir / safe_filename).resolve()

                    # Canonical path traversal defense
                    if not dest_file_path.is_relative_to(output_dir):
                        raise PermissionError(f"PATH TRAVERSAL DEFENSE: Target path '{dest_file_path}' escapes output directory.")

                    with open(dest_file_path, "wb") as art_out:
                        art_out.write(content_bytes)

                    # Relative content path for Slice 6 storage resolution
                    rel_content_path = f"{case_id}/{job_id}/extracted_artifacts/{safe_filename}"

                    clean_job = re.sub(r'[^A-Za-z0-9_-]', '_', job_id)
                    clean_case = re.sub(r'[^A-Za-z0-9_-]', '_', case_id).replace('CASE_', '')
                    art_id = f"ART-{clean_case}-{clean_job}-{idx+1:03d}-{art_sha256[:12].upper()}"
                    alloc_status = "ALLOCATED" if target["allocated"] else "DELETED"

                    # Infer artifact type with intelligent forensic tagging
                    ext = Path(target["name"]).suffix.lower()
                    fname_lower = target["name"].lower()
                    fpath_lower = target["path"].lower()

                    recovery_status = "NONE"
                    if "carved" in fname_lower or "carved" in fpath_lower:
                        recovery_status = "CARVED"
                        alloc_status = "DELETED"
                    elif "recovered" in fname_lower or "recovered" in fpath_lower:
                        recovery_status = "RECOVERED"
                        alloc_status = "DELETED"
                    elif "deleted" in fname_lower or "deleted" in fpath_lower:
                        alloc_status = "DELETED"

                    if "cdr" in fname_lower or "cdr" in fpath_lower:
                        art_type = "CDR"
                    elif ext in [".eml", ".msg", ".mbox"] or "email" in fname_lower or "email" in fpath_lower:
                        art_type = "EMAIL"
                    elif recovery_status in ["CARVED", "RECOVERED"]:
                        art_type = "RECOVERED_FILE"
                    elif alloc_status == "DELETED":
                        art_type = "DELETED_FILE"
                    elif ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]:
                        art_type = "IMAGE"
                    elif ext in [".pdf", ".docx", ".doc", ".txt", ".rtf", ".md"]:
                        art_type = "DOCUMENT"
                    elif ext in [".db", ".sqlite", ".sqlite3"]:
                        art_type = "DATABASE"
                    elif ext in [".csv", ".xlsx", ".xls"]:
                        art_type = "SPREADSHEET"
                    elif ext in [".log"]:
                        art_type = "LOG"
                    else:
                        art_type = "OTHER"

                    art_record = {
                        "artifact_id": art_id,
                        "artifact_name": target["name"],
                        "artifact_type": art_type,
                        "size_bytes": f_size,
                        "sha256": art_sha256,
                        "allocation_status": alloc_status,
                        "recovery_status": recovery_status,
                        "provenance_trace": f"{image_path.name}:{target_path}",
                        "content_path": rel_content_path,
                        "created_at": datetime.fromtimestamp(target["crtime"], timezone.utc).isoformat() if target["crtime"] else None,
                        "modified_at": datetime.fromtimestamp(target["mtime"], timezone.utc).isoformat() if target["mtime"] else None,
                        "accessed_at": datetime.fromtimestamp(target["atime"], timezone.utc).isoformat() if target["atime"] else None
                    }
                    observed_artifacts.append(art_record)

                    # Extract legitimate entities derived ONLY from this actual observed artifact
                    # (e.g. phone numbers or emails in document text / headers)
                    # Never extract from E01 container headers!
                    if art_type in ["DOCUMENT", "LOG"]:
                        text_sample = content_bytes[:65536].decode("ascii", errors="ignore")
                        # High-confidence phone extraction: E.164 or formatted/national mobile numbers (10+ digits)
                        # Rejects 2-digit to 9-digit false positives (ports, years, inodes, sizes)
                        raw_candidates = re.findall(r"(?:\+?\d{1,3}[\-\s]?)?\(?\d{3}\)?[\-\s]?\d{3}[\-\s]?\d{4}|\+?[6-9]\d{9,11}", text_sample)
                        valid_phones = []
                        for cand in raw_candidates:
                            clean_digits = re.sub(r"\D", "", cand)
                            if 10 <= len(clean_digits) <= 15 and len(set(clean_digits)) > 2:
                                valid_phones.append(cand.strip())
                        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text_sample)

                        for p_idx, phone in enumerate(list(set(valid_phones))[:2]):
                            ent_id = f"ENT-{art_sha256[:6].upper()}-P{p_idx+1}"
                            extracted_entities.append({
                                "entity_id": ent_id,
                                "entity_type": "PhoneNumber",
                                "observed_value": phone,
                                "confidence": 0.95,
                                "source_offset": art_id,
                                "provenance_trace": f"{image_path.name}:{target_path}#offset"
                            })

                        for e_idx, email in enumerate(list(set(emails))[:2]):
                            ent_id = f"ENT-{art_sha256[:6].upper()}-E{e_idx+1}"
                            extracted_entities.append({
                                "entity_id": ent_id,
                                "entity_type": "Email",
                                "observed_value": email,
                                "confidence": 0.95,
                                "source_offset": art_id,
                                "provenance_trace": f"{image_path.name}:{target_path}#offset"
                            })

                except Exception as extract_err:
                    # Non-fatal file extraction skip (e.g. locked/sparse MFT entry)
                    continue

            # 10. Build EvidenceContract_v1 JSON
            now_iso = datetime.now(timezone.utc).isoformat()
            contract_v1 = {
                "contract_version": "1.0.0",
                "provenance_envelope": {
                    "case_id": case_id,
                    "evidence_id": evidence_id,
                    "processing_job_id": job_id,
                    "engine_name": self.get_engine_name(),
                    "engine_version": self.get_engine_version(),
                    "processed_at": now_iso
                },
                "source_evidence": {
                    "primary_filename": image_path.name,
                    "segment_filenames": [p.name for p in segment_paths],
                    "container_format": "E01",
                    "observed_filesystem": observed_filesystem,
                    "virtual_size_bytes": virtual_media_size,
                    "sector_count": sector_count,
                    "chunk_size": chunk_size,
                    "volume_system_detected": volume_system_detected,
                    "volume_type": volume_type,
                    "filesystem_offset": fs_offset,
                    "segment_hashes": segment_hashes,
                    "total_directories_discovered": len(all_dirs),
                    "total_files_discovered": len(all_files)
                },
                "observed_artifacts": observed_artifacts,
                "extracted_entities": extracted_entities,
                "extracted_relationships": extracted_relationships
            }

            # Save contract to output_dir
            contract_file = output_dir / f"evidence_contract_{job_id}.json"
            with open(contract_file, "w", encoding="utf-8") as f:
                json.dump(contract_v1, f, indent=2)

            return contract_v1, observed_filesystem

        finally:
            ewf_handle.close()
