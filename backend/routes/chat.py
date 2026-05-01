from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from auth.middleware import decode_token
from filter.engine import ContentFilter
from proxy.claude import stream_chat
from config import settings

router = APIRouter(prefix="/api")

_filter = ContentFilter(settings.content_filter_path)


async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth_header[7:]
    payload = decode_token(token, settings.jwt_secret)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


class ChatMessage(BaseModel):
    role: str
    content: str
    file_content: Optional[str] = None
    file_name: Optional[str] = None


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None


@router.post("/chat")
async def chat(body: ChatRequest, user: dict = Depends(get_current_user)):
    last_message = body.messages[-1]
    if last_message.role == "user":
        result = _filter.scan_text(last_message.content)
        if result.blocked:
            raise HTTPException(status_code=403, detail={
                "error": "content_filtered",
                "message": result.message,
                "rule": result.rule,
            })
        if last_message.file_content:
            file_result = _filter.scan_text(last_message.file_content)
            if file_result.blocked:
                raise HTTPException(status_code=403, detail={
                    "error": "content_filtered",
                    "message": file_result.message,
                    "rule": file_result.rule,
                })

    messages_dicts = [m.model_dump() for m in body.messages]

    async def event_stream():
        async for chunk in stream_chat(messages_dicts, body.model):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
