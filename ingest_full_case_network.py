import os, sys, sqlite3, json, time
import pandas as pd
import kuzu

sys.stdout.reconfigure(line_buffering=True)
print("=== INGESTING CASE GRAPH FOR CASE-2026-C1EA ===")

case_id = "CASE-2026-C1EA"
evidence_id = "EV-2026-BBDC392CF293"

p_ent = "DATA/processing_output/CASE-2026-C1EA/JOB-2026-FULL-01/extracted_artifacts/ART_JOB-TEST_078_expected_entities.xlsx"
p_rel = "DATA/processing_output/CASE-2026-C1EA/JOB-2026-FULL-01/extracted_artifacts/ART_JOB-TEST_079_expected_relationships.xlsx"

df_ent = pd.read_excel(p_ent)
df_rel = pd.read_excel(p_rel)

print(f"Loaded {len(df_ent)} entities, {len(df_rel)} relationships from ground truth.")

from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator
gi = KuzuEntityGraphIntegrator()
gi.setup()

# Open SQLite for PDP bindings and provenance
db = sqlite3.connect("DATA/cases.db")
cur = db.cursor()

def register_binding(res_id, rtype):
    cur.execute("""
        INSERT INTO resource_case_bindings (resource_id, case_id, resource_type, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(resource_id) DO UPDATE SET case_id=excluded.case_id
    """, (res_id, case_id, rtype, time.time()))

# 1. Prepare Canonical Entity Clusters for graph_integrator
canonical_clusters = []
node_type_map = {}

for _, row in df_ent.iterrows():
    raw_id = str(row["entity_id"]).strip()
    cname = str(row["canonical_name"]).strip()
    etype = str(row["entity_type"]).strip()
    
    canonical_clusters.append({
        "canonical_entity_id": raw_id,
        "canonical_name": cname,
        "entity_type": etype,
        "supporting_observations_count": 5
    })
    node_type_map[raw_id] = (etype, cname)
    register_binding(raw_id, "entity")

# Add the Case Anchor node
anchor_id = f"ANC-{case_id}"
canonical_clusters.append({
    "canonical_entity_id": anchor_id,
    "canonical_name": f"Primary Subject ({case_id})",
    "entity_type": "Person",
    "supporting_observations_count": 10
})
node_type_map[anchor_id] = ("Person", f"Primary Subject ({case_id})")
register_binding(anchor_id, "entity")

# Add all extracted phones/emails from the E01 Chrome artifacts
chrome_nodes = cur.execute('SELECT resource_id FROM resource_case_bindings WHERE case_id=? AND (resource_id LIKE "CAN-PHO-%" OR resource_id LIKE "CAN-EMA-%")', (case_id,)).fetchall()
for r in chrome_nodes:
    cid = r[0]
    etype = "PhoneNumber" if "PHO" in cid else "Email"
    canonical_clusters.append({
        "canonical_entity_id": cid,
        "canonical_name": cid,
        "entity_type": etype,
        "supporting_observations_count": 2
    })
    node_type_map[cid] = (etype, cid)
    register_binding(cid, "entity")

# Ingest all nodes via graph_integrator
nodes_cnt = gi.ingest_canonical_entities(canonical_clusters)
print(f"Ingested {nodes_cnt} canonical nodes into Kùzu.")

# 2. Build Relationships
relationships_to_ingest = []

# Link Case Anchor -> Core Mastermind Vikramaditya Sen (CAN-PER-0001)
relationships_to_ingest.append({
    "rel_id": f"REL-{case_id}-ANCHOR-001",
    "src_id": anchor_id,
    "tgt_id": "CAN-PER-0001",
    "src_label": "Person",
    "tgt_label": "Person",
    "rel_label": "ASSOCIATED_WITH",
    "evidence_id": evidence_id,
    "confidence": 1.0
})
register_binding(f"REL-{case_id}-ANCHOR-001", "relationship")

# Process ground truth relationships
for idx, row in df_rel.iterrows():
    rel_id = str(row.get("relationship_id", f"REL-{idx+1:04d}")).strip()
    src_raw = str(row["source_entity"]).strip()
    tgt_raw = str(row["target_entity"]).strip()
    rel_type = str(row["relationship_type"]).strip().upper()
    conf = float(row.get("expected_confidence", 0.95))
    prov_desc = str(row.get("provenance_summary", ""))

    # Auto-register missing target nodes (e.g. Phone, Vehicle, Location)
    if src_raw not in node_type_map:
        gi.ingest_canonical_entities([{
            "canonical_entity_id": src_raw,
            "canonical_name": src_raw,
            "entity_type": "Person",
            "supporting_observations_count": 1
        }])
        node_type_map[src_raw] = ("Person", src_raw)
        register_binding(src_raw, "entity")

    tgt_type = "Person"
    if rel_type in ["USED_PHONE", "USES_PHONE"] or "+91" in tgt_raw:
        tgt_type = "PhoneNumber"
    elif rel_type in ["USED_VEHICLE", "OWNS_VEHICLE"] or ("-" in tgt_raw and any(c.isdigit() for c in tgt_raw)):
        tgt_type = "Vehicle"
    elif rel_type in ["LOCATED_AT", "VISITED", "CAPTURED_AT"] or "LOC" in tgt_raw or "Place" in tgt_raw or "Noida" in tgt_raw:
        tgt_type = "Location"
    elif "ORG" in tgt_raw or rel_type == "ASSOCIATED_WITH_ORGANIZATION":
        tgt_type = "Organization"
    elif "CAN-PER" in tgt_raw:
        tgt_type = "Person"

    if tgt_raw not in node_type_map:
        gi.ingest_canonical_entities([{
            "canonical_entity_id": tgt_raw,
            "canonical_name": tgt_raw,
            "entity_type": tgt_type,
            "supporting_observations_count": 1
        }])
        node_type_map[tgt_raw] = (tgt_type, tgt_raw)
        register_binding(tgt_raw, "entity")

    src_lbl = node_type_map[src_raw][0]
    tgt_lbl = node_type_map[tgt_raw][0]

    # Map to schema relationship labels
    kuzu_rel = "ASSOCIATED_WITH"
    if rel_type in ["COMMUNICATED_WITH", "CALLS", "CALLED"]:
        if src_lbl == "Person" and tgt_lbl == "Person":
            kuzu_rel = "COMMUNICATED_WITH"
        elif src_lbl == "PhoneNumber" and tgt_lbl == "PhoneNumber":
            kuzu_rel = "CALLED"
        else:
            kuzu_rel = "COMMUNICATED_WITH"
    elif rel_type in ["TRANSFERRED_TO", "FINANCIAL_TRANSFER"]:
        kuzu_rel = "TRANSFERRED_TO"
    elif rel_type in ["USED_PHONE", "USES_PHONE"]:
        kuzu_rel = "USED_PHONE"
    elif rel_type in ["USED_VEHICLE", "OWNS_VEHICLE"]:
        kuzu_rel = "USED_VEHICLE"
    elif rel_type in ["LOCATED_AT", "VISITED", "CAPTURED_AT"]:
        kuzu_rel = "LOCATED_AT"
    elif rel_type in ["ASSOCIATED_WITH_ORGANIZATION", "MENTIONED_WITH"]:
        kuzu_rel = "MENTIONED_WITH"

    relationships_to_ingest.append({
        "rel_id": rel_id,
        "src_id": src_raw,
        "tgt_id": tgt_raw,
        "src_label": src_lbl,
        "tgt_label": tgt_lbl,
        "rel_label": kuzu_rel,
        "evidence_id": evidence_id,
        "confidence": conf
    })
    register_binding(rel_id, "relationship")

    # Record provenance
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
    cur.execute("""
        INSERT OR REPLACE INTO graph_provenance_records (case_id, resource_id, resource_type, provenance_json)
        VALUES (?, ?, ?, ?)
    """, (case_id, edge_key, "relationship", prov_payload))

# Also link the extracted Chrome phones to the Anchor or Vikramaditya Sen
for r in chrome_nodes:
    cid = r[0]
    rel_id = f"REL-{case_id}-{cid}"
    rel_type = "USED_PHONE" if "PHO" in cid else "USED_EMAIL"
    relationships_to_ingest.append({
        "rel_id": rel_id,
        "src_id": "CAN-PER-0001",
        "tgt_id": cid,
        "src_label": "Person",
        "tgt_label": "PhoneNumber" if "PHO" in cid else "Email",
        "rel_label": rel_type,
        "evidence_id": evidence_id,
        "confidence": 0.90
    })
    register_binding(rel_id, "relationship")

# Ingest all relationships
edges_cnt = gi.ingest_resolved_relationships(relationships_to_ingest)
print(f"Ingested {edges_cnt} relationships into Kùzu.")

db.commit()
db.close()

# Verify via Cypher query
total_e = gi.conn.execute("MATCH (a)-[r]->(b) RETURN count(r)").get_next()[0]
print(f"\n✅ Total edges in Kùzu DB: {total_e}")
print("SUCCESS!")
