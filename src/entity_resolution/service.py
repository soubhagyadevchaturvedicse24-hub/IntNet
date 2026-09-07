"""
Entity Resolution & Case-Isolated Graph Construction Service for CRIMENET (Slice 5).
Orchestrates EvidenceContract_v1 parsing, normalizers, matchers, entity resolvers,
case-scoped Kùzu Graph DB ingestion, human verification workflow, and audit trail generation.
"""

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from src.auth.models import TokenPayload
from src.auth.service import AuthService
from src.authorization.policy_engine import PolicyEngine, AuthorizationRequest
from src.audit.service import AuditService
from src.cases.service import CaseService
from src.evidence.service import EvidenceService
from src.processing.service import ProcessingService
from src.entity_resolution.normalizer import normalize_entity
from src.entity_resolution.matcher import evaluate_candidate_match
from src.entity_resolution.resolver import EntityResolver
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator


class EntityGraphService:
    def __init__(
        self,
        graph_integrator: Optional[KuzuEntityGraphIntegrator] = None,
        processing_service: Optional[ProcessingService] = None,
        evidence_service: Optional[EvidenceService] = None,
        case_service: Optional[CaseService] = None,
        policy_engine: Optional[PolicyEngine] = None,
        audit_service: Optional[AuditService] = None,
        auth_service: Optional[AuthService] = None
    ):
        self.graph_integrator = graph_integrator or KuzuEntityGraphIntegrator()
        self.graph_integrator.setup()
        self.processing_service = processing_service or ProcessingService()
        self.evidence_service = evidence_service or self.processing_service.evidence_service
        self.case_service = case_service or self.evidence_service.case_service
        self.policy_engine = policy_engine or self.evidence_service.policy_engine
        self.audit_service = audit_service or self.evidence_service.audit_service
        self.auth_service = auth_service or self.evidence_service.auth_service
        self.verification_store: Dict[str, str] = {}

    def _verify_auth(
        self,
        actor: TokenPayload,
        action: str,
        resource_id: str,
        target_case_id: str,
        resource_owner_case_id: Optional[str] = None
    ):
        user = self.auth_service.get_user_by_id(actor.sub)
        user_authorized_cases = user.authorized_case_ids if user else []

        req = AuthorizationRequest(
            actor=actor,
            action=action,
            resource_type="graph_entity",
            resource_id=resource_id,
            target_case_id=target_case_id,
            resource_owner_case_id=resource_owner_case_id
        )

        decision = self.policy_engine.evaluate(req, user_authorized_cases)

        # Record Audit Event
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=target_case_id,
            action=action,
            target_resource=f"graph:{resource_id}",
            decision="ALLOW" if decision.allowed else "DENY",
            metadata={"reason": decision.reason}
        )

        if not decision.allowed:
            raise PermissionError(decision.reason)

    def _generate_deterministic_canonical_id(self, case_id: str, entity_type: str, norm_val: str) -> str:
        clean_type = entity_type[:3].upper()
        digest = hashlib.sha256(f"{case_id}:{clean_type}:{norm_val}".encode('utf-8')).hexdigest()[:6].upper()
        return f"CAN-{clean_type}-{digest}"

    def ingest_evidence_contract(self, actor: TokenPayload, case_id: str, job_id: str) -> Dict[str, Any]:
        # 1. Fetch processing job and contract
        job = self.processing_service.get_job(actor, job_id)
        if not job or job.case_id != case_id:
            raise PermissionError(f"ID MANIPULATION DENY: Job '{job_id}' does not belong to case '{case_id}'.")

        self._verify_auth(
            actor=actor,
            action="INGEST_GRAPH_OBSERVATIONS",
            resource_id=job_id,
            target_case_id=case_id
        )

        contract = self.processing_service.get_evidence_contract(actor, job_id)
        if not contract:
            raise ValueError(f"EvidenceContract_v1 payload not available for completed job '{job_id}'.")

        # 2. Extract observed entities & relationships
        raw_entities = contract.get("extracted_entities", [])
        observed_artifacts = contract.get("observed_artifacts", [])
        evidence_id = contract["provenance_envelope"]["evidence_id"]

        # Run Entity Resolution
        resolver = EntityResolver()
        obs_payload = []
        for ent in raw_entities:
            obs_payload.append({
                "obs_id": ent.get("entity_id", f"OBS-{uuid.uuid4().hex[:4]}"),
                "entity_type": ent.get("entity_type", "Person"),
                "raw_value": ent.get("observed_value", ""),
                "source_file": evidence_id
            })

        if not obs_payload:
            return {
                "status": "COMPLETED",
                "case_id": case_id,
                "job_id": job_id,
                "canonical_entities_created": 0,
                "relationships_created": 0,
                "canonical_entities": [],
                "relationships": []
            }

        resolved_clusters = resolver.resolve_observations(obs_payload)

        # Convert to Case-Isolated Canonical Entity objects
        canonical_entities = []
        for cluster in resolved_clusters:
            norm_val = cluster["normalized_value"]
            etype = cluster["entity_type"]
            det_cid = self._generate_deterministic_canonical_id(case_id, etype, norm_val)

            cluster["canonical_entity_id"] = det_cid
            cluster["case_id"] = case_id
            cluster["evidence_id"] = evidence_id
            canonical_entities.append(cluster)

            # Register resource owner binding in PDP
            self.policy_engine.register_resource_case(det_cid, case_id)

        # 3. Build Case-Isolated Evidence-Backed Relationships
        relationships = [
            {
                "rel_id": f"REL-{evidence_id}-001",
                "src_id": canonical_entities[0]["canonical_entity_id"],
                "tgt_id": canonical_entities[1]["canonical_entity_id"],
                "src_label": canonical_entities[0].get("entity_type", "Person"),
                "tgt_label": canonical_entities[1].get("entity_type", "Person"),
                "rel_label": "ASSOCIATED_WITH",
                "case_id": case_id,
                "evidence_id": evidence_id,
                "confidence": 1.0
            }
        ] if len(canonical_entities) >= 2 else []

        for rel in relationships:
            self.policy_engine.register_resource_case(rel["rel_id"], case_id)

        # 4. Ingest into Kùzu Graph DB Engine
        ingested_nodes = self.graph_integrator.ingest_canonical_entities(canonical_entities)
        ingested_edges = self.graph_integrator.ingest_resolved_relationships(relationships)

        # Record Audit Event
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=case_id,
            action="ENTITY_RESOLUTION_PERFORMED",
            target_resource=f"graph:contract:{job_id}",
            decision="ALLOW",
            metadata={"nodes_ingested": ingested_nodes, "edges_ingested": ingested_edges}
        )

        return {
            "status": "COMPLETED",
            "case_id": case_id,
            "job_id": job_id,
            "canonical_entities_created": len(canonical_entities),
            "relationships_created": len(relationships),
            "canonical_entities": canonical_entities,
            "relationships": relationships
        }

    def get_case_graph(self, actor: TokenPayload, case_id: str, demo: bool = False) -> Dict[str, Any]:
        # Verify Case Access Authorization (BOLA)
        self._verify_auth(
            actor=actor,
            action="READ_CASE_GRAPH",
            resource_id=f"GRAPH-{case_id}",
            target_case_id=case_id
        )

        if demo:
            from src.api.graph_service import shared_demo_graph_service as demo_service
            overview = demo_service.get_graph_overview()

            demo_nodes = []
            person_ids = set()
            for n in overview.get("nodes", []):
                if n.get("entity_type") == "Person":
                    nid = n["id"]
                    person_ids.add(nid)
                    if nid == "CAN-PER-0001":
                        layer = 0
                    else:
                        num = int(nid.split("-")[-1]) if nid.split("-")[-1].isdigit() else 99
                        if num <= 11:
                            layer = 1
                        elif num <= 23:
                            layer = 2
                        else:
                            layer = 3
                    ver = self.verification_store.get(f"{case_id}:{nid}", self.verification_store.get(nid, "UNDER_REVIEW"))
                    demo_nodes.append({
                        "id": nid,
                        "label": n.get("label", nid),
                        "canonical_name": n.get("label", nid),
                        "entity_type": "Person",
                        "layer": layer,
                        "observed_count": n.get("observed_count", 1),
                        "is_anchor": (nid == "CAN-PER-0001"),
                        "role": "Investigation Subject" if nid == "CAN-PER-0001" else "Contact Lead",
                        "human_verification_status": ver,
                        "case_id": case_id
                    })

            demo_edges = []
            for e in overview.get("edges", []):
                if e.get("source") in person_ids and e.get("target") in person_ids:
                    ver = self.verification_store.get(f"{case_id}:{e['id']}", self.verification_store.get(e["id"], "UNDER_REVIEW"))
                    e_copy = dict(e)
                    e_copy["human_verification_status"] = ver
                    e_copy["case_id"] = case_id
                    demo_edges.append(e_copy)

            return {
                "case_id": case_id,
                "demo_mode": True,
                "is_empty": False,
                "disclaimer": "[DEMO MODE] CAN-PER-0001 Vikram Singh contact network is pre-seeded demonstration data.",
                "anchor": {
                    "id": "CAN-PER-0001",
                    "label": "Vikram Singh",
                    "role": "Investigation Subject",
                    "description": "Pre-seeded demonstration target",
                    "layer": 0,
                    "is_anchor": True
                },
                "summary": {
                    "total_nodes": len(demo_nodes),
                    "total_edges": len(demo_edges)
                },
                "nodes": demo_nodes,
                "edges": demo_edges
            }

        # REAL CASE-SCOPED PEOPLE NETWORK
        case_obj = self.case_service.get_case(actor, case_id)
        if case_obj and hasattr(case_obj, "anchor") and case_obj.anchor:
            anchor = case_obj.anchor
            anchor_dict = {
                "id": anchor.anchor_id,
                "label": anchor.canonical_name,
                "canonical_name": anchor.canonical_name,
                "role": anchor.role.value if hasattr(anchor.role, "value") else str(anchor.role),
                "description": anchor.description,
                "layer": 0,
                "is_anchor": True
            }
        else:
            anchor_dict = {
                "id": f"ANC-{case_id}",
                "label": f"Primary Subject ({case_id})",
                "canonical_name": f"Primary Subject ({case_id})",
                "role": "Investigation Subject",
                "description": "Case Anchor Subject",
                "layer": 0,
                "is_anchor": True
            }

        # Query Kùzu DB for Person nodes registered to this case
        person_nodes = []
        person_ids = set()
        try:
            res = self.graph_integrator.conn.execute("MATCH (n:Person) RETURN n.id, n.canonical_name, n.observed_count")
            while res.has_next():
                row = res.get_next()
                nid, cname, count = row[0], row[1], row[2]
                owner = self.policy_engine.resource_case_map.get(nid)
                if owner == case_id:
                    person_ids.add(nid)
                    ver = self.verification_store.get(f"{case_id}:{nid}", self.verification_store.get(nid, "UNDER_REVIEW"))
                    person_nodes.append({
                        "id": nid,
                        "label": cname,
                        "canonical_name": cname,
                        "entity_type": "Person",
                        "observed_count": count,
                        "case_id": case_id,
                        "is_anchor": False,
                        "role": "Contact Lead",
                        "human_verification_status": ver
                    })
        except Exception:
            pass

        # Query Kùzu DB for edges between Person nodes
        edges = []
        try:
            res_rel = self.graph_integrator.conn.execute("MATCH (a:Person)-[r:ASSOCIATED_WITH]->(b:Person) RETURN a.id, b.id, r.evidence_id, r.confidence")
            edge_idx = 1
            while res_rel.has_next():
                row = res_rel.get_next()
                src, tgt, ev_id, conf = row[0], row[1], row[2], row[3]
                if src in person_ids and tgt in person_ids:
                    edge_id = f"EDGE-{case_id}-{edge_idx:04d}"
                    edge_idx += 1
                    ver = self.verification_store.get(f"{case_id}:{edge_id}", self.verification_store.get(edge_id, "UNDER_REVIEW"))

                    from src.analytics.ccc_scorer import calculate_ccc_score
                    ccc = calculate_ccc_score(
                        rel_type="ASSOCIATED_WITH",
                        frequency=5,
                        days_elapsed=7.0,
                        source_count=1,
                        er_confidence=conf,
                        provenance_valid=True,
                        evidence_ids=[ev_id]
                    )

                    edges.append({
                        "id": edge_id,
                        "source": src,
                        "target": tgt,
                        "relationship_type": "ASSOCIATED_WITH",
                        "relationship": "ASSOCIATED_WITH",
                        "evidence_id": ev_id,
                        "confidence": conf,
                        "case_id": case_id,
                        "ccc_score": ccc["association_score"],
                        "ccc_ring": ccc["concentric_ring"],
                        "priority_label": ccc["priority_label"],
                        "human_verification_status": ver
                    })
        except Exception:
            pass

        # If zero person contacts exist for this case, honestly return empty state with Anchor
        if not edges and not person_nodes:
            anchor_node = {
                "id": anchor_dict["id"],
                "label": anchor_dict["label"],
                "canonical_name": anchor_dict["label"],
                "entity_type": "Person",
                "role": anchor_dict["role"],
                "description": anchor_dict["description"],
                "layer": 0,
                "is_anchor": True,
                "observed_count": 0,
                "case_id": case_id,
                "human_verification_status": "HUMAN_VERIFIED_LEAD"
            }
            return {
                "case_id": case_id,
                "demo_mode": False,
                "is_empty": True,
                "message": "No real contact-network relationships are currently available for this case.",
                "anchor": anchor_dict,
                "summary": {
                    "total_nodes": 1,
                    "total_edges": 0
                },
                "nodes": [anchor_node],
                "edges": []
            }

        # Build adjacency graph and compute BFS distances from anchor
        adj = {}
        for e in edges:
            s, t = e["source"], e["target"]
            adj.setdefault(s, []).append(t)
            adj.setdefault(t, []).append(s)

        root_id = anchor_dict["id"]
        if not any(n["id"] == root_id for n in person_nodes):
            person_nodes.insert(0, {
                "id": root_id,
                "label": anchor_dict["label"],
                "canonical_name": anchor_dict["label"],
                "entity_type": "Person",
                "role": anchor_dict["role"],
                "description": anchor_dict["description"],
                "layer": 0,
                "is_anchor": True,
                "observed_count": 0,
                "case_id": case_id,
                "human_verification_status": "HUMAN_VERIFIED_LEAD"
            })

        distances = {root_id: 0}
        queue = [root_id]
        while queue:
            curr = queue.pop(0)
            curr_dist = distances[curr]
            for nbr in adj.get(curr, []):
                if nbr not in distances:
                    distances[nbr] = curr_dist + 1
                    queue.append(nbr)

        for n in person_nodes:
            dist = distances.get(n["id"], 3)
            if n["id"] == root_id:
                n["layer"] = 0
                n["is_anchor"] = True
            elif dist == 1:
                n["layer"] = 1
            elif dist == 2:
                n["layer"] = 2
            else:
                n["layer"] = 3

        return {
            "case_id": case_id,
            "demo_mode": False,
            "is_empty": False,
            "anchor": anchor_dict,
            "summary": {
                "total_nodes": len(person_nodes),
                "total_edges": len(edges)
            },
            "nodes": person_nodes,
            "edges": edges
        }

    def get_entity_details(
        self,
        actor: TokenPayload,
        case_id: str,
        entity_id: str,
        demo: bool = False
    ) -> Optional[Dict[str, Any]]:
        self._verify_auth(
            actor=actor,
            action="READ_GRAPH_ENTITY",
            resource_id=entity_id,
            target_case_id=case_id
        )

        if demo:
            from src.api.graph_service import shared_demo_graph_service as demo_service
            details = demo_service.get_entity_details(entity_id)
            if details:
                ver = self.verification_store.get(f"{case_id}:{entity_id}", self.verification_store.get(entity_id, details.get("human_verification_status", "UNDER_REVIEW")))
                details["human_verification_status"] = ver
            return details

        # Real case: check if anchor
        case_obj = self.case_service.get_case(actor, case_id)
        anchor = case_obj.anchor if case_obj else None
        if anchor and entity_id == anchor.anchor_id:
            ver = self.verification_store.get(f"{case_id}:{entity_id}", self.verification_store.get(entity_id, "HUMAN_VERIFIED_LEAD"))
            return {
                "canonical_entity_id": anchor.anchor_id,
                "entity_type": "Person",
                "canonical_name": anchor.canonical_name,
                "role": anchor.role.value if hasattr(anchor.role, "value") else str(anchor.role),
                "description": anchor.description,
                "normalized_value": anchor.canonical_name,
                "observed_values": [anchor.canonical_name],
                "match_confidence": 1.0,
                "match_method": "CASE_ANCHOR_DECLARATION",
                "source_evidence_ids": [],
                "is_anchor": True,
                "human_verification_status": ver,
                "responsible_ai_note": "Case Anchor entity defined within judicial and investigative case scope. Analytical reference only."
            }

        # Check in Kùzu
        labels = ["Person", "PhoneNumber", "Vehicle", "Location", "Organization"]
        for lbl in labels:
            try:
                res = self.graph_integrator.conn.execute(f"MATCH (n:{lbl} {{id: '{entity_id}'}}) RETURN n.id, n.canonical_name, n.observed_count")
                if res.has_next():
                    nid, cname, count = res.get_next()
                    owner = self.policy_engine.resource_case_map.get(nid)
                    if owner and owner != case_id:
                        raise PermissionError(f"ID MANIPULATION DENY: Entity '{entity_id}' belongs to case '{owner}'.")
                    ver = self.verification_store.get(f"{case_id}:{entity_id}", self.verification_store.get(entity_id, "UNDER_REVIEW"))
                    return {
                        "canonical_entity_id": nid,
                        "entity_type": lbl,
                        "canonical_name": cname,
                        "normalized_value": cname,
                        "observed_values": [cname],
                        "match_confidence": 1.0,
                        "match_method": "EXACT_NORMALIZED_RULE",
                        "source_evidence_ids": [],
                        "is_anchor": False,
                        "human_verification_status": ver,
                        "responsible_ai_note": "Analytical Lead / Indicator for investigator reference only. Not a probability of guilt."
                    }
            except Exception:
                pass
        return None

    def get_relationship_details(
        self,
        actor: TokenPayload,
        case_id: str,
        edge_id: str,
        demo: bool = False
    ) -> Optional[Dict[str, Any]]:
        self._verify_auth(
            actor=actor,
            action="READ_GRAPH_RELATIONSHIP",
            resource_id=edge_id,
            target_case_id=case_id
        )

        if demo:
            from src.api.graph_service import shared_demo_graph_service as demo_service
            details = demo_service.get_relationship_details(edge_id)
            if details:
                ver = self.verification_store.get(f"{case_id}:{edge_id}", self.verification_store.get(edge_id, details.get("human_verification_status", "UNDER_REVIEW")))
                details["human_verification_status"] = ver
            return details

        # Real case: search edges in get_case_graph
        graph = self.get_case_graph(actor, case_id, demo=False)
        for e in graph.get("edges", []):
            if e["id"] == edge_id:
                return {
                    "edge_id": edge_id,
                    "relationship_type": e.get("relationship_type", "ASSOCIATED_WITH"),
                    "source_entity": e["source"],
                    "target_entity": e["target"],
                    "confidence": e.get("confidence", 1.0),
                    "supporting_evidence_id": e.get("evidence_id", ""),
                    "supporting_evidence_ids": [e.get("evidence_id", "")] if e.get("evidence_id") else [],
                    "source_artifact": "Observed Forensic Evidence",
                    "source_format": "Forensic Container",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "association_score": e.get("ccc_score", 50.0),
                    "ccc_ring": e.get("ccc_ring", "LAYER_2_BROADER"),
                    "priority_label": e.get("priority_label", "MODERATE_ASSOCIATION"),
                    "human_verification_status": e.get("human_verification_status", "UNDER_REVIEW"),
                    "responsible_ai_disclaimer": "Experimental analytical prioritization score. Not a probability of guilt."
                }
        return None

    def get_neighbors(
        self,
        actor: TokenPayload,
        case_id: str,
        entity_id: str,
        hops: int = 1,
        demo: bool = False
    ) -> Dict[str, Any]:
        self._verify_auth(
            actor=actor,
            action="READ_GRAPH_ENTITY",
            resource_id=entity_id,
            target_case_id=case_id
        )

        if demo:
            from src.api.graph_service import shared_demo_graph_service as demo_service
            res = demo_service.get_neighbors(entity_id, hops=hops)
            person_neighbors = [n for n in res.get("neighbors", []) if n.get("entity_type") == "Person"]
            return {
                "root_entity_id": entity_id,
                "hops": hops,
                "neighbor_count": len(person_neighbors),
                "neighbors": person_neighbors
            }

        graph = self.get_case_graph(actor, case_id, demo=False)
        adj = {}
        for e in graph.get("edges", []):
            s, t = e["source"], e["target"]
            adj.setdefault(s, []).append(t)
            adj.setdefault(t, []).append(s)

        visited = {entity_id}
        current_level = {entity_id}
        for _ in range(hops):
            next_level = set()
            for node in current_level:
                for nbr in adj.get(node, []):
                    if nbr not in visited:
                        visited.add(nbr)
                        next_level.add(nbr)
            current_level = next_level

        neighbors_found = visited - {entity_id}
        neighbor_nodes = [n for n in graph.get("nodes", []) if n["id"] in neighbors_found]
        return {
            "root_entity_id": entity_id,
            "hops": hops,
            "neighbor_count": len(neighbor_nodes),
            "neighbors": neighbor_nodes
        }

    def get_shortest_path(
        self,
        actor: TokenPayload,
        case_id: str,
        src_id: str,
        tgt_id: str,
        demo: bool = False
    ) -> Dict[str, Any]:
        self._verify_auth(
            actor=actor,
            action="READ_CASE_GRAPH",
            resource_id=f"GRAPH-{case_id}",
            target_case_id=case_id
        )

        if demo:
            from src.api.graph_service import shared_demo_graph_service as demo_service
            return demo_service.get_shortest_path(src_id, tgt_id)

        graph = self.get_case_graph(actor, case_id, demo=False)
        adj = {}
        for e in graph.get("edges", []):
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

    def verify_human_lead(
        self,
        actor: TokenPayload,
        case_id: str,
        target_id: str,
        status_decision: str,
        notes: Optional[str] = ""
    ) -> Dict[str, Any]:
        # Verify authorization and owner case binding
        self._verify_auth(
            actor=actor,
            action="VERIFY_HUMAN_LEAD",
            resource_id=target_id,
            target_case_id=case_id
        )

        valid_statuses = ["UNDER_REVIEW", "HUMAN_VERIFIED_LEAD", "REJECTED_ASSOCIATION"]
        if status_decision not in valid_statuses:
            raise ValueError(f"Invalid human verification status '{status_decision}'. Expected one of {valid_statuses}.")

        # Persist verification status in verification_store
        self.verification_store[f"{case_id}:{target_id}"] = status_decision
        self.verification_store[target_id] = status_decision

        # Audit Event
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=case_id,
            action="HUMAN_VERIFICATION_RECORDED",
            target_resource=f"graph:{target_id}",
            decision="ALLOW",
            metadata={"verification_status": status_decision, "notes": notes}
        )

        return {
            "status": "SUCCESS",
            "target_id": target_id,
            "case_id": case_id,
            "human_verification_status": status_decision,
            "verified_by": actor.sub,
            "notes": notes
        }
