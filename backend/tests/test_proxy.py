"""Tests for LLM proxy module — verifies provider selection and message formatting."""
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from proxy.claude import _build_messages, stream_chat


def test_build_messages_text_only():
    messages = [{"role": "user", "content": "Hello", "file_content": None, "file_name": None}]
    result = _build_messages(messages)
    assert result == [{"role": "user", "content": "Hello"}]


def test_build_messages_with_file():
    messages = [{"role": "user", "content": "Analyze this", "file_content": "col1,col2\na,b", "file_name": "data.csv"}]
    result = _build_messages(messages)
    assert "[File: data.csv]" in result[0]["content"]
    assert "col1,col2" in result[0]["content"]


def test_build_messages_multiple():
    messages = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "Help me"},
    ]
    result = _build_messages(messages)
    assert len(result) == 3
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"
    assert result[2]["content"] == "Help me"


@patch("proxy.claude.settings")
@pytest.mark.asyncio
async def test_stream_chat_selects_anthropic(mock_settings):
    mock_settings.llm_provider = "anthropic"
    mock_settings.anthropic_api_key = "fake-key"
    mock_settings.claude_model = "claude-sonnet-4-20250514"

    with patch("proxy.claude._stream_anthropic") as mock_anthropic:
        async def fake():
            yield "hello"
        mock_anthropic.return_value = fake()

        chunks = []
        async for chunk in stream_chat([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        assert chunks == ["hello"]
        mock_anthropic.assert_called_once()


@patch("proxy.claude.settings")
@pytest.mark.asyncio
async def test_stream_chat_selects_openrouter(mock_settings):
    mock_settings.llm_provider = "openrouter"
    mock_settings.openrouter_api_key = "fake-key"
    mock_settings.openrouter_model = "google/gemma-3-4b-it:free"

    with patch("proxy.claude._stream_openrouter") as mock_openrouter:
        async def fake():
            yield "world"
        mock_openrouter.return_value = fake()

        chunks = []
        async for chunk in stream_chat([{"role": "user", "content": "hi"}]):
            chunks.append(chunk)
        assert chunks == ["world"]
        mock_openrouter.assert_called_once()
