from fastapi import APIRouter
from proxy.claude import get_model_display_name
from config import settings

router = APIRouter()


@router.get("/api/health")
async def health():
    return {"status": "ok"}


@router.get("/api/config")
async def get_config():
    return {
        "model": get_model_display_name(),
        "provider": settings.llm_provider,
    }
