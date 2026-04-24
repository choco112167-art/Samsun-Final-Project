"""환경 변수 로드 (FastAPI 백엔드). .env와 프로세스 환경을 읽습니다."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str = ""
    supabase_anon_key: str = ""
    log_level: str = "info"
    cors_origins: str = "*"
    # GEMINI_API_KEY — 신조어 RAG(Gemini)에서 사용, 미설정 시 환경변수 직접 조회
    gemini_api_key: str = ""
    # Ollama HTTP 베이스 (예: http://127.0.0.1:11434) — 추천·로컬 임베딩과 동일 호스트
    ollama_base_url: str = "http://127.0.0.1:11434"

    def cors_origins_list(self) -> list[str]:
        raw = (self.cors_origins or "*").strip()
        if raw == "*":
            return ["*"]
        return [p.strip() for p in raw.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
