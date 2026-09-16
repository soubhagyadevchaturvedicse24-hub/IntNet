"""
Direct ingestion of CDR and Financial data from CRIMENET_DEMO_CASE
into the Kùzu graph for CASE-2026-C1EA.
"""
import csv, hashlib, sys, os, kuzu
sys.path.insert(0, os.getcwd())

case_id = "CASE-2026-C1EA"
evidence_id = "EV-2026-BBDC392CF293"

from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator

gi = KuzuEntityGraphIntegrator()
gi.setup()
conn = gi.conn

from src.policy.engine import PolicyEngine
from src.api.auth_routes import policy_engine

def gen_id(etype_prefix, case, val):
    digest = hashlib.sha256(f"{case}:{etype_prefix}:{val.strip().lower()}".encode()).hexdigest()[:6].upper()
    return f"CAN-{etype_prefix}-{digest}"

def upsert_node(label, nid, name):
    safe_name = name.replace("'", "''")
    try:
        conn.execute(f"MERGE (n:{label} {{id: '{nid}'}}) ON MATCH SET n.canonical_name = '{safe_name}'")
    except:
        try:
            conn.execute(f"INSERT INTO {label} VALUES ('{nid}', '{safe_name}', 1)")
        except:
            pass
    policy_engine.register_resource_case(nid, case_id)

def upsert_edge(rel_label, src_label, tgt_label, src_id, tgt_id, ev_id, conf=0.95):
    try:
        conn.execute(
            f"MATCH (a:{src_label} {{id: '{src_id}'}}), (b:{tgt_label} {{id: '{tgt_id}'}}) "
            f"CREATE (a)-[:{rel_label} {{evidence_id: '{ev_id}', confidence: {conf}}}]->(b)"
        )
    except Exception as e:
        pass  # already exists or schema mismatch

nodes_created = 0
edges_created = 0

# ── 1. CDR: CDR_Target_Vikramaditya_Sen.csv ──────────────────────────────────
cdr_file = "Test_Image3/CRIMENET_DEMO_CASE/Evidence/CDR/CDR_Target_Vikramaditya_Sen.csv"
if not os.path.exists(cdr_file):
    cdr_file = "CRIMENET_DEMO_CASE/Evidence/CDR/CDR_Target_Vikramaditya_Sen.csv"

print("Checking CDR file:", cdr_file, "->", os.path.exists(cdr_file))

# The E01 has it at Test 2/ — extract from DB artifacts instead
import sqlite3
db = sqlite3.connect("DATA/cases.db")
cdr_arts = db.execute(
    "SELECT artifact_id, filename, content_reference FROM artifacts WHERE case_id=? AND category='CDR'",
    (case_id,)
).fetchall()
doc_arts = db.execute(
    "SELECT artifact_id, filename, content_reference FROM artifacts WHERE case_id=? AND category='SPREADSHEET'",
    (case_id,)
).fetchall()
db.close()

print(f"CDR artifacts: {len(cdr_arts)}")
for a in cdr_arts:
    print(f"  {a[1]}: {a[2]}")

# Build from the actual extracted artifacts in processing_output
import json
# Use the TEST_RUN contract to find path
with open("DATA/processing_output/TEST_RUN/evidence_contract_JOB-TEST.json", "r") as f:
    contract = json.load(f)

# Build a path map from artifact filename to extracted file path
art_dir = "DATA/processing_output/TEST_RUN/extracted_artifacts"
extracted = {}
for fname in os.listdir(art_dir):
    extracted[fname] = os.path.join(art_dir, fname)

# Map contract artifact content_path -> local path
content_map = {}
for art in contract.get("observed_artifacts", []):
    fn = os.path.basename(art["content_path"])
    local = os.path.join(art_dir, fn)
    if os.path.exists(local):
        content_map[art["artifact_name"]] = local

print("\nExtracted files available:", list(content_map.keys())[:10])

# ── Process CDR files for CALLED relationships ─────────────────────────────
def parse_cdr(filepath, art_name):
    global nodes_created, edges_created
    try:
        with open(filepath, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return
        cols = [c.lower().strip() for c in rows[0].keys()]
        print(f"  CDR {art_name} cols: {cols}")
        for row in rows:
            low = {k.lower().strip(): v for k, v in row.items()}
            caller = low.get("caller_number") or low.get("a_number") or low.get("from_number") or low.get("caller")
            callee = low.get("called_number") or low.get("b_number") or low.get("to_number") or low.get("receiver")
            if caller and callee and caller.strip() and callee.strip():
                caller = caller.strip().replace(" ", "").replace("-", "")
                callee = callee.strip().replace(" ", "").replace("-", "")
                src_id = gen_id("PHO", case_id, caller)
                tgt_id = gen_id("PHO", case_id, callee)
                upsert_node("PhoneNumber", src_id, caller)
                upsert_node("PhoneNumber", tgt_id, callee)
                nodes_created += 2
                upsert_edge("CALLED", "PhoneNumber", "PhoneNumber", src_id, tgt_id, evidence_id, 0.95)
                edges_created += 1
    except Exception as e:
        print(f"  ERROR: {e}")

for art_name, local_path in content_map.items():
    if "cdr" in art_name.lower() or "cdr" in local_path.lower():
        print(f"\nParsing CDR: {art_name}")
        parse_cdr(local_path, art_name)

# ── Process Financial files for TRANSFERRED_TO relationships ──────────────
def parse_financial(filepath, art_name):
    global nodes_created, edges_created
    try:
        with open(filepath, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return
        cols = [c.lower().strip() for c in rows[0].keys()]
        print(f"  Financial {art_name} cols: {cols}")
        for row in rows:
            low = {k.lower().strip(): v for k, v in row.items()}
            src_acc = (low.get("sender_account") or low.get("from_account") or low.get("debit_account") or low.get("account_no") or "").strip()
            tgt_acc = (low.get("receiver_account") or low.get("to_account") or low.get("credit_account") or low.get("beneficiary_account") or "").strip()
            if src_acc and tgt_acc and src_acc != tgt_acc:
                src_id = gen_id("BAN", case_id, src_acc)
                tgt_id = gen_id("BAN", case_id, tgt_acc)
                upsert_node("BankAccount", src_id, src_acc)
                upsert_node("BankAccount", tgt_id, tgt_acc)
                nodes_created += 2
                upsert_edge("TRANSFERRED_TO", "BankAccount", "BankAccount", src_id, tgt_id, evidence_id, 0.90)
                edges_created += 1
    except Exception as e:
        print(f"  ERROR: {e}")

for art_name, local_path in content_map.items():
    if any(k in art_name.lower() for k in ["bank", "financial", "upi", "icici", "hdfc", "sbi", "hawala", "ledger"]):
        print(f"\nParsing Financial: {art_name}")
        parse_financial(local_path, art_name)

# ── Final summary ────────────────────────────────────────────────────────
print(f"\n✅ Nodes upserted: {nodes_created}")
print(f"✅ Edges created: {edges_created}")

# Verify
from collections import Counter
type_counts = Counter()
for lbl in ["Person", "PhoneNumber", "Email", "BankAccount", "Organization", "Location", "Vehicle"]:
    try:
        res = conn.execute(f"MATCH (n:{lbl}) RETURN count(n)")
        cnt = res.get_next()[0]
        if cnt > 0:
            type_counts[lbl] = cnt
    except:
        pass

edge_counts = Counter()
for rel, s, t in [
    ("CALLED", "PhoneNumber", "PhoneNumber"),
    ("TRANSFERRED_TO", "BankAccount", "BankAccount"),
    ("USED_PHONE", "Person", "PhoneNumber"),
    ("ASSOCIATED_WITH", "Person", "Person"),
]:
    try:
        res = conn.execute(f"MATCH (a:{s})-[r:{rel}]->(b:{t}) RETURN count(r)")
        cnt = res.get_next()[0]
        if cnt > 0:
            edge_counts[f"{s}-{rel}->{t}"] = cnt
    except:
        pass

print("\n=== KÙZU GRAPH SUMMARY ===")
print("Nodes:", dict(type_counts))
print("Edges:", dict(edge_counts))
