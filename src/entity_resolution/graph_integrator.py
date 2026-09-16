"""
Graph Integrator for Resolved Canonical Entities & Evidence-Backed Relationships (Slice 5 & Slice 8B).
Idempotently ingests resolved Canonical Entities and Evidence-Backed Relationships into Kùzu Graph database.
Supports process-safe concurrency and fallback when database file lock is held by another process.
"""

import os
import shutil
from typing import List, Dict, Any, Optional
import kuzu


class KuzuEntityGraphIntegrator:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("KUZU_DB_PATH", "BENCHMARKS/kuzu_slice5_graph_db")
        self.db = None
        self.conn = None

    def setup(self):
        if not self.db:
            try:
                from pathlib import Path
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
                self.db = kuzu.Database(self.db_path)
                self.conn = kuzu.Connection(self.db)
            except RuntimeError as e:
                if "Could not set lock" in str(e) or "lock" in str(e).lower():
                    from pathlib import Path
                    fallback_path = f"{self.db_path}_proc_{os.getpid()}"
                    Path(fallback_path).parent.mkdir(parents=True, exist_ok=True)
                    self.db = kuzu.Database(fallback_path)
                    self.conn = kuzu.Connection(self.db)
                else:
                    raise

        # Node Table Schemas
        node_labels = ["Person", "PhoneNumber", "Email", "Vehicle", "Location", "Organization", "BankAccount"]
        for label in node_labels:
            try:
                self.conn.execute(f"CREATE NODE TABLE {label}(id STRING, canonical_name STRING, observed_count INT64, PRIMARY KEY (id))")
            except Exception:
                pass

        # Relationship Table Schemas
        valid_rels = [
            ("CALLED", "PhoneNumber", "PhoneNumber"),
            ("USED_PHONE", "Person", "PhoneNumber"),
            ("USED_EMAIL", "Person", "Email"),
            ("USED_VEHICLE", "Person", "Vehicle"),
            ("VISITED", "Person", "Location"),
            ("LOCATED_AT", "Person", "Location"),
            ("CAPTURED_AT", "Person", "Location"),
            ("ASSOCIATED_WITH", "Person", "Person"),
            ("TRANSFERRED_TO", "Person", "Person"),
            ("TRANSFERRED_TO", "BankAccount", "BankAccount"),
            ("MENTIONED_WITH", "Person", "Organization"),
        ]
        for rel_label, src, tgt in valid_rels:
            try:
                self.conn.execute(f"CREATE REL TABLE {rel_label}(FROM {src} TO {tgt}, evidence_id STRING, confidence DOUBLE)")
            except Exception:
                pass

        # Multi-type relationship groups
        rel_group_defs = [
            ("COMMUNICATED_WITH", [("Email", "Email"), ("Person", "Person")]),
        ]
        for group_label, pairs in rel_group_defs:
            try:
                pairs_str = ", ".join([f"FROM {s} TO {t}" for s, t in pairs])
                self.conn.execute(f"CREATE REL TABLE GROUP {group_label}({pairs_str}, evidence_id STRING, confidence DOUBLE)")
            except Exception:
                for s, t in pairs:
                    try:
                        self.conn.execute(f"CREATE REL TABLE {group_label}(FROM {s} TO {t}, evidence_id STRING, confidence DOUBLE)")
                    except Exception:
                        pass

    def ingest_canonical_entities(self, canonical_clusters: List[Dict[str, Any]]) -> int:
        """
        Idempotently inserts or updates canonical entity nodes.
        """
        count = 0
        for cluster in canonical_clusters:
            cid = cluster["canonical_entity_id"]
            etype = cluster.get("entity_type", "Person")
            cname = cluster.get("canonical_name", "").replace("'", "''")
            obs_cnt = cluster.get("supporting_observations_count", 1)

            # Map to schema label
            etype_up = etype.upper()
            if etype_up in ["PHONE", "PHONENUMBER"]:
                label = "PhoneNumber"
            elif etype_up in ["EMAIL", "EMAILADDRESS"]:
                label = "Email"
            elif etype_up in ["PERSON", "PERSONNAME"]:
                label = "Person"
            elif etype_up in ["VEHICLE", "VEHICLEPLATE"]:
                label = "Vehicle"
            elif etype_up in ["LOCATION", "ADDRESS"]:
                label = "Location"
            elif etype_up in ["ORGANIZATION", "ORG"]:
                label = "Organization"
            elif etype_up in ["BANKACCOUNT", "ACCOUNT", "FINANCIAL"]:
                label = "BankAccount"
            else:
                label = "Person"

            try:
                # Check existence for idempotency
                check_res = self.conn.execute(f"MATCH (n:{label} {{id: '{cid}'}}) RETURN n.id")
                if check_res.has_next():
                    # Node already exists, update observed_count
                    self.conn.execute(f"MATCH (n:{label} {{id: '{cid}'}}) SET n.observed_count = n.observed_count + {obs_cnt}")
                else:
                    self.conn.execute(
                        f"CREATE (n:{label} {{id: '{cid}', canonical_name: '{cname}', observed_count: {obs_cnt}}})"
                    )
                count += 1
            except Exception:
                pass
        return count

    def ingest_resolved_relationships(self, relationships: List[Dict[str, Any]]) -> int:
        """
        Idempotently inserts resolved evidence-backed relationships.
        """
        count = 0
        seen_in_batch = set()
        existing_edges = set()
        try:
            res_exist = self.conn.execute("MATCH (a)-[r]->(b) RETURN a.id, label(r), b.id, r.evidence_id")
            while res_exist.has_next():
                row = res_exist.get_next()
                existing_edges.add((row[0], row[1], row[2], str(row[3])))
        except Exception:
            pass

        for rel in relationships:
            src_id = rel["src_id"]
            tgt_id = rel["tgt_id"]
            src_label = rel.get("src_label", "Person")
            tgt_label = rel.get("tgt_label", "Person")
            rel_label = rel.get("rel_label", "ASSOCIATED_WITH")
            evidence_id = rel.get("evidence_id", "EV-UNKNOWN")
            conf = rel.get("confidence", 1.0)

            # Normalize labels to match Node Table Schemas
            label_map = {
                "PHONE": "PhoneNumber",
                "PHONENUMBER": "PhoneNumber",
                "EMAIL": "Email",
                "PERSON": "Person",
                "VEHICLE": "Vehicle",
                "LOCATION": "Location",
                "ORGANIZATION": "Organization",
                "BANKACCOUNT": "BankAccount",
            }
            src_clean = label_map.get(src_label.upper(), src_label)
            tgt_clean = label_map.get(tgt_label.upper(), tgt_label)

            edge_key = (src_clean, src_id, rel_label, tgt_clean, tgt_id, evidence_id)
            if edge_key in seen_in_batch:
                count += 1
                continue
            seen_in_batch.add(edge_key)

            if (src_id, rel_label, tgt_id, str(evidence_id)) in existing_edges:
                count += 1
                continue

            try:
                self.conn.execute(
                    f"MATCH (a:{src_clean} {{id: '{src_id}'}}), (b:{tgt_clean} {{id: '{tgt_id}'}}) "
                    f"CREATE (a)-[r:{rel_label} {{evidence_id: '{evidence_id}', confidence: {conf}}}]->(b)"
                )
                existing_edges.add((src_id, rel_label, tgt_id, str(evidence_id)))
                count += 1
            except Exception:
                pass
        return count

    def teardown(self):
        if self.conn:
            del self.conn
            self.conn = None
        if self.db:
            del self.db
            self.db = None
