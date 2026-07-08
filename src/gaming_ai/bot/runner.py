from typing import Any

from gaming_ai.config import Settings
from gaming_ai.database import (
    DatabaseClient,
    MemoryRepository,
    OpinionRepository,
    PlayerRepository,
    RelationshipRepository,
    SessionRepository,
)
from gaming_ai.discord import GamingBot, VoiceManager
from gaming_ai.models.behavior import BehaviorConfig
from gaming_ai.services.conversation import ConversationEngine
from gaming_ai.services.conversation_manager import ConversationManager
from gaming_ai.services.humalike import HumalikeService
from gaming_ai.services.llm import GeminiClient, LLMClient, LLMService, OpenAIClient
from gaming_ai.services.memory import MemoryEngine
from gaming_ai.services.mood import MoodEngine
from gaming_ai.services.response_generator import ResponseGenerator
from gaming_ai.services.turn_manager import TurnManager
from gaming_ai.utils.logging import logger
from gaming_ai.voice import (
    EdgeTTSEngine,
    ElevenLabsTTSEngine,
    LanguageDetector,
    LocalSTTEngine,
    OpenAITTSEngine,
    SpeakerTracker,
    STTEngine,
    TTSEngine,
    VoicePipeline,
)


class BotRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # ── Database ───────────────────────────────────────────────
        self.db_client = DatabaseClient(
            url=settings.supabase_url,
            key=settings.supabase_key,
        )
        self.player_repo: PlayerRepository | None = None
        self.session_repo: SessionRepository | None = None
        self.memory_repo: MemoryRepository | None = None
        self.opinion_repo: OpinionRepository | None = None
        self.relationship_repo: RelationshipRepository | None = None
        self.stt_engine: Any = None
        self._llm_client: LLMClient | None = None
        self.llm_service: LLMService | None = None
        self.tts_engine: TTSEngine | None = None
        self.memory_engine: MemoryEngine | None = None
        self.conversation_manager: ConversationManager | None = None
        self.humalike_service: HumalikeService | None = None

        # ── STT ─────────────────────────────────────────────────────
        if settings.stt_provider == "local":
            self.stt_engine = LocalSTTEngine(
                model_size=settings.local_whisper_model,
            )
        else:
            self.stt_engine = STTEngine(
                api_key=settings.openai_api_key,
                model=settings.whisper_model,
            )

        self.speaker_tracker = SpeakerTracker()
        self.language_detector = LanguageDetector()

        # ── LLM ─────────────────────────────────────────────────────
        if settings.llm_provider == "gemini":
            self._llm_client = GeminiClient(
                api_key=settings.gemini_api_key,
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
        elif settings.llm_provider == "openrouter":
            self._llm_client = OpenAIClient(
                api_key=settings.openrouter_api_key,
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                base_url="https://openrouter.ai/api/v1",
            )
        else:
            self._llm_client = OpenAIClient(
                api_key=settings.openai_api_key,
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
        self.llm_service = LLMService(client=self._llm_client)

        # ── TTS ─────────────────────────────────────────────────────
        if settings.tts_provider == "elevenlabs":
            self.tts_engine = ElevenLabsTTSEngine(
                api_key=settings.elevenlabs_api_key,
                voice_id=settings.elevenlabs_voice_id,
            )
        elif settings.tts_provider == "edge":
            self.tts_engine = EdgeTTSEngine(
                voice=settings.edge_tts_voice,
            )
        else:
            self.tts_engine = OpenAITTSEngine(
                api_key=settings.openai_api_key,
                voice=settings.tts_voice,
            )

        # ── Humalike ────────────────────────────────────────────────
        self.humalike_service = HumalikeService(
            api_key=settings.humalike_api_key,
            base_url=settings.humalike_base_url,
        )

        # ── Conversation ────────────────────────────────────────────
        self.voice_manager = VoiceManager()
        self.conversation_engine = ConversationEngine()
        self.behavior_config = BehaviorConfig()
        self.mood_engine = MoodEngine(config=self.behavior_config)
        self.turn_manager = TurnManager(config=self.behavior_config)
        self.response_generator = ResponseGenerator(
            config=self.behavior_config,
            llm_service=self.llm_service,
        )

        self.voice_pipeline = VoicePipeline(
            stt_engine=self.stt_engine,
            speaker_tracker=self.speaker_tracker,
            language_detector=self.language_detector,
        )

        # ── Bot ────────────────────────────────────────────────────
        self.bot = GamingBot(settings, self.voice_manager, self.voice_pipeline, self.tts_engine)
        if settings.dev_guild_id:
            self.bot.set_dev_guild(settings.dev_guild_id)

        if not self.stt_engine.is_available():
            logger.warning("STT engine not available — speech-to-text disabled")
        if self._llm_client is not None and not self._llm_client.is_available():
            logger.warning("LLM client not available — using fallback responses")
        if self.tts_engine is not None and not self.tts_engine.is_available():
            logger.warning("TTS engine not available — bot will be text-only")

    async def initialize_database(self) -> None:
        if not self.settings.supabase_url or not self.settings.supabase_key:
            logger.warning(
                "SUPABASE_URL or SUPABASE_KEY not set — database features disabled"
            )
            return

        client = await self.db_client.connect()
        self.player_repo = PlayerRepository(client)
        self.session_repo = SessionRepository(client)
        self.memory_repo = MemoryRepository(client)
        self.opinion_repo = OpinionRepository(client)
        self.relationship_repo = RelationshipRepository(client)

        self.memory_engine = MemoryEngine(
            memory_repo=self.memory_repo,
            session_repo=self.session_repo,
        )

        if self._llm_client is not None and self.memory_engine is not None:
            self.llm_service = LLMService(
                client=self._llm_client,
                memory_engine=self.memory_engine,
            )

        self.response_generator = ResponseGenerator(
            opinion_repo=self.opinion_repo,
            player_repo=self.player_repo,
            config=self.behavior_config,
            llm_service=self.llm_service,
        )
        self.conversation_manager = ConversationManager(
            conversation_engine=self.conversation_engine,
            memory_engine=self.memory_engine,
            mood_engine=self.mood_engine,
            turn_manager=self.turn_manager,
            response_generator=self.response_generator,
            relationship_repo=self.relationship_repo,
            player_repo=self.player_repo,
            opinion_repo=self.opinion_repo,
            config=self.behavior_config,
            tts_engine=self.tts_engine,
            voice_manager=self.voice_manager,
            humalike=self.humalike_service,
        )
        self.bot.conversation_manager = self.conversation_manager
        self.voice_pipeline.set_on_utterance(
            self.conversation_manager.handle_utterance,
        )
        logger.info("Database, memory, and conversation manager initialized")

    async def shutdown(self) -> None:
        logger.info("Shutting down bot...")
        for guild_id in self.conversation_engine.get_active_guilds():
            if self.conversation_manager is not None:
                await self.conversation_manager.end_session(guild_id)
            else:
                self.conversation_engine.end_session(guild_id)
        await self.voice_pipeline.stop()
        await self.voice_manager.disconnect_all()
        await self.db_client.disconnect()
        await self.bot.close()

    async def run(self) -> None:
        logger.info("Starting Discord bot...")
        try:
            await self.initialize_database()
            async with self.bot:
                await self.bot.start(self.settings.discord_token)
        except Exception:
            logger.exception("Fatal error running bot")
        finally:
            logger.info("Bot stopped")
