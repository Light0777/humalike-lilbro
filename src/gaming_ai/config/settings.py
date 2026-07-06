
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    discord_token: str = ""
    discord_application_id: str = ""

    supabase_url: str = ""
    supabase_key: str = ""

    openai_api_key: str = ""
    gemini_api_key: str = ""

    elevenlabs_api_key: str = ""

    stt_provider: str = "openai"
    whisper_model: str = "base"
    local_whisper_model: str = "base"

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 512

    tts_provider: str = "openai"
    tts_voice: str = "nova"
    edge_tts_voice: str = "en-US-EmmaMultilingualNeural"
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"

    bot_prefix: str = "!"
    bot_activity: str = "playing with friends"

    voice_sample_rate: int = 48000
    voice_channels: int = 2

    vad_threshold: float = 500.0
    vad_silence_timeout: float = 0.8
    vad_min_utterance: float = 0.3
    vad_max_utterance: float = 30.0

    dev_guild_id: int = 0

    humalike_api_key: str = ""
    humalike_base_url: str = "https://api.humalike.com"

    log_level: str = "INFO"
