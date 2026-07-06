from typing import Any, cast

from postgrest.types import CountMethod

from gaming_ai.database.repositories.base import BaseRepository


class ConversationRepository(BaseRepository):
    @property
    def table_name(self) -> str:
        return "conversations"

    async def find_by_session(
        self, session_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .eq("session_id", session_id)
            .order("turn_timestamp", desc=False)
            .limit(limit)
            .execute()
        )
        return cast(list[dict[str, Any]], result.data)

    async def find_by_player(
        self, player_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .eq("player_id", player_id)
            .order("turn_timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return cast(list[dict[str, Any]], result.data)

    async def count_by_session(self, session_id: str) -> int:
        result = await (
            self._client.table(self.table_name)
            .select("id", count=CountMethod.exact)
            .eq("session_id", session_id)
            .execute()
        )
        return result.count or 0
