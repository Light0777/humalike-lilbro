from typing import Any, cast

from gaming_ai.database.repositories.base import BaseRepository


class EventRepository(BaseRepository):
    @property
    def table_name(self) -> str:
        return "events"

    async def find_by_session(
        self, session_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .eq("session_id", session_id)
            .order("event_timestamp", desc=False)
            .limit(limit)
            .execute()
        )
        return cast(list[dict[str, Any]], result.data)

    async def find_by_type(
        self, event_type: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .eq("type", event_type)
            .order("event_timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        return cast(list[dict[str, Any]], result.data)
