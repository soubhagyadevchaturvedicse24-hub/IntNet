import sqlite3, kuzu
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator

gi = KuzuEntityGraphIntegrator()
gi.setup()
conn = gi.conn

case_id = 'CASE-2026-C1EA'
anchor_id = f'ANC-{case_id}'
ev_id = 'EV-2026-BBDC392CF293'

# 1. Ensure anchor is registered in Person and PDP
db = sqlite3.connect('DATA/cases.db')
cur = db.cursor()
cur.execute("""
    INSERT INTO resource_case_bindings (resource_id, case_id, resource_type, created_at)
    VALUES (?, ?, ?, 1788807794.0)
    ON CONFLICT(resource_id) DO UPDATE SET case_id=excluded.case_id
""", (anchor_id, case_id, "entity"))

try:
    conn.execute(f"INSERT INTO Person VALUES ('{anchor_id}', 'Primary Subject (CASE-2026-C1EA)', 1)")
except:
    pass

# 2. Get all phone & email nodes in CASE-2026-C1EA
nodes = cur.execute('SELECT resource_id FROM resource_case_bindings WHERE case_id=? AND (resource_id LIKE "CAN-PHO-%" OR resource_id LIKE "CAN-EMA-%")', (case_id,)).fetchall()
node_ids = [n[0] for n in nodes]
print(f'Linking {len(node_ids)} nodes to anchor {anchor_id}...')

edges_count = 0
for idx, nid in enumerate(node_ids, 1):
    edge_id = f"EDGE-{case_id}-{idx:04d}"
    if 'PHO' in nid:
        try:
            conn.execute(f"MATCH (a:Person {{id: '{anchor_id}'}}), (b:PhoneNumber {{id: '{nid}'}}) CREATE (a)-[:USED_PHONE {{evidence_id: '{ev_id}', confidence: 0.95}}]->(b)")
            edges_count += 1
            cur.execute("""
                INSERT INTO resource_case_bindings (resource_id, case_id, resource_type, created_at)
                VALUES (?, ?, ?, 1788807794.0)
                ON CONFLICT(resource_id) DO UPDATE SET case_id=excluded.case_id
            """, (edge_id, case_id, "relationship"))
        except Exception as e:
            print(f"Error linking {nid}: {e}")
    elif 'EMA' in nid:
        try:
            conn.execute(f"MATCH (a:Person {{id: '{anchor_id}'}}), (b:Email {{id: '{nid}'}}) CREATE (a)-[:USED_EMAIL {{evidence_id: '{ev_id}', confidence: 0.95}}]->(b)")
            edges_count += 1
            cur.execute("""
                INSERT INTO resource_case_bindings (resource_id, case_id, resource_type, created_at)
                VALUES (?, ?, ?, 1788807794.0)
                ON CONFLICT(resource_id) DO UPDATE SET case_id=excluded.case_id
            """, (edge_id, case_id, "relationship"))
        except Exception as e:
            print(f"Error linking {nid}: {e}")

db.commit()
db.close()

print(f'Successfully created {edges_count} edges to anchor!')
