from typing import Any, cast

from gaming_ai.database.repositories.base import BaseRepository


class RelationshipRepository(BaseRepository):
    @property
    def table_name(self) -> str:
        return "relationships"

    async def find_by_player(self, player_id: str) -> dict[str, Any] | None:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .eq("player_id", player_id)
            .limit(1)
            .execute()
        )
        return cast(dict[str, Any], result.data[0]) if result.data else None

    async def upsert(
        self, player_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        existing = await self.find_by_player(player_id)
        if existing:
            update_data = {**data, "updated_at": self._now()}
            result = await (
                self._client.table(self.table_name)
                .update(update_data)
                .eq("player_id", player_id)
                .execute()
            )
            return cast(dict[str, Any], result.data[0])
        else:
            return await self.insert({
                "player_id": player_id,
                **data,
            })
