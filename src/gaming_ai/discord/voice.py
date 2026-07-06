from typing import Any

from discord import VoiceChannel, VoiceProtocol

from gaming_ai.utils.logging import logger


class VoiceManager:
    def __init__(self) -> None:
        self._connections: dict[int, VoiceProtocol] = {}

    async def join(
        self,
        channel: VoiceChannel,
        *,
        cls: type[VoiceProtocol] | None = None,
    ) -> VoiceProtocol:
        guild_id = channel.guild.id
        if guild_id in self._connections:
            vc = self._connections[guild_id]
            vc_channel = getattr(vc, "channel", None)
            if vc_channel is not None and vc_channel.id != channel.id:
                move_to = getattr(vc, "move_to", None)
                if move_to is not None:
                    await move_to(channel)
            return vc

        connect_kwargs: dict[str, Any] = {"timeout": 30.0}
        if cls is not None:
            connect_kwargs["cls"] = cls

        voice_client: VoiceProtocol = await channel.connect(**connect_kwargs)
        self._connections[guild_id] = voice_client
        logger.info(
            "Connected to voice channel {} ({}) in guild {}",
            channel.name, channel.id, guild_id,
        )
        return voice_client

    async def leave(self, guild_id: int) -> None:
        voice_client = self._connections.pop(guild_id, None)
        if voice_client is None:
            logger.warning(
                "Attempted to leave voice in guild {} but no connection found",
                guild_id,
            )
            return

        await voice_client.disconnect(force=False)
        logger.info("Disconnected from voice in guild {}", guild_id)

    def get(self, guild_id: int) -> VoiceProtocol | None:
        return self._connections.get(guild_id)

    def is_connected(self, guild_id: int) -> bool:
        return guild_id in self._connections

    async def disconnect_all(self) -> None:
        guild_ids = list(self._connections.keys())
        for guild_id in guild_ids:
            await self.leave(guild_id)
        logger.info("Disconnected from all voice channels")
