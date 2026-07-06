from typing import Any, cast

from gaming_ai.database.repositories.base import BaseRepository


class OpinionRepository(BaseRepository):
    @property
    def table_name(self) -> str:
        return "opinions"

    async def find_by_player(
        self, player_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .eq("player_id", player_id)
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return cast(list[dict[str, Any]], result.data)

    async def find_by_topic(
        self, topic: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .eq("topic", topic)
            .order("confidence", desc=True)
            .limit(limit)
            .execute()
        )
        return cast(list[dict[str, Any]], result.data)

    async def find_player_opinion(
        self,
        player_id: str,
        topic: str,
        target_player_id: str | None = None,
    ) -> dict[str, Any] | None:
        query = (
            self._client.table(self.table_name)
            .select("*")
            .eq("player_id", player_id)
            .eq("topic", topic)
        )
        if target_player_id:
            query = query.eq("target_player_id", target_player_id)
        else:
            query = query.is_("target_player_id", "null")
        result = await query.limit(1).execute()
        return cast(dict[str, Any], result.data[0]) if result.data else None

    async def upsert(
        self,
        player_id: str,
        topic: str,
        data: dict[str, Any],
        target_player_id: str | None = None,
    ) -> dict[str, Any]:
        existing = await self.find_player_opinion(
            player_id, topic, target_player_id,
        )
        if existing:
            update_data = {**data, "updated_at": self._now()}
            result = await (
                self._client.table(self.table_name)
                .update(update_data)
                .eq("id", existing["id"])
                .execute()
            )
            return cast(dict[str, Any], result.data[0])
        else:
            insert_data: dict[str, Any] = {
                "player_id": player_id,
                "topic": topic,
                **data,
            }
            if target_player_id:
                insert_data["target_player_id"] = target_player_id
            result = await (
                self._client.table(self.table_name)
                .insert(insert_data)
                .execute()
            )
            return cast(dict[str, Any], result.data[0])
