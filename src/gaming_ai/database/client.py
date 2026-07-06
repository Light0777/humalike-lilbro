
from loguru import logger
from supabase import create_async_client
from supabase._async.client import AsyncClient


class DatabaseClient:
    def __init__(self, url: str, key: str) -> None:
        self._url = url
        self._key = key
        self._client: AsyncClient | None = None

    async def connect(self) -> AsyncClient:
        if self._client is None:
            self._client = await create_async_client(self._url, self._key)
            logger.info("Connected to Supabase database")
        return self._client

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.aclose()  # type: ignore[attr-defined]
            self._client = None
            logger.info("Disconnected from Supabase database")

    async def get_client(self) -> AsyncClient:
        if self._client is None:
            return await self.connect()
        return self._client

    def is_connected(self) -> bool:
        return self._client is not None
