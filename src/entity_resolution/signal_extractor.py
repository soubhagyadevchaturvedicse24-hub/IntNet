"""
Deterministic Forensic Signal & Relationship Extractor for CRIMENET (Slice 8B).
Extracts deterministic signals (Phone, Email, Person, Location, Organization, BankAccount)
and evidence-backed relationships strictly from deep parsed observations.

CRITICAL FORENSIC RULES:
1. Extraction != Identity != Guilt.
2. High-confidence deterministic signals only (Regex, structured columns).
3. Strictly NO generic name co-occurrence ASSOCIATED_WITH relationships.
4. Complete provenance preserved for every signal and relationship.
"""

import hashlib
import re
from typing import List, Dict, Any, Tuple, Optional

from src.parsers.models import ExtractedObservation, ObservationType
from src.entity_resolution.normalizer import (
    normalize_entity,
    normalize_phone_number,
    normalize_email,
    normalize_person_name,
    normalize_location,
    normalize_organization,
    normalize_bank_account,
)
from src.entity_resolution.signals import ExtractedSignal, ExtractedRelationship


class ObservationSignalExtractor:
    """
    Deterministic signal and relationship extraction engine.
    Extracts evidentiary signals from ExtractedObservation containers without speculative guessing.
    """

    # High-confidence Regex Patterns
    RE_EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
    # International & Indian E.164 phone patterns
    RE_PHONE_INTL = re.compile(r'(?:\+91[\-\s]?)?[6-9]\d{9}\b|\+[1-9]\d{6,14}\b')
    # Explicit structured text field prefixes
    RE_NAME_FIELD = re.compile(r'(?i)\b(?:name|contact|person|suspect|officer|author|target|subject|holder)\s*[:=]\s*([A-Za-z\s.]{2,40})(?=[\r\n,;]|\s{2,}|$)')
    RE_ORG_FIELD = re.compile(r'(?i)\b(?:org|organization|company|agency|firm|bank)\s*[:=]\s*([A-Za-z0-9\s.&]{2,50})(?=[\r\n,;]|\s{2,}|$)')
    RE_IFSC = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b')
    RE_ACC_FIELD = re.compile(r'(?i)\b(?:a/c|acc|account|bank\s*a/c)\s*(?:no\.?|num(?:ber)?\.?)?\s*[:=]?\s*([0-9]{9,18})\b')

    # Structured SQLite Column Mappings
    PHONE_COLS = {"phone", "mobile", "contact_no", "contact_number", "phone_number", "tel", "sender_phone", "receiver_phone"}
    EMAIL_COLS = {"email", "mail", "email_address", "sender_email", "receiver_email"}
    NAME_COLS = {"name", "full_name", "contact_name", "person_name", "suspect_name", "target_name", "sender_name", "receiver_name", "user_name"}
    ACC_COLS = {"account_no", "account_number", "acc_no", "ifsc", "upi_id", "bank_account"}
    LOC_COLS = {"location", "city", "address", "state", "gps_coords"}
    ORG_COLS = {"org", "organization", "company", "agency", "department"}

    @staticmethod
    def _generate_deterministic_signal_id(case_id: str, obs_id: str, etype: str, norm_val: str) -> str:
        digest = hashlib.sha256(f"{case_id}:{obs_id}:{etype}:{norm_val}".encode("utf-8")).hexdigest()[:8].upper()
        return f"SIG-{etype[:3].upper()}-{digest}"

    @staticmethod
    def _generate_deterministic_rel_id(case_id: str, src_sig_id: str, tgt_sig_id: str, rel_label: str) -> str:
        digest = hashlib.sha256(f"{case_id}:{src_sig_id}:{tgt_sig_id}:{rel_label}".encode("utf-8")).hexdigest()[:8].upper()
        return f"REL-{digest}"

    @staticmethod
    def _parse_email_header_recipient(header_str: str) -> List[Tuple[Optional[str], str]]:
        """
        Parses an email header field containing one or more recipients.
        Returns list of (display_name, email_address) tuples.
        display_name is None unless an explicit display name is bound in the header
        (e.g. 'John Doe <jdoe@domain.com>'). Never infers Person identity from email/domain alone.
        """
        if not header_str:
            return []
        results = []
        parts = re.split(r'[,;](?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)', header_str)
        for part in parts:
            clean = part.strip()
            if not clean:
                continue
            match = re.match(r'^(?:"|\')?([^<>\"]+?)(?:"|\')?\s*<([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})>$', clean)
            if match:
                disp_name = match.group(1).strip()
                email_addr = match.group(2).strip()
                if "@" not in disp_name and len(disp_name) >= 2 and any(c.isalpha() for c in disp_name):
                    results.append((disp_name, email_addr))
                else:
                    results.append((None, email_addr))
            else:
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', clean)
                if email_match:
                    results.append((None, email_match.group(0)))
        return results

    def extract_signals_from_observation(
        self,
        obs: ExtractedObservation,
        case_id: str,
        evidence_id: str,
        artifact_id: str,
        job_id: str = "",
    ) -> List[ExtractedSignal]:
        """
        Extracts high-confidence deterministic signals from a single ExtractedObservation.
        """
        signals: List[ExtractedSignal] = []
        loc_ref = obs.location_reference or "Unknown Location"
        obs_id = obs.observation_id

        # 1. DOCUMENT TEXT EXTRACTION
        if obs.observation_type == ObservationType.DOCUMENT_TEXT and isinstance(obs.value, str):
            text = obs.value

            # A. Phone Numbers
            phones = self.RE_PHONE_INTL.findall(text)
            for raw_phone in set(phones):
                norm_phone = normalize_phone_number(raw_phone)
                if norm_phone and len(norm_phone) >= 10:
                    sig_id = self._generate_deterministic_signal_id(case_id, obs_id, "PhoneNumber", norm_phone)
                    signals.append(
                        ExtractedSignal(
                            signal_id=sig_id,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            entity_type="PhoneNumber",
                            observed_value=raw_phone.strip(),
                            normalized_value=norm_phone,
                            source_location=loc_ref,
                            extraction_method="REGEX_PHONE_E164",
                            confidence=1.0,
                            provenance_trace=f"{artifact_id}:{obs_id}#{loc_ref}",
                        )
                    )

            # B. Email Addresses
            emails = self.RE_EMAIL.findall(text)
            for raw_email in set(emails):
                norm_email = normalize_email(raw_email)
                if norm_email:
                    sig_id = self._generate_deterministic_signal_id(case_id, obs_id, "Email", norm_email)
                    signals.append(
                        ExtractedSignal(
                            signal_id=sig_id,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            entity_type="Email",
                            observed_value=raw_email.strip(),
                            normalized_value=norm_email,
                            source_location=loc_ref,
                            extraction_method="REGEX_RFC5322_EMAIL",
                            confidence=1.0,
                            provenance_trace=f"{artifact_id}:{obs_id}#{loc_ref}",
                        )
                    )

            # C. Explicit Structured Name Prefixes (Strict Regex, NOT broad capitalized words)
            name_matches = self.RE_NAME_FIELD.findall(text)
            for raw_name in set(name_matches):
                norm_name = normalize_person_name(raw_name)
                # Ensure minimum length and valid token count
                if norm_name and len(norm_name.split()) >= 1 and len(norm_name) >= 3:
                    sig_id = self._generate_deterministic_signal_id(case_id, obs_id, "Person", norm_name)
                    signals.append(
                        ExtractedSignal(
                            signal_id=sig_id,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            entity_type="Person",
                            observed_value=raw_name.strip(),
                            normalized_value=norm_name,
                            source_location=loc_ref,
                            extraction_method="STRUCTURED_NAME_PREFIX",
                            confidence=0.95,
                            provenance_trace=f"{artifact_id}:{obs_id}#{loc_ref}",
                        )
                    )

            # D. Financial Identifiers (IFSC & Explicit Bank Accounts)
            ifsc_matches = self.RE_IFSC.findall(text)
            for raw_ifsc in set(ifsc_matches):
                norm_ifsc = normalize_bank_account(raw_ifsc)
                sig_id = self._generate_deterministic_signal_id(case_id, obs_id, "BankAccount", norm_ifsc)
                signals.append(
                    ExtractedSignal(
                        signal_id=sig_id,
                        case_id=case_id,
                        evidence_id=evidence_id,
                        artifact_id=artifact_id,
                        observation_id=obs_id,
                        job_id=job_id,
                        entity_type="BankAccount",
                        observed_value=raw_ifsc.strip(),
                        normalized_value=norm_ifsc,
                        source_location=loc_ref,
                        extraction_method="REGEX_IFSC_CODE",
                        confidence=1.0,
                        provenance_trace=f"{artifact_id}:{obs_id}#{loc_ref}",
                    )
                )

            acc_matches = self.RE_ACC_FIELD.findall(text)
            for raw_acc in set(acc_matches):
                norm_acc = normalize_bank_account(raw_acc)
                sig_id = self._generate_deterministic_signal_id(case_id, obs_id, "BankAccount", norm_acc)
                signals.append(
                    ExtractedSignal(
                        signal_id=sig_id,
                        case_id=case_id,
                        evidence_id=evidence_id,
                        artifact_id=artifact_id,
                        observation_id=obs_id,
                        job_id=job_id,
                        entity_type="BankAccount",
                        observed_value=raw_acc.strip(),
                        normalized_value=norm_acc,
                        source_location=loc_ref,
                        extraction_method="STRUCTURED_BANK_ACCOUNT",
                        confidence=0.95,
                        provenance_trace=f"{artifact_id}:{obs_id}#{loc_ref}",
                    )
                )

        # 2. DOCUMENT METADATA EXTRACTION
        elif obs.observation_type == ObservationType.DOCUMENT_METADATA:
            if obs.key in ["author", "creator"] and isinstance(obs.value, str):
                norm_name = normalize_person_name(obs.value)
                if norm_name and len(norm_name) >= 3:
                    sig_id = self._generate_deterministic_signal_id(case_id, obs_id, "Person", norm_name)
                    signals.append(
                        ExtractedSignal(
                            signal_id=sig_id,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            entity_type="Person",
                            observed_value=obs.value.strip(),
                            normalized_value=norm_name,
                            source_location=loc_ref,
                            extraction_method="PDF_METADATA_AUTHOR",
                            confidence=0.90,
                            provenance_trace=f"{artifact_id}:{obs_id}#{loc_ref}",
                        )
                    )

        # 3. SQLITE SAMPLE ROWS EXTRACTION (Structured Relational Fields)
        elif obs.observation_type == ObservationType.SQLITE_SAMPLE_ROWS and isinstance(obs.value, dict):
            rows = obs.value.get("rows", [])
            for row_idx, row in enumerate(rows):
                row_loc = f"{loc_ref}, Row {row_idx + 1}"
                for col_name, col_val in row.items():
                    if not col_val or not isinstance(col_val, (str, int)):
                        continue
                    str_val = str(col_val).strip()
                    col_lower = col_name.lower()

                    # Phone columns
                    if col_lower in self.PHONE_COLS:
                        norm_phone = normalize_phone_number(str_val)
                        if norm_phone and len(norm_phone) >= 10:
                            sig_id = self._generate_deterministic_signal_id(case_id, f"{obs_id}-R{row_idx}", "PhoneNumber", norm_phone)
                            signals.append(
                                ExtractedSignal(
                                    signal_id=sig_id,
                                    case_id=case_id,
                                    evidence_id=evidence_id,
                                    artifact_id=artifact_id,
                                    observation_id=obs_id,
                                    job_id=job_id,
                                    entity_type="PhoneNumber",
                                    observed_value=str_val,
                                    normalized_value=norm_phone,
                                    source_location=row_loc,
                                    extraction_method=f"SQLITE_COLUMN:{col_name}",
                                    confidence=1.0,
                                    provenance_trace=f"{artifact_id}:{obs_id}#{row_loc}:{col_name}",
                                )
                            )

                    # Email columns
                    elif col_lower in self.EMAIL_COLS:
                        norm_email = normalize_email(str_val)
                        if norm_email:
                            sig_id = self._generate_deterministic_signal_id(case_id, f"{obs_id}-R{row_idx}", "Email", norm_email)
                            signals.append(
                                ExtractedSignal(
                                    signal_id=sig_id,
                                    case_id=case_id,
                                    evidence_id=evidence_id,
                                    artifact_id=artifact_id,
                                    observation_id=obs_id,
                                    job_id=job_id,
                                    entity_type="Email",
                                    observed_value=str_val,
                                    normalized_value=norm_email,
                                    source_location=row_loc,
                                    extraction_method=f"SQLITE_COLUMN:{col_name}",
                                    confidence=1.0,
                                    provenance_trace=f"{artifact_id}:{obs_id}#{row_loc}:{col_name}",
                                )
                            )

                    # Name / Person columns
                    elif col_lower in self.NAME_COLS:
                        norm_name = normalize_person_name(str_val)
                        if norm_name and len(norm_name) >= 2:
                            sig_id = self._generate_deterministic_signal_id(case_id, f"{obs_id}-R{row_idx}", "Person", norm_name)
                            signals.append(
                                ExtractedSignal(
                                    signal_id=sig_id,
                                    case_id=case_id,
                                    evidence_id=evidence_id,
                                    artifact_id=artifact_id,
                                    observation_id=obs_id,
                                    job_id=job_id,
                                    entity_type="Person",
                                    observed_value=str_val,
                                    normalized_value=norm_name,
                                    source_location=row_loc,
                                    extraction_method=f"SQLITE_COLUMN:{col_name}",
                                    confidence=1.0,
                                    provenance_trace=f"{artifact_id}:{obs_id}#{row_loc}:{col_name}",
                                )
                            )

                    # Financial account columns
                    elif col_lower in self.ACC_COLS:
                        norm_acc = normalize_bank_account(str_val)
                        if norm_acc:
                            sig_id = self._generate_deterministic_signal_id(case_id, f"{obs_id}-R{row_idx}", "BankAccount", norm_acc)
                            signals.append(
                                ExtractedSignal(
                                    signal_id=sig_id,
                                    case_id=case_id,
                                    evidence_id=evidence_id,
                                    artifact_id=artifact_id,
                                    observation_id=obs_id,
                                    job_id=job_id,
                                    entity_type="BankAccount",
                                    observed_value=str_val,
                                    normalized_value=norm_acc,
                                    source_location=row_loc,
                                    extraction_method=f"SQLITE_COLUMN:{col_name}",
                                    confidence=1.0,
                                    provenance_trace=f"{artifact_id}:{obs_id}#{row_loc}:{col_name}",
                                )
                            )

                    # Location columns
                    elif col_lower in self.LOC_COLS:
                        norm_loc = normalize_location(str_val)
                        if norm_loc:
                            sig_id = self._generate_deterministic_signal_id(case_id, f"{obs_id}-R{row_idx}", "Location", norm_loc)
                            signals.append(
                                ExtractedSignal(
                                    signal_id=sig_id,
                                    case_id=case_id,
                                    evidence_id=evidence_id,
                                    artifact_id=artifact_id,
                                    observation_id=obs_id,
                                    job_id=job_id,
                                    entity_type="Location",
                                    observed_value=str_val,
                                    normalized_value=norm_loc,
                                    source_location=row_loc,
                                    extraction_method=f"SQLITE_COLUMN:{col_name}",
                                    confidence=1.0,
                                    provenance_trace=f"{artifact_id}:{obs_id}#{row_loc}:{col_name}",
                                )
                            )

        # 4. IMAGE GPS EXTRACTION
        elif obs.observation_type == ObservationType.IMAGE_GPS and isinstance(obs.value, dict):
            lat = obs.value.get("latitude")
            lon = obs.value.get("longitude")
            if lat is not None and lon is not None:
                coord_str = f"{float(lat):.5f}, {float(lon):.5f}"
                sig_id = self._generate_deterministic_signal_id(case_id, obs_id, "Location", coord_str)
                signals.append(
                    ExtractedSignal(
                        signal_id=sig_id,
                        case_id=case_id,
                        evidence_id=evidence_id,
                        artifact_id=artifact_id,
                        observation_id=obs_id,
                        job_id=job_id,
                        entity_type="Location",
                        observed_value=f"Lat: {lat}, Lon: {lon}",
                        normalized_value=coord_str,
                        source_location=loc_ref,
                        extraction_method="IMAGE_EXIF_GPS",
                        confidence=1.0,
                        provenance_trace=f"{artifact_id}:{obs_id}#{loc_ref}",
                    )
                )

        # 5. AUTOPSY FORENSIC ACCOUNT EXTRACTION
        elif obs.observation_type == ObservationType.FORENSIC_ACCOUNT and isinstance(obs.value, dict):
            acc_type = obs.value.get("account_type", "")
            ident = (obs.value.get("account_unique_identifier") or "").strip()
            row_id = obs.value.get("row_id", "0")
            if acc_type == "EMAIL" and ident:
                norm_email = normalize_email(ident)
                if norm_email:
                    sig_id = self._generate_deterministic_signal_id(case_id, obs_id, "Email", norm_email)
                    signals.append(
                        ExtractedSignal(
                            signal_id=sig_id,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            entity_type="Email",
                            observed_value=ident,
                            normalized_value=norm_email,
                            source_location=loc_ref,
                            extraction_method="AUTOPSY_ACCOUNTS_TABLE",
                            confidence=1.0,
                            provenance_trace=f"{artifact_id}:{obs_id}#accounts:{row_id}",
                        )
                    )

        # 6. AUTOPSY FORENSIC COMMUNICATION RELATIONSHIP EXTRACTION (Account Pairs)
        elif obs.observation_type == ObservationType.FORENSIC_COMMUNICATION and isinstance(obs.value, dict):
            from_acc = (obs.value.get("from_account") or "").strip()
            to_acc = (obs.value.get("to_account") or "").strip()
            rel_id = obs.value.get("row_id", "0")

            if from_acc:
                norm_from = normalize_email(from_acc)
                if norm_from:
                    sig_id_from = self._generate_deterministic_signal_id(case_id, f"{obs_id}-FROM", "Email", norm_from)
                    signals.append(
                        ExtractedSignal(
                            signal_id=sig_id_from,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            entity_type="Email",
                            observed_value=from_acc,
                            normalized_value=norm_from,
                            source_location=f"{loc_ref}:from",
                            extraction_method="AUTOPSY_ACCOUNT_COMM_FROM",
                            confidence=1.0,
                            provenance_trace=f"{artifact_id}:{obs_id}#account_relationships:{rel_id}:from",
                        )
                    )

            if to_acc:
                norm_to = normalize_email(to_acc)
                if norm_to:
                    sig_id_to = self._generate_deterministic_signal_id(case_id, f"{obs_id}-TO", "Email", norm_to)
                    signals.append(
                        ExtractedSignal(
                            signal_id=sig_id_to,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            entity_type="Email",
                            observed_value=to_acc,
                            normalized_value=norm_to,
                            source_location=f"{loc_ref}:to",
                            extraction_method="AUTOPSY_ACCOUNT_COMM_TO",
                            confidence=1.0,
                            provenance_trace=f"{artifact_id}:{obs_id}#account_relationships:{rel_id}:to",
                        )
                    )

        # 7. AUTOPSY FORENSIC EMAIL MESSAGE (Blackboard TSK_EMAIL_MSG)
        elif obs.observation_type == ObservationType.FORENSIC_EMAIL_MESSAGE and isinstance(obs.value, dict):
            ef = obs.value.get("email_from", "")
            et = obs.value.get("email_to", "")
            row_id = obs.value.get("row_id", "0")

            # Parse sender (extract Email, and Person ONLY when explicit display name exists)
            from_entries = self._parse_email_header_recipient(ef)
            for idx, (disp_name, email_addr) in enumerate(from_entries):
                norm_email = normalize_email(email_addr)
                if norm_email:
                    sig_email = self._generate_deterministic_signal_id(case_id, f"{obs_id}-F{idx}", "Email", norm_email)
                    signals.append(
                        ExtractedSignal(
                            signal_id=sig_email,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            entity_type="Email",
                            observed_value=email_addr,
                            normalized_value=norm_email,
                            source_location=f"{loc_ref}:from",
                            extraction_method="AUTOPSY_EMAIL_FROM",
                            confidence=1.0,
                            provenance_trace=f"{artifact_id}:{obs_id}#blackboard_artifacts:{row_id}:from",
                        )
                    )
                # Display name binding: ONLY when explicit display name exists (Never from email/domain alone)
                if disp_name:
                    norm_name = normalize_person_name(disp_name)
                    if norm_name and len(norm_name) >= 3:
                        sig_person = self._generate_deterministic_signal_id(case_id, f"{obs_id}-FP{idx}", "Person", norm_name)
                        signals.append(
                            ExtractedSignal(
                                signal_id=sig_person,
                                case_id=case_id,
                                evidence_id=evidence_id,
                                artifact_id=artifact_id,
                                observation_id=obs_id,
                                job_id=job_id,
                                entity_type="Person",
                                observed_value=disp_name,
                                normalized_value=norm_name,
                                source_location=f"{loc_ref}:from_name",
                                extraction_method="AUTOPSY_EMAIL_FROM_NAME",
                                confidence=0.95,
                                provenance_trace=f"{artifact_id}:{obs_id}#blackboard_artifacts:{row_id}:from_name",
                            )
                        )

            # Parse recipients
            to_entries = self._parse_email_header_recipient(et)
            for idx, (disp_name, email_addr) in enumerate(to_entries):
                norm_email = normalize_email(email_addr)
                if norm_email:
                    sig_email = self._generate_deterministic_signal_id(case_id, f"{obs_id}-T{idx}", "Email", norm_email)
                    signals.append(
                        ExtractedSignal(
                            signal_id=sig_email,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            entity_type="Email",
                            observed_value=email_addr,
                            normalized_value=norm_email,
                            source_location=f"{loc_ref}:to",
                            extraction_method="AUTOPSY_EMAIL_TO",
                            confidence=1.0,
                            provenance_trace=f"{artifact_id}:{obs_id}#blackboard_artifacts:{row_id}:to",
                        )
                    )
                if disp_name:
                    norm_name = normalize_person_name(disp_name)
                    if norm_name and len(norm_name) >= 3:
                        sig_person = self._generate_deterministic_signal_id(case_id, f"{obs_id}-TP{idx}", "Person", norm_name)
                        signals.append(
                            ExtractedSignal(
                                signal_id=sig_person,
                                case_id=case_id,
                                evidence_id=evidence_id,
                                artifact_id=artifact_id,
                                observation_id=obs_id,
                                job_id=job_id,
                                entity_type="Person",
                                observed_value=disp_name,
                                normalized_value=norm_name,
                                source_location=f"{loc_ref}:to_name",
                                extraction_method="AUTOPSY_EMAIL_TO_NAME",
                                confidence=0.95,
                                provenance_trace=f"{artifact_id}:{obs_id}#blackboard_artifacts:{row_id}:to_name",
                            )
                        )

        # 8. AUTOPSY FORENSIC EXIF GPS (Blackboard TSK_METADATA_EXIF)
        elif obs.observation_type == ObservationType.FORENSIC_EXIF_GPS and isinstance(obs.value, dict):
            lat = obs.value.get("latitude")
            lon = obs.value.get("longitude")
            row_id = obs.value.get("row_id", "0")
            if lat is not None and lon is not None:
                coord_str = f"{float(lat):.5f}, {float(lon):.5f}"
                sig_id = self._generate_deterministic_signal_id(case_id, obs_id, "Location", coord_str)
                signals.append(
                    ExtractedSignal(
                        signal_id=sig_id,
                        case_id=case_id,
                        evidence_id=evidence_id,
                        artifact_id=artifact_id,
                        observation_id=obs_id,
                        job_id=job_id,
                        entity_type="Location",
                        observed_value=f"Lat: {lat}, Lon: {lon}",
                        normalized_value=coord_str,
                        source_location=loc_ref,
                        extraction_method="AUTOPSY_EXIF_GPS",
                        confidence=1.0,
                        provenance_trace=f"{artifact_id}:{obs_id}#blackboard_artifacts:{row_id}",
                    )
                )

        # 9. AUTOPSY FORENSIC WEB HISTORY (Blackboard TSK_WEB_HISTORY)
        elif obs.observation_type == ObservationType.FORENSIC_WEB_HISTORY and isinstance(obs.value, dict):
            uname = (obs.value.get("user_name") or "").strip()
            row_id = obs.value.get("row_id", "0")
            if uname and uname.upper() not in ["SYSTEM", "LOCAL SERVICE", "NETWORK SERVICE", "ROOT", "DEFAULT", "ALL USERS"]:
                norm_name = normalize_person_name(uname)
                if norm_name and len(norm_name) >= 3:
                    sig_id = self._generate_deterministic_signal_id(case_id, obs_id, "Person", norm_name)
                    signals.append(
                        ExtractedSignal(
                            signal_id=sig_id,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            entity_type="Person",
                            observed_value=uname,
                            normalized_value=norm_name,
                            source_location=loc_ref,
                            extraction_method="AUTOPSY_WEB_USER",
                            confidence=0.90,
                            provenance_trace=f"{artifact_id}:{obs_id}#blackboard_artifacts:{row_id}",
                        )
                    )

        return signals

    def extract_relationships_from_observation(
        self,
        obs: ExtractedObservation,
        signals: List[ExtractedSignal],
        case_id: str,
        evidence_id: str,
        artifact_id: str,
        job_id: str = "",
    ) -> List[ExtractedRelationship]:
        """
        Extracts evidence-backed relationships strictly from structured or explicit contextual bindings.
        NOTE: Generic co-occurrence of two Person mentions NEVER produces an ASSOCIATED_WITH relationship.
        """
        relationships: List[ExtractedRelationship] = []
        loc_ref = obs.location_reference or "Unknown"
        obs_id = obs.observation_id

        # 1. SQLITE ROW-LEVEL STRUCTURED BINDINGS
        if obs.observation_type == ObservationType.SQLITE_SAMPLE_ROWS and isinstance(obs.value, dict):
            rows = obs.value.get("rows", [])
            for row_idx, row in enumerate(rows):
                row_signals = [s for s in signals if f"-R{row_idx}" in s.signal_id or f"Row {row_idx + 1}" in s.source_location]
                
                person_sigs = [s for s in row_signals if s.entity_type == "Person"]
                phone_sigs = [s for s in row_signals if s.entity_type == "PhoneNumber"]
                loc_sigs = [s for s in row_signals if s.entity_type == "Location"]

                # A. Contact Record: Person + Phone in the same table row -> USED_PHONE
                for p_sig in person_sigs:
                    for ph_sig in phone_sigs:
                        rel_id = self._generate_deterministic_rel_id(case_id, p_sig.signal_id, ph_sig.signal_id, "USED_PHONE")
                        relationships.append(
                            ExtractedRelationship(
                                rel_id=rel_id,
                                case_id=case_id,
                                evidence_id=evidence_id,
                                artifact_id=artifact_id,
                                observation_id=obs_id,
                                job_id=job_id,
                                source_signal_id=p_sig.signal_id,
                                target_signal_id=ph_sig.signal_id,
                                source_label="Person",
                                target_label="PhoneNumber",
                                rel_label="USED_PHONE",
                                source_location=f"{loc_ref}, Row {row_idx + 1}",
                                extraction_method="SQLITE_ROW_CONTACT_BINDING",
                                confidence=1.0,
                                human_verification_status="UNDER_REVIEW",
                            )
                        )

                # B. Residence/Location Record: Person + Location in same table row -> LOCATED_AT
                for p_sig in person_sigs:
                    for l_sig in loc_sigs:
                        rel_id = self._generate_deterministic_rel_id(case_id, p_sig.signal_id, l_sig.signal_id, "LOCATED_AT")
                        relationships.append(
                            ExtractedRelationship(
                                rel_id=rel_id,
                                case_id=case_id,
                                evidence_id=evidence_id,
                                artifact_id=artifact_id,
                                observation_id=obs_id,
                                job_id=job_id,
                                source_signal_id=p_sig.signal_id,
                                target_signal_id=l_sig.signal_id,
                                source_label="Person",
                                target_label="Location",
                                rel_label="LOCATED_AT",
                                source_location=f"{loc_ref}, Row {row_idx + 1}",
                                extraction_method="SQLITE_ROW_LOCATION_BINDING",
                                confidence=1.0,
                                human_verification_status="UNDER_REVIEW",
                            )
                        )

                # C. Call Log / Communication: Sender Phone + Receiver Phone -> CALLED
                if len(phone_sigs) >= 2:
                    # Check if columns indicate directionality (e.g. caller/callee or sender/receiver)
                    caller_sig = next((s for s in phone_sigs if "caller" in s.extraction_method.lower() or "sender" in s.extraction_method.lower()), phone_sigs[0])
                    callee_sig = next((s for s in phone_sigs if s != caller_sig), phone_sigs[1])
                    rel_id = self._generate_deterministic_rel_id(case_id, caller_sig.signal_id, callee_sig.signal_id, "CALLED")
                    relationships.append(
                        ExtractedRelationship(
                            rel_id=rel_id,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            source_signal_id=caller_sig.signal_id,
                            target_signal_id=callee_sig.signal_id,
                            source_label="PhoneNumber",
                            target_label="PhoneNumber",
                            rel_label="CALLED",
                            source_location=f"{loc_ref}, Row {row_idx + 1}",
                            extraction_method="SQLITE_ROW_COMMUNICATION_LOG",
                            confidence=1.0,
                            human_verification_status="UNDER_REVIEW",
                        )
                    )

        # 2. EXPLICIT STRUCTURED DOCUMENT CARD BINDING
        elif obs.observation_type == ObservationType.DOCUMENT_TEXT and isinstance(obs.value, str):
            text = obs.value
            person_sigs = [s for s in signals if s.entity_type == "Person" and s.observation_id == obs_id]
            phone_sigs = [s for s in signals if s.entity_type == "PhoneNumber" and s.observation_id == obs_id]

            # Look for explicit contact card syntax in document (e.g. "Name: Vikram Singh, Phone: +919876543210")
            for p_sig in person_sigs:
                for ph_sig in phone_sigs:
                    # Check if the name and phone appear in tight proximity within a line (< 120 chars)
                    p_pos = text.find(p_sig.observed_value)
                    ph_pos = text.find(ph_sig.observed_value)
                    if p_pos != -1 and ph_pos != -1 and abs(p_pos - ph_pos) < 120:
                        # Verify structured separators between them
                        snippet = text[min(p_pos, ph_pos):max(p_pos, ph_pos) + len(ph_sig.observed_value)]
                        if "\n\n" not in snippet:  # Same paragraph / block
                            rel_id = self._generate_deterministic_rel_id(case_id, p_sig.signal_id, ph_sig.signal_id, "USED_PHONE")
                            relationships.append(
                                ExtractedRelationship(
                                    rel_id=rel_id,
                                    case_id=case_id,
                                    evidence_id=evidence_id,
                                    artifact_id=artifact_id,
                                    observation_id=obs_id,
                                    job_id=job_id,
                                    source_signal_id=p_sig.signal_id,
                                    target_signal_id=ph_sig.signal_id,
                                    source_label="Person",
                                    target_label="PhoneNumber",
                                    rel_label="USED_PHONE",
                                    source_location=loc_ref,
                                    extraction_method="DOCUMENT_STRUCTURED_CONTACT_BLOCK",
                                    confidence=0.90,
                                    human_verification_status="UNDER_REVIEW",
                                )
                            )

        # 3. AUTOPSY ACCOUNT RELATIONSHIP COMMUNICATION (Email -> COMMUNICATED_WITH -> Email)
        elif obs.observation_type == ObservationType.FORENSIC_COMMUNICATION and isinstance(obs.value, dict):
            from_sigs = [s for s in signals if s.observation_id == obs_id and s.extraction_method == "AUTOPSY_ACCOUNT_COMM_FROM"]
            to_sigs = [s for s in signals if s.observation_id == obs_id and s.extraction_method == "AUTOPSY_ACCOUNT_COMM_TO"]
            for fs in from_sigs:
                for ts in to_sigs:
                    rel_id = self._generate_deterministic_rel_id(case_id, fs.signal_id, ts.signal_id, "COMMUNICATED_WITH")
                    relationships.append(
                        ExtractedRelationship(
                            rel_id=rel_id,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            source_signal_id=fs.signal_id,
                            target_signal_id=ts.signal_id,
                            source_label="Email",
                            target_label="Email",
                            rel_label="COMMUNICATED_WITH",
                            source_location=loc_ref,
                            extraction_method="AUTOPSY_ACCOUNT_RELATIONSHIP",
                            confidence=1.0,
                            human_verification_status="UNDER_REVIEW",
                        )
                    )

        # 4. AUTOPSY EMAIL MESSAGE (TSK_EMAIL_MSG)
        elif obs.observation_type == ObservationType.FORENSIC_EMAIL_MESSAGE and isinstance(obs.value, dict):
            from_person = [s for s in signals if s.observation_id == obs_id and s.extraction_method == "AUTOPSY_EMAIL_FROM_NAME"]
            from_email = [s for s in signals if s.observation_id == obs_id and s.extraction_method == "AUTOPSY_EMAIL_FROM"]
            to_person = [s for s in signals if s.observation_id == obs_id and s.extraction_method == "AUTOPSY_EMAIL_TO_NAME"]
            to_email = [s for s in signals if s.observation_id == obs_id and s.extraction_method == "AUTOPSY_EMAIL_TO"]

            # A. Display name binding: Person -> USED_EMAIL -> Email (Strictly when header binds name to email)
            for p_sig in from_person:
                for e_sig in from_email:
                    rel_id = self._generate_deterministic_rel_id(case_id, p_sig.signal_id, e_sig.signal_id, "USED_EMAIL")
                    relationships.append(
                        ExtractedRelationship(
                            rel_id=rel_id,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            source_signal_id=p_sig.signal_id,
                            target_signal_id=e_sig.signal_id,
                            source_label="Person",
                            target_label="Email",
                            rel_label="USED_EMAIL",
                            source_location=f"{loc_ref}:from",
                            extraction_method="EMAIL_HEADER_NAME_BINDING",
                            confidence=1.0,
                            human_verification_status="UNDER_REVIEW",
                        )
                    )

            for p_sig in to_person:
                for e_sig in to_email:
                    rel_id = self._generate_deterministic_rel_id(case_id, p_sig.signal_id, e_sig.signal_id, "USED_EMAIL")
                    relationships.append(
                        ExtractedRelationship(
                            rel_id=rel_id,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            source_signal_id=p_sig.signal_id,
                            target_signal_id=e_sig.signal_id,
                            source_label="Person",
                            target_label="Email",
                            rel_label="USED_EMAIL",
                            source_location=f"{loc_ref}:to",
                            extraction_method="EMAIL_HEADER_NAME_BINDING",
                            confidence=1.0,
                            human_verification_status="UNDER_REVIEW",
                        )
                    )

            # B. Primary communication graph: Email -> COMMUNICATED_WITH -> Email
            for fe in from_email:
                for te in to_email:
                    rel_id = self._generate_deterministic_rel_id(case_id, fe.signal_id, te.signal_id, "COMMUNICATED_WITH")
                    relationships.append(
                        ExtractedRelationship(
                            rel_id=rel_id,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            source_signal_id=fe.signal_id,
                            target_signal_id=te.signal_id,
                            source_label="Email",
                            target_label="Email",
                            rel_label="COMMUNICATED_WITH",
                            source_location=loc_ref,
                            extraction_method="EMAIL_MESSAGE_COMMUNICATION",
                            confidence=1.0,
                            human_verification_status="UNDER_REVIEW",
                        )
                    )

            # C. Person-level communication: Person -> COMMUNICATED_WITH -> Person
            # Created ONLY when explicit Person <-> Email evidence exists on both ends
            for fp in from_person:
                for tp in to_person:
                    rel_id = self._generate_deterministic_rel_id(case_id, fp.signal_id, tp.signal_id, "COMMUNICATED_WITH")
                    relationships.append(
                        ExtractedRelationship(
                            rel_id=rel_id,
                            case_id=case_id,
                            evidence_id=evidence_id,
                            artifact_id=artifact_id,
                            observation_id=obs_id,
                            job_id=job_id,
                            source_signal_id=fp.signal_id,
                            target_signal_id=tp.signal_id,
                            source_label="Person",
                            target_label="Person",
                            rel_label="COMMUNICATED_WITH",
                            source_location=loc_ref,
                            extraction_method="EMAIL_MESSAGE_PERSON_COMMUNICATION",
                            confidence=0.95,
                            human_verification_status="UNDER_REVIEW",
                        )
                    )

        return relationships
