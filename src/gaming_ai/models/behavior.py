from dataclasses import dataclass, field


class ResponseType:
    SILENT = "silent"
    ACKNOWLEDGMENT = "acknowledgment"
    QUESTION = "question"
    OPINION = "opinion"
    GREETING = "greeting"
    FAREWELL = "farewell"
    FOLLOW_UP = "follow_up"
    DIRECT_ANSWER = "direct_answer"


@dataclass
class MoodState:
    valence: float = 0.0
    energy: float = 0.5
    confidence: float = 0.5
    last_updated: float = 0.0


@dataclass
class ResponseIntent:
    should_respond: bool = False
    priority: int = 0
    response_type: str = ResponseType.SILENT
    delay: float = 1.0
    response_text: str = ""
    target_player_id: str | None = None


@dataclass
class ResponseContext:
    utterance_text: str = ""
    player_id: str = ""
    player_name: str = ""
    topic: str = ""
    is_question: bool = False
    is_greeting: bool = False
    is_farewell: bool = False
    is_direct_address: bool = False
    silence_before: float = 0.0
    mood: MoodState = field(default_factory=MoodState)
    familiarity: float = 0.0
    trust: float = 0.5
    rapport: float = 0.5


@dataclass
class BehaviorConfig:
    min_silence_before_response: float = 1.0
    max_silence_before_prompt: float = 4.0
    question_response_delay: float = 0.5
    opinion_confidence_threshold: float = 0.65
    greeting_silence_threshold: float = 0.3
    farewell_silence_threshold: float = 2.0
    max_response_length: int = 280
    familiarity_casual_threshold: float = 0.4
    trust_share_threshold: float = 0.6
    mood_decay_rate: float = 0.05
    mood_update_from_event: float = 0.15
