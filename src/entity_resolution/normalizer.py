"""
Rule-Based Normalization Engine for Entity Resolution (Slice 5 & Slice 8B).
Normalizes raw strings extracted from Evidence Contracts and parsed observations
into canonical baseline representations.
"""

import re


def normalize_person_name(name: str) -> str:
    if not name:
        return ""
    # Strip leading/trailing whitespace first
    cleaned = name.strip()
    # Strip honorifics & titles (with or without trailing period)
    cleaned = re.sub(r'^(?:mr\.|mrs\.|ms\.|dr\.|prof\.|shri|smt\.|mr|mrs|ms|dr|prof)\s+', '', cleaned, flags=re.IGNORECASE)
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
    elif len(digits) == 11 and digits.startswith("0"):
        return f"+91{digits[1:]}"
    elif phone.startswith("+"):
        return f"+{digits}"
    return digits


def normalize_email(email: str) -> str:
    if not email:
        return ""
    return email.strip().lower()


def normalize_vehicle_plate(plate: str) -> str:
    if not plate:
        return ""
    # Remove spaces, dashes, dots, and convert to uppercase
    cleaned = re.sub(r'[\s\.\-]', '', plate)
    return cleaned.upper()


def normalize_location(loc: str) -> str:
    if not loc:
        return ""
    # Check if location is decimal coordinates e.g. "28.6139, 77.2090"
    coord_match = re.match(r'^\s*([\-+]?\d+(?:\.\d+)?)\s*,\s*([\-+]?\d+(?:\.\d+)?)\s*$', str(loc))
    if coord_match:
        lat = round(float(coord_match.group(1)), 5)
        lon = round(float(coord_match.group(2)), 5)
        return f"{lat:.5f}, {lon:.5f}"

    cleaned = re.sub(r'[^\w\s]', ' ', loc)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.title()


def normalize_organization(org: str) -> str:
    if not org:
        return ""
    cleaned = org.strip()
    cleaned = re.sub(r'\b(pvt|ltd|inc|corp|corporation|private|limited)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^\w\s]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned.title()


def normalize_bank_account(acc: str) -> str:
    if not acc:
        return ""
    cleaned = re.sub(r'[\s\.\-]', '', acc)
    return cleaned.upper()


def normalize_entity(entity_type: str, raw_value: str) -> str:
    etype = entity_type.upper()
    if etype in ["PERSON", "PERSONNAME"]:
        return normalize_person_name(raw_value)
    elif etype in ["PHONENUMBER", "PHONE"]:
        return normalize_phone_number(raw_value)
    elif etype in ["EMAIL", "EMAILADDRESS"]:
        return normalize_email(raw_value)
    elif etype in ["VEHICLE", "VEHICLEPLATE"]:
        return normalize_vehicle_plate(raw_value)
    elif etype in ["LOCATION", "ADDRESS"]:
        return normalize_location(raw_value)
    elif etype in ["ORGANIZATION", "ORG"]:
        return normalize_organization(raw_value)
    elif etype in ["BANKACCOUNT", "ACCOUNT", "FINANCIAL", "IFSC", "UPI"]:
        return normalize_bank_account(raw_value)
    else:
        return re.sub(r'\s+', ' ', str(raw_value)).strip()
