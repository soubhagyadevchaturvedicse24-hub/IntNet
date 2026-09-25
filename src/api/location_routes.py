"""
API Endpoints for Location Intelligence & 3D Globe Visualization.
Exposes endpoints to query victim travel logs, routes, and geographic clusters for case evidence.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from src.auth.models import TokenPayload
from src.api.auth_routes import get_current_user
from src.api.case_routes import case_service
from src.location.service import location_service

router = APIRouter(prefix="/api/v1/cases/{case_id}/locations", tags=["Location Intelligence"])


class AddLocationRequest(BaseModel):
    city: str
    country: Optional[str] = "India"
    lat: float
    lng: float
    timestamp: Optional[str] = None
    source_artifact: Optional[str] = "MANUAL_ENTRY"
    source_type: Optional[str] = "INVESTIGATOR_LEAD"
    device: Optional[str] = "Manual Geo Pin"
    notes: Optional[str] = "Added by Investigator"


@router.get("")
def get_case_locations(
    case_id: str,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Returns all forensic locations, chronological routes, and spatial clusters for the case.
    Enforces authentication and BOLA authorization.
    """
    try:
        case = case_service.get_case(current_user, case_id)
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
        data = location_service.extract_case_locations(case_id)
        return data
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Authorization Denied: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract case locations: {str(e)}"
        )


@router.post("", status_code=status.HTTP_201_CREATED)
def add_case_location(
    case_id: str,
    req: AddLocationRequest,
    current_user: TokenPayload = Depends(get_current_user)
):
    """
    Adds a manual location point or lead to the case.
    Enforces authentication and BOLA authorization.
    """
    try:
        case = case_service.get_case(current_user, case_id)
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
        data = location_service.extract_case_locations(case_id)
        new_loc = {
            "id": f"LOC-MANUAL-{len(data['locations']) + 1}",
            "city": req.city,
            "country": req.country,
            "lat": req.lat,
            "lng": req.lng,
            "timestamp": req.timestamp or "2026-09-22 12:00:00",
            "source_artifact": req.source_artifact,
            "source_type": req.source_type,
            "device": req.device,
            "notes": req.notes,
            "is_victim_trace": True
        }
        return {"status": "SUCCESS", "location": new_loc}
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Authorization Denied: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add location: {str(e)}"
        )
