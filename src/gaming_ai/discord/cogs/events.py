import traceback

import discord
from discord import app_commands
from discord.ext import commands

from gaming_ai.utils.logging import logger


class EventHandlers(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        assert self.bot.user is not None
        logger.info(
            "Bot is ready. Logged in as {} ({})",
            self.bot.user, self.bot.user.id,
        )
        for guild in self.bot.guilds:
            logger.info("  Connected to guild: {} ({})", guild.name, guild.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        logger.info("Joined guild: {} ({})", guild.name, guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        logger.info("Removed from guild: {} ({})", guild.name, guild.id)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        bot_user = self.bot.user
        if bot_user is None:
            return
        if member.id == bot_user.id:
            if before.channel and not after.channel:
                logger.info(
                    "Bot was disconnected from voice in guild {}",
                    member.guild.id,
                )
            elif not before.channel and after.channel:
                logger.info(
                    "Bot connected to voice in guild {}",
                    member.guild.id,
                )

    @commands.Cog.listener()
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Command on cooldown. Try again in {error.retry_after:.0f}s.",
                ephemeral=True,
            )
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True,
            )
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                "I don't have the required permissions: "
                + ", ".join(error.missing_permissions),
                ephemeral=True,
            )
        elif isinstance(error, app_commands.CommandNotFound):
            await interaction.response.send_message(
                "Command not found.", ephemeral=True,
            )
        else:
            logger.error("Unhandled command error: {}", error)
            logger.debug("Traceback:\n{}", traceback.format_exc())
            await interaction.response.send_message(
                "An unexpected error occurred.",
                ephemeral=True,
            )
