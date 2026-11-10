"""edge-tts (free, no key). Needs internet access to Microsoft's speech service."""
from __future__ import annotations

from ..config import get_settings
from .base import ProviderError, TTSProvider, TTSResult


class EdgeTTS(TTSProvider):
    name, label = "edge", "Edge TTS"

    def voice_for(self, language: str) -> str:
        s = get_settings()
        return {"te": s.edge_voice_te, "hi": s.edge_voice_hi, "en": s.edge_voice_en}.get(language, s.edge_voice_te)

    async def synthesize(self, text: str, language: str) -> TTSResult:
        import edge_tts

        audio = bytearray()
        try:
            async for chunk in edge_tts.Communicate(text, self.voice_for(language)).stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"edge-tts failed: {e!r}"[:200]) from e
        if not audio:
            raise ProviderError("edge-tts returned no audio")
        return TTSResult(audio=bytes(audio), mime="audio/mpeg")
