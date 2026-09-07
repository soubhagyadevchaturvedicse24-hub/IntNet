"""
Image Forensic Artifact Parser for CRIMENET (Slice 8A).
Extracts image dimensions, format, color mode, and EXIF/GPS observations.
NOTE: EXIF GPS coordinates are strictly recorded as observed digital device metadata,
and MUST NEVER be interpreted as proof that a suspect was physically present at that location.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from PIL import Image, ExifTags

from src.parsers.base import ArtifactParser
from src.parsers.models import (
    ParserType,
    ObservationType,
    ExtractedObservation,
)


class ImageParser(ArtifactParser):
    """
    Parser for image files (PNG, JPEG, TIFF, BMP, WebP, GIF).
    Enforces format header magic byte validation and extracts EXIF/GPS observations.
    """

    # Magic byte signatures
    SIGNATURES = {
        "PNG": b"\x89PNG\r\n\x1a\n",
        "JPEG": b"\xff\xd8\xff",
        "BMP": b"BM",
        "TIFF_LE": b"II*\x00",
        "TIFF_BE": b"MM\x00*",
        "GIF87": b"GIF87a",
        "GIF89": b"GIF89a",
    }

    def __init__(self, max_file_size_bytes: int = 50 * 1024 * 1024):
        super().__init__(max_file_size_bytes=max_file_size_bytes)

    def get_parser_type(self) -> ParserType:
        return ParserType.IMAGE

    def get_parser_name(self) -> str:
        return "CRIMENET_IMAGE_EXIF_PARSER"

    def get_parser_version(self) -> str:
        return "1.0.0"

    def can_parse(self, file_path: Path, header_bytes: bytes) -> bool:
        """Validates header magic bytes against supported image formats."""
        if header_bytes.startswith(self.SIGNATURES["PNG"]):
            return True
        if header_bytes.startswith(self.SIGNATURES["JPEG"]):
            return True
        if header_bytes.startswith(self.SIGNATURES["BMP"]):
            return True
        if header_bytes.startswith(self.SIGNATURES["TIFF_LE"]) or header_bytes.startswith(self.SIGNATURES["TIFF_BE"]):
            return True
        if header_bytes.startswith(self.SIGNATURES["GIF87"]) or header_bytes.startswith(self.SIGNATURES["GIF89"]):
            return True
        # WebP: starts with RIFF, then 4 bytes of size, then WEBP
        if header_bytes.startswith(b"RIFF") and len(header_bytes) >= 12 and header_bytes[8:12] == b"WEBP":
            return True
        return False

    @staticmethod
    def _convert_dms_to_deg(dms_tuple) -> Optional[float]:
        """Converts degrees, minutes, seconds tuple to decimal degrees."""
        try:
            d = float(dms_tuple[0])
            m = float(dms_tuple[1])
            s = float(dms_tuple[2])
            return d + (m / 60.0) + (s / 3600.0)
        except Exception:
            return None

    def _extract_gps_data(self, raw_gps_info: Dict[Any, Any]) -> Optional[Dict[str, Any]]:
        """Parses GPSInfo dictionary safely."""
        if not raw_gps_info:
            return None

        gps_data = {}
        for k, v in raw_gps_info.items():
            sub_tag_name = ExifTags.GPSTAGS.get(k, str(k))
            gps_data[sub_tag_name] = v

        lat = None
        lon = None

        lat_ref = gps_data.get("GPSLatitudeRef")
        lat_dms = gps_data.get("GPSLatitude")
        if lat_dms:
            deg = self._convert_dms_to_deg(lat_dms)
            if deg is not None:
                lat = -deg if lat_ref in ["S", "s"] else deg

        lon_ref = gps_data.get("GPSLongitudeRef")
        lon_dms = gps_data.get("GPSLongitude")
        if lon_dms:
            deg = self._convert_dms_to_deg(lon_dms)
            if deg is not None:
                lon = -deg if lon_ref in ["W", "w"] else deg

        alt = None
        alt_val = gps_data.get("GPSAltitude")
        if alt_val is not None:
            try:
                alt = float(alt_val)
            except Exception:
                pass

        if lat is not None or lon is not None:
            return {
                "latitude": lat,
                "longitude": lon,
                "altitude": alt,
                "raw_tags": {str(k): str(v) for k, v in gps_data.items()},
            }
        return None

    def _execute_parse(
        self,
        file_path: Path,
        artifact_metadata: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[ExtractedObservation]]:
        """Parses image using Pillow, extracting dimensions, color mode, and EXIF/GPS."""
        observations: List[ExtractedObservation] = []
        artifact_id = artifact_metadata.get("artifact_id", "ART")

        with Image.open(file_path) as img:
            width, height = img.size
            img_format = img.format or "UNKNOWN"
            color_mode = img.mode

            # Observation: Dimensions
            observations.append(
                ExtractedObservation(
                    observation_id=f"{artifact_id}-OBS-IMG-DIM",
                    observation_type=ObservationType.IMAGE_DIMENSIONS,
                    location_reference="Image Header",
                    key="dimensions",
                    value={"width": width, "height": height, "aspect_ratio": round(width / height, 3) if height else 0},
                    provenance_note="Pillow:Image.size",
                )
            )

            # Observation: Color Mode & Format
            observations.append(
                ExtractedObservation(
                    observation_id=f"{artifact_id}-OBS-IMG-FMT",
                    observation_type=ObservationType.IMAGE_DIMENSIONS,
                    location_reference="Image Header",
                    key="format_mode",
                    value={"format": img_format, "color_mode": color_mode},
                    provenance_note="Pillow:Image.format_and_mode",
                )
            )

            # EXIF extraction
            exif_dict: Dict[str, Any] = {}
            gps_info_raw = None

            try:
                raw_exif = img.getexif()
                if raw_exif:
                    for tag_id, val in raw_exif.items():
                        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                        if tag_name == "GPSInfo":
                            gps_info_raw = val
                        else:
                            # Normalize stringifiable values
                            exif_dict[tag_name] = str(val) if not isinstance(val, (int, float, str)) else val

                    # Also inspect IFD for GPS if not in root
                    if hasattr(raw_exif, "get_ifd"):
                        try:
                            gps_ifd = raw_exif.get_ifd(ExifTags.IFD.GPSInfo)
                            if gps_ifd:
                                gps_info_raw = gps_ifd
                        except Exception:
                            pass
            except Exception:
                pass

            # Fallback for older PIL EXIF handling
            if not exif_dict and hasattr(img, "_getexif"):
                try:
                    legacy_exif = img._getexif()
                    if legacy_exif:
                        for tag_id, val in legacy_exif.items():
                            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                            if tag_name == "GPSInfo":
                                gps_info_raw = val
                            else:
                                exif_dict[tag_name] = str(val) if not isinstance(val, (int, float, str)) else val
                except Exception:
                    pass

            # Create EXIF observations
            for k, v in exif_dict.items():
                observations.append(
                    ExtractedObservation(
                        observation_id=f"{artifact_id}-OBS-EXIF-{k}",
                        observation_type=ObservationType.IMAGE_EXIF,
                        location_reference=f"EXIF:{k}",
                        key=k,
                        value=v,
                        provenance_note=f"Pillow:EXIF:{k}",
                    )
                )

            # GPS metadata observation
            gps_observation_data = None
            if gps_info_raw:
                gps_observation_data = self._extract_gps_data(gps_info_raw)
                if gps_observation_data:
                    observations.append(
                        ExtractedObservation(
                            observation_id=f"{artifact_id}-OBS-GPS",
                            observation_type=ObservationType.IMAGE_GPS,
                            location_reference="EXIF:GPSInfo",
                            key="device_reported_gps",
                            value={
                                "latitude": gps_observation_data["latitude"],
                                "longitude": gps_observation_data["longitude"],
                                "altitude": gps_observation_data.get("altitude"),
                            },
                            provenance_note=(
                                "Observed camera hardware header tag (device-reported metadata only; "
                                "NEVER interpreted as proof of physical human presence)"
                            ),
                        )
                    )

            structured_metadata = {
                "format": img_format,
                "color_mode": color_mode,
                "width": width,
                "height": height,
                "has_exif": bool(exif_dict or gps_observation_data),
                "exif_tag_count": len(exif_dict),
                "exif_metadata": exif_dict,
                "has_gps": bool(gps_observation_data),
                "gps_metadata": gps_observation_data,
            }

            return structured_metadata, observations
