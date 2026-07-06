import asyncio
from typing import Any

from gaming_ai.utils.logging import logger

try:
    import google.genai as genai
    from google.genai import types as genai_types

    _HAS_GEMINI = True
except ImportError:
    _HAS_GEMINI = False

from gaming_ai.services.llm.client import LLMClient


def _convert_messages(messages: list[dict[str, Any]]) -> list[genai_types.Content]:
    contents: list[genai_types.Content] = []
    for msg in messages:
        role = msg.get("role", "user")
        gemini_role = "model" if role == "assistant" else "user"
        text = msg.get("content", "") or ""
        parts = [genai_types.Part(text=text)]
        contents.append(genai_types.Content(role=gemini_role, parts=parts))
    return contents


class GeminiClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> None:
        self._client = genai.Client(api_key=api_key) if _HAS_GEMINI else None
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._available = bool(api_key) and _HAS_GEMINI

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str = "",
        temperature: float = 0.0,
        max_tokens: int = 0,
    ) -> str:
        if not self._available or self._client is None:
            return ""

        system_text = ""
        chat_messages: list[dict[str, Any]] = []
        for msg in messages:
            if msg.get("role") == "system":
                system_text = msg.get("content", "") or ""
            else:
                chat_messages.append(msg)

        contents = _convert_messages(chat_messages) if chat_messages else None
        config = genai_types.GenerateContentConfig(
            system_instruction=system_text or None,
            temperature=temperature or self._temperature,
            max_output_tokens=max_tokens or self._max_tokens,
        )

        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=model or self._model,
                    contents=contents,
                    config=config,
                ),
                timeout=15.0,
            )
            return response.text or ""
        except TimeoutError:
            logger.warning("Gemini API timed out after 15s")
            return ""
        except Exception:
            logger.exception("Gemini API call failed")
            return ""

    def is_available(self) -> bool:
        return self._available
