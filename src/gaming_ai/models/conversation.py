from dataclasses import dataclass, field

from gaming_ai.models import Utterance


@dataclass
class SpeakerState:
    user_id: str
    name: str
    joined_at: float
    last_utterance_at: float | None = None
    utterance_count: int = 0
    is_speaking: bool = False


@dataclass
class TurnRecord:
    utterance: Utterance
    is_interruption: bool = False
    silence_before: float = 0.0


@dataclass
class ConversationState:
    guild_id: int
    channel_id: int
    started_at: float
    last_activity_at: float
    speakers: dict[str, SpeakerState] = field(default_factory=dict)
    turns: list[TurnRecord] = field(default_factory=list)
    active_topic: str | None = None
    game_name: str | None = None
    max_turns: int = 100


@dataclass
class InterruptionInfo:
    interrupted_user_id: str
    interrupting_user_id: str
    timestamp: float
