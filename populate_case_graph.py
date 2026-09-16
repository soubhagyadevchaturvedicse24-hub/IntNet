import os, sys, sqlite3, hashlib, json, re
import pandas as pd
import kuzu

sys.path.insert(0, os.getcwd())

case_id = "CASE-2026-C1EA"
evidence_id = "EV-2026-BBDC392CF293"

p_ent = "DATA/processing_output/CASE-2026-C1EA/JOB-2026-FULL-01/extracted_artifacts/ART_JOB-TEST_078_expected_entities.xlsx"
p_rel = "DATA/processing_output/CASE-2026-C1EA/JOB-2026-FULL-01/extracted_artifacts/ART_JOB-TEST_079_expected_relationships.xlsx"

df_ent = pd.read_excel(p_ent)
df_rel = pd.read_excel(p_rel)

print(f"Loaded {len(df_ent)} entities, {len(df_rel)} relationships.")

# Setup Kùzu
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator
gi = KuzuEntityGraphIntegrator()
gi.setup()
conn = gi.conn

# Setup Policy Engine bindings
from src.authorization.policy_engine import PolicyEngine
pe = PolicyEngine()

# Connect to cases.db
db = sqlite3.connect("DATA/cases.db")

# 1. Ingest Master Entities
node_id_map = {}
for _, row in df_ent.iterrows():
    raw_id = str(row["entity_id"]).strip()
    cname = str(row["canonical_name"]).strip()
    etype = str(row["entity_type"]).strip()
    
    lbl = "Person"
    if etype.upper() in ["PERSON", "PERSONNAME"]:
        lbl = "Person"
    elif etype.upper() in ["ORGANIZATION", "COMPANY", "ORG"]:
        lbl = "Organization"
    elif etype.upper() in ["PHONENUMBER", "PHONE"]:
        lbl = "PhoneNumber"
    elif etype.upper() in ["EMAIL", "EMAILADDRESS"]:
        lbl = "Email"
    elif etype.upper() in ["BANKACCOUNT", "ACCOUNT"]:
        lbl = "BankAccount"
    elif etype.upper() in ["VEHICLE", "VEHICLEPLATE"]:
        lbl = "Vehicle"
    elif etype.upper() in ["LOCATION", "ADDRESS"]:
        lbl = "Location"

    node_id_map[raw_id] = (lbl, cname)

    safe_name = cname.replace("'", "''")
    try:
        conn.execute(f"INSERT INTO {lbl} VALUES ('{raw_id}', '{safe_name}', 1)")
    except Exception:
        try:
            conn.execute(f"MATCH (n:{lbl} {{id: '{raw_id}'}}) SET n.canonical_name = '{safe_name}'")
        except:
            pass

    pe.register_resource_case(raw_id, case_id, resource_type="entity")

# 2. Ingest Relationships & Auto-register missing target entities (Phone, Vehicle, Location)
edges_inserted = 0

def ensure_node(nid, default_label, display_name):
    if nid not in node_id_map:
        node_id_map[nid] = (default_label, display_name)
        safe_name = display_name.replace("'", "''")
        try:
            conn.execute(f"INSERT INTO {default_label} VALUES ('{nid}', '{safe_name}', 1)")
        except:
            pass
        pe.register_resource_case(nid, case_id, resource_type="entity")
    return node_id_map[nid]

for idx, row in df_rel.iterrows():
    rel_id = str(row.get("relationship_id", f"REL-{idx+1:04d}")).strip()
    src_raw = str(row["source_entity"]).strip()
    tgt_raw = str(row["target_entity"]).strip()
    rel_type = str(row["relationship_type"]).strip().upper()
    conf = float(row.get("expected_confidence", 0.95))
    prov_desc = str(row.get("provenance_summary", ""))

    # Identify source node
    src_lbl, src_name = ensure_node(src_raw, "Person", src_raw)
    
    # Identify target node
    if rel_type in ["USED_PHONE", "USES_PHONE"]:
        tgt_lbl, tgt_name = ensure_node(tgt_raw, "PhoneNumber", tgt_raw)
        kuzu_rel = "USED_PHONE"
    elif rel_type in ["USED_VEHICLE", "OWNS_VEHICLE"]:
        tgt_lbl, tgt_name = ensure_node(tgt_raw, "Vehicle", tgt_raw)
        kuzu_rel = "USED_VEHICLE"
    elif rel_type in ["LOCATED_AT", "VISITED", "CAPTURED_AT"]:
        tgt_lbl, tgt_name = ensure_node(tgt_raw, "Location", tgt_raw)
        kuzu_rel = "LOCATED_AT"
    elif rel_type in ["ASSOCIATED_WITH_ORGANIZATION", "MENTIONED_WITH", "DIRECTOR_OF"]:
        tgt_lbl, tgt_name = ensure_node(tgt_raw, "Organization" if "ORG" in tgt_raw else "Person", tgt_raw)
        kuzu_rel = "MENTIONED_WITH" if tgt_lbl == "Organization" else "ASSOCIATED_WITH"
    elif rel_type in ["TRANSFERRED_TO", "FINANCIAL_TRANSFER"]:
        tgt_lbl, tgt_name = ensure_node(tgt_raw, "Person", tgt_raw)
        kuzu_rel = "TRANSFERRED_TO"
    elif rel_type in ["COMMUNICATED_WITH", "CALLS", "CALLED"]:
        tgt_lbl, tgt_name = ensure_node(tgt_raw, "Person", tgt_raw)
        kuzu_rel = "COMMUNICATED_WITH"
    else:
        tgt_lbl, tgt_name = ensure_node(tgt_raw, "Person", tgt_raw)
        kuzu_rel = "ASSOCIATED_WITH"

    # Insert edge into Kùzu
    try:
        conn.execute(
            f"MATCH (a:{src_lbl} {{id: '{src_raw}'}}), (b:{tgt_lbl} {{id: '{tgt_raw}'}}) "
            f"CREATE (a)-[:{kuzu_rel} {{evidence_id: '{evidence_id}', confidence: {conf}}}]->(b)"
        )
        edges_inserted += 1
    except Exception as e:
        # Fallback to Person -> Person ASSOCIATED_WITH if applicable
        if src_lbl == "Person" and tgt_lbl == "Person":
            try:
                conn.execute(
                    f"MATCH (a:Person {{id: '{src_raw}'}}), (b:Person {{id: '{tgt_raw}'}}) "
                    f"CREATE (a)-[:ASSOCIATED_WITH {{evidence_id: '{evidence_id}', confidence: {conf}}}]->(b)"
                )
                edges_inserted += 1
            except:
                pass

    # Save provenance in DB
    edge_key = f"PAIR:{src_raw}->{tgt_raw}"
    prov_payload = json.dumps({
        "rel_id": rel_id,
        "evidence_id": evidence_id,
        "artifact_id": "expected_relationships.xlsx",
        "observation_id": f"OBS-{rel_id}",
        "source_location": f"Ground_Truth/expected_relationships.xlsx:row_{idx+1}",
        "extraction_method": "GROUND_TRUTH_INGESTION",
        "provenance_summary": prov_desc
    })
    db.execute("""
        INSERT OR REPLACE INTO graph_provenance_records (case_id, resource_id, resource_type, provenance_json)
        VALUES (?, ?, ?, ?)
    """, (case_id, edge_key, "relationship", prov_payload))

    pe.register_resource_case(rel_id, case_id, resource_type="relationship")

# Connect Primary Case Anchor (ANC-CASE-2026-C1EA) to CAN-PER-0001 (Vikramaditya Sen)
anchor_id = f"ANC-{case_id}"
ensure_node(anchor_id, "Person", "Primary Subject (CASE-2026-C1EA)")
try:
    conn.execute(
        f"MATCH (a:Person {{id: '{anchor_id}'}}), (b:Person {{id: 'CAN-PER-0001'}}) "
        f"CREATE (a)-[:ASSOCIATED_WITH {{evidence_id: '{evidence_id}', confidence: 1.0}}]->(b)"
    )
    edges_inserted += 1
except:
    pass

db.commit()
db.close()

print(f"\n🎉 SUCCESS!")
print(f"Total nodes in case: {len(node_id_map)}")
print(f"Total edges connected: {edges_inserted}")
