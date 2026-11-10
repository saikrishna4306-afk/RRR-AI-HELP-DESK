import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Force offline mock providers for every test, regardless of a developer's .env
_tmp = Path(tempfile.mkdtemp(prefix="rrr-test-"))
os.environ.update({
    "LLM_PROVIDER": "mock", "LLM_FALLBACK": "mock", "STT_PROVIDER": "mock", "STT_FALLBACK": "mock",
    "TTS_PROVIDER": "mock", "TTS_FALLBACK": "mock", "VISION_PROVIDER": "mock", "EMBED_PROVIDER": "hash",
    "GNANI_API_KEY": "", "GEMINI_API_KEY": "", "ADMIN_TOKEN": "test-token", "RATE_LIMIT_PER_MIN": "1000",
    "DATABASE_URL": f"sqlite:///{(_tmp / 'test.db').as_posix()}",
})

from backend.config import get_settings  # noqa: E402

get_settings.cache_clear()


@pytest.fixture(scope="session")
def tmpdir_session():
    yield _tmp
    shutil.rmtree(_tmp, ignore_errors=True)


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def desk(client):
    from backend.main import desk

    return desk
