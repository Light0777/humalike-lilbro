import asyncio
import io
import wave
from typing import Any

from gaming_ai.utils.logging import logger

try:
    from openai import OpenAI
    from openai.types.audio import TranscriptionVerbose

    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False
    OpenAI = None  # type: ignore[assignment, misc]
    TranscriptionVerbose = None  # type: ignore[assignment, misc]


class STTEngine:
    def __init__(self, api_key: str, model: str = "whisper-1") -> None:
        self._client = OpenAI(api_key=api_key) if (_HAS_OPENAI and api_key) else None
        self._model = model

    def is_available(self) -> bool:
        return self._client is not None

    @staticmethod
    def pcm_to_wav(
        pcm_data: bytes,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,
    ) -> bytes:
        with io.BytesIO() as buf:
            with wave.open(buf, "wb") as wav:
                wav.setnchannels(channels)
                wav.setsampwidth(sample_width)
                wav.setframerate(sample_rate)
                wav.writeframes(pcm_data)
            return buf.getvalue()

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> tuple[str, str]:
        if self._client is None:
            return "", "en"

        wav_bytes = self.pcm_to_wav(audio_bytes)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "file": ("audio.wav", wav_bytes, "audio/wav"),
            "response_format": "verbose_json",
        }
        if language:
            kwargs["language"] = language

        try:
            client = self._client
            assert client is not None

            def _transcribe() -> object:
                return client.audio.transcriptions.create(**kwargs)

            result: object = await asyncio.to_thread(_transcribe)
            if _HAS_OPENAI:
                assert isinstance(result, TranscriptionVerbose)
                result_text: str = result.text
                result_lang: str = result.language or "en"
            else:
                result_text = ""
                result_lang = "en"
            logger.debug(
                "Transcribed {} bytes: lang={}, text={!r:.60}",
                len(audio_bytes),
                result_lang,
                result_text,
            )
            return result_text, result_lang
        except Exception:
            logger.exception("Whisper transcription failed")
            return "", "en"
