"""Calls Gnani STT, TTS and LLM once each with your .env and prints status codes / bodies.
Usage:  python scripts/smoke_gnani.py   (uses about a few credits)"""
from __future__ import annotations

import io
import math
import struct
import sys
import wave
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.config import get_settings  # noqa: E402


def tone(seconds=1.5, rate=16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(int(seconds * rate))))
    return buf.getvalue()


def show(name: str, r: httpx.Response, binary: bool = False) -> None:
    ok = r.status_code < 400
    print(f"\n[{name}] HTTP {r.status_code} {'OK' if ok else 'FAILED'}  content-type={r.headers.get('content-type')}")
    if binary and ok:
        print(f"  received {len(r.content)} bytes of audio")
    else:
        print("  body:", r.text[:800])


def main() -> None:
    s = get_settings()
    if not s.gnani_api_key:
        sys.exit("GNANI_API_KEY is empty in .env")
    h = {"X-API-Key-ID": s.gnani_api_key}
    sample = Path(__file__).resolve().parent.parent / "eval" / "audio" / "sample_te.wav"
    audio = sample.read_bytes() if sample.exists() else tone()
    with httpx.Client(timeout=40) as c:
        r = c.post(f"{s.gnani_base_url}/stt/v3", headers=h, files={"audio_file": ("a.wav", audio, "audio/wav")},
                   data={"model": s.gnani_stt_model, "language_code": "te-IN"})
        show("STT /stt/v3", r)
        voice = s.gnani_tts_voice_te or s.gnani_tts_voice_hi
        payload = {"text": "నమస్కారం, ఇది ఒక పరీక్ష." if s.gnani_tts_voice_te else "नमस्ते, यह एक परीक्षण है।", "voice": voice,
                   "model": s.gnani_tts_model, "language": "te-IN" if s.gnani_tts_voice_te else "hi-IN", "speed": 1.0,
                   "audio_config": {"sample_rate": 48000, "num_channels": 1, "sample_width": 2, "encoding": "linear_pcm", "container": "wav"}}
        r = c.post(f"{s.gnani_base_url}/api/v1/tts/inference", headers=h, json=payload)
        show(f"TTS voice={voice}", r, binary=True)
        if r.status_code < 400:
            Path("smoke_tts.wav").write_bytes(r.content)
            print("  saved smoke_tts.wav (open it to hear the voice)")
        if s.gnani_llm_base_url and s.gnani_llm_model:
            key = s.llm_key_gnani
            r = c.post(s.gnani_llm_base_url.rstrip("/") + "/chat/completions",
                       headers={"Authorization": f"Bearer {key}", "X-API-Key-ID": key},
                       json={"model": s.gnani_llm_model, "messages": [{"role": "user", "content": "Reply with the JSON {\"ok\": true}"}]})
            show("LLM /chat/completions", r)
        else:
            print("\n[LLM] skipped: set GNANI_LLM_BASE_URL and GNANI_LLM_MODEL in .env")


if __name__ == "__main__":
    main()
