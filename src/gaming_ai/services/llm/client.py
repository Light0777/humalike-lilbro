from abc import ABC, abstractmethod
from typing import Any

try:
    from openai import AsyncOpenAI

    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False
    AsyncOpenAI = None  # type: ignore[assignment, misc]


class LLMClient(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str = "",
        temperature: float = 0.0,
        max_tokens: int = 0,
    ) -> str:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


class OpenAIClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key) if _HAS_OPENAI else None
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str = "",
        temperature: float = 0.0,
        max_tokens: int = 0,
    ) -> str:
        if not _HAS_OPENAI or self._client is None:
            return ""
        response = await self._client.chat.completions.create(
            model=model or self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature or self._temperature,
            max_tokens=max_tokens or self._max_tokens,
        )
        return response.choices[0].message.content or ""

    def is_available(self) -> bool:
        return _HAS_OPENAI and self._client is not None and bool(self._client.api_key)
