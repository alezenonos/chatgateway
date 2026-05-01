import uuid
import time
from typing import Optional, List
import jwt


class MockAuthProvider:
    def __init__(self, users: str, secret: str, token_expiry: int = 86400):
        self._users = [u.strip() for u in users.split(",")]
        self._secret = secret
        self._token_expiry = token_expiry

    def list_users(self) -> List[str]:
        return self._users

    def login(self, username: str) -> Optional[str]:
        if username not in self._users:
            return None

        now = int(time.time())
        payload = {
            "sub": str(uuid.uuid5(uuid.NAMESPACE_DNS, username)),
            "email": f"{username}@smithhoward.com",
            "name": username,
            "roles": ["user"],
            "iat": now,
            "exp": now + self._token_expiry,
            "iss": "mock-idp",
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")
