import asyncio
import audioop
import time
from collections.abc import Callable, Coroutine
from typing import Any

from discord.ext.voice_recv import VoiceRecvClient

from gaming_ai.discord.audio_receiver import AudioReceiver
from gaming_ai.models import Utterance
from gaming_ai.utils.logging import logger
from gaming_ai.voice.language import LanguageDetector
from gaming_ai.voice.speaker import SpeakerTracker

UtteranceCallback = Callable[[Utterance], Coroutine[Any, Any, None]]


class VoicePipeline:
    def __init__(
        self,
        stt_engine: Any,
        speaker_tracker: SpeakerTracker,
        language_detector: LanguageDetector,
    ) -> None:
        self.stt = stt_engine
        self.speaker_tracker = speaker_tracker
        self.language_detector = language_detector
        self._receiver: AudioReceiver | None = None
        self._voice_client: VoiceRecvClient | None = None
        self._on_utterance_callback: UtteranceCallback | None = None
        self._guild_id: int | None = None
        self._channel_id: int | None = None
        self._health_task: asyncio.Task[None] | None = None

    def set_on_utterance(self, callback: UtteranceCallback) -> None:
        self._on_utterance_callback = callback

    async def start(self, voice_client: VoiceRecvClient) -> None:
        if self._voice_client is not None:
            logger.warning("Pipeline already running, stopping first")
            await self.stop()

        self._voice_client = voice_client
        self._guild_id = voice_client.guild.id
        self._channel_id = voice_client.channel.id
        self.speaker_tracker.clear()

        self._receiver = AudioReceiver(
            callback=self._on_audio_segment,
        )

        voice_client.listen(self._receiver)
        logger.info(
            "Voice pipeline started on guild {} channel {} ({}) — listening={}",
            self._guild_id, voice_client.channel.name, voice_client.channel.id,
            voice_client.is_listening(),
        )

        conn = voice_client._connection
        logger.info(
            "Voice conn: has_socket={} ws={} endpoint_ip={} port={}",
            conn.socket is not None,
            conn.ws is not None,
            conn.endpoint_ip, conn.voice_port,
        )
        reader = conn._socket_reader
        logger.info(
            "Socket reader: running={} idle_paused={} callbacks={}",
            reader._running.is_set(), reader._idle_paused, len(reader._callbacks),
        )
        if not reader._running.is_set():
            reader.resume(force=True)
            logger.info("Force-resumed socket reader: running={}", reader._running.is_set())

        self._health_task = asyncio.create_task(self._health_loop())

    async def stop(self) -> None:
        if self._receiver is not None:
            self._receiver.flush_all()

        vc = self._voice_client
        if vc is not None:
            try:
                vc.stop_listening()
            except Exception:
                logger.exception("Error stopping voice pipeline")
            self._voice_client = None
            self._receiver = None
            self._guild_id = None
            self._channel_id = None

        if self._health_task is not None:
            self._health_task.cancel()
            self._health_task = None

        logger.info("Voice pipeline stopped")

    async def _on_audio_segment(
        self,
        user_id: int,
        pcm_data: bytes,
        sample_rate: int,
        channels: int,
    ) -> None:
        logger.debug(
            "Processing audio segment: user={}, {} bytes, {}ch {}hz",
            user_id, len(pcm_data), channels, sample_rate,
        )
        try:
            mono = audioop.tomono(pcm_data, 2, 0.5, 0.5)
            resampled, _ = audioop.ratecv(mono, 2, 1, sample_rate, 16000, None)
        except Exception:
            logger.exception("Audio conversion failed")
            return

        logger.debug("Transcribing {} bytes of audio...", len(resampled))
        text, language = await self.stt.transcribe(resampled)
        logger.debug("Transcription result: lang={}, text={!r:.100}", language, text)

        if not text.strip():
            return

        language = self.language_detector.normalize(language)
        self.speaker_tracker.record_utterance(user_id)

        utterance = Utterance(
            player_id=str(user_id),
            text=text,
            timestamp=time.time(),
            language=language,
            guild_id=self._guild_id,
            channel_id=self._channel_id,
        )

        logger.info(
            "Utterance from user {} [{}]: {}",
            user_id, language, text[:100],
        )

        if self._on_utterance_callback is not None:
            await self._on_utterance_callback(utterance)

    def is_listening(self) -> bool:
        return self._voice_client is not None and self._voice_client.is_listening()

    @property
    def voice_client(self) -> VoiceRecvClient | None:
        return self._voice_client

    async def _health_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(30)
                if self._voice_client is None:
                    break
                sink = self._voice_client.sink
                pkt_count = -1
                pkt_age = 0.0
                if sink is not None and hasattr(sink, '_packet_count'):
                    s: Any = sink
                    pkt_count = s._packet_count
                    if pkt_count > 0:
                        pkt_age = time.time() - s._last_packet_ts
                logger.info(
                    "Pipeline health: connected={} listening={} packets={} last_pkt={:.0f}s ago",
                    self._voice_client.is_connected(),
                    self._voice_client.is_listening(),
                    pkt_count,
                    pkt_age,
                )
        except asyncio.CancelledError:
            pass
