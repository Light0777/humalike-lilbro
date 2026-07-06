import io
from typing import cast

from discord import PCMAudio, VoiceClient

from gaming_ai.database.repositories.opinion import OpinionRepository
from gaming_ai.database.repositories.player import PlayerRepository
from gaming_ai.database.repositories.relationship import RelationshipRepository
from gaming_ai.discord.voice import VoiceManager
from gaming_ai.models import Utterance
from gaming_ai.models.behavior import BehaviorConfig
from gaming_ai.services.conversation import ConversationEngine
from gaming_ai.services.memory import MemoryEngine
from gaming_ai.services.mood import MoodEngine
from gaming_ai.services.response_generator import ResponseGenerator
from gaming_ai.services.turn_manager import TurnManager
from gaming_ai.utils.logging import logger
from gaming_ai.voice.tts import TTSEngine


class ConversationManager:
    def __init__(
        self,
        conversation_engine: ConversationEngine,
        mood_engine: MoodEngine,
        turn_manager: TurnManager,
        response_generator: ResponseGenerator,
        memory_engine: MemoryEngine | None = None,
        relationship_repo: RelationshipRepository | None = None,
        player_repo: PlayerRepository | None = None,
        opinion_repo: OpinionRepository | None = None,
        config: BehaviorConfig | None = None,
        tts_engine: TTSEngine | None = None,
        voice_manager: VoiceManager | None = None,
    ) -> None:
        self._conversation_engine = conversation_engine
        self._memory_engine = memory_engine
        self._mood_engine = mood_engine
        self._turn_manager = turn_manager
        self._response_generator = response_generator
        self._relationship_repo = relationship_repo
        self._player_repo = player_repo
        self._opinion_repo = opinion_repo
        self._config = config or BehaviorConfig()
        self._tts_engine = tts_engine
        self._voice_manager = voice_manager

        self._pending_responses: dict[int, str | None] = {}

    async def handle_utterance(self, utterance: Utterance) -> None:
        if utterance.guild_id is None:
            return

        guild_id = utterance.guild_id
        player_id = utterance.player_id

        logger.info(
            "Handling utterance from player {} in guild {}: {}",
            player_id, guild_id, utterance.text[:80],
        )

        await self._conversation_engine.process_utterance(utterance)
        session = self._conversation_engine.get_session(guild_id)
        if session is None:
            return

        self._mood_engine.update_from_utterance(utterance, guild_id)
        mood = self._mood_engine.get_mood(guild_id)

        familiarity, trust, rapport = await self._load_relationship(player_id)

        if familiarity > 0:
            self._mood_engine.update_from_speaker_relationship(
                guild_id, familiarity, trust,
            )
            mood = self._mood_engine.get_mood(guild_id)

        intent = await self._turn_manager.decide_response(
            utterance=utterance,
            session=session,
            mood=mood,
            familiarity=familiarity,
            trust=trust,
            rapport=rapport,
        )

        if intent.should_respond:
            text = await self._response_generator.generate(
                intent=intent,
                context=await self._turn_manager.build_context(
                    utterance, session, mood, familiarity, trust, rapport,
                ),
                utterance=utterance,
                session=session,
                mood=mood,
            )
            self._pending_responses[guild_id] = text
            logger.info(
                "Response for guild {}: [{}] {}",
                guild_id, intent.response_type, text,
            )
            await self._play_response(guild_id, text)
        else:
            self._pending_responses.pop(guild_id, None)

        if self._memory_engine:
            await self._memory_engine.store_interaction_memory(
                utterance=utterance,
                response=self._pending_responses.get(guild_id),
                topic=session.active_topic or "",
                session_id=str(guild_id),
            )

    def get_pending_response(self, guild_id: int) -> str | None:
        response = self._pending_responses.get(guild_id)
        self._pending_responses.pop(guild_id, None)
        return response

    def peek_pending_response(self, guild_id: int) -> str | None:
        return self._pending_responses.get(guild_id)

    async def end_session(self, guild_id: int) -> None:
        self._pending_responses.pop(guild_id, None)
        self._mood_engine.reset_session(guild_id)
        session = self._conversation_engine.end_session(guild_id)
        if session is None:
            return

        if self._memory_engine:
            summary = await self._memory_engine.summarize_session(
                turns=session.turns,
                game_name=session.game_name,
            )
            for turn in session.turns:
                await self._memory_engine.store_interaction_memory(
                    utterance=turn.utterance,
                    response=None,
                    topic=summary,
                    session_id=str(guild_id),
                )

    # ── Helpers ─────────────────────────────────────────────────────

    async def _load_relationship(
        self, player_id: str,
    ) -> tuple[float, float, float]:
        if self._relationship_repo is None:
            return 0.0, 0.5, 0.5
        try:
            rel = await self._relationship_repo.find_by_player(player_id)
            if rel is None:
                return 0.0, 0.5, 0.5
            return (
                rel.get("familiarity", 0) or 0,
                rel.get("trust", 0.5) or 0.5,
                rel.get("rapport", 0.5) or 0.5,
            )
        except Exception:
            logger.warning("Could not load relationship for {} (DB not ready?)", player_id)
            return 0.0, 0.5, 0.5

    async def _play_response(self, guild_id: int, text: str) -> None:
        if self._tts_engine is None or self._voice_manager is None:
            return
        if not self._tts_engine.is_available():
            return

        vc = self._voice_manager.get(guild_id)
        if vc is None:
            return
        voice_client = cast(VoiceClient, vc)

        try:
            pcm_data = await self._tts_engine.synthesize(text)
            source = PCMAudio(io.BytesIO(pcm_data))
            voice_client.play(source)
            logger.debug("Playing TTS response in guild {}", guild_id)
        except Exception:
            logger.exception("Failed to play TTS response in guild {}", guild_id)

    def _get_player_name(self, player_id: str, guild_id: int) -> str:
        session = self._conversation_engine.get_session(guild_id)
        if session:
            speaker = session.speakers.get(player_id)
            if speaker:
                return speaker.name
        return player_id
