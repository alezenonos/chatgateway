import jwt
from auth.mock_provider import MockAuthProvider
from auth.middleware import decode_token


SECRET = "test-secret"


def test_mock_provider_lists_users():
    provider = MockAuthProvider(users="alice,bob,charlie", secret=SECRET)
    assert provider.list_users() == ["alice", "bob", "charlie"]


def test_mock_provider_creates_valid_jwt():
    provider = MockAuthProvider(users="alice,bob", secret=SECRET)
    token = provider.login("alice")
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    assert payload["email"] == "alice@smithhoward.com"
    assert payload["name"] == "alice"
    assert payload["roles"] == ["user"]
    assert "sub" in payload
    assert "exp" in payload


def test_mock_provider_rejects_unknown_user():
    provider = MockAuthProvider(users="alice,bob", secret=SECRET)
    token = provider.login("hacker")
    assert token is None


def test_decode_token_valid():
    provider = MockAuthProvider(users="alice", secret=SECRET)
    token = provider.login("alice")
    payload = decode_token(token, SECRET)
    assert payload["email"] == "alice@smithhoward.com"


def test_decode_token_invalid():
    payload = decode_token("invalid.token.here", SECRET)
    assert payload is None


def test_decode_token_expired():
    import time
    provider = MockAuthProvider(users="alice", secret=SECRET, token_expiry=-1)
    token = provider.login("alice")
    time.sleep(0.1)
    payload = decode_token(token, SECRET)
    assert payload is None


# --- Regression tests: auth route integration ---

def test_auth_users_endpoint():
    """Auth users endpoint should list configured mock users."""
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    response = client.get("/api/auth/users")
    assert response.status_code == 200
    assert "users" in response.json()
    assert len(response.json()["users"]) > 0


def test_auth_login_valid_user():
    """Login with a valid mock user should return a token."""
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"username": "john.doe"})
    assert response.status_code == 200
    assert "token" in response.json()
    assert len(response.json()["token"]) > 0


def test_auth_login_invalid_user():
    """Login with unknown user should return 401."""
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"username": "hacker"})
    assert response.status_code == 401
