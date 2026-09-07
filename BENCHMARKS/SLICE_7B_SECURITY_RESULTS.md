# CRIMENET Slice 7B — Security & Authorization Validation Results

**Date:** September 7, 2026  
**Auditor:** CRIMENET Forensic Security & Access Control Lab  
**Security Standard:** Zero-Trust Forensic Enclave, PolicyEngine BOLA/BFLA Enforcement, Cryptographic Immutability

---

## 1. Security Overview

Slice 7B validates that the integrated Investigator Workspace enforces strict authentication, role-based access control, broken object-level authorization (BOLA) defense, broken function-level authorization (BFLA) defense, and local evidence path sanitization.

All endpoints handling sensitive forensic images, case metadata, and extracted artifacts require valid JWT credentials and case-scoped authorization.

---

## 2. Authentication & Identity Verification

| Test Scenario | Input / Request | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Valid Login** | `officer1` / `OfficerPass123!` | HTTP 200, JWT token returned | HTTP 200, valid JWT issued | **PASS** |
| **Invalid Password** | `officer1` / `WrongPassword` | HTTP 401 Unauthorized | HTTP 401 Unauthorized | **PASS** |
| **Unknown Username** | `unknown_user` / `AnyPassword` | HTTP 401 Unauthorized | HTTP 401 Unauthorized | **PASS** |
| **Unauthenticated /me** | `GET /api/v1/auth/me` (No Auth Header) | HTTP 401 Unauthorized | HTTP 401 Unauthorized | **PASS** |
| **Authenticated /me** | `GET /api/v1/auth/me` (Bearer JWT) | HTTP 200, user identity | HTTP 200, `officer1` | **PASS** |
| **Tampered Token** | Modified JWT payload signature | HTTP 401 Unauthorized | HTTP 401 Unauthorized | **PASS** |

---

## 3. BOLA & BFLA Access Control Defense Matrix

| Attack Vector | Actor | Target Resource | Mechanism | Response | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cross-Case Retrieval** | `officer2` | `CASE-2026-001` | URL Parameter Tampering | HTTP 403 Forbidden | **PASS** |
| **Cross-Case Evidence Read** | `officer2` | `EV-2026-15F0` in Case 001 | BOLA Direct Resource Query | HTTP 403 Forbidden | **PASS** |
| **Cross-Case Evidence Process** | `officer2` | Trigger Process on Case 001 | BOLA Action Request | HTTP 403 Forbidden | **PASS** |
| **Cross-Case Artifact Listing** | `officer2` | Artifacts for Case 001 | BOLA Endpoint Query | HTTP 403 Forbidden | **PASS** |
| **Cross-Case Content Stream** | `officer2` | `ART-2026-001-1E6EA53D` Content | Unauthorized Data Exfiltration | HTTP 403 Forbidden | **PASS** |
| **Unauthenticated Stream** | Anonymous | `ART-2026-001-1E6EA53D` Content | Direct URL Access without Token | HTTP 401 Unauthorized | **PASS** |
| **Non-existent Artifact** | `officer1` | `ART-NONEXISTENT-9999` | Probing Non-existent Resource | HTTP 404 Not Found | **PASS** |
| **Judicial Override Attempt** | `officer1` | Judicial Override API | Vertical Privilege Escalation | HTTP 403 Forbidden | **PASS** |
| **Audit Logs Inspection** | `officer1` | System Audit Trails | Vertical Privilege Escalation | HTTP 403 Forbidden | **PASS** |

---

## 4. Local Evidence Registration & Path Security

To support local registration of large raw forensic disk images without duplicating 1.8 GB of evidence on disk, `POST /api/v1/cases/{case_id}/evidence` accepts `local_image_path` under five defense-in-depth controls:

```
User Input: local_image_path
     │
     ▼
[Step 1: Canonical Path Resolution] ──► Path(p).resolve() eliminates relative elements
     │
     ▼
[Step 2: Server Directory Allowlist] ──► Must reside in D:\Proto SIH\Images\ or approved vault
     │                                   (Rejects D:\Windows\System32, /etc/passwd, etc.)
     ▼
[Step 3: Path Traversal Check] ────────► Path.is_relative_to(allowlist) prevents parent escape
     │
     ▼
[Step 4: Existence & Magic Header] ────► File must exist; header must begin with b"EVF"
     │
     ▼
[Step 5: Zero-Byte NTFS Hardlink] ─────► os.link() preserves byte count, blocks alterations
```

### Empirical Test Results:

1. **Path Traversal Escape Attack:**  
   - Input: `local_image_path: "../../Windows/System32/cmd.exe"`  
   - Result: `HTTP 403 Forbidden` (`SECURITY ALERT: Path 'D:\Windows\System32\cmd.exe' is outside approved evidence locations.`)  
   - Status: **PASS**

2. **Non-Existent File Probe:**  
   - Input: `local_image_path: "D:/Proto SIH/Images/DoesNotExist_12345.E01"`  
   - Result: `HTTP 400 Bad Request` (`Forensic source file not found`)  
   - Status: **PASS**

3. **Valid Approved Local Path:**  
   - Input: `local_image_path: "D:/Proto SIH/Images/Images_Set_1.E01"`  
   - Result: `HTTP 201 Created`, Evidence ID `EV-2026-15F0`, companion `.E02` co-located via zero-byte hardlink.  
   - Status: **PASS**

---

## 5. Artifact Content Streaming Security

Browser native viewers (such as `<iframe>` and `<img>`) cannot attach custom `Authorization: Bearer <token>` headers to standard `src` attributes.  
Instead of compromising security with cookies, query string tokens, or unauthenticated endpoints, CRIMENET implements **Bearer-Authenticated Blob Streaming**:

1. Frontend initiates authenticated `fetch(content_url, { headers: { 'Authorization': 'Bearer ' + token } })`.
2. Backend validates JWT and enforces BOLA authorization for the target case and artifact.
3. Backend validates content path canonical containment within `DATA/processing_output/`.
4. Frontend receives validated binary stream, generates an ephemeral `URL.createObjectURL(blob)`, and injects into the viewer.
5. On modal close, `URL.revokeObjectURL()` immediately deallocates memory, preventing token or content leakage.

---

## 6. Cryptographic Chain-of-Custody & Evidence Immutability

| Artifact / Segment | Pre-Test SHA-256 Digest | Post-Test SHA-256 Digest | Match? |
| :--- | :--- | :--- | :--- |
| **`Images_Set_1.E01`** | `733948eee283af8e0dc9c6e389039569a41c4522172e8cdfcebf34e86f1cd21a` | `733948eee283af8e0dc9c6e389039569a41c4522172e8cdfcebf34e86f1cd21a` | **100.0% IDENTICAL** |
| **`Images_Set_1.E02`** | `1da71529a72d2e10e060efe900616f098691c65787ada11c95cefed7f8e0f84d` | `1da71529a72d2e10e060efe900616f098691c65787ada11c95cefed7f8e0f84d` | **100.0% IDENTICAL** |

**Conclusion:** Zero bits were modified, rewritten, or transformed throughout the full end-to-end integration and testing cycle.
