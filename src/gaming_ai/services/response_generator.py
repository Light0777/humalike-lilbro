import random

from gaming_ai.database.repositories.opinion import OpinionRepository
from gaming_ai.database.repositories.player import PlayerRepository
from gaming_ai.models import Utterance
from gaming_ai.models.behavior import (
    BehaviorConfig,
    MoodState,
    ResponseContext,
    ResponseIntent,
    ResponseType,
)
from gaming_ai.models.conversation import ConversationState
from gaming_ai.services.llm.service import LLMService
from gaming_ai.utils.logging import logger

ACKNOWLEDGMENTS: list[str] = [
    "Yeah, I hear you.",
    "Right.",
    "Okay.",
    "I see what you mean.",
    "Got it.",
    "Makes sense.",
    "Uh-huh.",
    "True.",
]

GREETINGS: list[str] = [
    "Hey there!",
    "Hi!",
    "Hello!",
    "Yo, what's up?",
    "Hey, glad you joined!",
    "Hi everyone!",
]

FAREWELLS: list[str] = [
    "Later!",
    "See ya!",
    "Good game, everyone!",
    "Catch you next time.",
    "Peace out!",
    "GG, see you around!",
]

PROMPTS: list[str] = [
    "So, what are we thinking?",
    "Anyone have a plan?",
    "What's the play?",
    "I'm listening.",
    "Thoughts?",
    "What should we do?",
]

OPINION_PREFIXES: list[str] = [
    "Honestly, ",
    "I think ",
    "In my opinion, ",
    "If you ask me, ",
    "Personally, ",
]


class ResponseGenerator:
    def __init__(
        self,
        opinion_repo: OpinionRepository | None = None,
        player_repo: PlayerRepository | None = None,
        config: BehaviorConfig | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self._opinion_repo = opinion_repo
        self._player_repo = player_repo
        self._config = config or BehaviorConfig()
        self._llm_service = llm_service

    async def generate(
        self,
        intent: ResponseIntent,
        context: ResponseContext,
        utterance: Utterance | None = None,
        session: ConversationState | None = None,
        mood: MoodState | None = None,
    ) -> str:
        if not intent.should_respond:
            return ""

        if self._llm_service is not None and utterance is not None and session is not None:
            llm_text = await self._llm_service.generate_response(
                utterance=utterance,
                session=session,
                mood=mood,
                player_name=context.player_name,
                familiarity=context.familiarity,
                trust=context.trust,
                rapport=context.rapport,
            )
            if llm_text:
                return llm_text

        return await self._fallback_generate(intent, context)

    async def _fallback_generate(
        self, intent: ResponseIntent, context: ResponseContext,
    ) -> str:
        response_type = intent.response_type

        if response_type == ResponseType.GREETING:
            text = self._pick(GREETINGS)
        elif response_type == ResponseType.FAREWELL:
            text = self._pick(FAREWELLS)
        elif response_type == ResponseType.OPINION:
            text = await self._build_opinion_text(context)
        elif response_type in (ResponseType.DIRECT_ANSWER, ResponseType.QUESTION):
            text = await self._build_answer_text(context)
        elif response_type == ResponseType.FOLLOW_UP:
            text = self._pick(PROMPTS)
        else:
            text = self._pick(ACKNOWLEDGMENTS)

        if intent.target_player_id and context.player_name and not context.player_name.isdigit():
            text = f"{context.player_name}: {text}"

        if self._config.max_response_length and len(text) > self._config.max_response_length:
            text = text[: self._config.max_response_length - 3] + "..."

        logger.debug("Generated fallback response [{}]: {}", response_type, text)
        return text

    # ── Response builders ───────────────────────────────────────────

    async def _build_answer_text(self, context: ResponseContext) -> str:
        topic = context.topic

        if self._opinion_repo and topic:
            try:
                opinions = await self._opinion_repo.find_by_topic(topic, limit=1)
            except Exception:
                opinions = []
            if opinions:
                opinion = opinions[0]
                sentiment = opinion.get("sentiment", 0) or 0
                confidence = opinion.get("confidence", 0) or 0
                if confidence >= self._config.opinion_confidence_threshold:
                    prefix = self._pick(OPINION_PREFIXES)
                    if sentiment > 0.3:
                        return f"{prefix}I like {topic}. It's pretty good."
                    elif sentiment < -0.3:
                        return f"{prefix}I'm not really a fan of {topic}."
                    else:
                        return f"{prefix}{topic} is okay, I guess."

        return self._build_neutral_comment(context)

    async def _build_opinion_text(self, context: ResponseContext) -> str:
        if not self._opinion_repo:
            return self._pick(ACKNOWLEDGMENTS)

        topic = context.topic
        if not topic:
            try:
                opinions = await self._opinion_repo.find_by_player(context.player_id, limit=3)
            except Exception:
                opinions = []
            if opinions:
                topics = [o.get("topic", "") for o in opinions if o.get("topic")]
                if topics:
                    target_topic = random.choice(topics)
                    try:
                        opinions_on = await self._opinion_repo.find_by_topic(target_topic, limit=1)
                    except Exception:
                        opinions_on = []
                    if opinions_on:
                        sentiment = opinions_on[0].get("sentiment", 0) or 0
                        if sentiment > 0:
                            return f"I have a positive opinion about {target_topic}."
                        elif sentiment < 0:
                            return f"I'm not a fan of {target_topic}."

        return self._build_neutral_comment(context)

    def _build_neutral_comment(self, context: ResponseContext) -> str:
        if context.is_question:
            return random.choice([
                "Hmm, good question. Let me think about that.",
                "I'm not sure, honestly.",
                "That's a tough one.",
                "Good question! I'd have to think about it.",
            ])
        return self._pick(ACKNOWLEDGMENTS)

    @staticmethod
    def _pick(options: list[str]) -> str:
        return random.choice(options)
