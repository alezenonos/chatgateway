import os
from pydantic_settings import BaseSettings

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    auth_provider: str = "mock"
    mock_users: str = "john.doe,jane.smith,admin"
    jwt_secret: str = "local-dev-secret-change-me"

    llm_provider: str = "openrouter"
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    openrouter_model: str = "liquid/lfm-2.5-1.2b-instruct:free"

    content_filter_path: str = os.path.join(PROJECT_ROOT, "config", "content-filter.yaml")

    class Config:
        env_file = os.path.join(PROJECT_ROOT, ".env")


settings = Settings()
