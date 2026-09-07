"""
Audit Service for CRIMENET.
Logs all investigator actions, authorization decisions, and security events into a tamper-evident audit log.
"""

import time
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.integrity.provider import IntegrityProvider, LocalCryptoChainIntegrityProvider


class AuditEvent(BaseModel):
    event_id: str
    actor_id: str
    actor_role: str
    case_id: str
    action: str
    target_resource: str
    timestamp: float
    decision: str  # "ALLOW" or "DENY"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    previous_event_hash: str
    event_hash: str


class AuditService:
    def __init__(self, integrity_provider: Optional[IntegrityProvider] = None):
        self.integrity_provider = integrity_provider or LocalCryptoChainIntegrityProvider()
        self.audit_log: List[AuditEvent] = []

    def record_event(
        self,
        actor_id: str,
        actor_role: str,
        case_id: str,
        action: str,
        target_resource: str,
        decision: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        event_id = f"AUD-{uuid.uuid4().hex[:12].upper()}"
        timestamp = time.time()
        prev_hash = self.audit_log[-1].event_hash if self.audit_log else LocalCryptoChainIntegrityProvider.GENESIS_HASH

        raw_event_dict = {
            "event_id": event_id,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "case_id": case_id,
            "action": action,
            "target_resource": target_resource,
            "timestamp": timestamp,
            "decision": decision,
            "metadata": metadata or {}
        }

        event_hash = self.integrity_provider.calculate_event_hash(raw_event_dict, prev_hash)

        event = AuditEvent(
            event_id=event_id,
            actor_id=actor_id,
            actor_role=actor_role,
            case_id=case_id,
            action=action,
            target_resource=target_resource,
            timestamp=timestamp,
            decision=decision,
            metadata=metadata or {},
            previous_event_hash=prev_hash,
            event_hash=event_hash
        )

        self.audit_log.append(event)
        return event

    def get_events(self) -> List[AuditEvent]:
        return list(self.audit_log)

    def verify_integrity(self) -> bool:
        dict_events = [e.model_dump() for e in self.audit_log]
        return self.integrity_provider.verify_chain(dict_events)
