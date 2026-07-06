import uuid
from typing import Any, cast

from gaming_ai.utils.logging import logger

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

_HUMALIKE_BASE = "https://api.humalike.com"
_THREAD_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "humalike-lilbro")


class HumalikeService:
    def __init__(self, api_key: str, base_url: str = _HUMALIKE_BASE) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._threads: dict[str, str] = {}
        self._available = bool(api_key) and _HAS_HTTPX

    def is_available(self) -> bool:
        return self._available

    async def ensure_thread(self, guild_id: str) -> str | None:
        thread_id = self._threads.get(guild_id)
        if thread_id:
            return thread_id

        if not self._available:
            return None

        thread_uuid = str(uuid.uuid5(_THREAD_NAMESPACE, guild_id))

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/turn-taking/actions/open_thread",
                    headers=self._headers(),
                    json={"thread_id": thread_uuid},
                )
                if resp.is_error:
                    logger.warning(
                        "Humalike open_thread failed ({}): {}",
                        resp.status_code, resp.text[:120],
                    )
                    return None

                data = resp.json()
                tid = cast(str, data["thread"]["id"])
                self._threads[guild_id] = tid
                logger.info("Humalike thread opened for guild {}: {}", guild_id, tid)
                return tid

        except Exception:
            logger.exception("Humalike open_thread error for guild {}", guild_id)
            return None

    async def should_speak(
        self,
        guild_id: str,
        sender: str,
        content: str,
        system_prompt: str = "",
    ) -> bool | None:
        if not self._available:
            return None

        tid = await self.ensure_thread(guild_id)
        if tid is None:
            return None

        try:
            body: dict[str, Any] = {
                "thread_id": tid,
                "messages": [{"sender": sender, "content": content}],
            }
            if system_prompt:
                body["system_prompt"] = system_prompt

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self._base_url}/v1/turn-taking/actions/submit_messages",
                    headers=self._headers(),
                    json=body,
                )
                if resp.is_error:
                    logger.warning(
                        "Humalike submit_messages failed ({}): {}",
                        resp.status_code, resp.text[:120],
                    )
                    return None

                data = resp.json()
                decision = cast(str, data.get("decision", "stay_silent"))
                logger.debug(
                    "Humalike decision for {}: {} (epoch={})",
                    sender, decision, data.get("turn_epoch"),
                )
                return decision == "speak"

        except Exception:
            logger.exception("Humalike should_speak error for guild {}", guild_id)
            return None

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def reset_thread(self, guild_id: str) -> None:
        self._threads.pop(guild_id, None)
