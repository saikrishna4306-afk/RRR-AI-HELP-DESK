import pytest

from backend import ledger
from backend.config import get_settings
from backend.providers.base import Chain, ProviderError, ProviderUnavailable, STTProvider, STTResult
from backend.providers.gnani import GnaniSTT
from backend.providers.mock import MockSTT


class Broken(STTProvider):
    name, label = "broken", "Broken"
    calls = 0

    async def transcribe(self, wav, language, session_id=""):
        Broken.calls += 1
        raise ProviderError("boom")


class NoKey(STTProvider):
    name, label = "nokey", "NoKey"

    def available(self):
        return False

    async def transcribe(self, wav, language, session_id=""):
        raise AssertionError("must not be called")


async def test_fallback_chain_skips_unconfigured_and_failed():
    MockSTT.questions = {"te": ["q1"]}
    res, used = await Chain("stt", [NoKey(), Broken(), MockSTT()], attempts=2).run("transcribe", b"", "te", "s")
    assert isinstance(res, STTResult) and used.provider == "mock"
    assert "nokey: not configured" in used.note and "broken" in used.note
    assert Broken.calls == 2  # retried with backoff before falling back


async def test_all_fail_raises():
    with pytest.raises(ProviderError):
        await Chain("stt", [Broken()], attempts=1).run("transcribe", b"", "te")


async def test_credit_budget_fallback(client, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "gnani_api_key", "dummy")
    monkeypatch.setattr(s, "gnani_stt_credits_per_sec", 1.0)
    assert GnaniSTT().available() is True
    monkeypatch.setattr(s, "gnani_credit_budget", 10.0)
    ledger.record("gnani", "stt", "audio_sec", 11.0, "test")
    assert GnaniSTT().available() is False  # budget reached -> skipped -> free providers used
    res, used = await Chain("stt", [GnaniSTT(), MockSTT()]).run("transcribe", b"", "te", "s")
    assert used.provider == "mock"


def test_unavailable_is_exception():
    assert issubclass(ProviderUnavailable, Exception)
