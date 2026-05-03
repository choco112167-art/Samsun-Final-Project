"""환경 변수 로드 (FastAPI 백엔드). .env와 프로세스 환경을 읽습니다."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_anon_key: str = ""
    log_level: str = "info"
    cors_origins: str = (
        "http://localhost:5173,"
        "https://samsun-newsapp.apps.tossmini.com,"
        "https://samsun-newsapp.private-apps.tossmini.com"
    )
    llm_provider: str = "openrouter"
    embedding_provider: str = "openrouter"
    model_name: str = "qwen3.5:4b"
    ollama_base_url: str = "http://localhost:11434"
    custom_model_mode: str = "off"
    custom_model_server_url: str = ""
    factcheck_enabled: bool = True

    @property
    def effective_supabase_key(self) -> str:
        return self.supabase_key or self.supabase_anon_key

    def cors_origins_list(self) -> list[str]:
        raw = (self.cors_origins or "*").strip()
        if raw == "*":
            return ["*"]
        return [p.strip() for p in raw.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
