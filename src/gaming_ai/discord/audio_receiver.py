import asyncio
import audioop
import time
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

from discord import Member, User
from discord.ext.voice_recv import AudioSink, VoiceData

from gaming_ai.utils.logging import logger


class AudioReceiver(AudioSink):
    def __init__(
        self,
        callback: Callable[[int, bytes, int, int], Coroutine[Any, Any, None]],
        *,
        vad_threshold: float = 200.0,
        silence_timeout: float = 0.8,
        min_utterance: float = 0.3,
        max_utterance: float = 30.0,
    ) -> None:
        super().__init__()
        self._callback = callback
        self._loop: asyncio.AbstractEventLoop | None = None

        self.vad_threshold = vad_threshold
        self.silence_timeout = silence_timeout
        self.min_utterance = min_utterance
        self.max_utterance = max_utterance

        self.sample_rate = 48000
        self.sample_width = 2
        self.channels = 2

        self._buffers: dict[int, bytearray] = defaultdict(bytearray)
        self._speaking: dict[int, bool] = {}
        self._silence_start: dict[int, float] = {}
        self._segment_start: dict[int, float] = {}

    def write(self, user: Member | User | None, data: VoiceData) -> None:
        if user is None:
            logger.debug(
                "write() called with None user, pcm_len={}",
                len(data.pcm) if data.pcm else 0,
            )
            return
        if not data.pcm:
            logger.debug("write() called for user {} with empty pcm", user.id)
            return

        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        user_id = user.id
        pcm = data.pcm
        rms = audioop.rms(pcm, self.sample_width)
        is_speaking = rms > self.vad_threshold

        if not self._speaking.get(user_id, False) and is_speaking:
            logger.info(
                "Speech started for user {} (rms={:.0f}, thr={})",
                user_id, rms, self.vad_threshold,
            )

        now = time.time()

        if is_speaking:
            if not self._speaking.get(user_id, False):
                self._speaking[user_id] = True
                self._segment_start[user_id] = now
                self._buffers[user_id] = bytearray()

            self._buffers[user_id].extend(pcm)
            self._silence_start.pop(user_id, None)

            elapsed = now - self._segment_start.get(user_id, now)
            if elapsed >= self.max_utterance:
                self._finalize_segment(user_id)
        else:
            if self._speaking.get(user_id, False):
                self._buffers[user_id].extend(pcm)
                if user_id not in self._silence_start:
                    self._silence_start[user_id] = now
                elif now - self._silence_start[user_id] >= self.silence_timeout:
                    self._finalize_segment(user_id)

    def _finalize_segment(self, user_id: int) -> None:
        buf = self._buffers.pop(user_id, None)
        self._speaking.pop(user_id, None)
        self._silence_start.pop(user_id, None)
        self._segment_start.pop(user_id, None)

        if buf is None or len(buf) == 0:
            return

        pcm_data = bytes(buf)
        duration = len(pcm_data) / (
            self.sample_rate * self.sample_width * self.channels
        )

        logger.debug(
            "Finalized segment for user {}: {:.1f}s ({} bytes)",
            user_id, duration, len(pcm_data),
        )

        if duration < self.min_utterance:
            logger.debug(
                "Segment too short ({:.1f}s < {:.1f}s), dropping",
                duration, self.min_utterance,
            )
            return

        if self._loop is not None and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._callback(user_id, pcm_data, self.sample_rate, self.channels),
                self._loop,
            )

    def flush_all(self) -> None:
        for user_id in list(self._buffers.keys()):
            self._finalize_segment(user_id)

    def wants_opus(self) -> bool:
        return False

    def cleanup(self) -> None:
        self.flush_all()
