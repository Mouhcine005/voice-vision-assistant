import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _whisper_engine_by_default(monkeypatch):
    """Tests never call Gemini for speech unless a test opts in."""
    monkeypatch.setattr(settings, "stt_engine", "whisper")
