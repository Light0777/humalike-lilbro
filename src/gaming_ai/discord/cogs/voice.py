import io
import time
from typing import cast

import discord
from discord import VoiceChannel, app_commands
from discord.ext import commands
from discord.ext.voice_recv import VoiceRecvClient

from gaming_ai.discord.voice import VoiceManager
from gaming_ai.utils.logging import logger
from gaming_ai.voice.pipeline import VoicePipeline
from gaming_ai.voice.tts import TTSEngine


class VoiceCommands(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        voice_manager: VoiceManager,
        voice_pipeline: VoicePipeline,
        tts_engine: TTSEngine | None = None,
    ) -> None:
        self.bot = bot
        self.voice_manager = voice_manager
        self.voice_pipeline = voice_pipeline
        self._tts_engine = tts_engine

    @app_commands.command(name="join", description="Join your current voice channel")
    async def join(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        user = interaction.user
        if not isinstance(user, discord.Member) or user.voice is None:
            await interaction.response.send_message(
                "You need to be in a voice channel first.",
                ephemeral=True,
            )
            return

        channel = user.voice.channel
        if not isinstance(channel, VoiceChannel):
            await interaction.response.send_message(
                "I can only join regular voice channels.",
                ephemeral=True,
            )
            return

        if self.voice_manager.is_connected(guild_id):
            await interaction.response.send_message(
                "I'm already connected to a voice channel on this server.",
                ephemeral=True,
            )
            return

        try:
            raw_client = await self.voice_manager.join(channel, cls=VoiceRecvClient)
            voice_client = cast(VoiceRecvClient, raw_client)
            await self.voice_pipeline.start(voice_client)
            await interaction.response.send_message(
                f"Joined **{channel.name}** and started listening.",
                ephemeral=True,
            )
            logger.info(
                "Joined and listening on {} ({}) in guild {}",
                channel.name, channel.id, guild_id,
            )
        except discord.Forbidden:
            logger.error(
                "Missing permissions to join voice channel {} in guild {}",
                channel.name, guild_id,
            )
            await interaction.response.send_message(
                "I don't have permission to join that voice channel.",
                ephemeral=True,
            )
        except Exception:
            logger.exception(
                "Failed to join voice channel {} in guild {}",
                channel.name, guild_id,
            )
            await interaction.response.send_message(
                "Failed to join the voice channel. Please try again.",
                ephemeral=True,
            )

    @app_commands.command(name="leave", description="Leave the current voice channel")
    async def leave(self, interaction: discord.Interaction) -> None:
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        if not self.voice_manager.is_connected(guild_id):
            await interaction.response.send_message(
                "I'm not in a voice channel on this server.",
                ephemeral=True,
            )
            return

        await self.voice_pipeline.stop()
        await self.voice_manager.leave(guild_id)
        await interaction.response.send_message(
            "Left the voice channel.",
            ephemeral=True,
        )
        logger.info("Left voice channel in guild {}", guild_id)

    @app_commands.command(name="ping", description="Check if the bot is responsive")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            f"Pong! Latency: {latency}ms",
            ephemeral=True,
        )

    @app_commands.command(name="say", description="Make the bot say something in voice")
    @app_commands.describe(text="Text to speak")
    async def say(self, interaction: discord.Interaction, text: str) -> None:
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True,
            )
            return

        if self._tts_engine is None or not self._tts_engine.is_available():
            await interaction.response.send_message(
                "TTS engine is not available.", ephemeral=True,
            )
            return

        vc = self.voice_manager.get(guild_id)
        if vc is None:
            await interaction.response.send_message(
                "Bot is not in a voice channel. Use /join first.", ephemeral=True,
            )
            return

        await interaction.response.send_message(f"Saying: {text}", ephemeral=True)
        try:
            pcm_data = await self._tts_engine.synthesize(text)
            audio_source = discord.PCMAudio(io.BytesIO(pcm_data))
            cast(discord.VoiceClient, vc).play(audio_source)
            logger.info("TTS say: {} in guild {}", text, guild_id)
        except Exception:
            logger.exception("TTS /say failed")
            await interaction.followup.send("Failed to play audio.", ephemeral=True)

    @app_commands.command(name="chat", description="Send a text message to the bot for a response")
    @app_commands.describe(text="Message to send to the bot")
    async def chat(self, interaction: discord.Interaction, text: str) -> None:
        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True,
            )
            return

        cm = getattr(self.bot, "conversation_manager", None)
        if cm is None:
            await interaction.response.send_message(
                "Bot is not fully initialized yet.", ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        from gaming_ai.models import Utterance

        utterance = Utterance(
            player_id=str(interaction.user.id),
            text=text,
            timestamp=time.time(),
            language="en",
            guild_id=guild_id,
            channel_id=interaction.channel_id or 0,
        )

        logger.info("Chat command: processing utterance: {}", text)
        try:
            await cm.handle_utterance(utterance)
        except Exception:
            logger.exception("Chat command: handle_utterance failed")

        pending = cm.peek_pending_response(guild_id)
        if pending:
            await interaction.followup.send(
                f"**You:** {text}\n**Bot:** {pending}",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"**You:** {text}\n*(bot decided not to respond)*",
                ephemeral=True,
            )
