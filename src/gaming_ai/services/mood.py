import time

from gaming_ai.models import Utterance
from gaming_ai.models.behavior import BehaviorConfig, MoodState
from gaming_ai.utils.logging import logger

POSITIVE_WORDS: set[str] = {
    "love", "amazing", "awesome", "great", "fun", "nice", "cool",
    "good", "best", "fantastic", "wonderful", "excellent", "happy",
    "beautiful", "perfect", "win", "victory", "champion",
}

NEGATIVE_WORDS: set[str] = {
    "hate", "terrible", "awful", "worst", "bad", "horrible",
    "sucks", "stupid", "annoying", "frustrating", "angry", "sad",
    "disappointed", "ugly", "loss", "defeat", "boring",
}


class MoodEngine:
    def __init__(self, config: BehaviorConfig | None = None) -> None:
        self._config = config or BehaviorConfig()
        self._moods: dict[int, MoodState] = {}

    def _get_or_create(self, guild_id: int) -> MoodState:
        if guild_id not in self._moods:
            self._moods[guild_id] = MoodState(last_updated=time.time())
        return self._moods[guild_id]

    def get_mood(self, guild_id: int) -> MoodState:
        mood = self._get_or_create(guild_id)
        self._apply_decay(mood)
        return mood

    def update_from_utterance(self, utterance: Utterance, guild_id: int) -> None:
        mood = self._get_or_create(guild_id)
        self._apply_decay(mood)

        text_lower = utterance.text.lower()
        for word in POSITIVE_WORDS:
            if word in text_lower:
                mood.valence = min(mood.valence + self._config.mood_update_from_event * 0.5, 1.0)
                mood.energy = min(mood.energy + self._config.mood_update_from_event * 0.3, 1.0)
                break

        for word in NEGATIVE_WORDS:
            if word in text_lower:
                mood.valence = max(mood.valence - self._config.mood_update_from_event * 0.5, -1.0)
                mood.energy = max(mood.energy - self._config.mood_update_from_event * 0.2, 0.0)
                break

        mood.confidence = min(
            mood.confidence + self._config.mood_update_from_event * 0.1,
            1.0,
        )
        mood.last_updated = time.time()

        logger.debug("Mood updated for guild {}: valence={:.2f}, energy={:.2f}, confidence={:.2f}",
                      guild_id, mood.valence, mood.energy, mood.confidence)

    def update_from_speaker_relationship(
        self, guild_id: int, familiarity: float, trust: float,
    ) -> None:
        mood = self._get_or_create(guild_id)
        self._apply_decay(mood)

        mood.confidence = max(mood.confidence, trust * 0.8)
        if familiarity > self._config.familiarity_casual_threshold:
            mood.energy = min(mood.energy + 0.05, 1.0)

        mood.last_updated = time.time()

    def reset_session(self, guild_id: int) -> None:
        self._moods[guild_id] = MoodState(last_updated=time.time())

    def _apply_decay(self, mood: MoodState) -> None:
        now = time.time()
        elapsed = now - mood.last_updated
        if elapsed < 30:
            return

        decay_factor = self._config.mood_decay_rate * (elapsed / 60)
        if mood.valence > 0:
            mood.valence = max(mood.valence - decay_factor, 0.0)
        elif mood.valence < 0:
            mood.valence = min(mood.valence + decay_factor, 0.0)

        if mood.energy > 0.5:
            mood.energy = max(mood.energy - decay_factor * 0.5, 0.5)
        elif mood.energy < 0.5:
            mood.energy = min(mood.energy + decay_factor * 0.5, 0.5)

        mood.last_updated = now
