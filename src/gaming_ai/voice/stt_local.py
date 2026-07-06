import asyncio
import io
import wave
from typing import Any, cast

from gaming_ai.utils.logging import logger

try:
    import numpy as np
    from faster_whisper import WhisperModel  # type: ignore[import-untyped]

    _HAS_WHISPER = True
except ImportError:
    _HAS_WHISPER = False
    np = cast(Any, None)
    WhisperModel = cast(Any, None)


class LocalSTTEngine:
    def __init__(self, model_size: str = "base") -> None:
        self._model: WhisperModel | None = None
        self._model_size = model_size
        self._available = _HAS_WHISPER

    def is_available(self) -> bool:
        return self._available

    def _ensure_model(self) -> None:
        if self._model is None and self._available and WhisperModel is not None:
            logger.info(
                "Loading Whisper model '{}' (first load ~140MB)...",
                self._model_size,
            )
            self._model = WhisperModel(
                self._model_size,
                device="cpu",
                compute_type="int8",
            )
            logger.info("Whisper model '{}' loaded successfully", self._model_size)

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
        if not self._available or np is None:
            return "", "en"

        self._ensure_model()
        if self._model is None:
            return "", "en"

        samples = (
            np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        )

        try:
            segments, info = await asyncio.to_thread(
                self._model.transcribe,
                samples,
                language=language,
                beam_size=1,
            )

            text = " ".join(seg.text.strip() for seg in segments)
            detected_lang = info.language or "en"
            logger.debug(
                "Transcribed {} samples: lang={}, text={!r:.60}",
                len(samples),
                detected_lang,
                text,
            )
            return text, detected_lang
        except Exception:
            logger.exception("Local Whisper transcription failed")
            return "", "en"
