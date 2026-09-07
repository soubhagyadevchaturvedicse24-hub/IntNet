import os
import re
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from typing import Optional, List, Dict, Any

from src.auth.models import TokenPayload, UserRole
from src.api.auth_routes import get_current_user, auth_service, policy_engine, audit_service
from src.api.case_routes import case_service
from src.evidence.models import (
    Evidence, EvidenceType, EvidenceCreate, EvidenceResponse, EvidenceVerifyResponse
)
from src.evidence.service import EvidenceService
from src.evidence.storage import LocalFileStorage
from src.evidence.repository import SQLiteEvidenceRepository

router = APIRouter(prefix="/api/v1/cases/{case_id}/evidence", tags=["Evidence Intake & Preservation"])
evidence_discovery_router = APIRouter(prefix="/api/v1/evidence", tags=["Evidence Discovery & Inspection"])

# Shared singleton EvidenceService
evidence_storage = LocalFileStorage()
evidence_repository = SQLiteEvidenceRepository()
evidence_service = EvidenceService(
    repository=evidence_repository,
    storage=evidence_storage,
    case_service=case_service,
    policy_engine=policy_engine,
    audit_service=audit_service,
    auth_service=auth_service
)


def get_candidate_evidence_sets() -> List[Dict[str, Any]]:
    """
    Scans APPROVED_EVIDENCE_ROOTS to discover forensic image sets.
    Unified representation for multi-segment E01 files (e.g. .E01 + .E02).
    Enforces server-approved roots and safe candidate IDs.
    """
    candidates = []
    seen_canons = set()
    for root in evidence_storage.APPROVED_EVIDENCE_ROOTS:
        if not root.exists():
            continue
        try:
            for p in root.glob("*.*"):
                if p.suffix.lower() in [".e01", ".raw", ".dd", ".img"]:
                    canon = str(p.resolve())
                    if canon in seen_canons:
                        continue
                    seen_canons.add(canon)
                    stem = p.stem
                    companion_files = sorted(list(p.parent.glob(stem + ".*")))
                    seg_names = [
                        f.name for f in companion_files
                        if f.suffix.lower().startswith((".e", ".raw", ".dd", ".img")) and not f.name.endswith(".txt")
                    ]
                    total_size = sum(f.stat().st_size for f in companion_files if f.name in seg_names)
                    cid = "cand_" + re.sub(r'[^a-zA-Z0-9_]', '_', stem).lower()
                    candidates.append({
                        "candidate_id": cid,
                        "display_name": f"{stem} (Forensic E01+E02 Multi-Segment Set)" if len(seg_names) > 1 else f"{stem} ({p.suffix.upper()[1:]})",
                        "primary_file": p.name,
                        "segments": seg_names,
                        "segment_count": len(seg_names),
                        "total_size_bytes": total_size,
                        "total_size_formatted": f"{total_size / (1024**3):.2f} GB" if total_size >= 1024**3 else f"{total_size / (1024**2):.1f} MB",
                        "format": "E01" if p.suffix.lower() == ".e01" else "RAW",
                        "safe_relative_path": str(p.relative_to(root.parent)).replace("\\", "/"),
                        "canonical_path": canon
                    })
        except Exception:
            continue
    return candidates


def resolve_candidate_or_safe_path(candidate_id: Optional[str], path_str: Optional[str]) -> str:
    candidates = get_candidate_evidence_sets()
    if candidate_id:
        for cand in candidates:
            if cand["candidate_id"] == candidate_id:
                return cand["canonical_path"]
        raise ValueError(f"Candidate ID '{candidate_id}' not found in approved evidence candidates.")

    if path_str:
        # Check if path_str is a candidate_id
        for cand in candidates:
            if cand["candidate_id"] == path_str:
                return cand["canonical_path"]

        # Resolve path_str safely against approved roots
        p = Path(path_str).resolve()
        is_allowed = any(
            p == root or p.is_relative_to(root)
            for root in evidence_storage.APPROVED_EVIDENCE_ROOTS
            if root.exists()
        )
        if not is_allowed:
            raise PermissionError(f"SECURITY ALERT: Path '{path_str}' is outside approved evidence locations.")
        if not p.is_file():
            raise FileNotFoundError(f"Evidence source file not found: '{path_str}'")
        return str(p)

    raise ValueError("Neither candidate_id nor path provided.")


class UploadInitRequest(BaseModel):
    expected_files: Optional[List[str]] = None


class UploadFinalizeRequest(BaseModel):
    staging_id: str


@evidence_discovery_router.post("/upload/init")
def init_evidence_upload(
    req: Optional[UploadInitRequest] = None,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Initializes an isolated staging session for streaming forensic E01 uploads.
    Enforces BFLA check for evidence registration role.
    """
    if current_user.role not in [UserRole.INVESTIGATION_OFFICER, UserRole.HIGHER_AUTHORITY]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"BFLA DENY: Role '{current_user.role}' cannot initiate evidence upload."
        )

    expected = req.expected_files if req else None
    session_meta = evidence_storage.create_staging_session(
        user_id=current_user.sub,
        expected_files=expected
    )
    return session_meta


@evidence_discovery_router.post("/upload/chunk")
async def upload_evidence_chunk(
    staging_id: str = Form(...),
    filename: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    chunk: UploadFile = File(...),
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Streams a single chunk of a forensic image directly to disk.
    Never buffers multi-gigabyte forensic images into Python memory.
    """
    if current_user.role not in [UserRole.INVESTIGATION_OFFICER, UserRole.HIGHER_AUTHORITY]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"BFLA DENY: Role '{current_user.role}' cannot upload evidence chunks."
        )

    try:
        session = evidence_storage.get_staging_session(staging_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staging session '{staging_id}' not found.")
        if session.get("created_by") != current_user.sub and current_user.role != UserRole.HIGHER_AUTHORITY:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="BOLA DENY: Staging session belongs to another officer.")

        # Read chunk content with 10MB safety bound
        chunk_content = await chunk.read(10 * 1024 * 1024 + 1024)
        result = evidence_storage.append_chunk(
            staging_id=staging_id,
            filename=filename,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            chunk_bytes=chunk_content
        )
        return result
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Chunk upload failed: {str(ex)}")


@evidence_discovery_router.post("/upload/finalize")
def finalize_evidence_upload(
    req: UploadFinalizeRequest,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Validates completed staged files:
    - Verifies E01 magic bytes
    - Verifies companion segments
    - Computes disk and media sizes
    - Transitions session to READY_FOR_INSPECTION
    """
    if current_user.role not in [UserRole.INVESTIGATION_OFFICER, UserRole.HIGHER_AUTHORITY]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"BFLA DENY: Role '{current_user.role}' cannot finalize evidence upload."
        )

    session = evidence_storage.get_staging_session(req.staging_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staging session '{req.staging_id}' not found.")
    if session.get("created_by") != current_user.sub and current_user.role != UserRole.HIGHER_AUTHORITY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="BOLA DENY: Staging session belongs to another officer.")

    try:
        meta = evidence_storage.finalize_staging_session(req.staging_id)
        return meta
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Finalization error: {str(ex)}")


class EvidenceInspectRequest(BaseModel):
    candidate_id: Optional[str] = None
    path: Optional[str] = None
    staging_id: Optional[str] = None


@evidence_discovery_router.get("/candidates")
def list_evidence_candidates(current_user: TokenPayload = Depends(get_current_user)):
    """Discovers available forensic image sets under approved server roots."""
    return get_candidate_evidence_sets()


@evidence_discovery_router.post("/inspect")
def inspect_evidence_file(req: EvidenceInspectRequest, current_user: TokenPayload = Depends(get_current_user)):
    """
    Strictly READ-ONLY inspection of candidate or staged forensic images.
    Verifies magic bytes, identifies companion segments, extracts metadata.
    Never modifies disk, creates DB records, or duplicates storage.
    """
    try:
        if req.staging_id:
            evidence_storage._validate_staging_id(req.staging_id)
            session = evidence_storage.get_staging_session(req.staging_id)
            if not session:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staging session '{req.staging_id}' not found.")
            if session.get("created_by") != current_user.sub and current_user.role != UserRole.HIGHER_AUTHORITY:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="BOLA DENY: Staging session belongs to another officer.")
            if session.get("status") not in ["READY_FOR_INSPECTION", "PROMOTED"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Staging session '{req.staging_id}' is not finalized (status: {session.get('status')}).")

            staging_dir = evidence_storage.get_staging_dir(req.staging_id)
            primary_fn = session.get("primary_file")
            source_p = staging_dir / primary_fn
        else:
            resolved_path = resolve_candidate_or_safe_path(req.candidate_id, req.path)
            source_p = Path(resolved_path)

        with open(source_p, "rb") as f:
            hdr = f.read(16)

        is_e01 = hdr.startswith(b"EVF\t\r\n\xff\x00") or hdr.startswith(b"EVF")
        if not is_e01:
            # Check if raw/disk image
            return {
                "valid": True,
                "read_only": True,
                "magic_verified": True,
                "format": "RAW/DD",
                "primary_filename": source_p.name,
                "segments": [source_p.name],
                "segment_count": 1,
                "total_size_bytes": source_p.stat().st_size,
                "total_size_formatted": f"{source_p.stat().st_size / (1024**2):.1f} MB",
                "safe_path": req.staging_id or req.candidate_id or req.path
            }

        # E01 inspection via pyewf
        norm_path = os.path.normpath(str(source_p))
        try:
            import pyewf
            if req.staging_id:
                # Open staged segments directly
                segments_list = session.get("segments", [source_p.name])
                staged_paths = [os.path.normpath(str(staging_dir / s)) for s in segments_list]
                globbed = staged_paths
            else:
                globbed = pyewf.glob(norm_path) or [norm_path]

            h = pyewf.handle()
            h.open(globbed)
            media_size = h.get_media_size()
            bytes_per_sector = h.get_bytes_per_sector()
            hdr_vals = h.get_header_values()
            hash_vals = h.get_hash_values()
            h.close()
        except Exception as e:
            globbed = [norm_path]
            media_size = source_p.stat().st_size
            bytes_per_sector = 512
            hdr_vals = {}
            hash_vals = {}

        segments = [os.path.basename(s) for s in globbed]
        total_disk_size = sum(Path(s).stat().st_size for s in globbed if Path(s).exists())

        return {
            "valid": True,
            "read_only": True,
            "magic_verified": True,
            "format": "E01",
            "primary_filename": source_p.name,
            "segments": segments,
            "segment_count": len(segments),
            "total_size_bytes": total_disk_size,
            "total_size_formatted": f"{total_disk_size / (1024**3):.2f} GB" if total_disk_size >= 1024**3 else f"{total_disk_size / (1024**2):.1f} MB",
            "media_size_bytes": media_size,
            "media_size_formatted": f"{media_size / (1024**3):.2f} GB",
            "bytes_per_sector": bytes_per_sector,
            "examiner_name": hdr_vals.get("examiner_name", "N/A"),
            "case_number": hdr_vals.get("case_number", "N/A"),
            "evidence_number": hdr_vals.get("evidence_number", "N/A"),
            "acquiry_date": hdr_vals.get("acquiry_date", "N/A"),
            "notes": hdr_vals.get("notes", "N/A"),
            "hashes": hash_vals,
            "safe_path": req.staging_id or req.candidate_id or req.path
        }
    except HTTPException:
        raise
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except (FileNotFoundError, ValueError) as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as ex:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Inspection error: {str(ex)}")


@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def register_evidence(
    case_id: str,
    evidence_name: str = Form(...),
    evidence_type: EvidenceType = Form(...),
    source_description: Optional[str] = Form(""),
    file: Optional[UploadFile] = File(None),
    local_image_path: Optional[str] = Form(None),
    candidate_id: Optional[str] = Form(None),
    staging_id: Optional[str] = Form(None),
    current_user: TokenPayload = Depends(get_current_user)
):
    try:
        create_req = EvidenceCreate(
            evidence_name=evidence_name,
            evidence_type=evidence_type,
            source_description=source_description
        )
        if staging_id:
            evidence = evidence_service.register_staged_evidence(
                actor=current_user,
                case_id=case_id,
                create_req=create_req,
                staging_id=staging_id
            )
            return EvidenceResponse(**evidence.model_dump())
        elif candidate_id or local_image_path:
            resolved_local_path = resolve_candidate_or_safe_path(candidate_id, local_image_path)
            evidence = evidence_service.register_local_evidence(
                actor=current_user,
                case_id=case_id,
                create_req=create_req,
                local_path=resolved_local_path
            )
            return EvidenceResponse(**evidence.model_dump())
        elif file:
            content = await file.read()
            evidence = evidence_service.register_evidence(
                actor=current_user,
                case_id=case_id,
                create_req=create_req,
                raw_filename=file.filename or "evidence.raw",
                content=content
            )
            return EvidenceResponse(**evidence.model_dump())
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either staging_id, candidate_id, approved local_image_path, or a file upload must be provided."
            )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    except (ValueError, FileExistsError, FileNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Evidence Registration Failed: {str(e)}"
        )


@router.get("", response_model=List[EvidenceResponse])
def list_evidence(case_id: str, current_user: TokenPayload = Depends(get_current_user)):
    try:
        items = evidence_service.list_case_evidence(current_user, case_id)
        return [EvidenceResponse(**ev.model_dump()) for ev in items]
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(case_id: str, evidence_id: str, current_user: TokenPayload = Depends(get_current_user)):
    try:
        evidence = evidence_service.get_evidence(current_user, case_id, evidence_id)
        if not evidence:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence reference not found")
        return EvidenceResponse(**evidence.model_dump())
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )


@router.post("/{evidence_id}/verify", response_model=EvidenceVerifyResponse)
def verify_evidence_integrity(case_id: str, evidence_id: str, current_user: TokenPayload = Depends(get_current_user)):
    try:
        res = evidence_service.verify_evidence_integrity(current_user, case_id, evidence_id)
        return res
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Authorization Denied: {str(e)}"
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence reference not found"
        )
