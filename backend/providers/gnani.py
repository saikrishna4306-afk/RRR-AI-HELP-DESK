"""Gnani (Vachana) adapters over plain httpx. Field names follow docs.gnani.ai. NOT verified live."""
from __future__ import annotations

import io
import json
import wave

import httpx

from .. import ledger
from ..config import get_settings
from .base import LLMProvider, ProviderError, ProviderUnavailable, STTProvider, STTResult, TTSProvider, TTSResult

LANG_CODES = {"te": "te-IN", "hi": "hi-IN", "en": "en-IN"}


def wav_seconds(data: bytes) -> float:
    try:
        with wave.open(io.BytesIO(data)) as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:  # noqa: BLE001
        return 0.0


def _raise_for(r: httpx.Response) -> None:
    if r.status_code in (401, 403):
        raise ProviderUnavailable(f"auth failed {r.status_code}")
    if r.status_code >= 400:
        raise ProviderError(f"HTTP {r.status_code}: {r.text[:200]}")


class _GnaniBase:
    def available(self) -> bool:
        s = get_settings()
        return bool(s.gnani_api_key) and ledger.gnani_budget_ok()

    @property
    def headers(self) -> dict:
        return {"X-API-Key-ID": get_settings().gnani_api_key}


class GnaniSTT(_GnaniBase, STTProvider):
    name, label = "gnani", "Gnani Prisma"

    async def transcribe(self, wav: bytes, language: str, session_id: str = "") -> STTResult:
        s = get_settings()
        code = LANG_CODES.get(language, "indic-auto" if s.gnani_stt_model == "prisma-v3.0" else "te-IN")
        files = {"audio_file": ("audio.wav", wav, "audio/wav")}
        data = {"model": s.gnani_stt_model, "language_code": code}
        async with httpx.AsyncClient(timeout=s.provider_timeout_s) as c:
            r = await c.post(f"{s.gnani_base_url}/stt/v3", headers=self.headers, files=files, data=data)
        _raise_for(r)
        body = r.json()
        if not body.get("success", True):
            raise ProviderError(f"gnani stt unsuccessful: {str(body)[:200]}")
        ledger.record("gnani", "stt", "audio_sec", wav_seconds(wav), body.get("request_id", ""))
        det = (body.get("detected_language_code") or code or "").split("-")[0] or None
        return STTResult(transcript=(body.get("transcript") or "").strip(), language=det if det in LANG_CODES else None)


class GnaniTTS(_GnaniBase, TTSProvider):
    name, label = "gnani", "Gnani Timbre"

    def voice_for(self, language: str) -> str:
        s = get_settings()
        return {"te": s.gnani_tts_voice_te, "hi": s.gnani_tts_voice_hi, "en": s.gnani_tts_voice_en}.get(language, "")

    async def synthesize(self, text: str, language: str) -> TTSResult:
        s = get_settings()
        voice = self.voice_for(language)
        if not voice:
            raise ProviderUnavailable(f"no Gnani voice set for {language}")
        payload = {
            "text": text,
            "voice": voice,
            "model": s.gnani_tts_model,
            "language": LANG_CODES.get(language, "te-IN"),
            "speed": 1.0,
            "audio_config": {"sample_rate": 48000, "num_channels": 1, "sample_width": 2, "encoding": "linear_pcm", "container": "wav"},
        }
        async with httpx.AsyncClient(timeout=s.provider_timeout_s) as c:
            r = await c.post(f"{s.gnani_base_url}/api/v1/tts/inference", headers=self.headers, json=payload)
        _raise_for(r)
        if not r.content or "json" in r.headers.get("content-type", ""):
            raise ProviderError(f"gnani tts returned no audio: {r.text[:200]}")
        ledger.record("gnani", "tts", "chars", len(text))
        return TTSResult(audio=r.content, mime="audio/wav")


class GnaniLLM(_GnaniBase, LLMProvider):
    """OpenAI-compatible chat completions; endpoint/model come from .env."""

    name, label = "gnani", "Gnani LLM"

    def available(self) -> bool:
        s = get_settings()
        return bool(s.gnani_llm_base_url and s.gnani_llm_model and s.llm_key_gnani) and ledger.gnani_budget_ok()

    async def complete_json(self, system: str, user: str, purpose: str) -> str:
        s = get_settings()
        key = s.llm_key_gnani
        headers = {"Authorization": f"Bearer {key}", "X-API-Key-ID": key}
        payload = {
            "model": s.gnani_llm_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
        }
        url = s.gnani_llm_base_url.rstrip("/") + "/chat/completions"
        async with httpx.AsyncClient(timeout=s.provider_timeout_s) as c:
            r = await c.post(url, headers=headers, json=payload)
        _raise_for(r)
        body = r.json()
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ProviderError(f"unexpected LLM body: {json.dumps(body)[:200]}") from e
        tokens = (body.get("usage") or {}).get("total_tokens") or (len(system) + len(user) + len(text)) / 4
        ledger.record("gnani", "llm", "tokens", float(tokens), purpose)
        return text
