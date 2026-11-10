"""Upload validation: size and duration limits."""
from __future__ import annotations

import io
import struct
import wave

from .config import get_settings


class UploadError(ValueError):
    pass


def wav_duration(data: bytes) -> float | None:
    try:
        with wave.open(io.BytesIO(data)) as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:  # noqa: BLE001
        return None


def mp4_duration(data: bytes) -> float | None:
    """Read duration from the mvhd box (MP4/MOV) without ffmpeg."""
    i = data.find(b"mvhd")
    if i < 4:
        return None
    try:
        version = data[i + 4]
        if version == 1:
            timescale, duration = struct.unpack(">IQ", data[i + 24 : i + 36])
        else:
            timescale, duration = struct.unpack(">II", data[i + 16 : i + 24])
        return duration / timescale if timescale else None
    except struct.error:
        return None


def check_audio(data: bytes) -> None:
    s = get_settings()
    if len(data) > s.max_audio_mb * 1024 * 1024:
        raise UploadError(f"Audio is larger than {s.max_audio_mb:g} MB.")
    dur = wav_duration(data)
    if dur is not None and dur > s.max_audio_seconds + 0.5:
        raise UploadError(f"Audio is longer than {s.max_audio_seconds:g} seconds.")


def check_media(data: bytes, mime: str) -> str:
    s = get_settings()
    mime = (mime or "").lower()
    if mime.startswith("image/"):
        if len(data) > s.max_image_mb * 1024 * 1024:
            raise UploadError(f"Image is larger than {s.max_image_mb:g} MB.")
        return "image"
    if mime.startswith("video/"):
        if len(data) > s.max_video_mb * 1024 * 1024:
            raise UploadError(f"Video is larger than {s.max_video_mb:g} MB.")
        dur = mp4_duration(data)
        if dur is not None and dur > s.max_video_seconds + 0.5:
            raise UploadError(f"Video is longer than {s.max_video_seconds:g} seconds.")
        return "video"
    raise UploadError("Please upload a photo (JPG/PNG) or a short video (MP4/MOV/WEBM).")


def check_text(text: str) -> None:
    if len(text or "") > get_settings().max_text_chars:
        raise UploadError(f"Text is longer than {get_settings().max_text_chars} characters.")
