"""All configuration comes from environment variables / .env (never from code edits)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")

    # provider selection
    llm_provider: str = "mock"
    llm_fallback: str = "gemini"
    stt_provider: str = "mock"
    stt_fallback: str = "gemini"
    tts_provider: str = "gnani"
    tts_fallback: str = "edge"
    vision_provider: str = "gemini"
    embed_provider: str = "hash"

    # gnani
    gnani_api_key: str = ""
    gnani_base_url: str = "https://api.vachana.ai"
    gnani_stt_model: str = "prisma-v3.0"
    gnani_tts_model: str = "timbre-v3.0"
    gnani_tts_voice_te: str = "Shivani"
    gnani_tts_voice_hi: str = "Shivani"
    gnani_tts_voice_en: str = "Shivani"
    gnani_llm_base_url: str = ""
    gnani_llm_api_key: str = ""
    gnani_llm_model: str = ""
    gnani_stt_credits_per_sec: float = 0.0
    gnani_tts_credits_per_1k_chars: float = 0.0
    gnani_llm_credits_per_1k_tokens: float = 0.0
    gnani_credit_budget: float = 5000.0

    # gemini
    gemini_api_key: str = ""
    gemini_llm_model: str = ""
    gemini_vision_model: str = ""
    gemini_embed_model: str = ""
    gemini_stt_model: str = ""

    # edge-tts voices
    edge_voice_te: str = "te-IN-ShrutiNeural"
    edge_voice_hi: str = "hi-IN-SwaraNeural"
    edge_voice_en: str = "en-IN-NeerjaNeural"

    # app
    admin_token: str = "change-me"
    database_url: str = f"sqlite:///{(DATA / 'app.db').as_posix()}"
    allowed_origins: str = "http://localhost:8000,http://localhost:5173"
    confidence_threshold_hash: float = 0.32
    confidence_threshold_gemini: float = 0.55
    vision_min_confidence: float = 0.6
    provider_timeout_s: float = 25.0
    rate_limit_per_min: int = 30

    # upload limits
    max_audio_mb: float = 2.0
    max_audio_seconds: float = 30.0
    max_image_mb: float = 5.0
    max_video_mb: float = 15.0
    max_video_seconds: float = 20.0
    max_text_chars: int = 1000

    @property
    def llm_key_gnani(self) -> str:
        return self.gnani_llm_api_key or self.gnani_api_key

    def threshold_for(self, embed_model: str) -> float:
        return self.confidence_threshold_gemini if embed_model.startswith("gemini") else self.confidence_threshold_hash


@lru_cache
def get_settings() -> Settings:
    return Settings()
