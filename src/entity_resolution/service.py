"""
Entity Resolution & Case-Isolated Graph Construction Service for CRIMENET (Slice 5 & Slice 8B).
Orchestrates EvidenceContract_v1 and deep parsed observation extraction, normalizers, matchers,
entity resolvers, case-scoped Kùzu Graph DB ingestion, human verification workflow, and audit trail generation.
"""

import hashlib
import json
import sqlite3
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
from src.artifacts.repository import SQLiteArtifactRepository
from src.parsers.models import ParsedArtifact
from src.parsers.repository import SQLiteParsedArtifactRepository
from src.entity_resolution.normalizer import normalize_entity
from src.entity_resolution.matcher import evaluate_candidate_match
from src.entity_resolution.resolver import EntityResolver
from src.entity_resolution.graph_integrator import KuzuEntityGraphIntegrator
from src.entity_resolution.signal_extractor import ObservationSignalExtractor
from src.entity_resolution.signals import ExtractedSignal, ExtractedRelationship


class EntityGraphService:
    def __init__(
        self,
        graph_integrator: Optional[KuzuEntityGraphIntegrator] = None,
        processing_service: Optional[ProcessingService] = None,
        evidence_service: Optional[EvidenceService] = None,
        case_service: Optional[CaseService] = None,
        policy_engine: Optional[PolicyEngine] = None,
        audit_service: Optional[AuditService] = None,
        auth_service: Optional[AuthService] = None,
        parsed_repo: Optional[SQLiteParsedArtifactRepository] = None,
        signal_extractor: Optional[ObservationSignalExtractor] = None,
        artifact_repo: Optional[SQLiteArtifactRepository] = None,
    ):
        self.graph_integrator = graph_integrator or KuzuEntityGraphIntegrator()
        self.graph_integrator.setup()
        self.processing_service = processing_service or ProcessingService()
        self.evidence_service = evidence_service or self.processing_service.evidence_service
        self.case_service = case_service or self.evidence_service.case_service
        self.policy_engine = policy_engine or self.evidence_service.policy_engine
        self.audit_service = audit_service or self.evidence_service.audit_service
        self.auth_service = auth_service or self.evidence_service.auth_service
        self.parsed_repo = parsed_repo or SQLiteParsedArtifactRepository()
        self.signal_extractor = signal_extractor or ObservationSignalExtractor()
        self.artifact_repo = artifact_repo or SQLiteArtifactRepository()
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

    def _save_graph_provenance(self, case_id: str, canonical_entities: List[Dict[str, Any]], canonical_relationships: List[Dict[str, Any]]):
        db_path = getattr(self.policy_engine, "db_path", "DATA/cases.db")
        if not db_path or db_path == ":memory:":
            return
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_provenance_records (
                    case_id TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    PRIMARY KEY (case_id, resource_id)
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_graph_prov_case ON graph_provenance_records(case_id);")

            # Save canonical entities
            for ent in canonical_entities:
                cid = ent.get("canonical_entity_id")
                if cid:
                    conn.execute("""
                        INSERT INTO graph_provenance_records (case_id, resource_id, resource_type, provenance_json)
                        VALUES (?, ?, 'ENTITY', ?)
                        ON CONFLICT(case_id, resource_id) DO UPDATE SET provenance_json = excluded.provenance_json;
                    """, (case_id, cid, json.dumps(ent)))

            # Save canonical relationships (by rel_id and by pair)
            pair_map = {}
            for r in canonical_relationships:
                rid = r.get("rel_id")
                if rid:
                    conn.execute("""
                        INSERT INTO graph_provenance_records (case_id, resource_id, resource_type, provenance_json)
                        VALUES (?, ?, 'RELATIONSHIP', ?)
                        ON CONFLICT(case_id, resource_id) DO UPDATE SET provenance_json = excluded.provenance_json;
                    """, (case_id, rid, json.dumps(r)))

                pair_key = f"PAIR:{r.get('src_id')}->{r.get('tgt_id')}"
                if pair_key not in pair_map:
                    pair_map[pair_key] = r

            for pkey, rdata in pair_map.items():
                conn.execute("""
                    INSERT INTO graph_provenance_records (case_id, resource_id, resource_type, provenance_json)
                    VALUES (?, ?, 'RELATIONSHIP_PAIR', ?)
                    ON CONFLICT(case_id, resource_id) DO UPDATE SET provenance_json = excluded.provenance_json;
                """, (case_id, pkey, json.dumps(rdata)))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Graph provenance persistence warning: {e}")

    def _get_graph_provenance(self, case_id: str, resource_id: str) -> Optional[Dict[str, Any]]:
        db_path = getattr(self.policy_engine, "db_path", "DATA/cases.db")
        if not db_path or db_path == ":memory:":
            return None
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT provenance_json FROM graph_provenance_records WHERE case_id = ? AND resource_id = ? LIMIT 1;",
                (case_id, resource_id)
            )
            row = cur.fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
        except Exception:
            pass
        return None

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

    def ingest_parsed_observations(
        self,
        actor: TokenPayload,
        case_id: str,
        artifact_id: Optional[str] = None,
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Slice 8B Core Bridge:
        Processes deep parsed observations into normalized signals, canonical entities,
        and evidence-backed relationships, then ingests them into Kùzu Graph DB.
        Enforces BOLA authorization, case boundaries, and idempotency.
        """
        self._verify_auth(
            actor=actor,
            action="INGEST_GRAPH_OBSERVATIONS",
            resource_id=job_id or artifact_id or f"OBS-{case_id}",
            target_case_id=case_id,
        )

        # Scoped retrieval of parsed artifacts
        parsed_artifacts: List[ParsedArtifact] = []
        if artifact_id:
            parsed = self.parsed_repo.get_by_id(artifact_id)
            if not parsed:
                raise KeyError(f"Parsed artifact '{artifact_id}' not found.")
            if parsed.case_id != case_id:
                raise PermissionError(f"ID MANIPULATION DENIED: Artifact belongs to case '{parsed.case_id}', not '{case_id}'.")
            parsed_artifacts = [parsed]
        elif job_id:
            all_case_parsed = self.parsed_repo.list_by_case(case_id)
            matched = []
            for p in all_case_parsed:
                if job_id in p.artifact_id or p.structured_metadata.get("job_id") == job_id:
                    matched.append(p)
                else:
                    try:
                        art = self.artifact_repo.get_by_id(p.artifact_id)
                        if art and art.processing_job_id == job_id:
                            matched.append(p)
                    except Exception:
                        pass
            parsed_artifacts = matched
        else:
            parsed_artifacts = self.parsed_repo.list_by_case(case_id)

        all_signals: List[ExtractedSignal] = []
        all_relationships: List[ExtractedRelationship] = []

        for parsed in parsed_artifacts:
            # Authoritative evidence_id and job_id derivation
            ev_id = parsed.structured_metadata.get("evidence_id")
            j_id = parsed.structured_metadata.get("job_id") or job_id
            if not ev_id or not j_id:
                try:
                    art = self.artifact_repo.get_by_id(parsed.artifact_id)
                    if art:
                        if not ev_id:
                            ev_id = art.evidence_id
                        if not j_id:
                            j_id = art.processing_job_id
                except Exception:
                    pass
            ev_id = ev_id or parsed.artifact_id
            j_id = j_id or "JOB-UNKNOWN"

            for obs in parsed.observations:
                sigs = self.signal_extractor.extract_signals_from_observation(
                    obs=obs,
                    case_id=case_id,
                    evidence_id=ev_id,
                    artifact_id=parsed.artifact_id,
                    job_id=j_id,
                )
                all_signals.extend(sigs)
                rels = self.signal_extractor.extract_relationships_from_observation(
                    obs=obs,
                    signals=sigs,
                    case_id=case_id,
                    evidence_id=ev_id,
                    artifact_id=parsed.artifact_id,
                    job_id=j_id,
                )
                all_relationships.extend(rels)

        if not all_signals:
            return {
                "status": "COMPLETED",
                "case_id": case_id,
                "artifacts_processed": len(parsed_artifacts),
                "signals_extracted": 0,
                "canonical_entities_created": 0,
                "relationships_created": 0,
                "canonical_entities": [],
                "relationships": [],
            }

        # Run Entity Resolution on extracted signals
        resolver = EntityResolver()
        obs_payload = []
        for sig in all_signals:
            obs_payload.append({
                "obs_id": sig.signal_id,
                "entity_type": sig.entity_type,
                "raw_value": sig.observed_value,
                "source_file": sig.artifact_id,
            })

        resolved_clusters = resolver.resolve_observations(obs_payload)

        # Map signal_id -> canonical_entity_id
        signal_to_canonical: Dict[str, str] = {}
        canonical_entities = []

        for cluster in resolved_clusters:
            norm_val = cluster["normalized_value"]
            etype = cluster["entity_type"]
            det_cid = self._generate_deterministic_canonical_id(case_id, etype, norm_val)

            # Map every raw signal obs_id in this cluster to det_cid
            for obs_id in cluster["source_evidence_ids"]:
                signal_to_canonical[obs_id] = det_cid

            # Collect complete 5-part provenance across all supporting signals
            cluster_signals = [s for s in all_signals if signal_to_canonical.get(s.signal_id) == det_cid or s.signal_id in cluster["source_evidence_ids"]]
            ev_ids = sorted(list({s.evidence_id for s in cluster_signals if s.evidence_id}))
            art_ids = sorted(list({s.artifact_id for s in cluster_signals if s.artifact_id}))
            job_ids_set = sorted(list({s.job_id for s in cluster_signals if s.job_id}))
            obs_ids_set = sorted(list({s.observation_id for s in cluster_signals if s.observation_id}))

            cluster["canonical_entity_id"] = det_cid
            cluster["case_id"] = case_id
            cluster["evidence_id"] = ev_ids[0] if ev_ids else (cluster["supporting_sources"][0] if cluster["supporting_sources"] else "EV-UNKNOWN")
            cluster["source_evidence_ids"] = ev_ids if ev_ids else cluster["source_evidence_ids"]
            cluster["source_artifact_ids"] = art_ids
            cluster["source_job_ids"] = job_ids_set
            cluster["source_observation_ids"] = obs_ids_set
            canonical_entities.append(cluster)

        # Canonicalize relationships
        canonical_relationships = []
        rel_bindings = []
        for rel in all_relationships:
            src_cid = signal_to_canonical.get(rel.source_signal_id)
            tgt_cid = signal_to_canonical.get(rel.target_signal_id)
            if src_cid and tgt_cid and src_cid != tgt_cid:
                rel_dict = {
                    "rel_id": rel.rel_id,
                    "src_id": src_cid,
                    "tgt_id": tgt_cid,
                    "src_label": rel.source_label,
                    "tgt_label": rel.target_label,
                    "rel_label": rel.rel_label,
                    "case_id": case_id,
                    "evidence_id": rel.evidence_id,
                    "artifact_id": rel.artifact_id,
                    "observation_id": rel.observation_id,
                    "job_id": rel.job_id,
                    "confidence": rel.confidence,
                    "source_location": rel.source_location,
                    "extraction_method": rel.extraction_method,
                    "human_verification_status": rel.human_verification_status,
                    "source_signal_id": rel.source_signal_id,
                    "target_signal_id": rel.target_signal_id,
                }
                canonical_relationships.append(rel_dict)
                rel_bindings.append((rel.rel_id, case_id, "relationship"))

        # Bulk register resource owner bindings in PolicyEngine (High-performance single transaction)
        all_bindings = [(c["canonical_entity_id"], case_id, "entity") for c in canonical_entities] + rel_bindings
        if hasattr(self.policy_engine, "register_resources_batch"):
            self.policy_engine.register_resources_batch(all_bindings)
        else:
            for rid, cid, rtype in all_bindings:
                self.policy_engine.register_resource_case(rid, cid, rtype)

        # Ingest into Kùzu DB idempotently
        ingested_nodes = self.graph_integrator.ingest_canonical_entities(canonical_entities)
        ingested_edges = self.graph_integrator.ingest_resolved_relationships(canonical_relationships)

        # Persist 5-stage forensic graph provenance in SQLite
        self._save_graph_provenance(case_id, canonical_entities, canonical_relationships)

        # Record Audit Event
        self.audit_service.record_event(
            actor_id=actor.sub,
            actor_role=actor.role.value,
            case_id=case_id,
            action="OBSERVATIONS_INGESTED_TO_GRAPH",
            target_resource=f"graph:parsed_obs:{case_id}",
            decision="ALLOW",
            metadata={
                "artifacts_processed": len(parsed_artifacts),
                "signals_extracted": len(all_signals),
                "nodes_ingested": ingested_nodes,
                "edges_ingested": ingested_edges,
            },
        )

        return {
            "status": "COMPLETED",
            "case_id": case_id,
            "artifacts_processed": len(parsed_artifacts),
            "signals_extracted": len(all_signals),
            "canonical_entities_created": len(canonical_entities),
            "relationships_created": len(canonical_relationships),
            "canonical_entities": canonical_entities,
            "relationships": canonical_relationships,
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

        # REAL CASE-SCOPED PEOPLE & CONTACT NETWORK
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

        # Query Kùzu DB for nodes registered to this case
        entity_nodes = []
        entity_ids = set()
        node_labels = ["Person", "PhoneNumber", "Email", "Vehicle", "Location", "Organization", "BankAccount"]
        for lbl in node_labels:
            try:
                res = self.graph_integrator.conn.execute(f"MATCH (n:{lbl}) RETURN n.id, n.canonical_name, n.observed_count")
                while res.has_next():
                    row = res.get_next()
                    nid, cname, count = row[0], row[1], row[2]
                    owner = self.policy_engine.get_resource_case(nid) if hasattr(self.policy_engine, "get_resource_case") else self.policy_engine.resource_case_map.get(nid)
                    if owner == case_id:
                        entity_ids.add(nid)
                        ver = self.verification_store.get(f"{case_id}:{nid}", self.verification_store.get(nid, "UNDER_REVIEW"))
                        entity_nodes.append({
                            "id": nid,
                            "label": cname,
                            "canonical_name": cname,
                            "entity_type": lbl,
                            "observed_count": count,
                            "case_id": case_id,
                            "is_anchor": False,
                            "role": "Contact Lead" if lbl == "Person" else lbl,
                            "human_verification_status": ver
                        })
            except Exception:
                pass

        from src.analytics.ccc_scorer import calculate_ccc_score

        # Query Kùzu DB for edges registered to this case and group by connected pair
        edge_tables = [
            ("COMMUNICATED_WITH", "Email", "Email"),
            ("COMMUNICATED_WITH", "Person", "Person"),
            ("ASSOCIATED_WITH", "Person", "Person"),
            ("USED_PHONE", "Person", "PhoneNumber"),
            ("USED_EMAIL", "Person", "Email"),
            ("CALLED", "PhoneNumber", "PhoneNumber"),
            ("LOCATED_AT", "Person", "Location"),
            ("CAPTURED_AT", "Person", "Location"),
            ("VISITED", "Person", "Location"),
            ("TRANSFERRED_TO", "Person", "Person"),
            ("TRANSFERRED_TO", "BankAccount", "BankAccount"),
            ("MENTIONED_WITH", "Person", "Organization"),
        ]
        
        # Group raw edges by node pair to eliminate messy multi-string hairballs
        raw_pair_map = {}
        for rel_lbl, src_lbl, tgt_lbl in edge_tables:
            try:
                res_rel = self.graph_integrator.conn.execute(
                    f"MATCH (a:{src_lbl})-[r:{rel_lbl}]->(b:{tgt_lbl}) RETURN a.id, b.id, r.evidence_id, r.confidence"
                )
                while res_rel.has_next():
                    row = res_rel.get_next()
                    src, tgt, ev_id, conf = row[0], row[1], row[2], row[3]
                    if src in entity_ids and tgt in entity_ids and src != tgt:
                        pair_key = (src, tgt)
                        if pair_key not in raw_pair_map:
                            raw_pair_map[pair_key] = []
                        raw_pair_map[pair_key].append({
                            "rel_lbl": rel_lbl,
                            "ev_id": ev_id,
                            "conf": conf or 1.0
                        })
            except Exception:
                pass

        edges = []
        edge_idx = 1
        for (src, tgt), items in raw_pair_map.items():
            edge_id = f"EDGE-{case_id}-{edge_idx:04d}"
            edge_idx += 1
            ver = self.verification_store.get(f"{case_id}:{edge_id}", self.verification_store.get(edge_id, "UNDER_REVIEW"))

            # Register resource case binding so BOLA passes
            self.policy_engine.register_resource_case(edge_id, case_id)

            # Lookup provenance from persistent store
            prov = self._get_graph_provenance(case_id, f"PAIR:{src}->{tgt}") or {}
            rel_id = prov.get("rel_id", edge_id)
            self.policy_engine.register_resource_case(rel_id, case_id)

            # Consolidated multi-link metrics
            distinct_types = list(dict.fromkeys(it["rel_lbl"] for it in items))
            total_interactions = len(items)
            max_conf = max(it["conf"] for it in items)
            ev_list = [it["ev_id"] for it in items if it.get("ev_id")]
            if not ev_list and prov.get("evidence_id"):
                ev_list = [prov["evidence_id"]]

            # Format human-readable concise relationship label
            if len(distinct_types) == 1:
                rel_summary = f"{distinct_types[0]} ({total_interactions}x)" if total_interactions > 1 else distinct_types[0]
            else:
                rel_summary = f"{len(distinct_types)} Link Types ({total_interactions} Connections)"

            ccc = calculate_ccc_score(
                rel_type=distinct_types[0],
                frequency=min(total_interactions * 4, 60),
                days_elapsed=7.0,
                source_count=len(set(ev_list)) or 1,
                er_confidence=max_conf,
                provenance_valid=True,
                evidence_ids=ev_list
            )

            edges.append({
                "id": edge_id,
                "rel_id": rel_id,
                "source": src,
                "target": tgt,
                "relationship_type": distinct_types[0] if len(distinct_types) == 1 else "MULTI_LINK",
                "relationship": rel_summary,
                "distinct_types": distinct_types,
                "interaction_count": total_interactions,
                "is_consolidated": total_interactions > 1,
                "evidence_id": ", ".join(list(dict.fromkeys(ev_list))),
                "artifact_id": prov.get("artifact_id", "autopsy.db"),
                "observation_id": prov.get("observation_id", ""),
                "source_location": prov.get("source_location", ""),
                "extraction_method": prov.get("extraction_method", ""),
                "source_signal_id": prov.get("source_signal_id", ""),
                "target_signal_id": prov.get("target_signal_id", ""),
                "confidence": max_conf,
                "case_id": case_id,
                "ccc_score": ccc["association_score"],
                "ccc_ring": ccc["concentric_ring"],
                "priority_label": ccc["priority_label"],
                "human_verification_status": ver,
                "connections_breakdown": [
                    {
                        "relationship_type": it["rel_lbl"],
                        "evidence_id": it["ev_id"],
                        "confidence": it["conf"]
                    }
                    for it in items
                ]
            })

        # If zero contacts exist for this case, honestly return empty state with Anchor
        if not edges and not entity_nodes:
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
        if not any(n["id"] == root_id for n in entity_nodes):
            entity_nodes.insert(0, {
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

        # Multi-layer Concentric Layout calculation:
        bfs_root = root_id
        if (root_id not in adj or not adj[root_id]) and adj:
            bfs_root = max(adj.keys(), key=lambda k: len(adj[k]))

        distances = {bfs_root: 0}
        queue = [bfs_root]
        while queue:
            curr = queue.pop(0)
            curr_dist = distances[curr]
            for nbr in adj.get(curr, []):
                if nbr not in distances:
                    distances[nbr] = curr_dist + 1
                    queue.append(nbr)

        for n in entity_nodes:
            dist = distances.get(n["id"], 3)
            if n["id"] == bfs_root:
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
                "total_nodes": len(entity_nodes),
                "total_edges": len(edges)
            },
            "nodes": entity_nodes,
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
        labels = ["Person", "PhoneNumber", "Email", "Vehicle", "Location", "Organization", "BankAccount"]
        for lbl in labels:
            try:
                res = self.graph_integrator.conn.execute(f"MATCH (n:{lbl} {{id: '{entity_id}'}}) RETURN n.id, n.canonical_name, n.observed_count")
                if res.has_next():
                    nid, cname, count = res.get_next()
                    owner = self.policy_engine.resource_case_map.get(nid)
                    if owner != case_id:
                        if owner:
                            raise PermissionError(f"ID MANIPULATION DENY: Entity '{entity_id}' belongs to case '{owner}'.")
                        return None
                    ver = self.verification_store.get(f"{case_id}:{entity_id}", self.verification_store.get(entity_id, "UNDER_REVIEW"))
                    ent_prov = self._get_graph_provenance(case_id, nid) or {}
                    ev_ids = ent_prov.get("source_evidence_ids", [])
                    art_ids = ent_prov.get("source_artifact_ids", [])
                    obs_ids = ent_prov.get("source_observation_ids", [])
                    return {
                        "canonical_entity_id": nid,
                        "entity_type": lbl,
                        "canonical_name": cname,
                        "normalized_value": cname,
                        "observed_values": [cname],
                        "match_confidence": 1.0,
                        "match_method": ent_prov.get("match_method", "EXACT_NORMALIZED_RULE"),
                        "source_evidence_ids": ev_ids,
                        "source_artifacts": art_ids,
                        "source_observations": obs_ids,
                        "case_id": case_id,
                        "is_anchor": False,
                        "human_verification_status": ver,
                        "provenance_chain": {
                            "canonical_entity_id": nid,
                            "source_signal_ids": ent_prov.get("source_evidence_ids", []),
                            "source_observation_ids": obs_ids,
                            "source_artifact_ids": art_ids,
                            "source_evidence_ids": ev_ids,
                            "case_id": case_id,
                        },
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
            if e["id"] == edge_id or e.get("rel_id") == edge_id:
                prov_chain = {
                    "relationship_id": e.get("rel_id", edge_id),
                    "source_signal_id": e.get("source_signal_id", f"SIG-{e['source']}"),
                    "target_signal_id": e.get("target_signal_id", f"SIG-{e['target']}"),
                    "observation_id": e.get("observation_id", "OBS-AUTOPSY-SQLITE"),
                    "artifact_id": e.get("artifact_id", "autopsy.db"),
                    "evidence_id": e.get("evidence_id", ""),
                    "case_id": case_id,
                    "source_location": e.get("source_location", "autopsy.db:relational"),
                    "extraction_method": e.get("extraction_method", "AUTOPSY_FORENSIC_ADAPTER"),
                }
                return {
                    "edge_id": edge_id,
                    "rel_id": e.get("rel_id", edge_id),
                    "relationship_type": e.get("relationship_type", "COMMUNICATED_WITH"),
                    "relationship": e.get("relationship", "COMMUNICATED_WITH"),
                    "source": e["source"],
                    "target": e["target"],
                    "source_entity": e["source"],
                    "target_entity": e["target"],
                    "confidence": e.get("confidence", 1.0),
                    "case_id": case_id,
                    "supporting_evidence_id": e.get("evidence_id", ""),
                    "supporting_evidence_ids": [e.get("evidence_id", "")] if e.get("evidence_id") else [],
                    "source_artifact": e.get("artifact_id") or "autopsy.db",
                    "observation_id": e.get("observation_id", ""),
                    "source_location": e.get("source_location", ""),
                    "source_format": "Autopsy Forensic SQLite Database",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "association_score": e.get("ccc_score", 80.0),
                    "ccc_score": e.get("ccc_score", 80.0),
                    "ccc_ring": e.get("ccc_ring", "LAYER_1_DIRECT"),
                    "priority_label": e.get("priority_label", "STRONG_ASSOCIATION"),
                    "human_verification_status": e.get("human_verification_status", "UNDER_REVIEW"),
                    "interaction_count": e.get("interaction_count", 1),
                    "distinct_types": e.get("distinct_types", [e.get("relationship_type")]),
                    "is_consolidated": e.get("is_consolidated", False),
                    "connections_breakdown": e.get("connections_breakdown", []),
                    "provenance_chain": prov_chain,
                    "responsible_ai_disclaimer": "Forensic relationship extracted from verified evidence. Not a probability of guilt."
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

    def compute_graph_analytics(
        self,
        actor: TokenPayload,
        case_id: str,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Slice 8D: Computes case-isolated forensic graph analytics covering all 9 algorithms.
        Enforces strict authorization: user must have READ_CASE_GRAPH on case_id.
        """
        self._verify_auth(
            actor=actor,
            action="READ_CASE_GRAPH",
            resource_id=f"GRAPH-{case_id}",
            target_case_id=case_id
        )

        # Retrieve case-isolated graph
        case_graph = self.get_case_graph(actor, case_id, demo=False)

        # Extract timestamps for communications in this case from parsed_repo observations
        temporal_timestamps: List[int] = []
        if self.parsed_repo:
            try:
                artifacts = self.parsed_repo.list_by_case(case_id)
                for art in artifacts:
                    for obs in art.observations:
                        obs_type_val = obs.observation_type.value if hasattr(obs.observation_type, "value") else str(obs.observation_type)
                        if obs_type_val in ["FORENSIC_COMMUNICATION", "FORENSIC_EMAIL_MESSAGE"]:
                            if isinstance(obs.value, dict):
                                ts = obs.value.get("date_time") or obs.value.get("datetime_sent") or obs.value.get("datetime_rcvd")
                                if isinstance(ts, (int, float)) and ts > 0:
                                    temporal_timestamps.append(int(ts))
            except Exception:
                pass

        from src.analytics.graph_analytics import NetworkGraphAnalytics
        analytics_engine = NetworkGraphAnalytics()
        return analytics_engine.compute_analytics(
            case_graph=case_graph,
            temporal_timestamps=temporal_timestamps,
            source_id=source_id,
            target_id=target_id,
            entity_id=entity_id
        )

