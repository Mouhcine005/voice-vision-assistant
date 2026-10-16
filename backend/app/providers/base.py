from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(Exception):
    """A vision provider failed (bad config, bad request, or all retries used up)."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


@dataclass
class ChatTurn:
    """One previous message in the conversation (used for follow-up questions)."""

    role: str  # "user" or "assistant"
    text: str


@dataclass
class VLMResult:
    text: str
    provider: str
    model: str
    latency_ms: float
    used_fallback: bool = False
    attempts: int = 1


class VLMProvider(ABC):
    """Every vision-language provider (Gemini, Mistral, Ollama...) implements this."""

    name: str

    @abstractmethod
    async def generate(
        self,
        *,
        system_prompt: str,
        user_text: str,
        image_bytes: bytes | None = None,
        mime_type: str = "image/jpeg",
        history: list[ChatTurn] | None = None,
    ) -> VLMResult:
        """Return the model's answer for this image + text."""
