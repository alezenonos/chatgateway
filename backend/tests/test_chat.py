from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from auth.mock_provider import MockAuthProvider

client = TestClient(app)
_provider = MockAuthProvider(users="testuser", secret="local-dev-secret-change-me")


def _auth_header():
    token = _provider.login("testuser")
    return {"Authorization": f"Bearer {token}"}


def test_chat_requires_auth():
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 401


def test_chat_blocks_ni_number():
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "My NI is AB123456C"}]},
        headers=_auth_header(),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "uk_national_insurance"


def test_chat_blocks_credit_card():
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Card 4111111111111111"}]},
        headers=_auth_header(),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "credit_card"


@patch("routes.chat.stream_chat")
def test_chat_streams_response(mock_stream):
    async def fake_stream(messages, model):
        yield "Hello"
        yield " World"

    mock_stream.return_value = fake_stream([], None)
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Hi there"}]},
        headers=_auth_header(),
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "data: Hello" in body
    assert "data: [DONE]" in body


# --- Regression tests: auth edge cases ---

def test_chat_rejects_expired_token():
    """Expired JWT should return 401."""
    expired_provider = MockAuthProvider(users="testuser", secret="local-dev-secret-change-me", token_expiry=-1)
    import time
    token = expired_provider.login("testuser")
    time.sleep(0.1)
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_chat_rejects_malformed_auth_header():
    """Auth header without 'Bearer ' prefix should fail."""
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": "NotBearer some-token"},
    )
    assert response.status_code == 401


def test_chat_rejects_wrong_secret_token():
    """Token signed with wrong secret should fail."""
    wrong_provider = MockAuthProvider(users="testuser", secret="wrong-secret")
    token = wrong_provider.login("testuser")
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


# --- Regression tests: content filter in chat ---

def test_chat_blocks_bank_account():
    """Bank account numbers in chat should be blocked."""
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Pay to 12-34-56 12345678"}]},
        headers=_auth_header(),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["rule"] == "uk_bank_account"


def test_chat_allows_clean_message():
    """Clean message should not be blocked (returns 200 even if Claude fails)."""
    # We mock stream_chat since there's no API key in CI
    with patch("routes.chat.stream_chat") as mock_stream:
        async def fake_stream(messages, model):
            yield "OK"
        mock_stream.return_value = fake_stream([], None)
        response = client.post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "What is our Q3 revenue?"}]},
            headers=_auth_header(),
        )
        assert response.status_code == 200


def test_chat_filter_error_response_format():
    """Content filter error should return structured JSON with error, message, rule."""
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "NI AB123456C"}]},
        headers=_auth_header(),
    )
    detail = response.json()["detail"]
    assert "error" in detail
    assert "message" in detail
    assert "rule" in detail
    assert detail["error"] == "content_filtered"


# --- Regression tests: health endpoint ---

def test_health_endpoint():
    """Health check should always return 200."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_no_auth_required():
    """Health endpoint should not require authentication."""
    response = client.get("/api/health")
    assert response.status_code == 200
