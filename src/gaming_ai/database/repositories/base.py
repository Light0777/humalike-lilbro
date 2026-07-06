from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, cast

from postgrest.types import CountMethod
from supabase._async.client import AsyncClient


class BaseRepository(ABC):
    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    @property
    @abstractmethod
    def table_name(self) -> str:
        ...

    async def find_by_id(self, id: str) -> dict[str, Any] | None:
        result = await (
            self._client.table(self.table_name)
            .select("*")
            .eq("id", id)
            .execute()
        )
        return cast(dict[str, Any], result.data[0]) if result.data else None

    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> list[dict[str, Any]]:
        query = (
            self._client.table(self.table_name)
            .select("*")
            .order(order_by, desc=descending)
            .range(offset, offset + limit - 1)
        )
        result = await query.execute()
        return cast(list[dict[str, Any]], result.data)

    async def insert(self, data: dict[str, Any]) -> dict[str, Any]:
        result = await (
            self._client.table(self.table_name)
            .insert(data)
            .execute()
        )
        return cast(dict[str, Any], result.data[0])

    async def update(
        self, id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        result = await (
            self._client.table(self.table_name)
            .update(data)
            .eq("id", id)
            .execute()
        )
        return cast(dict[str, Any], result.data[0])

    async def delete(self, id: str) -> None:
        await (
            self._client.table(self.table_name)
            .delete()
            .eq("id", id)
            .execute()
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    async def count(self, column: str = "id") -> int:
        result = await (
            self._client.table(self.table_name)
            .select(column, count=CountMethod.exact)
            .execute()
        )
        return result.count or 0
