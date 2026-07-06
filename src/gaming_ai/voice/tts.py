import audioop
import io
import wave
from abc import ABC, abstractmethod

import httpx
import miniaudio  # type: ignore[import-untyped]

from gaming_ai.utils.logging import logger

try:
    from openai import AsyncOpenAI

    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False
    AsyncOpenAI = None  # type: ignore[assignment, misc]

TARGET_SAMPLE_RATE = 48000
TARGET_CHANNELS = 2
TARGET_SAMPLE_WIDTH = 2


class TTSEngine(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


class OpenAITTSEngine(TTSEngine):
    def __init__(
        self,
        api_key: str,
        voice: str = "nova",
        model: str = "tts-1",
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key) if _HAS_OPENAI else None
        self._voice = voice
        self._model = model

    async def synthesize(self, text: str) -> bytes:
        client = self._client
        assert client is not None
        response = await client.audio.speech.create(
            model=self._model,
            voice=self._voice,
            input=text,
            response_format="wav",
        )
        wav_bytes = response.content
        return self._wav_to_pcm(wav_bytes)

    def is_available(self) -> bool:
        return self._client is not None and bool(self._client.api_key)

    @staticmethod
    def _wav_to_pcm(wav_bytes: bytes) -> bytes:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
            nchannels = wav.getnchannels()
            sampwidth = wav.getsampwidth()
            framerate = wav.getframerate()
            pcm_data = wav.readframes(wav.getnframes())

        if sampwidth != TARGET_SAMPLE_WIDTH:
            logger.warning(
                "Unexpected sample width {} (expected {})",
                sampwidth, TARGET_SAMPLE_WIDTH,
            )

        if nchannels == 1:
            pcm_data = audioop.tostereo(pcm_data, sampwidth, 1, 1)

        if framerate != TARGET_SAMPLE_RATE:
            pcm_data, _ = audioop.ratecv(
                pcm_data, sampwidth, TARGET_CHANNELS,
                framerate, TARGET_SAMPLE_RATE, None,
            )

        return pcm_data


class ElevenLabsTTSEngine(TTSEngine):
    def __init__(
        self,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model_id: str = "eleven_monolingual_v1",
    ) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._model_id = model_id

    async def synthesize(self, text: str) -> bytes:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self._voice_id}",
                headers={"xi-api-key": self._api_key},
                json={
                    "text": text,
                    "model_id": self._model_id,
                    "output_format": "pcm_48000",
                },
            )
            response.raise_for_status()
            return response.content

    def is_available(self) -> bool:
        return bool(self._api_key)


class EdgeTTSEngine(TTSEngine):
    def __init__(self, voice: str = "en-US-EmmaMultilingualNeural") -> None:
        self._voice = voice
        self._available = True

    async def synthesize(self, text: str) -> bytes:
        from edge_tts import Communicate

        communicate = Communicate(text, voice=self._voice)
        mp3_chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                data = chunk.get("data")
                if data:
                    mp3_chunks.append(data)

        if not mp3_chunks:
            return b""

        mp3_data = b"".join(mp3_chunks)
        decoded = miniaudio.decode(
            mp3_data,
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=TARGET_CHANNELS,
            sample_rate=TARGET_SAMPLE_RATE,
        )
        return decoded.samples.tobytes()  # type: ignore[no-any-return]

    def is_available(self) -> bool:
        return self._available
