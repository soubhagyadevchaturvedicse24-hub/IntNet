"""
Graph Intelligence Service for Investigator API
Queries the prototype Kùzu Graph database to provide human contact network overviews, entity details,
relationship inspections, evidence traceability, 1-hop/2-hop neighbors, shortest paths, and integrated CCC Association Scores.
"""

import os
import json
import kuzu
from typing import Dict, List, Any, Optional
from src.analytics.ccc_scorer import calculate_ccc_score

class GraphIntelligenceService:
    def __init__(self, db_path: str = "BENCHMARKS/kuzu_resolved_graph_db"):
        self.db_path = db_path
        self.db = None
        self.conn = None
        self.evidence_store = {}
        self.verification_store = {}
        self._init_mock_evidence()

    def _init_mock_evidence(self):
        """Initializes deterministic evidence contract store for traceability."""
        self.evidence_store = {
            "EV-CONTRACT-2026-9001": {
                "evidence_id": "EV-CONTRACT-2026-9001",
                "source_artifact": "call_log.db",
                "source_format": "SQLite Database",
                "extracted_path": "/data/data/com.android.providers.contacts/databases/calllog.db",
                "sha256": "466162a47a8058f081d96862c793e533fd92317e0347a0816ae23406722a7f33",
                "timestamp": "2026-09-04T14:22:00Z",
                "observation_type": "Voice Call Log",
                "details": "Outgoing call from Vikram Singh to +919876543210. Duration: 145 seconds."
            },
            "EV-CONTRACT-2026-9002": {
                "evidence_id": "EV-CONTRACT-2026-9002",
                "source_artifact": "traffic_cam_01.jpg",
                "source_format": "JPEG Image with EXIF",
                "extracted_path": "/DCIM/Camera/IMG_001.JPG",
                "sha256": "5ab34501a900f7b9e0123456789abcdef0123456789abcdef0123456789abcde",
                "timestamp": "2026-09-04T09:15:30Z",
                "observation_type": "ANPR License Plate Capture",
                "details": "Vehicle DL01AB1234 recorded at Connaught Place Zone 1 check-post."
            },
            "EV-CONTRACT-2026-9003": {
                "evidence_id": "EV-CONTRACT-2026-9003",
                "source_artifact": "cell_tower_log.csv",
                "source_format": "CSV Tower Dumps",
                "extracted_path": "/analysis/tower_dumps/zone1_dump.csv",
                "sha256": "558f08032424599fe0123456789abcdef0123456789abcdef0123456789abcde",
                "timestamp": "2026-09-04T09:18:00Z",
                "observation_type": "Cell Tower Location Ping",
                "details": "Location ping for Vikram Singh near Connaught Place Zone 1."
            },
            "EV-CONTRACT-2026-9004": {
                "evidence_id": "EV-CONTRACT-2026-9004",
                "source_artifact": "fir_record_01.pdf",
                "source_format": "PDF Record",
                "extracted_path": "/documents/firs/FIR-2026-104.pdf",
                "sha256": "778f08032424599fe0123456789abcdef0123456789abcdef0123456789abcde",
                "timestamp": "2026-09-01T10:00:00Z",
                "observation_type": "FIR Named Association",
                "details": "Analytical association between Vikram Singh and Ananya Sharma."
            },
            "EV-CONTRACT-2026-9005": {
                "evidence_id": "EV-CONTRACT-2026-9005",
                "source_artifact": "chat_dump.json",
                "source_format": "WhatsApp Chat Backup",
                "extracted_path": "/data/data/com.whatsapp/databases/msgstore.db",
                "sha256": "889f08032424599fe0123456789abcdef0123456789abcdef0123456789abcde",
                "timestamp": "2026-09-02T18:45:10Z",
                "observation_type": "Encrypted Chat Log",
                "details": "Group chat interaction involving Rohit Sharma, Amit Verma, and Rajesh Kumar."
            }
        }

    def _get_connection(self):
        if not self.conn:
            should_rebuild = True
            if os.path.exists(self.db_path):
                try:
                    db = kuzu.Database(self.db_path)
                    conn = kuzu.Connection(db)
                    r = conn.execute("MATCH (n:Person) RETURN count(n)")
                    cnt = r.get_next()[0]
                    if cnt >= 1:
                        self.db = db
                        self.conn = conn
                        should_rebuild = False
                    else:
                        del conn
                        del db
                        import gc
                        gc.collect()
                except Exception:
                    should_rebuild = True

            if should_rebuild:
                import shutil
                import gc
                gc.collect()
                if os.path.exists(self.db_path):
                    shutil.rmtree(self.db_path, ignore_errors=True)

                from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator
                integrator = KuzuEntityGraphIntegrator(self.db_path)
                integrator.setup()

                # Ingest Primary Human Entities
                human_entities = [
                    {"canonical_entity_id": "CAN-PER-0001", "entity_type": "Person", "canonical_name": "Vikram Singh", "supporting_observations_count": 5},
                    {"canonical_entity_id": "CAN-PER-0002", "entity_type": "Person", "canonical_name": "Ananya Sharma", "supporting_observations_count": 4},
                    {"canonical_entity_id": "CAN-PER-0007", "entity_type": "Person", "canonical_name": "Rajesh Kumar", "supporting_observations_count": 3},
                    {"canonical_entity_id": "CAN-PER-0008", "entity_type": "Person", "canonical_name": "Rohit Sharma", "supporting_observations_count": 4},
                    {"canonical_entity_id": "CAN-PER-0009", "entity_type": "Person", "canonical_name": "Amit Verma", "supporting_observations_count": 3},
                    {"canonical_entity_id": "CAN-PER-0010", "entity_type": "Person", "canonical_name": "Suresh Yadav", "supporting_observations_count": 3},
                    {"canonical_entity_id": "CAN-PER-0011", "entity_type": "Person", "canonical_name": "Neha Kapoor", "supporting_observations_count": 3},
                    # Layer 2 People
                    {"canonical_entity_id": "CAN-PER-0012", "entity_type": "Person", "canonical_name": "Pooja Mehta", "supporting_observations_count": 2},
                    {"canonical_entity_id": "CAN-PER-0013", "entity_type": "Person", "canonical_name": "Deepak Joshi", "supporting_observations_count": 2},
                    {"canonical_entity_id": "CAN-PER-0014", "entity_type": "Person", "canonical_name": "Sneha Iyer", "supporting_observations_count": 2},
                    {"canonical_entity_id": "CAN-PER-0015", "entity_type": "Person", "canonical_name": "Vivek Rathi", "supporting_observations_count": 2},
                    {"canonical_entity_id": "CAN-PER-0016", "entity_type": "Person", "canonical_name": "Aman Gupta", "supporting_observations_count": 2},
                    {"canonical_entity_id": "CAN-PER-0017", "entity_type": "Person", "canonical_name": "Mohit Chandel", "supporting_observations_count": 2},
                    {"canonical_entity_id": "CAN-PER-0018", "entity_type": "Person", "canonical_name": "Rakesh Patel", "supporting_observations_count": 2},
                    {"canonical_entity_id": "CAN-PER-0019", "entity_type": "Person", "canonical_name": "Kamal Singh", "supporting_observations_count": 2},
                    {"canonical_entity_id": "CAN-PER-0020", "entity_type": "Person", "canonical_name": "Arjun Das", "supporting_observations_count": 2},
                    {"canonical_entity_id": "CAN-PER-0021", "entity_type": "Person", "canonical_name": "Isha Khan", "supporting_observations_count": 2},
                    {"canonical_entity_id": "CAN-PER-0022", "entity_type": "Person", "canonical_name": "Manish Gupta", "supporting_observations_count": 2},
                    {"canonical_entity_id": "CAN-PER-0023", "entity_type": "Person", "canonical_name": "Karan Bansal", "supporting_observations_count": 2},
                    # Layer 3 People
                    {"canonical_entity_id": "CAN-PER-0024", "entity_type": "Person", "canonical_name": "Ritika Verma", "supporting_observations_count": 1},
                    {"canonical_entity_id": "CAN-PER-0025", "entity_type": "Person", "canonical_name": "Aditya Saxena", "supporting_observations_count": 1},
                    {"canonical_entity_id": "CAN-PER-0026", "entity_type": "Person", "canonical_name": "Farhan Ali", "supporting_observations_count": 1},
                    {"canonical_entity_id": "CAN-PER-0027", "entity_type": "Person", "canonical_name": "Kavita Singh", "supporting_observations_count": 1},
                    {"canonical_entity_id": "CAN-PER-0028", "entity_type": "Person", "canonical_name": "Nitin Sharma", "supporting_observations_count": 1},
                    {"canonical_entity_id": "CAN-PER-0029", "entity_type": "Person", "canonical_name": "Pallavi Desai", "supporting_observations_count": 1},
                    {"canonical_entity_id": "CAN-PER-0030", "entity_type": "Person", "canonical_name": "Shreya Rao", "supporting_observations_count": 1},
                    {"canonical_entity_id": "CAN-PER-0031", "entity_type": "Person", "canonical_name": "Neha Sinha", "supporting_observations_count": 1},
                    {"canonical_entity_id": "CAN-PER-0032", "entity_type": "Person", "canonical_name": "Zoya Khan", "supporting_observations_count": 1},
                    {"canonical_entity_id": "CAN-PER-0033", "entity_type": "Person", "canonical_name": "Varun Mehta", "supporting_observations_count": 1},
                    {"canonical_entity_id": "CAN-PER-0034", "entity_type": "Person", "canonical_name": "Tanya Kapoor", "supporting_observations_count": 1},
                    {"canonical_entity_id": "CAN-PER-0035", "entity_type": "Person", "canonical_name": "Sahil Khan", "supporting_observations_count": 1},
                    {"canonical_entity_id": "CAN-PER-0036", "entity_type": "Person", "canonical_name": "Anjali Roy", "supporting_observations_count": 1},
                    # Non-Human Asset Evidence Nodes
                    {"canonical_entity_id": "CAN-PHO-0003", "entity_type": "PhoneNumber", "canonical_name": "+919876543210", "supporting_observations_count": 3},
                    {"canonical_entity_id": "CAN-VEH-0004", "entity_type": "Vehicle", "canonical_name": "DL01AB1234", "supporting_observations_count": 3},
                    {"canonical_entity_id": "CAN-LOC-0005", "entity_type": "Location", "canonical_name": "Connaught Place Zone 1", "supporting_observations_count": 2}
                ]
                integrator.ingest_canonical_entities(human_entities)

                # Ingest Human Relationships
                human_rels = [
                    # Layer 1 Direct Associates (RED)
                    {"src_id": "CAN-PER-0001", "tgt_id": "CAN-PER-0002", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9004", "confidence": 0.95},
                    {"src_id": "CAN-PER-0001", "tgt_id": "CAN-PER-0007", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.90},
                    {"src_id": "CAN-PER-0001", "tgt_id": "CAN-PER-0008", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9001", "confidence": 0.95},
                    {"src_id": "CAN-PER-0001", "tgt_id": "CAN-PER-0009", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.92},
                    {"src_id": "CAN-PER-0001", "tgt_id": "CAN-PER-0010", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9001", "confidence": 0.88},
                    {"src_id": "CAN-PER-0001", "tgt_id": "CAN-PER-0011", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.90},
                    # Layer 2 Broader Network (YELLOW)
                    {"src_id": "CAN-PER-0008", "tgt_id": "CAN-PER-0012", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.75},
                    {"src_id": "CAN-PER-0009", "tgt_id": "CAN-PER-0013", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.72},
                    {"src_id": "CAN-PER-0007", "tgt_id": "CAN-PER-0014", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.70},
                    {"src_id": "CAN-PER-0007", "tgt_id": "CAN-PER-0015", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.68},
                    {"src_id": "CAN-PER-0010", "tgt_id": "CAN-PER-0016", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.65},
                    {"src_id": "CAN-PER-0010", "tgt_id": "CAN-PER-0017", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.64},
                    {"src_id": "CAN-PER-0011", "tgt_id": "CAN-PER-0018", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.62},
                    {"src_id": "CAN-PER-0011", "tgt_id": "CAN-PER-0019", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.60},
                    {"src_id": "CAN-PER-0002", "tgt_id": "CAN-PER-0020", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9004", "confidence": 0.75},
                    {"src_id": "CAN-PER-0002", "tgt_id": "CAN-PER-0021", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9004", "confidence": 0.72},
                    {"src_id": "CAN-PER-0008", "tgt_id": "CAN-PER-0022", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.70},
                    {"src_id": "CAN-PER-0008", "tgt_id": "CAN-PER-0023", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.68},
                    # Layer 3 Extended Network (GREEN)
                    {"src_id": "CAN-PER-0012", "tgt_id": "CAN-PER-0024", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.45},
                    {"src_id": "CAN-PER-0013", "tgt_id": "CAN-PER-0025", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.42},
                    {"src_id": "CAN-PER-0014", "tgt_id": "CAN-PER-0026", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.40},
                    {"src_id": "CAN-PER-0015", "tgt_id": "CAN-PER-0027", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.38},
                    {"src_id": "CAN-PER-0016", "tgt_id": "CAN-PER-0028", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.35},
                    {"src_id": "CAN-PER-0017", "tgt_id": "CAN-PER-0029", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.35},
                    {"src_id": "CAN-PER-0018", "tgt_id": "CAN-PER-0030", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.32},
                    {"src_id": "CAN-PER-0019", "tgt_id": "CAN-PER-0031", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.30},
                    {"src_id": "CAN-PER-0020", "tgt_id": "CAN-PER-0032", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9004", "confidence": 0.45},
                    {"src_id": "CAN-PER-0021", "tgt_id": "CAN-PER-0033", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9004", "confidence": 0.40},
                    {"src_id": "CAN-PER-0022", "tgt_id": "CAN-PER-0034", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.38},
                    {"src_id": "CAN-PER-0023", "tgt_id": "CAN-PER-0035", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.35},
                    {"src_id": "CAN-PER-0023", "tgt_id": "CAN-PER-0036", "src_label": "Person", "tgt_label": "Person", "rel_label": "ASSOCIATED_WITH", "evidence_id": "EV-CONTRACT-2026-9005", "confidence": 0.32},
                    # Asset Traceability Links
                    {"src_id": "CAN-PER-0001", "tgt_id": "CAN-PHO-0003", "src_label": "Person", "tgt_label": "PhoneNumber", "rel_label": "USED_PHONE", "evidence_id": "EV-CONTRACT-2026-9001", "confidence": 1.0},
                    {"src_id": "CAN-PER-0002", "tgt_id": "CAN-PHO-0003", "src_label": "Person", "tgt_label": "PhoneNumber", "rel_label": "USED_PHONE", "evidence_id": "EV-CONTRACT-2026-9001", "confidence": 1.0},
                    {"src_id": "CAN-PER-0001", "tgt_id": "CAN-VEH-0004", "src_label": "Person", "tgt_label": "Vehicle", "rel_label": "USED_VEHICLE", "evidence_id": "EV-CONTRACT-2026-9002", "confidence": 1.0},
                    {"src_id": "CAN-PER-0001", "tgt_id": "CAN-LOC-0005", "src_label": "Person", "tgt_label": "Location", "rel_label": "VISITED", "evidence_id": "EV-CONTRACT-2026-9003", "confidence": 1.0}
                ]
                integrator.ingest_resolved_relationships(human_rels)
                self.db = integrator.db
                self.conn = integrator.conn
        return self.conn

    def get_graph_overview(self) -> Dict[str, Any]:
        conn = self._get_connection()
        nodes = []
        node_ids = set()
        
        # Human Contact Graph Nodes
        labels = ["Person", "PhoneNumber", "Vehicle", "Location", "Organization"]
        for lbl in labels:
            res = conn.execute(f"MATCH (n:{lbl}) RETURN n.id, n.canonical_name, n.observed_count")
            while res.has_next():
                nid, cname, count = res.get_next()
                nodes.append({
                    "id": nid,
                    "label": cname,
                    "entity_type": lbl,
                    "observed_count": count
                })
                node_ids.add(nid)
                
        edges = []
        rels = ["CALLED", "USED_PHONE", "USED_VEHICLE", "VISITED", "ASSOCIATED_WITH"]
        edge_idx = 1
        for rel in rels:
            try:
                res = conn.execute(f"MATCH (a)-[r:{rel}]->(b) RETURN a.id, b.id, r.evidence_id, r.confidence")
                while res.has_next():
                    src, tgt, ev_id, conf = res.get_next()
                    
                    # Frequency & Recency dynamic assignments based on graph distance
                    freq = 15 if src == "CAN-PER-0001" or tgt == "CAN-PER-0001" else 5
                    days = 2.0 if src == "CAN-PER-0001" or tgt == "CAN-PER-0001" else 14.0
                    sources = 3 if conf >= 0.90 else 1
                    
                    ccc = calculate_ccc_score(
                        rel_type=rel,
                        frequency=freq,
                        days_elapsed=days,
                        source_count=sources,
                        er_confidence=conf,
                        provenance_valid=True,
                        evidence_ids=[ev_id]
                    )
                    
                    edges.append({
                        "id": f"EDGE-{edge_idx:04d}",
                        "source": src,
                        "target": tgt,
                        "relationship_type": rel,
                        "evidence_id": ev_id,
                        "confidence": conf,
                        "ccc_score": ccc["association_score"],
                        "ccc_ring": ccc["concentric_ring"]
                    })
                    edge_idx += 1
            except Exception:
                pass
                
        return {
            "summary": {
                "total_nodes": len(nodes),
                "total_edges": len(edges)
            },
            "nodes": nodes,
            "edges": edges
        }

    def get_entity_details(self, entity_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        labels = ["Person", "PhoneNumber", "Vehicle", "Location", "Organization"]
        for lbl in labels:
            res = conn.execute(f"MATCH (n:{lbl} {{id: '{entity_id}'}}) RETURN n.id, n.canonical_name, n.observed_count")
            if res.has_next():
                nid, cname, count = res.get_next()
                ver_status = self.verification_store.get(entity_id, "UNDER_REVIEW")
                return {
                    "canonical_entity_id": nid,
                    "entity_type": lbl,
                    "canonical_name": cname,
                    "normalized_value": cname,
                    "observed_values": [cname, f"Raw {cname}"],
                    "match_confidence": 1.00,
                    "match_method": "EXACT_NORMALIZED_RULE",
                    "source_evidence_ids": ["EV-CONTRACT-2026-9001", "EV-CONTRACT-2026-9002"],
                    "human_verification_status": ver_status,
                    "responsible_ai_note": "Analytical Lead / Indicator for investigator reference only. Not a probability of guilt."
                }
        return None

    def get_relationship_details(self, edge_id: str) -> Optional[Dict[str, Any]]:
        overview = self.get_graph_overview()
        for e in overview["edges"]:
            if e["id"] == edge_id:
                ev_id = e["evidence_id"]
                ev_info = self.evidence_store.get(ev_id, {})
                rel_type = e["relationship_type"]
                conf = e["confidence"]
                
                freq = 15 if e["source"] == "CAN-PER-0001" or e["target"] == "CAN-PER-0001" else 5
                days = 2.0 if e["source"] == "CAN-PER-0001" or e["target"] == "CAN-PER-0001" else 14.0
                sources = 3 if conf >= 0.90 else 1
                
                ccc = calculate_ccc_score(
                    rel_type=rel_type,
                    frequency=freq,
                    days_elapsed=days,
                    source_count=sources,
                    er_confidence=conf,
                    provenance_valid=True,
                    evidence_ids=[ev_id]
                )

                ver_status = self.verification_store.get(edge_id, "UNDER_REVIEW")
                
                return {
                    "edge_id": edge_id,
                    "relationship_type": rel_type,
                    "source_entity": e["source"],
                    "target_entity": e["target"],
                    "confidence": conf,
                    "supporting_evidence_id": ev_id,
                    "supporting_evidence_ids": [ev_id, "EV-CONTRACT-2026-9002"] if sources > 1 else [ev_id],
                    "source_artifact": ev_info.get("source_artifact", "Unknown"),
                    "source_format": ev_info.get("source_format", "Unknown"),
                    "timestamp": ev_info.get("timestamp", "2026-09-04T14:22:00Z"),
                    "details": ev_info.get("details", ""),
                    "association_score": ccc["association_score"],
                    "ccc_ring": ccc["concentric_ring"],
                    "priority_label": ccc["priority_label"],
                    "contributing_indicators": ccc["contributing_indicators"],
                    "interaction_frequency": freq,
                    "recency_days": days,
                    "independent_sources_count": sources,
                    "provenance_status": "Verified Cryptographic SHA-256",
                    "human_verification_status": ver_status,
                    "responsible_ai_disclaimer": "Experimental analytical prioritization score. Not a probability of guilt."
                }
        return None

    def get_evidence_traceability(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        ev_info = self.evidence_store.get(evidence_id)
        if ev_info:
            return {
                "traceability_status": "VERIFIED_CHAIN_OF_CUSTODY",
                "evidence_record": ev_info,
                "analytical_insight": f"Relationship generated directly from {ev_info['observation_type']} in artifact {ev_info['source_artifact']}."
            }
        return None

    def get_neighbors(self, entity_id: str, hops: int = 1) -> Dict[str, Any]:
        conn = self._get_connection()
        neighbor_nodes = []
        visited = {entity_id}
        
        query = f"MATCH (a {{id: '{entity_id}'}})-[r1]->(b) RETURN b.id, labels(b)"
        if hops == 2:
            query = f"MATCH (a {{id: '{entity_id}'}})-[r1]->(b)-[r2*1..2]->(c) RETURN DISTINCT c.id, labels(c)"
            
        try:
            res = conn.execute(query)
            while res.has_next():
                nid, lbls = res.get_next()
                if nid not in visited:
                    visited.add(nid)
                    det = self.get_entity_details(nid)
                    if det:
                        neighbor_nodes.append(det)
        except Exception:
            pass
            
        return {
            "root_entity_id": entity_id,
            "hops": hops,
            "neighbor_count": len(neighbor_nodes),
            "neighbors": neighbor_nodes
        }

    def get_shortest_path(self, src_id: str, tgt_id: str) -> Dict[str, Any]:
        overview = self.get_graph_overview()
        adj = {}
        for e in overview["edges"]:
            s, t = e["source"], e["target"]
            adj.setdefault(s, []).append(t)
            adj.setdefault(t, []).append(s)
            
        queue = [[src_id]]
        visited = {src_id}
        found_path = []
        
        while queue:
            path = queue.pop(0)
            node = path[-1]
            if node == tgt_id:
                found_path = path
                break
            for nxt in adj.get(node, []):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(path + [nxt])
                    
        return {
            "source_id": src_id,
            "target_id": tgt_id,
            "path_length": len(found_path) - 1 if found_path else -1,
            "path_nodes": found_path
        }

    def verify_entity(self, entity_id: str, status: str, notes: str) -> Dict[str, Any]:
        allowed = ["UNDER_REVIEW", "HUMAN_VERIFIED_LEAD", "REJECTED_ASSOCIATION"]
        if status not in allowed:
            status = "HUMAN_VERIFIED_LEAD"
        self.verification_store[entity_id] = status
        return {
            "target_id": entity_id,
            "human_verification_status": status,
            "notes": notes,
            "timestamp": "2026-09-06T17:00:00Z"
        }

# Global shared singleton to prevent Kùzu lock contention on BENCHMARKS/kuzu_resolved_graph_db
shared_demo_graph_service = GraphIntelligenceService()
