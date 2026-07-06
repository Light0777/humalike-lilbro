from typing import Any, cast

from gaming_ai.database.repositories.base import BaseRepository


class MemoryRepository(BaseRepository):
    @property
    def table_name(self) -> str:
        return "memories"

    async def find_by_player(
        self, player_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .eq("player_id", player_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return cast(list[dict[str, Any]], result.data)

    async def find_important(
        self, min_importance: float = 0.7, limit: int = 20
    ) -> list[dict[str, Any]]:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .gte("importance", min_importance)
            .order("importance", desc=True)
            .limit(limit)
            .execute()
        )
        return cast(list[dict[str, Any]], result.data)

    async def mark_recalled(self, memory_id: str) -> None:
        memory = await self.find_by_id(memory_id)
        if memory:
            await self.update(memory_id, {
                "recall_count": (memory.get("recall_count", 0) or 0) + 1,
                "last_recalled_at": self._now(),
            })
