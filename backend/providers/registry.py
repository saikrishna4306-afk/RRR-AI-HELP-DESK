"""Builds provider chains from .env: primary -> fallback -> mock."""
from __future__ import annotations

from ..config import get_settings
from .base import Chain, Provider
from .edge import EdgeTTS
from .gemini import GeminiEmbedder, GeminiLLM, GeminiSTT, GeminiVision
from .gnani import GnaniLLM, GnaniSTT, GnaniTTS
from .mock import MockLLM, MockSTT, MockTTS, MockVision

FACTORIES: dict[str, dict[str, type[Provider]]] = {
    "llm": {"gnani": GnaniLLM, "gemini": GeminiLLM, "mock": MockLLM},
    "stt": {"gnani": GnaniSTT, "gemini": GeminiSTT, "mock": MockSTT},
    "tts": {"gnani": GnaniTTS, "edge": EdgeTTS, "mock": MockTTS},
    "vision": {"gemini": GeminiVision, "mock": MockVision},
}


def chain(service: str, override: list[Provider] | None = None) -> Chain:
    s = get_settings()
    if override is not None:
        return Chain(service, override, timeout_s=s.provider_timeout_s)
    names = {
        "llm": [s.llm_provider, s.llm_fallback],
        "stt": [s.stt_provider, s.stt_fallback],
        "tts": [s.tts_provider, s.tts_fallback],
        "vision": [s.vision_provider],
    }[service] + ["mock"]
    seen, providers = set(), []
    for n in names:
        n = (n or "").strip().lower()
        if n in FACTORIES[service] and n not in seen:
            seen.add(n)
            providers.append(FACTORIES[service][n]())
    return Chain(service, providers, timeout_s=s.provider_timeout_s)


def embedder():
    s = get_settings()
    return GeminiEmbedder() if s.embed_provider.lower() == "gemini" else None


def status() -> dict:
    out = {}
    for svc in ("llm", "stt", "tts", "vision"):
        out[svc] = [{"provider": p.name, "label": p.label, "configured": p.available()} for p in chain(svc).providers]
    g = GeminiEmbedder()
    out["embed"] = [{"provider": "gemini", "configured": g.available()}, {"provider": "hash", "configured": True}]
    return out
