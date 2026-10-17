from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ folder (config.py lives in backend/app/)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """All configuration comes from environment variables / backend/.env."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    app_env: str = "dev"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Active provider: gemini | mistral | cloudflare | ollama
    vlm_provider: str = "gemini"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_fallback_model: str = ""

    # Mistral
    mistral_api_key: str = ""
    mistral_model: str = ""

    # Cloudflare Workers AI
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    cloudflare_model: str = ""

    # Ollama (local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""

    # Speech to text
    whisper_model_size: str = "small"
    whisper_compute_type: str = "int8"
    whisper_beam_size: int = 1
    whisper_cpu_threads: int = 0  # 0 = library default

    # Text to speech
    tts_voice_en: str = "en-US-AriaNeural"
    tts_voice_fr: str = "fr-FR-DeniseNeural"
    tts_voice_ar: str = "ar-MA-MounaNeural"
    tts_timeout_seconds: float = 20.0

    # Images and requests
    max_image_side: int = 1024
    max_upload_mb: int = 10
    vlm_timeout_seconds: float = 40.0
    vlm_max_retries: int = 3

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
