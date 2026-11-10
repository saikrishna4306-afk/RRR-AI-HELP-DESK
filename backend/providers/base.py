"""Async provider interfaces and the fallback chain."""
from __future__ import annotations

import asyncio
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger("providers")


class ProviderUnavailable(Exception):
    """Provider not configured (missing key/model) or budget exhausted: skip silently."""


class ProviderError(Exception):
    """Provider was called and failed (retryable)."""


@dataclass
class STTResult:
    transcript: str
    language: str | None = None


@dataclass
class TTSResult:
    audio: bytes
    mime: str


@dataclass
class Used:
    service: str
    provider: str
    label: str
    ms: int
    note: str = ""


class Provider(ABC):
    name: str = "base"
    label: str = "Base"

    def available(self) -> bool:  # configured?
        return True


class LLMProvider(Provider):
    @abstractmethod
    async def complete_json(self, system: str, user: str, purpose: str) -> str: ...


class VisionProvider(Provider):
    @abstractmethod
    async def diagnose(self, data: bytes, mime: str, filename: str, prompt: str) -> str: ...


class STTProvider(Provider):
    @abstractmethod
    async def transcribe(self, wav: bytes, language: str, session_id: str = "") -> STTResult: ...


class TTSProvider(Provider):
    @abstractmethod
    async def synthesize(self, text: str, language: str) -> TTSResult: ...

    def voice_for(self, language: str) -> str:
        return ""


class EmbeddingProvider(Provider):
    model_name: str = "base"

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass
class Chain:
    service: str
    providers: list[Provider]
    timeout_s: float = 25.0
    attempts: int = 2
    log: list[Used] = field(default_factory=list)

    async def run(self, method: str, *args, **kwargs):
        """Try providers in order. Returns (result, Used). Raises ProviderError if all fail."""
        errors = []
        for p in self.providers:
            if not p.available():
                errors.append(f"{p.name}: not configured")
                continue
            t0 = time.perf_counter()
            try:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(self.attempts),
                    wait=wait_exponential(multiplier=0.4, max=3),
                    retry=retry_if_exception_type((ProviderError, asyncio.TimeoutError)),
                    reraise=True,
                ):
                    with attempt:
                        result = await asyncio.wait_for(getattr(p, method)(*args, **kwargs), self.timeout_s)
                used = Used(self.service, p.name, p.label, int((time.perf_counter() - t0) * 1000))
                if errors:
                    used.note = "fallback after: " + "; ".join(errors)
                return result, used
            except ProviderUnavailable as e:
                errors.append(f"{p.name}: {e}")
            except Exception as e:  # noqa: BLE001 - any provider failure moves down the chain
                logger.warning(f"{self.service} provider {p.name} failed: {e!r}")
                status = re.search(r"\bHTTP\s+(\d{3})\b", str(e), re.IGNORECASE)
                reason = f"HTTP {status.group(1)}" if status else type(e).__name__
                errors.append(f"{p.name}: {reason}")
        raise ProviderError(f"all {self.service} providers failed: " + "; ".join(errors))
