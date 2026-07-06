from typing import Any, cast

from gaming_ai.database.repositories.base import BaseRepository


class SessionRepository(BaseRepository):
    @property
    def table_name(self) -> str:
        return "sessions"

    async def find_active_by_guild(self, guild_id: str) -> dict[str, Any] | None:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .eq("guild_id", guild_id)
            .is_("ended_at", "null")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        return cast(dict[str, Any], result.data[0]) if result.data else None

    async def end_session(self, session_id: str, summary: str | None = None) -> dict[str, Any]:
        return await self.update(session_id, {
            "ended_at": self._now(),
            "summary": summary,
        })

    async def find_by_guild(
        self, guild_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .eq("guild_id", guild_id)
            .order("started_at", desc=True)
            .limit(limit)
            .execute()
        )
        return cast(list[dict[str, Any]], result.data)
