"""Gemini adapters via google-genai. Model names come from .env (run scripts/list_gemini_models.py). NOT verified live."""
from __future__ import annotations

from .. import ledger
from ..config import get_settings
from .base import (
    EmbeddingProvider,
    LLMProvider,
    ProviderError,
    ProviderUnavailable,
    STTProvider,
    STTResult,
    VisionProvider,
)

_client = None


def client():
    global _client
    s = get_settings()
    if not s.gemini_api_key:
        raise ProviderUnavailable("GEMINI_API_KEY empty")
    if _client is None:
        from google import genai

        _client = genai.Client(api_key=s.gemini_api_key)
    return _client


def _types():
    from google.genai import types

    return types


async def _generate(model: str, contents, system: str | None = None, json_mode: bool = False) -> str:
    if not model:
        raise ProviderUnavailable("Gemini model name empty in .env")
    types = _types()
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        temperature=0.2,
        response_mime_type="application/json" if json_mode else None,
    )
    try:
        resp = await client().aio.models.generate_content(model=model, contents=contents, config=cfg)
    except ProviderUnavailable:
        raise
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "API key" in msg or "PERMISSION" in msg or "401" in msg or "403" in msg:
            raise ProviderUnavailable(msg[:150]) from e
        raise ProviderError(msg[:200]) from e
    return resp.text or ""


class GeminiLLM(LLMProvider):
    name, label = "gemini", "Gemini"

    def available(self) -> bool:
        s = get_settings()
        return bool(s.gemini_api_key and s.gemini_llm_model)

    async def complete_json(self, system: str, user: str, purpose: str) -> str:
        text = await _generate(get_settings().gemini_llm_model, user, system=system, json_mode=True)
        ledger.record("gemini", "llm", "tokens", (len(system) + len(user) + len(text)) / 4, purpose)
        return text


class GeminiVision(VisionProvider):
    name, label = "gemini", "Gemini Vision"

    def available(self) -> bool:
        s = get_settings()
        return bool(s.gemini_api_key and s.gemini_vision_model)

    async def diagnose(self, data: bytes, mime: str, filename: str, prompt: str) -> str:
        types = _types()
        part = types.Part.from_bytes(data=data, mime_type=mime)
        text = await _generate(get_settings().gemini_vision_model, [part, prompt], json_mode=True)
        ledger.record("gemini", "vision", "files", 1, mime)
        return text


class GeminiSTT(STTProvider):
    name, label = "gemini", "Gemini STT"

    def available(self) -> bool:
        s = get_settings()
        return bool(s.gemini_api_key and s.gemini_stt_model)

    async def transcribe(self, wav: bytes, language: str, session_id: str = "") -> STTResult:
        types = _types()
        part = types.Part.from_bytes(data=wav, mime_type="audio/wav")
        text = await _generate(
            get_settings().gemini_stt_model,
            [part, "Transcribe exactly in the original script, output only the transcript."],
        )
        ledger.record("gemini", "stt", "files", 1)
        if not text.strip():
            raise ProviderError("empty transcript")
        return STTResult(transcript=text.strip(), language=None)


class GeminiEmbedder(EmbeddingProvider):
    name, label = "gemini", "Gemini embeddings"

    @property
    def model_name(self) -> str:  # type: ignore[override]
        return f"gemini:{get_settings().gemini_embed_model}"

    def available(self) -> bool:
        s = get_settings()
        return bool(s.gemini_api_key and s.gemini_embed_model)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.available():
            raise ProviderUnavailable("gemini embeddings not configured")
        out: list[list[float]] = []
        try:
            for i in range(0, len(texts), 50):
                resp = await client().aio.models.embed_content(model=get_settings().gemini_embed_model, contents=texts[i : i + 50])
                out.extend([list(e.values) for e in resp.embeddings])
        except ProviderUnavailable:
            raise
        except Exception as e:  # noqa: BLE001
            raise ProviderError(str(e)[:200]) from e
        return out
