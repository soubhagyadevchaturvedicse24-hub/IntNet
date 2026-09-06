"""
Rule-Based Normalization Engine for Entity Resolution
Normalizes raw strings extracted from Evidence Contracts into canonical baseline representations.
"""

import re

def normalize_person_name(name: str) -> str:
    if not name:
        return ""
    # Strip honorifics & titles
    cleaned = re.sub(r'^(mr\.|mrs\.|ms\.|dr\.|prof\.|shri|smt\.)\s+', '', name, flags=re.IGNORECASE)
    # Remove punctuation except letters and spaces
    cleaned = re.sub(r'[^\w\s]', '', cleaned)
    # Collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.title()

def normalize_phone_number(phone: str) -> str:
    if not phone:
        return ""
    # Strip non-digit characters except leading plus
    digits = re.sub(r'[^\d]', '', phone)
    if not digits:
        return ""
    # Standardize 10-digit Indian numbers to E.164 +91
    if len(digits) == 10:
        return f"+91{digits}"
    elif len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    elif phone.startswith("+"):
        return f"+{digits}"
    return digits

def normalize_vehicle_plate(plate: str) -> str:
    if not plate:
        return ""
    # Remove spaces, dashes, dots, and convert to uppercase
    cleaned = re.sub(r'[\s\.\-]', '', plate)
    return cleaned.upper()

def normalize_location(loc: str) -> str:
    if not loc:
        return ""
    cleaned = re.sub(r'[^\w\s]', ' ', loc)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.title()

def normalize_organization(org: str) -> str:
    if not org:
        return ""
    cleaned = re.sub(r'\b(pvt|ltd|inc|corp|corporation|private|limited)\b', '', org, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^\w\s]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.title()

def normalize_entity(entity_type: str, raw_value: str) -> str:
    etype = entity_type.upper()
    if etype in ["PERSON", "PERSONNAME"]:
        return normalize_person_name(raw_value)
    elif etype in ["PHONENUMBER", "PHONE"]:
        return normalize_phone_number(raw_value)
    elif etype in ["VEHICLE", "VEHICLEPLATE"]:
        return normalize_vehicle_plate(raw_value)
    elif etype in ["LOCATION", "ADDRESS"]:
        return normalize_location(raw_value)
    elif etype in ["ORGANIZATION", "ORG"]:
        return normalize_organization(raw_value)
    else:
        return re.sub(r'\s+', ' ', raw_value).strip()
