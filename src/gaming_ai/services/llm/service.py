from typing import Any

from gaming_ai.models import Utterance
from gaming_ai.models.behavior import MoodState
from gaming_ai.models.conversation import ConversationState, TurnRecord
from gaming_ai.services.llm.client import LLMClient
from gaming_ai.services.memory import MemoryEngine
from gaming_ai.utils.logging import logger

SYSTEM_PROMPT = (
    "You are a friendly AI gaming teammate in a Discord voice chat. "
    "You play multiplayer games with friends and join voice conversations. "
    "Be conversational, natural, and concise (1-3 sentences typically). "
    "Use casual language like a friend would. "
    "You can code-switch between Hindi and English naturally. "
    "Don't be overly formal or robotic. "
    "If you don't know something, just say so. "
    "Never break character or mention that you're an AI."
)


class LLMService:
    def __init__(
        self,
        client: LLMClient,
        memory_engine: MemoryEngine | None = None,
    ) -> None:
        self._client = client
        self._memory_engine = memory_engine

    async def generate_response(
        self,
        utterance: Utterance,
        session: ConversationState | None,
        mood: MoodState | None = None,
        player_name: str = "",
        familiarity: float = 0.0,
        trust: float = 0.5,
        rapport: float = 0.5,
    ) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        context_parts: list[str] = []
        if mood is not None:
            context_parts.append(
                f"Mood — valence:{mood.valence:.1f} "
                f"energy:{mood.energy:.1f} "
                f"confidence:{mood.confidence:.1f}",
            )
        context_parts.append(
            f"Relationship — familiarity:{familiarity:.1f} "
            f"trust:{trust:.1f} "
            f"rapport:{rapport:.1f}",
        )

        if self._memory_engine and utterance.guild_id is not None:
            player_profile = await self._memory_engine.remember_player(utterance.player_id)
            if player_profile:
                context_parts.append(f"Player profile:\n{player_profile}")

            relevant = await self._memory_engine.recall_for_context(
                query=utterance.text,
                player_id=utterance.player_id,
                limit=3,
            )
            if relevant:
                context_parts.append(f"Relevant memories:\n{relevant}")

        if session is not None:
            turns_html = self._format_history(session.turns[-6:])
            if turns_html:
                context_parts.append(f"Recent conversation:\n{turns_html}")

        if player_name:
            context_parts.append(f'{player_name} just said: "{utterance.text}"')
        else:
            context_parts.append(f'The player just said: "{utterance.text}"')

        context_text = "\n\n".join(context_parts)
        messages.append({"role": "user", "content": context_text})

        try:
            response = await self._client.chat(messages=messages)
            logger.debug("LLM response: {}", response[:120])
            return response
        except Exception:
            logger.exception("LLM response generation failed")
            return ""

    def _format_history(self, turns: list[TurnRecord]) -> str:
        if not turns:
            return ""
        lines: list[str] = []
        for turn in turns:
            uid = turn.utterance.player_id
            text = turn.utterance.text or ""
            tag = "[interruption]" if turn.is_interruption else ""
            lines.append(f"  {uid}: {text}{tag}")
        return "\n".join(lines)

    def is_available(self) -> bool:
        return self._client.is_available()
