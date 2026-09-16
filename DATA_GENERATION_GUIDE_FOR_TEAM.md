# CRIMENET Intelligence Lab — Synthetic Case Data Generation Guide
**Operational Guide & Evidentiary Blueprint for Team Members**

---

| **Document Metadata** | **Specification** |
|:---|:---|
| **Assigned Role** | Forensic Data Architect / Synthetic Evidence Creator |
| **Target Platform** | **CRIMENET Intelligence Lab** (SIH / National Crime Records Bureau) |
| **Objective** | Generate a comprehensive, realistic, and deeply interconnected synthetic case dataset (FIRs, financial ledgers, CDRs, CCTV photos with GPS, vehicle ANPR logs) to demonstrate automated network link discovery, criminal contact zones, and explainable decision-support graphs. |
| **Compliance Standard** | **100% Synthetic / Fictitious Data.** Absolutely zero personally identifiable information (PII) or confidential police records. All names, numbers, Aadhaar numbers, and accounts must be completely invented. |

---

## 1. Executive Overview & Your Mission

As the **Data Creation Specialist**, your role is the foundation of our entire project demonstration.

CRIMENET is not a simple database search tool or static viewer — it is an **AI-powered criminal relationship intelligence and decision-support platform**. When an investigator uploads a forensic case, our backend engines scan the files, resolve entities, extract hidden connections across different sources, and construct an interactive, explainable criminal network:

```text
[Raw Evidence Files & Folders]
   ├── FIR Documents (PDF / CCTNS format)
   ├── Bank Statements & UPI Ledgers (Google Sheets / CSV)
   ├── Call Detail Records & Mobile Dumps (CSV / SQLite)
   └── Surveillance Images & CCTV (JPG with EXIF GPS)
                  │
                  ▼ (Deep Parsers: SQLite, PDF, EXIF Media)
   [Entity Resolution: Resolves Persons, Phones, Accounts, Vehicles, Locations]
                  │
                  ▼ (Kùzu Graph Engine & CCC Scoring Algorithm)
   [Interactive Concentric Network: 🔴 Layer 1 (Red) | 🟡 Layer 2 (Yellow) | 🟢 Layer 3 (Green)]
```

### The Golden Rule of Synthetic Crime Data:
> **"Every key suspect and relationship must leave evidentiary breadcrumbs across at least two independent data sources."**
>
> If you mention a suspect phone number in a Call Detail Record (CDR), ensure that *same phone number* appears in an FIR suspect sheet, a UPI transaction remark, or an Android contact list. 
> If you record an ATM cash withdrawal in a bank statement, ensure a CCTV photograph exists at that *exact timestamp* and *GPS location*. 
> This multi-source cross-validation triggers CRIMENET's Entity Resolution and CCC (Criminal Contact Category) scoring to identify high-confidence analytical leads (🔴 RED Ring)!

---

## 2. The Master Crime Storyline: "Operation Cyber-Shield"
*(Use this blueprint directly or adapt it to your specific scenario)*

To ensure that all generated files, sheets, and photos fit together seamlessly, build all your records around a single, coherent syndicate storyline:

```text
                          [VICTIM]
                  Dr. Sunita Sharma (New Delhi)
                  Defrauded: ₹45,00,000 (Digital Arrest Scam)
                            │
                            ▼ (RTGS / Net Banking)
                [MULE LAYER 1 - RECRUITER & TRI-JUNCTION]
               Ramesh Varma (Noida, UP)
               Phone: +91-9876543210 | ICICI: 123405009876
                            │
            ┌───────────────┴───────────────┐
            ▼ (Split Transfer ₹15L)          ▼ (Split Transfer ₹15L)
  [MULE LAYER 2 - CASHOUT]           [SECONDARY INTERMEDIARY]
   Suresh Patel (Jaipur)              Alok Mehta (Tech / SIM Vendor)
   Phone: +91-9811223344              Phone: +91-9822334455
   HDFC: 987654123098                 Axis Bank: 445566778899
            │                                │
            └───────────────┬────────────────┘
                            ▼ (Cash Deliveries & VoIP Coordination)
                  [CENTRAL TARGET - SYNDICATE KINGPIN]
                       Vikram Singh (New Delhi)
               Phone: +91-9899887766 | Vehicle: DL-01-AB-1234
               HDFC: 50100456789012 | Cashout Zone: Noida Sec 18
```

### The 4 Network Layers to Generate:
1. **Layer 0 (Central Target / Key Suspect):**
   - **Name:** Vikram Singh
   - **Role:** Syndicate coordinator and principal beneficiary.
   - **Identifiers:** Phone `+91-9899887766`, Vehicle `DL-01-AB-1234`, Account `HDFC 50100456789012`.
2. **Layer 1 (Direct Criminal Associates — 🔴 RED Ring, CCC Score > 75):**
   - **Ramesh Varma:** Mule recruiter (`+91-9876543210`, 14 calls with Vikram, large financial transfers, co-located in Connaught Place).
   - **Suresh Patel:** Cash handler (`+91-9811223344`, 11 calls with Vikram, captured on ATM CCTV).
   - **Alok Mehta:** Infrastructure facilitator (`+91-9822334455`, shared VoIP server).
3. **Layer 2 (Intermediaries & Facilitators — 🟡 YELLOW Ring, CCC Score 41–75):**
   - 4 to 8 second-hop contacts: local SIM card vendors, car rental agents, bank branch contacts who deal with Ramesh or Suresh but have only indirect ties to Vikram.
4. **Layer 3 (Contextual / Peripheral Nodes — 🟢 GREEN Ring, CCC Score ≤ 40):**
   - 10 to 15 peripheral entities: the victim, family members, food delivery drivers, random incoming calls (1–2 one-off contacts).

---

## 3. Standardized Folder Architecture

Organize all case files inside this exact folder hierarchy. This guarantees our automated forensic intake and deep parsers can ingest the package without manual intervention:

```text
CASE_PACKAGE_2026_001/
├── 01_FIR_DOCUMENTS/
│   ├── FIR_2026_0101_Cyber_Arrest_Extortion.pdf
│   ├── FIR_2026_0102_Noida_Mule_Network.pdf
│   └── FIR_2026_0103_Illegal_SIM_Syndicate.pdf
├── 02_FINANCIAL_RECORDS/
│   ├── bank_statements/
│   │   ├── HDFC_Account_50100456789012_VikramSingh.csv
│   │   ├── ICICI_Mule_123405009876_RameshVarma.csv
│   │   ├── HDFC_Mule_987654123098_SureshPatel.csv
│   │   └── SBI_Victim_334455667788_SunitaSharma.csv
│   ├── upi_transactions/
│   │   └── UPI_Gateway_Consolidated_Ledger_2026.csv
│   └── cash_hawala/
│       └── Hawala_Token_Ledger_Encrypted.csv
├── 03_COMMUNICATION_CDRS/
│   ├── cdr_csv/
│   │   ├── CDR_Target_9899887766_Jan_Feb_2026.csv
│   │   ├── CDR_Mule1_9876543210_Jan_Feb_2026.csv
│   │   └── CDR_Mule2_9811223344_Jan_Feb_2026.csv
│   ├── mobile_extractions/
│   │   ├── contacts2.db              # SQLite contacts database
│   │   └── calllog.db                # SQLite calls database
│   └── chat_exports/
│       └── WhatsApp_Mule_Coordination_Chat.txt
├── 04_SURVEILLANCE_MEDIA/
│   ├── suspect_photos/
│   │   ├── SUSPECT_Vikram_Singh_Front.jpg
│   │   └── SUSPECT_Ramesh_Varma_Profile.jpg
│   ├── cctv_atm_captures/
│   │   ├── CCTV_ATM_Cashout_Sec18_Noida.jpg      # Embedded EXIF GPS!
│   │   └── CCTV_Hotel_Park_TriJunction.jpg       # Embedded EXIF GPS!
│   └── seized_id_documents/
│       ├── Forged_Aadhaar_Vikram_Singh.pdf
│       └── Fake_Rent_Agreement_Noida.pdf
├── 05_VEHICLE_ANPR/
│   ├── toll_fastag_logs/
│   │   └── FASTag_Toll_Transactions_DND_Flyway.csv
│   └── vehicle_snapshots/
│       └── ANPR_DND_Toll_DL01AB1234.jpg          # Embedded EXIF GPS!
└── 06_GROUND_TRUTH_MANIFEST/
    ├── GROUND_TRUTH_NETWORK.json
    └── CASE_SUMMARY_AND_LEADS.md
```

---

## 4. Exact Specifications for Each Data Type

### 4.1 First Information Reports (FIR Documents)
* **File Type:** `.pdf` (preferred, exported from Word/Google Docs) or `.txt`.
* **Standard:** CCTNS Police FIR Template.
* **Crucial Formatting Requirement for Entity Extraction:**
  Our NLP and regex parser looks for explicit prefixes. Always include a structured section in the FIR text formatted exactly like this:

```text
DETAILS OF KNOWN / SUSPECTED / ACCUSED PERSONS:
1. Accused #1 (Suspected Coordinator):
   Name: Vikram Singh
   Father's Name: Late Ranveer Singh
   Contact: +91-9899887766
   Address: Flat 402, Royal Palms, Rohini Sector 13, New Delhi - 110085
   Bank Account: 50100456789012 (HDFC Bank, IFSC: HDFC0001234)
   Associated Vehicle: DL-01-AB-1234 (Black Mahindra Scorpio)

2. Accused #2 (Mule Account Holder):
   Name: Ramesh Varma
   Contact: +91-9876543210
   Address: B-12, Sector 22, Noida, Uttar Pradesh - 201301
   Bank Account: 123405009876 (ICICI Bank, IFSC: ICIC0005678)
   UPI ID: ramesh.v@okhdfcbank
```

* **Narrative Section:**
  Write a 2 to 3 paragraph story explaining how Dr. Sunita Sharma was intimidated by callers posing as CBI/Customs officers, threatened with arrest over an illegal parcel, and coerced into transferring ₹45 Lakhs to the ICICI mule account.

---

### 4.2 Financial Records (Google Sheets / CSV Formats)

Financial data is the bedrock of our **Critical Contact Category (CCC)** scoring. It proves the flow of proceeds from victim to suspect.

#### Google Sheet #1: Bank Account Statements (`bank_statements/*.csv`)
Create one CSV per bank account. Ensure exact column names:

| Column Name | Type | Description | Example |
|---|---|---|---|
| `Transaction_ID` | String | Unique reference ID | `TXN-2026-9011` |
| `Date_Time` | YYYY-MM-DD HH:MM:SS | Exact transaction timestamp | `2026-02-14 10:15:22` |
| `Value_Date` | YYYY-MM-DD | Settlement date | `2026-02-14` |
| `Description_Remarks` | String | Purpose / Narrative | `RTGS-CYBER-ARREST-TRANSFER` |
| `Reference_UTR` | String | Interbank reference number | `UTR98765432101` |
| `Debit_INR` | Float (2 decimals) | Outgoing amount | `0.00` |
| `Credit_INR` | Float (2 decimals) | Incoming amount | `4500000.00` |
| `Balance_INR` | Float (2 decimals) | Running balance | `4500000.00` |
| `Counterparty_Account` | String | Destination / Origin Account | `123405009876` |
| `Counterparty_Name` | String | Beneficiary / Sender Name | `Ramesh Varma` |
| `Counterparty_IFSC` | String | 11-digit IFSC code | `ICIC0005678` |

#### How to Simulate the Illicit Fund Flow in the CSVs:
1. **Victim Account (`SBI_Victim...csv`):**
   - Debit: `₹45,00,000.00` → Credit to Ramesh Varma (`123405009876`) at `10:15:00`.
2. **Mule Account 1 (`ICICI_Mule...csv`):**
   - Receives `₹45,00,000.00` at `10:15:00`.
   - Within 15 minutes, splits the money:
     - Transfers `₹15,00,000.00` to Suresh Patel (`987654123098`) at `10:22:00`.
     - Transfers `₹15,00,000.00` to Vikram Singh (`50100456789012`) at `10:25:00`.
     - Retains `₹1,00,000.00` as commission.
3. **Primary Accused Account (`HDFC_Account...csv`):**
   - Receives `₹15,00,000.00` at `10:25:00`.
   - At `11:05:00`, logs an ATM cash withdrawal of `₹50,000.00` at Noida Sector 18 ATM.

---

#### Google Sheet #2: UPI Gateway Ledger (`upi_transactions/*.csv`)
Captures fast digital payments and micro-kickbacks:

| Column Name | Example Value |
|---|---|
| `UPI_Txn_ID` | `UPI-2026-88012` |
| `Timestamp` | `2026-02-14 12:30:10` |
| `Payer_VPA` | `ramesh.v@okhdfcbank` |
| `Payer_Name` | `Ramesh Varma` |
| `Payer_Mobile` | `+919876543210` |
| `Payee_VPA` | `vikram.king@paytm` |
| `Payee_Name` | `Vikram Singh` |
| `Payee_Mobile` | `+919899887766` |
| `Amount_INR` | `95000.00` |
| `Status` | `SUCCESS` |
| `Device_IP` | `103.21.144.62` |
| `Remarks` | `Mule Commission Feb Batch` |

---

### 4.3 Communication Records (CDRs & Phone Logs)

CDRs provide the frequency and temporal proximity required to position suspects into **Layer 1 (Red Ring)**.

#### Call Detail Records (`cdr_csv/*.csv`)
Use these standard telecom operator columns:

| Column Name | Format / Example | Operational Purpose |
|---|---|---|
| `Record_ID` | `CDR-2026-001` | Unique row identifier |
| `Caller_MSISDN` | `+919899887766` | Phone placing the call (E.164) |
| `Receiver_MSISDN` | `+919876543210` | Phone receiving the call (E.164) |
| `Call_DateTime` | `2026-02-14 09:15:30` | Date and time (must match timeline!) |
| `Call_Duration_Sec` | `420` | Duration in seconds (longer = closer relationship) |
| `Call_Type` | `OUTGOING` / `INCOMING` | Direction of call |
| `IMEI` | `864201041234567` | 15-digit handset hardware ID |
| `IMSI` | `404450123456789` | 15-digit SIM card subscription ID |
| `Cell_Tower_ID` | `DEL-CP-TWR04` | Specific tower serving call |
| `Tower_Location_Name` | `Connaught Place Inner Circle, Delhi` | Human-readable location |
| `Tower_GPS_Coordinates` | `28.6315, 77.2167` | Exact decimal coordinates |

#### Frequency Tuning for Ring Placement:
* **To place Ramesh Varma in 🔴 RED Ring:**
  - Create **12 to 16 calls** between Vikram (`+91-9899887766`) and Ramesh (`+91-9876543210`) over the 7 days surrounding the crime date.
  - Make several calls occur *immediately before* and *immediately after* the ₹45 Lakhs bank transfer!
* **To place Suresh Patel in 🔴 RED Ring:**
  - Create **10 calls** between Ramesh and Suresh, plus **8 calls** between Suresh and Vikram.
* **To place Alok Mehta in 🟡 YELLOW Ring:**
  - Create **4 calls** (infrequent, purely functional coordination).
* **For 🟢 GREEN Ring (Distant Contacts):**
  - Create **1 call** with a duration of 30 seconds.

---

### 4.4 Surveillance Images & CCTV Captures (with EXIF GPS)

Our media parser (`src/parsers/image_parser.py`) extracts EXIF metadata directly from JPEG files.

#### Guidelines for Images:
1. **File Format:** `.jpg` or `.jpeg` (standard JPEG files support EXIF).
2. **What Images to Create:**
   - `CCTV_ATM_Cashout_Sec18_Noida.jpg`: ATM surveillance camera showing a hooded individual at an ATM.
   - `CCTV_Hotel_Park_TriJunction.jpg`: Lobby camera showing two suspects sitting at a table together.
   - `ANPR_DND_Toll_DL01AB1234.jpg`: Toll booth capture of Vikram Singh's vehicle.
   - `SUSPECT_Vikram_Singh_Front.jpg`: Front-facing ID / mugshot photo.
3. **Mandatory Metadata to Embed in the Images:**
   - **GPS Coordinates (Latitude, Longitude):** Must point to the crime or meeting scene.
   - **Timestamp (DateTimeOriginal):** Must match the time of the transaction or CDR call!

---

### 4.5 Vehicle & ANPR Fastag Logs (`05_VEHICLE_ANPR/`)

Vehicle movements prove physical association and travel between crime locations:

| Log_ID | Timestamp | Toll_Plaza_Name | Lane | HSRP_Number | FASTag_ID | Direction | Make_Model |
|---|---|---|---|---|---|---|---|
| FASTAG-501 | 2026-02-14 08:45:10 | DND Flyway Toll Plaza | Lane 03 | DL-01-AB-1234 | 34161FA890 | Delhi to Noida | Mahindra Scorpio (Black) |
| FASTAG-502 | 2026-02-14 12:15:40 | DND Flyway Toll Plaza | Lane 06 | DL-01-AB-1234 | 34161FA890 | Noida to Delhi | Mahindra Scorpio (Black) |

---
## 5. Engineering "Criminal Contact Zones" & Tri-Junctions

The SIH evaluation team will specifically look for how well our system uncovers **Suspicious Contact Zones** and **Tri-Junction Entities**.

### 1. How to Construct a "Tri-Junction Entity":
A Tri-Junction entity connects two parties who never interact directly:

$$\text{Dr. Sunita Sharma (Victim)} \xrightarrow[\text{Bank Transfer}]{\text{₹45,00,000}} \mathbf{\text{Ramesh Varma [TRI-JUNCTION]}} \xrightarrow[\text{14 Calls + ₹15L Transfer}]{\text{Syndicate Proceeds}} \text{Vikram Singh (Accused)}$$

- The victim doesn't know Vikram Singh.
- Vikram Singh never called the victim.
- **Ramesh Varma is the Tri-Junction Node** that breaks the case wide open.

### 2. How to Construct a "Suspicious Geographic Zone":
Align multiple independent data sources to the **exact same physical coordinates**:

* **Zone 1: Connaught Place Inner Circle, New Delhi (`28.6315, 77.2167`)**
  - Vikram Singh's phone connects to Tower `DEL-CP-TWR04` at `2026-02-13 18:30:00`.
  - Ramesh Varma's phone connects to the *same tower* at `2026-02-13 18:35:00`.
  - Result: Co-location evidence (Meeting Lead)!

* **Zone 2: Sector 18 Market ATM, Noida (`28.5708, 77.3261`)**
  - HDFC ATM Cash withdrawal timestamp: `2026-02-14 11:05:00`.
  - CCTV Photo EXIF timestamp: `2026-02-14 11:05:12`, GPS: `28.5708, 77.3261`.
  - Toll booth logged vehicle `DL-01-AB-1234` exiting towards Noida 20 minutes earlier (`08:45:10`).
  - Result: Perfect multi-source tri-angulation!

---

## 6. Pre-Made Copy-Paste Google Sheets Templates

Share this section directly with the team member to paste straight into Google Sheets:

### Template A: `Bank_Transactions_Master.csv`
| Transaction_ID | Timestamp | Value_Date | Account_Number | Bank_Name | IFSC | Counterparty_Account | Counterparty_Name | Counterparty_IFSC | Debit_INR | Credit_INR | Balance_INR | UTR_Reference | Remarks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TXN-101 | 2026-02-14 10:15:00 | 2026-02-14 | 334455667788 | State Bank of India | SBIN0001234 | 123405009876 | Ramesh Varma | ICIC0005678 | 4500000.00 | 0.00 | 25000.00 | UTR901 | RTGS Cyber Arrest Extortion |
| TXN-102 | 2026-02-14 10:25:30 | 2026-02-14 | 123405009876 | ICICI Bank | ICIC0005678 | 50100456789012 | Vikram Singh | HDFC0001234 | 1500000.00 | 0.00 | 3000000.00 | UTR902 | IMPS Syndicate Transfer |
| TXN-103 | 2026-02-14 10:30:15 | 2026-02-14 | 123405009876 | ICICI Bank | ICIC0005678 | 987654123098 | Suresh Patel | HDFC0001234 | 1500000.00 | 0.00 | 1500000.00 | UTR903 | IMPS Hawala Cashout Share |
| TXN-104 | 2026-02-14 11:05:00 | 2026-02-14 | 50100456789012 | HDFC Bank | HDFC0001234 | CASH-WDL | Self (ATM) | HDFC0001234 | 50000.00 | 0.00 | 1450000.00 | ATM-01 | ATM Cashout Noida Sec 18 |

---

### Template B: `CDR_Communications_Master.csv`
| Record_ID | Caller_Number | Receiver_Number | Call_DateTime | Duration_Sec | Call_Type | IMEI | Cell_Tower_ID | Tower_Location | GPS_Coordinates |
|---|---|---|---|---|---|---|---|---|---|
| CDR-001 | +919899887766 | +919876543210 | 2026-02-13 18:30:00 | 420 | OUTGOING | 864201041234567 | TWR-DEL-CP01 | Connaught Place Inner Circle | 28.6315, 77.2167 |
| CDR-002 | +919876543210 | +919899887766 | 2026-02-13 19:15:20 | 185 | INCOMING | 865502049876543 | TWR-DEL-CP02 | Connaught Place Radial 3 | 28.6322, 77.2185 |
| CDR-003 | +919899887766 | +919876543210 | 2026-02-14 09:10:00 | 510 | OUTGOING | 864201041234567 | TWR-DEL-CP01 | Connaught Place Inner Circle | 28.6315, 77.2167 |
| CDR-004 | +919876543210 | +919811223344 | 2026-02-14 10:45:00 | 240 | OUTGOING | 865502049876543 | TWR-NOI-S18 | Sector 18 Market Noida | 28.5708, 77.3261 |
| CDR-005 | +919811223344 | +919899887766 | 2026-02-14 11:20:10 | 95 | OUTGOING | 867703041122334 | TWR-NOI-S18 | Sector 18 Market Noida | 28.5708, 77.3261 |

---

## 7. Ready-to-Use Python Script: Generate Geotagged Evidence Images

To make it effortless to generate test JPEG images with valid EXIF GPS coordinates, share this Python script. You can run it locally with `python generate_images.py`:

```python
"""
CRIMENET Synthetic Media Generator
Generates valid JPEG images embedded with exact EXIF GPS and timestamps.
Requires: pip install pillow piexif
"""
import os
import piexif
from PIL import Image, ImageDraw, ImageFont

def deg_to_dms(deg_float):
    deg = int(deg_float)
    min_float = (deg_float - deg) * 60
    minutes = int(min_float)
    sec_float = (min_float - minutes) * 60
    seconds = int(sec_float * 100)
    return ((deg, 1), (minutes, 1), (seconds, 100))

def create_evidence_image(filepath, title_text, lat, lon, timestamp_str="2026:02:14 11:05:12"):
    # Create a 800x600 dark surveillance frame
    img = Image.new("RGB", (800, 600), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    # Draw simple CCTV reticle overlay
    draw.rectangle([50, 50, 750, 550], outline=(0, 255, 136), width=2)
    draw.line([400, 40, 400, 70], fill=(0, 255, 136), width=2)
    draw.line([400, 530, 400, 560], fill=(0, 255, 136), width=2)
    draw.line([40, 300, 70, 300], fill=(0, 255, 136), width=2)
    draw.line([730, 300, 760, 300], fill=(0, 255, 136), width=2)
    
    # Draw text banner
    draw.text((70, 70), f"[CCTV SURVEILLANCE FEED - EVIDENCE LOG]", fill=(255, 255, 255))
    draw.text((70, 100), f"ARTIFACT: {title_text}", fill=(0, 255, 136))
    draw.text((70, 125), f"TIMESTAMP: {timestamp_str.replace(':', '-', 2)}", fill=(148, 163, 184))
    draw.text((70, 150), f"GPS COORDS: {lat:.5f} N, {lon:.5f} E", fill=(148, 163, 184))

    # Construct EXIF GPS dictionary
    lat_dms = deg_to_dms(abs(lat))
    lon_dms = deg_to_dms(abs(lon))
    lat_ref = b'N' if lat >= 0 else b'S'
    lon_ref = b'E' if lon >= 0 else b'W'

    gps_dict = {
        piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
        piexif.GPSIFD.GPSLatitudeRef: lat_ref,
        piexif.GPSIFD.GPSLatitude: lat_dms,
        piexif.GPSIFD.GPSLongitudeRef: lon_ref,
        piexif.GPSIFD.GPSLongitude: lon_dms,
    }

    exif_dict = {
        piexif.ExifIFD.DateTimeOriginal: timestamp_str.encode("utf-8"),
        piexif.ExifIFD.UserComment: b"CRIMENET Synthetic Forensic Evidence",
    }

    zeroth_dict = {
        piexif.ImageIFD.Make: b"Hikvision Digital Systems",
        piexif.ImageIFD.Model: b"DS-2CD7A26G0 ANPR CCTV",
    }

    exif_bytes = piexif.dump({"0th": zeroth_dict, "Exif": exif_dict, "GPS": gps_dict})
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    img.save(filepath, "jpeg", exif=exif_bytes)
    print(f"[+] Successfully generated geotagged evidence: {filepath} ({lat}, {lon})")

if __name__ == "__main__":
    # 1. Noida Sector 18 ATM Cashout
    create_evidence_image(
        "04_SURVEILLANCE_MEDIA/cctv_atm_captures/CCTV_ATM_Cashout_Sec18_Noida.jpg",
        "ATM Cash Withdrawal - Primary Suspect Cashout",
        28.5708, 77.3261,
        "2026:02:14 11:05:12"
    )
    # 2. Hotel Park Lobby Meeting (Tri-Junction)
    create_evidence_image(
        "04_SURVEILLANCE_MEDIA/cctv_atm_captures/CCTV_Hotel_Park_TriJunction.jpg",
        "Suspect Co-location Meeting - Connaught Place",
        28.6315, 77.2167,
        "2026:02:13 18:35:00"
    )
    # 3. DND Toll Plaza ANPR Capture
    create_evidence_image(
        "05_VEHICLE_ANPR/vehicle_snapshots/ANPR_DND_Toll_DL01AB1234.jpg",
        "Vehicle DL-01-AB-1234 Crossing DND Flyway",
        28.5724, 77.2789,
        "2026:02:14 08:45:10"
    )
```

---

## 8. Pre-Handover Quality Checklist

Before sending the completed dataset folder or Google Drive link to the development team, run through this verification checklist:

- [ ] **1. Multi-Source Confirmation:** Does every primary suspect (Vikram, Ramesh, Suresh) appear in **at least 2 independent file types** (e.g., both in an FIR and a CDR, or both in a Bank CSV and an Image)?
- [ ] **2. Phone Format Accuracy:** Are all mobile numbers in international standard or 10-digit format (e.g., `+919899887766` or `+91-9899887766`)?
- [ ] **3. Account & IFSC Compliance:**
  - Are bank accounts between 9 and 18 digits?
  - Are all IFSC codes 11 characters formatted as 4 letters + 0 + 6 alphanumeric characters (e.g., `SBIN0001234`, `HDFC0001234`, `ICIC0005678`)?
- [ ] **4. Chronological Realism:**
  - Crime event occurs → Bank funds transferred → Money split across mules → ATM cashout occurs → FIR registered.
  - No call or withdrawal occurs *before* the victim's money leaves their account.
- [ ] **5. Radial Layer Proportions:**
  - Layer 1 (Red Ring): 2 to 4 core contacts (high call frequency: 10+ calls).
  - Layer 2 (Yellow Ring): 5 to 8 intermediate contacts (moderate call frequency: 3–5 calls).
  - Layer 3 (Green Ring): 10 to 15 background entities (1–2 calls).
- [ ] **6. Clean Folder Hierarchy:** Are all files organized into the numbered subfolders (`01_FIR_DOCUMENTS`, `02_FINANCIAL_RECORDS`, etc.)?
- [ ] **7. Zero Real Confidential Data:** Are all names, numbers, Aadhaar numbers, and accounts 100% fictitious?

---

## 9. Summary: How This Will Be Demonstrated Live

When your completed folder is packaged into an evidence disk image and loaded into CRIMENET:

1. **Intake:** The investigator drags and drops the evidence file into the portal.
2. **Deep Parsing:** In seconds, our parsers ingest the FIR PDFs, scan the bank statement CSVs, read the CDR logs, and parse the EXIF GPS tags from the CCTV photos.
3. **Graph Construction:** The backend resolves all entities, detects that Ramesh Varma is the Tri-Junction connecting the victim to Vikram Singh, and computes CCC scores.
4. **Investigator Dashboard:**
   - Vikram Singh appears at the center.
   - 🔴 **Red Ring:** Ramesh Varma and Suresh Patel light up immediately.
   - **"Why Linked?" Panel:** Clicking the edge reveals: *"14 phone calls + ₹15,00,000 bank transfer + shared cell tower at Connaught Place."*
   - **Map & Timeline:** The suspect co-location at Connaught Place and Noida ATM lights up on the investigation map.

This creates a show-stopping, rock-solid demonstration for the hackathon judges and senior law enforcement officers!
