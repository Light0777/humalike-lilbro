from discord import Intents, Object
from discord.ext import commands

from gaming_ai.config import Settings
from gaming_ai.discord.cogs.events import EventHandlers
from gaming_ai.discord.cogs.voice import VoiceCommands
from gaming_ai.discord.voice import VoiceManager
from gaming_ai.services.conversation_manager import ConversationManager
from gaming_ai.utils.logging import logger
from gaming_ai.voice.pipeline import VoicePipeline
from gaming_ai.voice.tts import TTSEngine


class GamingBot(commands.Bot):
    def __init__(
        self,
        settings: Settings,
        voice_manager: VoiceManager,
        voice_pipeline: VoicePipeline,
        tts_engine: TTSEngine | None = None,
    ) -> None:
        intents = Intents.default()
        intents.message_content = True
        intents.voice_states = True

        super().__init__(
            command_prefix=settings.bot_prefix,
            intents=intents,
        )

        self.settings = settings
        self.voice_manager = voice_manager
        self.voice_pipeline = voice_pipeline
        self.tts_engine = tts_engine
        self.conversation_manager: ConversationManager | None = None
        self._guild_id: int | None = None

    async def setup_hook(self) -> None:
        await self.add_cog(
            VoiceCommands(self, self.voice_manager, self.voice_pipeline, self.tts_engine),
        )
        await self.add_cog(EventHandlers(self))

        if self._guild_id:
            guild = Object(id=self._guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("Slash commands synced to guild {}", self._guild_id)
        else:
            await self.tree.sync()
            logger.info("Slash commands synced globally")

    def set_dev_guild(self, guild_id: int) -> None:
        self._guild_id = guild_id
