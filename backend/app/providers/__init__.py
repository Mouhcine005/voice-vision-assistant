from functools import lru_cache

from app.config import settings
from app.providers.base import ChatTurn, ProviderError, VLMProvider, VLMResult

__all__ = ["ChatTurn", "ProviderError", "VLMProvider", "VLMResult", "get_provider"]


@lru_cache
def _build(name: str) -> VLMProvider:
    if name == "gemini":
        from app.providers.gemini import GeminiProvider

        return GeminiProvider()
    raise ProviderError(f"Provider '{name}' is not implemented yet.")


def get_provider(name: str | None = None) -> VLMProvider:
    """Return the active provider (chosen by VLM_PROVIDER in .env)."""
    return _build((name or settings.vlm_provider).lower())
