"""
Authentication Service for CRIMENET.
Handles password hashing, token issuance, token verification, and user lookup.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Dict, Optional, List

from src.auth.models import (
    User, UserRole, CourtLevel, JudicialContext, UserPublic, TokenPayload
)


class AuthService:
    def __init__(self, secret_key: str = "CRIMENET_SECRET_KEY_FOR_LOCAL_SERVERS_2026_CHANGE_IN_PROD"):
        self.secret_key = secret_key.encode('utf-8')
        self._user_db: Dict[str, User] = {}
        self._seed_default_users()

    def _hash_password(self, password: str, salt: Optional[bytes] = None) -> str:
        if salt is None:
            salt = secrets.token_bytes(16)
        # PBKDF2-HMAC-SHA256 with 100,000 iterations
        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations=100000
        )
        return f"pbkdf2:sha256:100000${salt.hex()}${pwd_hash.hex()}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            parts = stored_hash.split('$')
            if len(parts) != 3:
                return False
            alg_info, salt_hex, pwd_hash_hex = parts
            alg_name, hash_name, iterations = alg_info.split(':')
            salt = bytes.fromhex(salt_hex)
            expected_hash = bytes.fromhex(pwd_hash_hex)
            actual_hash = hashlib.pbkdf2_hmac(
                hash_name,
                password.encode('utf-8'),
                salt,
                int(iterations)
            )
            return hmac.compare_digest(actual_hash, expected_hash)
        except Exception:
            return False

    def create_access_token(self, user: User, expires_in_seconds: int = 3600) -> str:
        now = int(time.time())
        exp = now + expires_in_seconds
        jti = secrets.token_hex(16)
        
        jud_context_dict = user.judicial_context.model_dump() if user.judicial_context else None

        payload = {
            "sub": user.user_id,
            "username": user.username,
            "role": user.role.value,
            "judicial_context": jud_context_dict,
            "exp": exp,
            "jti": jti
        }

        header = {"alg": "HS256", "typ": "JWT"}
        encoded_header = base64.urlsafe_b64encode(json.dumps(header).encode('utf-8')).decode('utf-8').rstrip('=')
        encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8').rstrip('=')

        signature_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')
        signature = hmac.new(self.secret_key, signature_input, hashlib.sha256).digest()
        encoded_signature = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')

        return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

    def verify_access_token(self, token: str) -> Optional[TokenPayload]:
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            encoded_header, encoded_payload, encoded_signature = parts
            signature_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')

            # Verify signature
            expected_sig = hmac.new(self.secret_key, signature_input, hashlib.sha256).digest()
            actual_sig = base64.urlsafe_b64decode(encoded_signature + '==' * (-len(encoded_signature) % 4))
            
            if not hmac.compare_digest(actual_sig, expected_sig):
                return None

            # Decode payload
            payload_json = base64.urlsafe_b64decode(encoded_payload + '==' * (-len(encoded_payload) % 4)).decode('utf-8')
            payload_dict = json.loads(payload_json)

            # Check expiration
            if payload_dict.get('exp', 0) < time.time():
                return None

            # Parse role & judicial context
            role = UserRole(payload_dict['role'])
            jud_context = JudicialContext(**payload_dict['judicial_context']) if payload_dict.get('judicial_context') else None

            return TokenPayload(
                sub=payload_dict['sub'],
                username=payload_dict['username'],
                role=role,
                judicial_context=jud_context,
                exp=payload_dict['exp'],
                jti=payload_dict['jti']
            )
        except Exception:
            return None

    def _sync_user_cases(self, user: User):
        if not user or "*" in user.authorized_case_ids:
            return
        try:
            import sqlite3
            import os
            import json
            db_path = getattr(self, "db_path", "DATA/cases.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_case_authorizations (
                        user_id TEXT NOT NULL,
                        case_id TEXT NOT NULL,
                        granted_at REAL NOT NULL,
                        PRIMARY KEY (user_id, case_id)
                    );
                """)
                cursor = conn.cursor()
                # 1. Check explicit grants
                cursor.execute("SELECT case_id FROM user_case_authorizations WHERE user_id = ?", (user.user_id,))
                explicit_rows = cursor.fetchall()
                for (cid,) in explicit_rows:
                    if cid not in user.authorized_case_ids:
                        user.authorized_case_ids.append(cid)

                # 2. Check cases table
                cursor.execute("SELECT case_id, created_by, assigned_investigators_json FROM cases")
                rows = cursor.fetchall()
                conn.close()
                for cid, creator, assigned_json in rows:
                    if cid not in user.authorized_case_ids:
                        if creator in [user.user_id, user.username]:
                            user.authorized_case_ids.append(cid)
                        elif assigned_json:
                            try:
                                assigned = json.loads(assigned_json)
                                if isinstance(assigned, list) and (user.user_id in assigned or user.username in assigned):
                                    user.authorized_case_ids.append(cid)
                            except Exception:
                                pass
        except Exception:
            pass

    def authorize_user_for_case(self, user_id: str, case_id: str):
        user = self._user_db.get(user_id)
        if user and case_id not in user.authorized_case_ids:
            user.authorized_case_ids.append(case_id)
        try:
            import sqlite3
            import os
            import time
            db_path = getattr(self, "db_path", "DATA/cases.db")
            if os.path.exists(os.path.dirname(db_path)) or "/" not in db_path:
                conn = sqlite3.connect(db_path)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_case_authorizations (
                        user_id TEXT NOT NULL,
                        case_id TEXT NOT NULL,
                        granted_at REAL NOT NULL,
                        PRIMARY KEY (user_id, case_id)
                    );
                """)
                conn.execute("""
                    INSERT OR REPLACE INTO user_case_authorizations (user_id, case_id, granted_at)
                    VALUES (?, ?, ?)
                """, (user_id, case_id, time.time()))
                conn.commit()
                conn.close()
        except Exception:
            pass

    def revoke_user_case(self, user_id: str, case_id: str):
        user = self._user_db.get(user_id)
        if user and case_id in user.authorized_case_ids:
            user.authorized_case_ids.remove(case_id)
        try:
            import sqlite3
            import os
            db_path = getattr(self, "db_path", "DATA/cases.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.execute("DELETE FROM user_case_authorizations WHERE user_id = ? AND case_id = ?", (user_id, case_id))
                conn.commit()
                conn.close()
        except Exception:
            pass

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        user = self._user_db.get(user_id)
        if user:
            self._sync_user_cases(user)
        return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        for user in self._user_db.values():
            if user.username == username:
                self._sync_user_cases(user)
                return user
        return None

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = self.get_user_by_username(username)
        if not user or not user.is_active:
            return None
        if self.verify_password(password, user.password_hash):
            return user
        return None

    def get_judges(self) -> List[User]:
        return [
            u for u in self._user_db.values()
            if u.role == UserRole.COURT_JUDGE and u.is_active
        ]

    def _seed_default_users(self):
        # Default test seed users representing all roles & scopes
        seed_users = [
            User(
                user_id="USER-OFFICER-001",
                username="officer1",
                password_hash=self._hash_password("OfficerPass123!"),
                role=UserRole.INVESTIGATION_OFFICER,
                authorized_case_ids=["CASE-2026-BBDD", "CASE-2026-001"]
            ),
            User(
                user_id="USER-OFFICER-002",
                username="officer2",
                password_hash=self._hash_password("OfficerPass456!"),
                role=UserRole.INVESTIGATION_OFFICER,
                authorized_case_ids=["CASE-2026-002"]
            ),
            User(
                user_id="USER-BOSS-001",
                username="boss1",
                password_hash=self._hash_password("HigherAuthPass789!"),
                role=UserRole.HIGHER_AUTHORITY,
                authorized_case_ids=["CASE-2026-BBDD", "CASE-2026-001", "CASE-2026-002", "CASE-2026-003"]
            ),
            User(
                user_id="USER-JUDGE-001",
                username="judge_specific",
                password_hash=self._hash_password("JudgePass001!"),
                role=UserRole.COURT_JUDGE,
                judicial_context=JudicialContext(
                    court_level=CourtLevel.SPECIFIC_COURT,
                    assigned_court_id="COURT-DL-001",
                    jurisdiction_code="DELHI_DISTRICT"
                ),
                authorized_case_ids=["CASE-2026-BBDD", "CASE-2026-001"]
            ),
            User(
                user_id="USER-JUDGE-002",
                username="judge_high",
                password_hash=self._hash_password("JudgePass002!"),
                role=UserRole.COURT_JUDGE,
                judicial_context=JudicialContext(
                    court_level=CourtLevel.HIGH_COURT,
                    jurisdiction_code="DELHI_STATE"
                ),
                authorized_case_ids=["CASE-2026-001", "CASE-2026-002"]
            ),
            User(
                user_id="USER-JUDGE-003",
                username="judge_supreme",
                password_hash=self._hash_password("JudgePass003!"),
                role=UserRole.COURT_JUDGE,
                judicial_context=JudicialContext(
                    court_level=CourtLevel.SUPREME_COURT,
                    jurisdiction_code="NATIONAL"
                ),
                authorized_case_ids=["*"]
            ),
        ]
        for u in seed_users:
            self._user_db[u.user_id] = u
