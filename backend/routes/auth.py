from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import settings
from auth.mock_provider import MockAuthProvider

router = APIRouter(prefix="/api/auth")

_provider = MockAuthProvider(users=settings.mock_users, secret=settings.jwt_secret)


class LoginRequest(BaseModel):
    username: str


@router.get("/users")
async def list_users():
    return {"users": _provider.list_users()}


@router.post("/login")
async def login(body: LoginRequest):
    token = _provider.login(body.username)
    if token is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return {"token": token}
