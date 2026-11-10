"""Offline mock providers so the whole demo runs with no keys and no network."""
from __future__ import annotations

import io
import json
import math
import struct
import wave

from .base import LLMProvider, STTProvider, STTResult, TTSProvider, TTSResult, VisionProvider

FILENAME_HINTS = [
    ("needle", "needle_breaking"),
    ("nest", "thread_nesting"),
    ("tangle", "thread_nesting"),
    ("outline", "design_misalignment"),
    ("align", "design_misalignment"),
    ("gap", "design_misalignment"),
    ("thread", "upper_thread_breaking"),
]


class MockLLM(LLMProvider):
    name, label = "mock", "Mock LLM (template)"

    async def complete_json(self, system: str, user: str, purpose: str) -> str:
        ctx = json.loads(user)
        if purpose == "summary":
            return json.dumps({"summary": ctx.get("template_summary", "")}, ensure_ascii=False)
        # answer: reproduce the deterministic template (exercises the validation path)
        return json.dumps(ctx["template_answer"], ensure_ascii=False)


class MockVision(VisionProvider):
    name, label = "mock", "Mock vision (filename hints)"

    async def diagnose(self, data: bytes, mime: str, filename: str, prompt: str) -> str:
        fn = (filename or "").lower()
        for hint, fault in FILENAME_HINTS:
            if hint in fn:
                return json.dumps({"fault_id": fault, "confidence": 0.85, "visible_evidence": f"mock: filename contains '{hint}'"})
        return json.dumps({"fault_id": "unknown", "confidence": 0.2, "visible_evidence": "mock: no filename hint"})


class MockSTT(STTProvider):
    """Placeholder for offline demos; never invents a transcript."""

    name, label = "mock", "Mock STT (no transcription)"

    async def transcribe(self, wav: bytes, language: str, session_id: str = "") -> STTResult:
        return STTResult(transcript="", language=language if language in ("te", "hi", "en") else None)


def tone_wav(seconds: float = 0.6, freq: float = 660.0, rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        n = int(seconds * rate)
        frames = b"".join(
            struct.pack("<h", int(6000 * math.sin(2 * math.pi * freq * i / rate) * min(1, (n - i) / 2000)))
            for i in range(n)
        )
        w.writeframes(frames)
    return buf.getvalue()


class MockTTS(TTSProvider):
    """Returns a short chime; the browser then reads the text with its own speech engine."""

    name, label = "mock", "Mock TTS (browser voice)"

    async def synthesize(self, text: str, language: str) -> TTSResult:
        return TTSResult(audio=tone_wav(), mime="audio/wav")
