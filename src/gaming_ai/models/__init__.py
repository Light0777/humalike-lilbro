from dataclasses import dataclass


@dataclass
class Player:
    id: str
    name: str
    discord_id: str | None = None


@dataclass
class Utterance:
    player_id: str
    text: str
    timestamp: float
    language: str = "en"
    is_interruption: bool = False
    guild_id: int | None = None
    channel_id: int | None = None


@dataclass
class ConversationTurn:
    utterance: Utterance
    response: str | None = None
    emotion: str = "neutral"
