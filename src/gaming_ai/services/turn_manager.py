import random

from gaming_ai.models import Utterance
from gaming_ai.models.behavior import (
    BehaviorConfig,
    MoodState,
    ResponseContext,
    ResponseIntent,
    ResponseType,
)
from gaming_ai.models.conversation import ConversationState
from gaming_ai.utils.logging import logger

QUESTION_WORDS: set[str] = {
    "what", "how", "why", "when", "where", "who", "which",
    "do", "does", "did", "is", "are", "was", "were",
    "can", "could", "would", "should", "will", "shall",
    "have", "has", "had",
}

GREETING_WORDS: set[str] = {
    "hello", "hi", "hey", "yo", "sup", "greetings",
    "good morning", "good evening", "good afternoon",
    "what's up", "wassup", "howdy",
}

FAREWELL_WORDS: set[str] = {
    "bye", "goodbye", "later", "see ya", "see you",
    "gotta go", "out", "peace", "adios",
}

BOT_NAMES: set[str] = {
    "bot", "ai", "assistant", "bro", "gaming ai",
}


class TurnManager:
    def __init__(self, config: BehaviorConfig | None = None) -> None:
        self._config = config or BehaviorConfig()

    async def decide_response(
        self,
        utterance: Utterance,
        session: ConversationState,
        mood: MoodState,
        familiarity: float = 0.0,
        trust: float = 0.5,
        rapport: float = 0.5,
    ) -> ResponseIntent:
        text = utterance.text.strip()
        if not text:
            logger.debug("Empty utterance, no response")
            return ResponseIntent()

        context = await self.build_context(utterance, session, mood, familiarity, trust, rapport)
        logger.debug(
            "Decide: text={!r:.60} q={} g={} f={} a={} sil={:.1f}s fam={:.2f}",
            text, context.is_question, context.is_greeting, context.is_farewell,
            context.is_direct_address, context.silence_before, familiarity,
        )

        if context.is_greeting and context.silence_before < self._config.greeting_silence_threshold:
            logger.debug("-> greeting response")
            return await self._greeting_response(context)

        if context.is_farewell and context.silence_before > self._config.farewell_silence_threshold:
            logger.debug("-> farewell response")
            return await self._farewell_response(context)

        if context.is_question:
            logger.debug("-> question response")
            return await self._question_response(context)

        if context.is_direct_address:
            logger.debug("-> direct address response")
            return await self._direct_address_response(context)

        if context.silence_before > self._config.max_silence_before_prompt:
            logger.debug("-> prompt response (extended silence)")
            return await self._prompt_response(context)

        if len(text) > 3:
            prob = (
                0.2
                if familiarity < self._config.familiarity_casual_threshold
                else min(0.8, 0.3 + familiarity * 0.7)
            )
            if random.random() < prob:
                logger.debug("-> casual response (prob={:.2f})", prob)
                return await self._casual_response(context)
            else:
                logger.debug("-> no response (prob={:.2f} missed)", prob)

        return ResponseIntent()

    # ── Context builder ─────────────────────────────────────────────

    async def build_context(
        self,
        utterance: Utterance,
        session: ConversationState,
        mood: MoodState,
        familiarity: float,
        trust: float,
        rapport: float,
    ) -> ResponseContext:
        text = utterance.text.lower()
        silence_before = 0.0
        if session.turns:
            last_turn = session.turns[-1]
            silence_before = last_turn.silence_before

        return ResponseContext(
            utterance_text=utterance.text,
            player_id=utterance.player_id,
            player_name=self._get_player_name(utterance.player_id, session),
            topic=session.active_topic or "",
            is_question=self._is_question(text),
            is_greeting=self._is_greeting(text),
            is_farewell=self._is_farewell(text),
            is_direct_address=self._is_direct_address(text),
            silence_before=silence_before,
            mood=mood,
            familiarity=familiarity,
            trust=trust,
            rapport=rapport,
        )

    # ── Response type decision helpers ──────────────────────────────

    async def _greeting_response(self, context: ResponseContext) -> ResponseIntent:
        logger.debug("Greeting detected from player {}", context.player_id)
        return ResponseIntent(
            should_respond=True,
            priority=7,
            response_type=ResponseType.GREETING,
            delay=0.5,
            target_player_id=context.player_id,
        )

    async def _farewell_response(self, context: ResponseContext) -> ResponseIntent:
        logger.debug("Farewell detected from player {}", context.player_id)
        return ResponseIntent(
            should_respond=True,
            priority=6,
            response_type=ResponseType.FAREWELL,
            delay=0.5,
            target_player_id=context.player_id,
        )

    async def _question_response(self, context: ResponseContext) -> ResponseIntent:
        logger.debug(
            "Question detected from player {}: {}",
            context.player_id, context.utterance_text[:60],
        )
        return ResponseIntent(
            should_respond=True,
            priority=8,
            response_type=ResponseType.DIRECT_ANSWER,
            delay=self._config.question_response_delay,
            target_player_id=context.player_id,
        )

    async def _direct_address_response(self, context: ResponseContext) -> ResponseIntent:
        logger.debug("Direct address from player {}", context.player_id)
        return ResponseIntent(
            should_respond=True,
            priority=9,
            response_type=ResponseType.DIRECT_ANSWER,
            delay=0.5,
            target_player_id=context.player_id,
        )

    async def _prompt_response(self, context: ResponseContext) -> ResponseIntent:
        logger.debug("Extended silence, prompting player {}", context.player_id)
        return ResponseIntent(
            should_respond=True,
            priority=3,
            response_type=ResponseType.FOLLOW_UP,
            delay=0.8,
            target_player_id=context.player_id,
        )

    async def _casual_response(self, context: ResponseContext) -> ResponseIntent:
        logger.debug("Casual response triggered for player {}", context.player_id)
        return ResponseIntent(
            should_respond=True,
            priority=2,
            response_type=ResponseType.ACKNOWLEDGMENT,
            delay=1.0,
            target_player_id=context.player_id,
        )

    # ── Detection helpers ───────────────────────────────────────────

    def _is_question(self, text: str) -> bool:
        if text.rstrip().endswith("?"):
            return True
        first_word = text.split()[0] if text.split() else ""
        return first_word in QUESTION_WORDS

    def _is_greeting(self, text: str) -> bool:
        text_lower = text.lower().strip().rstrip("?!.")
        for word in GREETING_WORDS:
            if word in text_lower:
                return True
        return False

    def _is_farewell(self, text: str) -> bool:
        text_lower = text.lower().strip().rstrip("?!.")
        for word in FAREWELL_WORDS:
            if word in text_lower:
                return True
        return False

    def _is_direct_address(self, text: str) -> bool:
        text_lower = text.lower()
        for name in BOT_NAMES:
            if name in text_lower:
                return True
        return False

    @staticmethod
    def _get_player_name(player_id: str, session: ConversationState) -> str:
        speaker = session.speakers.get(player_id)
        return speaker.name if speaker else player_id
