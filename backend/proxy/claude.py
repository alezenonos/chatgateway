from typing import AsyncGenerator
import json
import httpx
from config import settings


def _build_messages(messages: list) -> list:
    """Convert internal message format to API format."""
    api_messages = []
    for msg in messages:
        content_parts = []
        if msg.get("content"):
            content_parts.append(msg["content"])
        if msg.get("file_content"):
            content_parts.append(f"[File: {msg['file_name']}]\n{msg['file_content']}")
        api_messages.append({"role": msg["role"], "content": "\n".join(content_parts)})
    return api_messages


def get_model_display_name() -> str:
    if settings.llm_provider == "openrouter":
        model = settings.openrouter_model
        name = model.split("/")[-1].replace(":free", "").replace("-it", "").replace("-instruct", "")
        return name.replace("-", " ").title()
    return settings.claude_model.replace("claude-", "Claude ").split("-2025")[0].title()


async def stream_chat(messages: list, model: str = None) -> AsyncGenerator[str, None]:
    provider = settings.llm_provider

    if provider == "openrouter":
        async for chunk in _stream_openrouter(messages, model):
            yield chunk
    else:
        async for chunk in _stream_anthropic(messages, model):
            yield chunk


async def _stream_anthropic(messages: list, model: str = None) -> AsyncGenerator[str, None]:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    model = model or settings.claude_model

    claude_messages = []
    for msg in messages:
        content = []
        if msg.get("content"):
            content.append({"type": "text", "text": msg["content"]})
        if msg.get("file_content"):
            content.append({"type": "text", "text": f"[File: {msg['file_name']}]\n{msg['file_content']}"})
        claude_messages.append({"role": msg["role"], "content": content})

    with client.messages.stream(
        model=model,
        max_tokens=4096,
        messages=claude_messages,
    ) as stream:
        for text in stream.text_stream:
            yield text


async def _stream_openrouter(messages: list, model: str = None) -> AsyncGenerator[str, None]:
    model = model or settings.openrouter_model
    api_messages = _build_messages(messages)

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:3000",
                "X-Title": "Smith+Howard Chat",
            },
            json={
                "model": model,
                "messages": api_messages,
                "stream": True,
                "max_tokens": 4096,
            },
            timeout=60.0,
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                try:
                    err = json.loads(body)
                    msg = err.get("error", {}).get("message", f"API error {response.status_code}")
                except json.JSONDecodeError:
                    msg = f"API error {response.status_code}"
                yield f"[Error: {msg}]"
                return

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
