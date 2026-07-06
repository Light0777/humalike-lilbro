import time
from collections import Counter

from gaming_ai.models import Utterance
from gaming_ai.models.conversation import (
    ConversationState,
    SpeakerState,
    TurnRecord,
)
from gaming_ai.utils.logging import logger

STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "this", "that", "these", "those",
    "and", "or", "but", "if", "because", "so", "then",
    "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "up", "about", "into", "over", "after", "before",
    "do", "does", "did", "done", "have", "has", "had",
    "not", "no", "yes", "yeah", "okay", "ok", "oh", "ah",
    "like", "just", "really", "very", "well", "right",
    "get", "got", "go", "went", "going", "say", "said",
    "know", "think", "see", "want", "come", "let", "can", "will",
    "hello", "hi", "hey", "yo", "sup", "greetings", "howdy",
    "what", "why", "when", "where", "who", "how", "which",
    "whats", "what's", "whos", "who's", "hows", "how's",
    "bye", "goodbye", "later", "peace", "out",
}


class ConversationEngine:
    def __init__(self, interruption_window: float = 1.5) -> None:
        self.interruption_window = interruption_window
        self._sessions: dict[int, ConversationState] = {}
        self._last_utterance_time: float | None = None
        self._last_speaker_id: str | None = None

    # ── Session management ──────────────────────────────────────────

    def get_or_create_session(self, guild_id: int, channel_id: int) -> ConversationState:
        if guild_id not in self._sessions:
            now = time.time()
            self._sessions[guild_id] = ConversationState(
                guild_id=guild_id,
                channel_id=channel_id,
                started_at=now,
                last_activity_at=now,
            )
            logger.info("Started conversation session for guild {}", guild_id)
        return self._sessions[guild_id]

    def end_session(self, guild_id: int) -> ConversationState | None:
        session = self._sessions.pop(guild_id, None)
        if session is not None:
            logger.info(
                "Ended conversation session for guild {} ({} turns, {} speakers)",
                guild_id, len(session.turns), len(session.speakers),
            )
        return session

    def get_session(self, guild_id: int) -> ConversationState | None:
        return self._sessions.get(guild_id)

    def set_game(self, guild_id: int, game_name: str) -> None:
        session = self._sessions.get(guild_id)
        if session is not None:
            session.game_name = game_name
            logger.info("Game set to {} for guild {}", game_name, guild_id)

    # ── Utterance processing ────────────────────────────────────────

    async def process_utterance(self, utterance: Utterance) -> None:
        if utterance.guild_id is None:
            return

        guild_id = utterance.guild_id
        session = self.get_or_create_session(guild_id, utterance.channel_id or 0)

        now = utterance.timestamp
        speaker = self._get_or_create_speaker(session, utterance)

        silence_before = 0.0
        if self._last_utterance_time is not None:
            silence_before = now - self._last_utterance_time

        is_interruption = self._detect_interruption(
            session, utterance, silence_before,
        )

        turn = TurnRecord(
            utterance=utterance,
            is_interruption=is_interruption,
            silence_before=silence_before,
        )

        session.turns.append(turn)
        if len(session.turns) > session.max_turns:
            session.turns.pop(0)

        speaker.last_utterance_at = now
        speaker.utterance_count += 1
        session.last_activity_at = now
        self._last_utterance_time = now
        self._last_speaker_id = utterance.player_id

        self._update_topic(session, utterance.text)

        logger.debug(
            "Turn #{}: user={}, lang={}, topic={}, silence={:.1f}s{}",
            len(session.turns),
            utterance.player_id,
            utterance.language,
            session.active_topic or "?",
            silence_before,
            " [INTERRUPTION]" if is_interruption else "",
        )

    # ── Queries ─────────────────────────────────────────────────────

    def get_silence_duration(self, guild_id: int) -> float:
        session = self._sessions.get(guild_id)
        if session is None:
            return 0.0
        return time.time() - session.last_activity_at

    def get_active_speakers(self, guild_id: int) -> list[SpeakerState]:
        session = self._sessions.get(guild_id)
        if session is None:
            return []
        now = time.time()
        return [
            s for s in session.speakers.values()
            if s.last_utterance_at is not None
            and (now - s.last_utterance_at) < 300
        ]

    def get_recent_turns(self, guild_id: int, n: int = 10) -> list[TurnRecord]:
        session = self._sessions.get(guild_id)
        if session is None:
            return []
        return session.turns[-n:]

    def get_active_guilds(self) -> list[int]:
        return list(self._sessions.keys())

    def get_session_summary(self, guild_id: int) -> dict[str, object]:
        session = self._sessions.get(guild_id)
        if session is None:
            return {}
        return {
            "duration_seconds": time.time() - session.started_at,
            "total_turns": len(session.turns),
            "active_speakers": len(session.speakers),
            "speakers": [
                {"id": s.user_id, "name": s.name, "utterances": s.utterance_count}
                for s in session.speakers.values()
            ],
            "active_topic": session.active_topic,
            "game": session.game_name,
        }

    # ── Internals ───────────────────────────────────────────────────

    def _get_or_create_speaker(
        self, session: ConversationState, utterance: Utterance,
    ) -> SpeakerState:
        uid = utterance.player_id
        if uid not in session.speakers:
            session.speakers[uid] = SpeakerState(
                user_id=uid,
                name=uid,
                joined_at=utterance.timestamp,
            )
        return session.speakers[uid]

    def _detect_interruption(
        self,
        session: ConversationState,
        utterance: Utterance,
        silence_before: float,
    ) -> bool:
        if silence_before > self.interruption_window:
            return False
        if self._last_speaker_id is None:
            return False
        if self._last_speaker_id == utterance.player_id:
            return False
        return True

    def _update_topic(self, session: ConversationState, text: str) -> None:
        words = text.lower().split()
        meaningful = [
            w.strip(".,!?;:'\"()[]")
            for w in words
            if w not in STOP_WORDS and len(w) > 2
        ]
        if not meaningful:
            return

        if session.game_name:
            session.active_topic = session.game_name
            return

        recent_text = ""
        for turn in session.turns[-5:]:
            recent_text += " " + turn.utterance.text.lower()

        all_words = [
            w.strip(".,!?;:'\"()[]")
            for w in recent_text.split()
            if w not in STOP_WORDS and len(w) > 2
        ]
        if all_words:
            common = Counter(all_words).most_common(3)
            session.active_topic = ", ".join(w for w, _ in common)
