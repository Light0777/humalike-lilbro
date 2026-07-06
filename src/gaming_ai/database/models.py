from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlayerRecord:
    id: str = ""
    discord_id: str = ""
    name: str = ""
    display_name: str = ""
    first_seen_at: str = ""
    last_active_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class SessionRecord:
    id: str = ""
    guild_id: str = ""
    channel_id: str = ""
    game_name: str | None = None
    started_at: str = ""
    ended_at: str | None = None
    turn_count: int = 0
    speaker_count: int = 0
    summary: str | None = None
    created_at: str = ""


@dataclass
class EventRecord:
    id: str = ""
    session_id: str | None = None
    player_id: str | None = None
    type: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    event_timestamp: str = ""
    created_at: str = ""


@dataclass
class ConversationRecord:
    id: str = ""
    session_id: str | None = None
    player_id: str | None = None
    text: str = ""
    language: str = "en"
    is_interruption: bool = False
    silence_before: float = 0.0
    response_text: str | None = None
    emotion: str = "neutral"
    turn_timestamp: str = ""
    created_at: str = ""


@dataclass
class RelationshipRecord:
    id: str = ""
    player_id: str = ""
    familiarity: float = 0.0
    trust: float = 0.5
    rapport: float = 0.5
    total_interactions: int = 0
    last_interaction_at: str | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class MemoryRecord:
    id: str = ""
    player_id: str | None = None
    type: str = "fact"
    content: str = ""
    importance: float = 0.5
    context: dict[str, Any] = field(default_factory=dict)
    last_recalled_at: str | None = None
    recall_count: int = 0
    created_at: str = ""


@dataclass
class OpinionRecord:
    id: str = ""
    player_id: str | None = None
    target_player_id: str | None = None
    topic: str = ""
    sentiment: float = 0.0
    confidence: float = 0.5
    source: str = "observed"
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
