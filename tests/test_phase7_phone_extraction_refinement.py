"""
Targeted tests for Phase 7: Phone extraction false-positive refinement.
Verifies that low-digit false positives (years, ports, inodes, sizes) and repetitive numbers are rejected,
while genuine phone numbers are properly extracted.
"""

import re


def extract_phones_from_text(text_sample: str):
    raw_candidates = re.findall(r"(?:\+?\d{1,3}[\-\s]?)?\(?\d{3}\)?[\-\s]?\d{3}[\-\s]?\d{4}|\+?[6-9]\d{9,11}", text_sample)
    valid_phones = []
    for cand in raw_candidates:
        clean_digits = re.sub(r"\D", "", cand)
        if 10 <= len(clean_digits) <= 15 and len(set(clean_digits)) > 2:
            valid_phones.append(cand.strip())
    return list(set(valid_phones))


def test_phone_extraction_rejects_false_positives():
    # Sample containing years, ports, inodes, byte sizes, and dummy repetitive strings
    noisy_text = """
    Log entry for year 2026 at port 8080.
    File size: 1048576 bytes, inode: 65535, sector: 512.
    Dummy code: 0000000000 and 1111111111.
    """
    extracted = extract_phones_from_text(noisy_text)
    assert len(extracted) == 0, f"False positives extracted: {extracted}"


def test_phone_extraction_accepts_valid_numbers():
    valid_text = """
    Contact suspect at +91-98765-43210 or alternate 9876543210.
    US office contact: (555) 123-4567.
    """
    extracted = extract_phones_from_text(valid_text)
    assert len(extracted) >= 2
    digits = [re.sub(r"\D", "", p) for p in extracted]
    assert any("9876543210" in d for d in digits)
    assert any("5551234567" in d for d in digits)
