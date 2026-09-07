"""
Evidence Storage Abstraction and Local Storage Engine for CRIMENET (Slice 3).
Provides secure, server-controlled file preservation, strict path traversal defense, and cryptographic byte hashing.
"""

from abc import ABC, abstractmethod
import hashlib
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any


class EvidenceStorage(ABC):
    @abstractmethod
    def save_bytes(self, case_id: str, evidence_id: str, raw_filename: str, content: bytes) -> Tuple[str, str, str, int]:
        """
        Preserves raw evidence bytes to server storage.
        Returns Tuple of (storage_reference, sha256_hash, md5_hash, size_bytes).
        """
        pass

    @abstractmethod
    def read_bytes(self, storage_reference: str) -> bytes:
        """Reads preserved bytes from storage reference."""
        pass

    @abstractmethod
    def calculate_stored_sha256(self, storage_reference: str) -> str:
        """Recalculates SHA-256 directly from preserved stored bytes on disk."""
        pass


class LocalFileStorage(EvidenceStorage):
    def __init__(self, base_dir: str = "DATA/evidence_store", staging_base_dir: str = "DATA/staging_evidence"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.staging_base_dir = Path(staging_base_dir).resolve()
        self.staging_base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        # Strip directory path separators, null bytes, and parent dir traversals
        clean_name = os.path.basename(filename.replace('\\', '/'))
        clean_name = re.sub(r'[^\w\.\-]', '_', clean_name)
        if not clean_name or clean_name in ['.', '..']:
            clean_name = "evidence.raw"
        return clean_name

    def _validate_safe_path(self, target_path: Path) -> Path:
        resolved = target_path.resolve()
        if not str(resolved).startswith(str(self.base_dir)):
            raise ValueError(f"SECURITY ALERT: Path traversal attempt detected: '{target_path}'")
        return resolved

    def _validate_safe_staging_path(self, target_path: Path) -> Path:
        resolved = target_path.resolve()
        if not str(resolved).startswith(str(self.staging_base_dir)):
            raise ValueError(f"SECURITY ALERT: Path traversal attempt detected in staging: '{target_path}'")
        return resolved

    def _validate_staging_id(self, staging_id: str) -> str:
        if not re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', str(staging_id)):
            raise ValueError(f"SECURITY ALERT: Invalid staging ID format: '{staging_id}'")
        return staging_id

    def save_bytes(self, case_id: str, evidence_id: str, raw_filename: str, content: bytes) -> Tuple[str, str, str, int]:
        clean_case = re.sub(r'[^\w\-]', '_', case_id)
        clean_ev = re.sub(r'[^\w\-]', '_', evidence_id)
        clean_file = self._sanitize_filename(raw_filename)

        case_folder = self.base_dir / clean_case
        target_path = case_folder / f"{clean_ev}_{clean_file}"
        safe_path = self._validate_safe_path(target_path)

        safe_path.parent.mkdir(parents=True, exist_ok=True)

        if safe_path.exists():
            raise FileExistsError(f"Evidence file reference already exists: '{clean_ev}'")

        # Write original un-transformed bytes
        with open(safe_path, 'wb') as f:
            f.write(content)

        # Calculate hashes directly from saved file
        sha256 = hashlib.sha256()
        md5 = hashlib.md5()
        size_bytes = len(content)

        with open(safe_path, 'rb') as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
                md5.update(chunk)

        storage_ref = str(safe_path.relative_to(self.base_dir)).replace('\\', '/')
        return storage_ref, sha256.hexdigest(), md5.hexdigest(), size_bytes

    APPROVED_EVIDENCE_ROOTS = [
        Path("Images").resolve(),
        Path("D:/Proto SIH/Images").resolve(),
        Path("DATA/test_images").resolve(),
    ]

    def link_local_evidence(
        self,
        case_id: str,
        evidence_id: str,
        source_path_str: str
    ) -> Tuple[str, str, str, int]:
        """
        Securely registers an existing forensic image using NTFS hardlinks (zero bytes duplicated).
        Enforces strict server-side allowlist, canonical resolution, traversal defense,
        header magic validation, and companion segment discovery.
        Returns Tuple of (storage_reference, sha256_hash, md5_hash, size_bytes).
        """
        source_path = Path(source_path_str).resolve()

        # 1. Server-side allowlist check (reject unauthorized paths)
        is_allowed = any(
            source_path == root or source_path.is_relative_to(root)
            for root in self.APPROVED_EVIDENCE_ROOTS
            if root.exists()
        )
        if not is_allowed:
            raise PermissionError(f"SECURITY ALERT: Path '{source_path}' is outside approved evidence locations.")

        if not source_path.is_file():
            raise FileNotFoundError(f"Forensic source file not found: '{source_path}'")

        # 2. Verify E01 Magic Header
        with open(source_path, "rb") as f:
            hdr = f.read(8)
            if not (hdr.startswith(b"EVF\t\r\n\xff\x00") or hdr.startswith(b"EVF")):
                raise ValueError(f"Invalid format: '{source_path.name}' is not a valid E01 forensic image.")

        # 3. Discover companion segments (e.g. .E02)
        try:
            import pyewf
            globbed = pyewf.glob(str(source_path)) or [str(source_path)]
        except Exception:
            globbed = [str(source_path)]
        segments = [Path(p).resolve() for p in globbed]

        # 4. Prepare target directory under self.base_dir
        clean_case = re.sub(r'[^\w\-]', '_', case_id)
        clean_ev = re.sub(r'[^\w\-]', '_', evidence_id)
        case_folder = self.base_dir / clean_case
        case_folder.mkdir(parents=True, exist_ok=True)

        primary_clean = self._sanitize_filename(source_path.name)
        primary_target = case_folder / f"{clean_ev}_{primary_clean}"
        safe_primary = self._validate_safe_path(primary_target)

        # 5. Link all companion segments into the target directory
        for seg in segments:
            seg_clean = self._sanitize_filename(seg.name)
            seg_target = case_folder / f"{clean_ev}_{seg_clean}"
            safe_seg = self._validate_safe_path(seg_target)
            if safe_seg.exists():
                os.unlink(safe_seg)
            try:
                os.link(str(seg), str(safe_seg))
            except Exception:
                import shutil
                shutil.copyfile(str(seg), str(safe_seg))

        # 6. Calculate cryptographic hashes directly from source file
        sha256 = hashlib.sha256()
        md5 = hashlib.md5()
        size_bytes = source_path.stat().st_size

        with open(source_path, 'rb') as f:
            while chunk := f.read(4 * 1024 * 1024):
                sha256.update(chunk)
                md5.update(chunk)

        storage_ref = str(safe_primary.relative_to(self.base_dir)).replace('\\', '/')
        return storage_ref, sha256.hexdigest(), md5.hexdigest(), size_bytes

    def read_bytes(self, storage_reference: str) -> bytes:
        target_path = self.base_dir / storage_reference
        safe_path = self._validate_safe_path(target_path)

        if not safe_path.exists():
            raise FileNotFoundError(f"Storage reference not found: '{storage_reference}'")

        with open(safe_path, 'rb') as f:
            return f.read()

    def calculate_stored_sha256(self, storage_reference: str) -> str:
        target_path = self.base_dir / storage_reference
        safe_path = self._validate_safe_path(target_path)

        if not safe_path.exists():
            raise FileNotFoundError(f"Storage reference not found: '{storage_reference}'")

        sha256 = hashlib.sha256()
        with open(safe_path, 'rb') as f:
            while chunk := f.read(65536):
                sha256.update(chunk)

        return sha256.hexdigest()

    # =========================================================================
    # PHASE 1: SECURE FORENSIC STAGING ENGINE (SLICE 7C)
    # =========================================================================

    def create_staging_session(self, user_id: str, expected_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Creates a dedicated staging directory and metadata tracking for an evidence upload."""
        staging_id = str(uuid.uuid4())
        session_dir = self.staging_base_dir / staging_id
        safe_session_dir = self._validate_safe_staging_path(session_dir)
        safe_session_dir.mkdir(parents=True, exist_ok=True)
        (safe_session_dir / "incomplete").mkdir(parents=True, exist_ok=True)

        session_meta = {
            "staging_id": staging_id,
            "created_by": user_id,
            "created_at": time.time(),
            "status": "UPLOADING",
            "expected_files": [self._sanitize_filename(f) for f in (expected_files or [])],
            "files": {}
        }
        with open(safe_session_dir / "session.json", "w", encoding="utf-8") as f:
            json.dump(session_meta, f, indent=2)

        return session_meta

    def append_chunk(
        self,
        staging_id: str,
        filename: str,
        chunk_index: int,
        total_chunks: int,
        chunk_bytes: bytes
    ) -> Dict[str, Any]:
        """
        Streams an incoming chunk directly to disk in an isolated staging session.
        Never buffers the entire multi-gigabyte forensic image into RAM.
        """
        self._validate_staging_id(staging_id)
        session_dir = self._validate_safe_staging_path(self.staging_base_dir / staging_id)
        session_file = session_dir / "session.json"
        if not session_file.exists():
            raise FileNotFoundError(f"Staging session '{staging_id}' not found.")

        with open(session_file, "r", encoding="utf-8") as f:
            session = json.load(f)

        if session.get("status") not in ["UPLOADING", "CHUNK_RECEIVED"]:
            raise ValueError(f"Staging session '{staging_id}' is not in an active upload state (status: {session.get('status')}).")

        clean_file = self._sanitize_filename(filename)
        ext = Path(clean_file).suffix.lower()
        if not re.match(r'^\.e\d{2,}$', ext, re.IGNORECASE):
            raise ValueError(f"Unsupported evidence format: '{clean_file}'. Slice 7C accepts forensic E01 multi-segment (.E01, .E02, etc.) only.")

        incomplete_dir = session_dir / "incomplete"
        incomplete_dir.mkdir(parents=True, exist_ok=True)
        part_file = self._validate_safe_staging_path(incomplete_dir / f"{clean_file}.part")

        # Write chunk incrementally
        mode = "wb" if chunk_index == 0 else "ab"
        with open(part_file, mode) as f:
            f.write(chunk_bytes)

        current_size = part_file.stat().st_size

        if clean_file not in session["files"]:
            session["files"][clean_file] = {
                "filename": clean_file,
                "bytes_received": current_size,
                "chunks_received": chunk_index + 1,
                "total_chunks": total_chunks,
                "is_complete": False
            }
        else:
            session["files"][clean_file]["bytes_received"] = current_size
            session["files"][clean_file]["chunks_received"] = chunk_index + 1
            session["files"][clean_file]["total_chunks"] = total_chunks

        is_complete = (chunk_index + 1 >= total_chunks)
        if is_complete:
            # Incrementally calculate SHA-256 and MD5 from disk in 4MB blocks
            sha256 = hashlib.sha256()
            md5 = hashlib.md5()
            with open(part_file, "rb") as f:
                while block := f.read(4 * 1024 * 1024):
                    sha256.update(block)
                    md5.update(block)

            dest_file = self._validate_safe_staging_path(session_dir / clean_file)
            if dest_file.exists():
                dest_file.unlink()
            shutil.move(str(part_file), str(dest_file))

            session["files"][clean_file]["is_complete"] = True
            session["files"][clean_file]["sha256"] = sha256.hexdigest()
            session["files"][clean_file]["md5"] = md5.hexdigest()
            session["files"][clean_file]["size_bytes"] = dest_file.stat().st_size

        session["status"] = "CHUNK_RECEIVED"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2)

        return {
            "staging_id": staging_id,
            "filename": clean_file,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "bytes_received": current_size,
            "is_complete": is_complete,
            "sha256": session["files"][clean_file].get("sha256")
        }

    def finalize_staging_session(self, staging_id: str) -> Dict[str, Any]:
        """
        Validates the completed staging session:
        - Confirms all chunks for all files have been received
        - Verifies E01 magic header
        - Detects and verifies sequential companion segments
        - Calculates unified media size via pyewf
        - Transitions status to READY_FOR_INSPECTION
        """
        self._validate_staging_id(staging_id)
        session_dir = self._validate_safe_staging_path(self.staging_base_dir / staging_id)
        session_file = session_dir / "session.json"
        if not session_file.exists():
            raise FileNotFoundError(f"Staging session '{staging_id}' not found.")

        with open(session_file, "r", encoding="utf-8") as f:
            session = json.load(f)

        files = session.get("files", {})
        if not files:
            raise ValueError(f"No files uploaded in staging session '{staging_id}'.")

        for fn, finfo in files.items():
            if not finfo.get("is_complete"):
                raise ValueError(f"File '{fn}' is incomplete (received {finfo.get('chunks_received')}/{finfo.get('total_chunks')} chunks).")

        primary_fn = None
        for fn in sorted(files.keys()):
            if fn.lower().endswith(".e01"):
                primary_fn = fn
                break

        if not primary_fn:
            raise ValueError("Invalid forensic image set: No primary .E01 image file found.")

        primary_path = self._validate_safe_staging_path(session_dir / primary_fn)
        if not primary_path.is_file():
            raise FileNotFoundError(f"Primary file '{primary_fn}' missing on disk.")

        # Verify E01 Magic Header
        with open(primary_path, "rb") as f:
            hdr = f.read(8)
            if not (hdr.startswith(b"EVF\t\r\n\xff\x00") or hdr.startswith(b"EVF")):
                raise ValueError(f"Invalid format: '{primary_fn}' is not a valid E01 forensic image (EVF header missing).")

        # Discover companion segments matching primary stem
        stem = primary_path.stem
        companion_files = sorted([
            f for f in session_dir.glob(f"{stem}.*")
            if f.is_file() and not f.name.endswith((".json", ".part"))
        ], key=lambda p: p.name.lower())

        seg_names = [f.name for f in companion_files]

        # Check for sequence gaps
        segment_suffixes = sorted([p.suffix.upper() for p in companion_files])
        if len(segment_suffixes) > 1:
            for i in range(len(segment_suffixes) - 1):
                cur_ext = segment_suffixes[i]
                next_ext = segment_suffixes[i + 1]
                if re.match(r'^\.E\d{2,}$', cur_ext) and re.match(r'^\.E\d{2,}$', next_ext):
                    try:
                        cur_num = int(cur_ext[2:])
                        next_num = int(next_ext[2:])
                    except Exception:
                        continue
                    if next_num != cur_num + 1:
                        raise ValueError(f"Fragmented container: Missing intermediate segment between {cur_ext} and {next_ext}.")


        # Calculate media size via pyewf
        media_size = primary_path.stat().st_size
        examiner = "N/A"
        try:
            import pyewf
            h = pyewf.handle()
            h.open([str(p) for p in companion_files])
            media_size = h.get_media_size()
            hdr_vals = h.get_header_values()
            examiner = hdr_vals.get("examiner_name", "N/A")
            h.close()
        except Exception:
            pass

        total_disk_size = sum(f.stat().st_size for f in companion_files)

        session["status"] = "READY_FOR_INSPECTION"
        session["primary_file"] = primary_fn
        session["segments"] = seg_names
        session["segment_count"] = len(seg_names)
        session["total_size_bytes"] = total_disk_size
        session["media_size_bytes"] = media_size
        session["examiner_name"] = examiner

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2)

        return {
            "staging_id": staging_id,
            "status": "READY_FOR_INSPECTION",
            "primary_filename": primary_fn,
            "segments": seg_names,
            "segment_count": len(seg_names),
            "total_size_bytes": total_disk_size,
            "total_size_formatted": f"{total_disk_size / (1024**3):.2f} GB" if total_disk_size >= 1024**3 else f"{total_disk_size / (1024**2):.1f} MB",
            "media_size_bytes": media_size,
            "format": "E01",
            "examiner_name": examiner
        }

    def get_staging_session(self, staging_id: str) -> Optional[Dict[str, Any]]:
        """Reads session metadata for a staging identifier."""
        try:
            self._validate_staging_id(staging_id)
            session_file = self.staging_base_dir / staging_id / "session.json"
            if not session_file.exists():
                return None
            with open(session_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def get_staging_dir(self, staging_id: str) -> Path:
        """Returns validated path to the staging directory."""
        self._validate_staging_id(staging_id)
        return self._validate_safe_staging_path(self.staging_base_dir / staging_id)

    def promote_staged_evidence(
        self,
        case_id: str,
        evidence_id: str,
        staging_id: str
    ) -> Tuple[str, str, str, int]:
        """
        Promotes finalized staged files from quarantine into the official case evidence store.
        Zero bytes corrupted, preserved hashes maintained.
        Returns Tuple of (storage_reference, sha256_hash, md5_hash, size_bytes).
        """
        self._validate_staging_id(staging_id)
        session_dir = self._validate_safe_staging_path(self.staging_base_dir / staging_id)
        session_file = session_dir / "session.json"
        if not session_file.exists():
            raise FileNotFoundError(f"Staging session '{staging_id}' not found.")

        with open(session_file, "r", encoding="utf-8") as f:
            session = json.load(f)

        if session.get("status") not in ["READY_FOR_INSPECTION", "PROMOTED"]:
            raise ValueError(f"Cannot promote staging session '{staging_id}': status is '{session.get('status')}'.")

        primary_fn = session.get("primary_file")
        if not primary_fn:
            raise ValueError(f"Staging session '{staging_id}' has no designated primary file.")

        clean_case = re.sub(r'[^\w\-]', '_', case_id)
        clean_ev = re.sub(r'[^\w\-]', '_', evidence_id)
        case_folder = self.base_dir / clean_case
        case_folder.mkdir(parents=True, exist_ok=True)

        primary_clean = self._sanitize_filename(primary_fn)
        primary_target = case_folder / f"{clean_ev}_{primary_clean}"
        safe_primary = self._validate_safe_path(primary_target)

        # Move/copy companion segments into case storage
        segments = session.get("segments", [primary_fn])
        for seg_name in segments:
            seg_source = self._validate_safe_staging_path(session_dir / seg_name)
            if not seg_source.exists():
                raise FileNotFoundError(f"Staged segment missing: '{seg_name}'")

            seg_clean = self._sanitize_filename(seg_name)
            seg_target = case_folder / f"{clean_ev}_{seg_clean}"
            safe_seg = self._validate_safe_path(seg_target)
            if safe_seg.exists():
                safe_seg.unlink()

            shutil.copyfile(str(seg_source), str(safe_seg))

        primary_info = session["files"].get(primary_fn, {})
        sha256_hash = primary_info.get("sha256")
        md5_hash = primary_info.get("md5")
        size_bytes = primary_info.get("size_bytes", safe_primary.stat().st_size)

        if not sha256_hash:
            sha256 = hashlib.sha256()
            md5 = hashlib.md5()
            with open(safe_primary, "rb") as f:
                while block := f.read(4 * 1024 * 1024):
                    sha256.update(block)
                    md5.update(block)
            sha256_hash = sha256.hexdigest()
            md5_hash = md5.hexdigest()

        session["status"] = "PROMOTED"
        session["promoted_to_case_id"] = case_id
        session["promoted_to_evidence_id"] = evidence_id
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2)

        storage_ref = str(safe_primary.relative_to(self.base_dir)).replace('\\', '/')
        return storage_ref, sha256_hash, md5_hash, size_bytes

    def cleanup_expired_staging(self, max_age_seconds: int = 86400) -> int:
        """Removes abandoned staging sessions older than max_age_seconds."""
        if not self.staging_base_dir.exists():
            return 0
        now = time.time()
        cleaned_count = 0
        for s_dir in self.staging_base_dir.iterdir():
            if not s_dir.is_dir():
                continue
            session_file = s_dir / "session.json"
            age = now - s_dir.stat().st_mtime
            if session_file.exists():
                try:
                    with open(session_file, "r", encoding="utf-8") as f:
                        session = json.load(f)
                    created = session.get("created_at", s_dir.stat().st_mtime)
                    age = now - created
                    if session.get("status") in ["UPLOADING", "CHUNK_RECEIVED"] and age < 3600:
                        continue
                except Exception:
                    pass
            if age > max_age_seconds:
                try:
                    shutil.rmtree(str(s_dir), ignore_errors=True)
                    cleaned_count += 1
                except Exception:
                    pass
        return cleaned_count
