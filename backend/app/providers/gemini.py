import asyncio
import base64
import logging
import time

import httpx

from app.config import settings
from app.providers.base import ChatTurn, ProviderError, VLMProvider, VLMResult

log = logging.getLogger("uvicorn.error")

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class GeminiProvider(VLMProvider):
    name = "gemini"

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise ProviderError("GEMINI_API_KEY is missing in backend/.env")
        if not settings.gemini_model:
            raise ProviderError("GEMINI_MODEL is missing in backend/.env")
        self.models: list[str] = [settings.gemini_model]
        fallback = settings.gemini_fallback_model
        if fallback and fallback != settings.gemini_model:
            self.models.append(fallback)

    @staticmethod
    def _build_payload(
        system_prompt: str,
        user_text: str,
        image_bytes: bytes | None,
        mime_type: str,
        history: list[ChatTurn] | None,
    ) -> dict:
        contents: list[dict] = []
        for turn in history or []:
            role = "user" if turn.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": turn.text}]})

        parts: list[dict] = []
        if image_bytes:
            parts.append(
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64.b64encode(image_bytes).decode(),
                    }
                }
            )
        parts.append({"text": user_text})
        contents.append({"role": "user", "parts": parts})

        payload: dict = {
            "contents": contents,
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
        }
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}
        return payload

    async def _call_once(self, client: httpx.AsyncClient, model: str, payload: dict) -> str:
        url = f"{BASE_URL}/models/{model}:generateContent"
        try:
            resp = await client.post(
                url,
                json=payload,
                headers={"x-goog-api-key": settings.gemini_api_key},
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise ProviderError(
                f"Network problem calling {model}: {type(exc).__name__}",
                retryable=True,
            ) from exc

        if resp.status_code != 200:
            try:
                message = resp.json()["error"]["message"]
            except Exception:  # noqa: BLE001
                message = resp.text[:300]
            raise ProviderError(
                f"{model}: HTTP {resp.status_code}: {message}",
                status_code=resp.status_code,
                retryable=resp.status_code in RETRYABLE_STATUS,
            )

        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            reason = (data.get("promptFeedback") or {}).get("blockReason", "unknown")
            raise ProviderError(f"{model}: no candidates returned (blockReason={reason})")

        candidate = candidates[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
        if not text:
            finish = candidate.get("finishReason", "unknown")
            raise ProviderError(f"{model}: empty answer (finishReason={finish})")
        return text

    async def generate(
        self,
        *,
        system_prompt: str,
        user_text: str,
        image_bytes: bytes | None = None,
        mime_type: str = "image/jpeg",
        history: list[ChatTurn] | None = None,
    ) -> VLMResult:
        payload = self._build_payload(system_prompt, user_text, image_bytes, mime_type, history)
        started = time.perf_counter()
        attempts = 0
        last_error: ProviderError | None = None
        max_retries = max(1, settings.vlm_max_retries)

        async with httpx.AsyncClient(timeout=settings.vlm_timeout_seconds) as client:
            for index, model in enumerate(self.models):
                for attempt in range(1, max_retries + 1):
                    attempts += 1
                    try:
                        text = await self._call_once(client, model, payload)
                    except ProviderError as exc:
                        last_error = exc
                        if exc.status_code == 404:
                            log.warning("Model %s is not available (404). Trying next model.", model)
                            break
                        if not exc.retryable:
                            raise
                        log.warning(
                            "Gemini %s attempt %d/%d failed: %s",
                            model,
                            attempt,
                            max_retries,
                            exc,
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(min(2 ** (attempt - 1), 8))
                        continue

                    return VLMResult(
                        text=text,
                        provider=self.name,
                        model=model,
                        latency_ms=(time.perf_counter() - started) * 1000,
                        used_fallback=index > 0,
                        attempts=attempts,
                    )

        raise ProviderError(f"All Gemini models failed. Last error: {last_error}")
