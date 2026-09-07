"""
IntegrityProvider Abstraction and Cryptographic Hash-Chained Implementation for CRIMENET.
Allows pluggable local cryptographic hash anchoring today and seamless blockchain anchoring in future.
"""

from abc import ABC, abstractmethod
import hashlib
import json
from typing import List, Dict, Any


class IntegrityProvider(ABC):
    @abstractmethod
    def calculate_event_hash(self, event_data: Dict[str, Any], previous_hash: str) -> str:
        """Calculates a cryptographic hash for an event given its data and previous event hash."""
        pass

    @abstractmethod
    def verify_chain(self, audit_events: List[Dict[str, Any]]) -> bool:
        """Verifies the unbroken cryptographic hash chain of audit events."""
        pass


class LocalCryptoChainIntegrityProvider(IntegrityProvider):
    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def _canonical_json(self, data: Dict[str, Any]) -> str:
        # Exclude hash fields if present inside data dictionary
        clean_data = {k: v for k, v in data.items() if k not in ["event_hash", "previous_event_hash"]}
        return json.dumps(clean_data, sort_keys=True, separators=(',', ':'))

    def calculate_event_hash(self, event_data: Dict[str, Any], previous_hash: str) -> str:
        canonical_str = self._canonical_json(event_data)
        payload = f"{previous_hash}:{canonical_str}".encode('utf-8')
        return hashlib.sha256(payload).hexdigest()

    def verify_chain(self, audit_events: List[Dict[str, Any]]) -> bool:
        if not audit_events:
            return True

        current_prev_hash = self.GENESIS_HASH

        for idx, event in enumerate(audit_events):
            recorded_prev_hash = event.get("previous_event_hash")
            recorded_event_hash = event.get("event_hash")

            if recorded_prev_hash != current_prev_hash:
                return False

            expected_hash = self.calculate_event_hash(event, recorded_prev_hash)
            if recorded_event_hash != expected_hash:
                return False

            current_prev_hash = recorded_event_hash

        return True
