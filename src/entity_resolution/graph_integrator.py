"""
Graph Integrator for Resolved Canonical Entities
Ingests resolved Canonical Entities and Evidence-Backed Relationships into Kùzu Graph database.
"""

import os
import shutil
from typing import List, Dict, Any
import kuzu

class KuzuEntityGraphIntegrator:
    def __init__(self, db_path: str = "BENCHMARKS/kuzu_resolved_graph_db"):
        self.db_path = db_path
        self.db = None
        self.conn = None

    def setup(self):
        self.teardown()
        if os.path.exists(self.db_path):
            shutil.rmtree(self.db_path, ignore_errors=True)
            
        self.db = kuzu.Database(self.db_path)
        self.conn = kuzu.Connection(self.db)
        
        # Node Schemas
        for label in ["Person", "PhoneNumber", "Vehicle", "Location", "Organization"]:
            try:
                self.conn.execute(f"CREATE NODE TABLE {label}(id STRING, canonical_name STRING, observed_count INT64, PRIMARY KEY (id))")
            except Exception:
                pass
            
        # Rel Schemas
        valid_rels = [
            ("CALLED", "PhoneNumber", "PhoneNumber"),
            ("USED_PHONE", "Person", "PhoneNumber"),
            ("USED_VEHICLE", "Person", "Vehicle"),
            ("VISITED", "Person", "Location"),
            ("ASSOCIATED_WITH", "Person", "Person")
        ]
        for rel_label, src, tgt in valid_rels:
            try:
                self.conn.execute(f"CREATE REL TABLE {rel_label}(FROM {src} TO {tgt}, evidence_id STRING, confidence DOUBLE)")
            except Exception:
                pass

    def ingest_canonical_entities(self, canonical_clusters: List[Dict[str, Any]]) -> int:
        count = 0
        for cluster in canonical_clusters:
            cid = cluster["canonical_entity_id"]
            etype = cluster["entity_type"]
            cname = cluster["canonical_name"].replace("'", "''")
            obs_cnt = cluster["supporting_observations_count"]
            
            # Label mapping
            label = etype
            if etype.upper() in ["PHONE", "PHONENUMBER"]:
                label = "PhoneNumber"
            elif etype.upper() in ["PERSON"]:
                label = "Person"
            elif etype.upper() in ["VEHICLE"]:
                label = "Vehicle"
            elif etype.upper() in ["LOCATION"]:
                label = "Location"
            elif etype.upper() in ["ORGANIZATION", "ORG"]:
                label = "Organization"
                
            try:
                self.conn.execute(
                    f"CREATE (n:{label} {{id: '{cid}', canonical_name: '{cname}', observed_count: {obs_cnt}}})"
                )
                count += 1
            except Exception:
                pass
        return count

    def ingest_resolved_relationships(self, relationships: List[Dict[str, Any]]) -> int:
        count = 0
        for rel in relationships:
            src_id = rel["src_id"]
            tgt_id = rel["tgt_id"]
            src_label = rel["src_label"]
            tgt_label = rel["tgt_label"]
            rel_label = rel["rel_label"]
            evidence_id = rel["evidence_id"]
            conf = rel.get("confidence", 1.0)
            
            try:
                self.conn.execute(
                    f"MATCH (a:{src_label} {{id: '{src_id}'}}), (b:{tgt_label} {{id: '{tgt_id}'}}) "
                    f"CREATE (a)-[r:{rel_label} {{evidence_id: '{evidence_id}', confidence: {conf}}}]->(b)"
                )
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
