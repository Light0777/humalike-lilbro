from typing import Any, cast

from gaming_ai.database.repositories.base import BaseRepository


class PlayerRepository(BaseRepository):
    @property
    def table_name(self) -> str:
        return "players"

    async def find_by_discord_id(self, discord_id: str) -> dict[str, Any] | None:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .eq("discord_id", discord_id)
            .limit(1)
            .execute()
        )
        return cast(dict[str, Any], result.data[0]) if result.data else None

    async def upsert_by_discord_id(
        self, discord_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        existing = await self.find_by_discord_id(discord_id)
        if existing:
            update_data = {**data, "updated_at": self._now()}
            result = await (
                self._client.table(self.table_name)
                .update(update_data)
                .eq("discord_id", discord_id)
                .execute()
            )
            return cast(dict[str, Any], result.data[0])
        else:
            return await self.insert({
                "discord_id": discord_id,
                **data,
            })

    async def update_last_active(self, player_id: str) -> None:
        await self.update(player_id, {"last_active_at": self._now()})
