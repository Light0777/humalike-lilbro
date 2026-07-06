# lilbro — the bot that acts human powered by humalike, due to brokeness I'm unable to buy llm's api keys and unable to test this bot to his full potential so if you have paid openAi key test it

Why I'm building this?

After reading through the Humalike plugin architecture, I wanted to test the behavior layer in a setting that feels much harder than normal chat.

Games are full of interruptions, multiple speakers, inside jokes, changing context, and long-term relationships.

LilBro is my attempt to see whether behavior, not just better language models, is what actually makes an AI feel human.
<img width="1915" height="948" alt="Group 1" src="https://github.com/user-attachments/assets/aa060219-80f3-47b9-8e44-ab29ae650fcf" />

flow chart:
<img width="1536" height="1024" alt="ChatGPT Image Jul 6, 2026, 08_56_42 PM" src="https://github.com/user-attachments/assets/acaded42-41c5-4ed1-8e4f-d81c9c79b9e0" />


## 🛠️ Tech Stack

| Language | Voice AI | Memory & DB | Speech-to-Text | Text-to-Speech |
|---|---|---|---|---|
| <img src="https://skillicons.dev/icons?i=python" height="32" /> | <img src="https://skillicons.dev/icons?i=discord" height="32" /> **discord.py** | <img src="https://skillicons.dev/icons?i=supabase" height="32" /> | 🎙️ **Whisper API** / **faster-whisper** | 🔊 **Edge TTS** / **ElevenLabs** / **OpenAI TTS** |

| LLM Brain | Package Manager | Linting |
|---|---|---|
| 🤖 **Gemini** / **OpenAI** | <img src="https://skillicons.dev/icons?i=py" height="32" /> **uv** | 🧹 **ruff** + **mypy** |

## ✨ Features

- 🎤 **Joins Discord voice** and listens in real-time using VAD (voice activity detection)
- 🧠 **Remembers you** — stores conversations, preferences, and facts across sessions
- 💬 **Talks back naturally** — knows when to respond, when to stay quiet, and reads the room
- 🗣️ **Hindi + English code-switching** — understands and speaks Hinglish
- 🧩 **Plug-and-play providers** — swap between OpenAI, Gemini, ElevenLabs, Edge TTS without touching code
- 🔇 **Smart silence detection** — won't interrupt, won't awkwardly fill dead air
- 🎭 **Mood engine** — its energy and confidence adapts to the conversation
- 🧪 **Fully local option** — run STT with faster-whisper, no cloud needed
- ⚡ **Fast slash commands** — `/join`, `/leave`, `/say`, `/chat` for testing

## Getting Started

**Requirements**

- Python 3.12+
- uv (package manager)

### Setup

1. Clone the repo:

```bash
git clone https://github.com/Light0777/humalike-lilbro.git
cd gaming-ai
```

2. Create virtual environment and install deps:

```bash
uv venv
uv pip install -e ".[dev]"
```

3. Copy the environment file and fill in your tokens:

```bash
cp .env.example .env
```

Required variables:

| Variable | Description |
|---|---|
| `DISCORD_TOKEN` | Your Discord bot token |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Your Supabase anon/public key |

Optional (but recommended):

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini` or `openai` |
| `STT_PROVIDER` | `openai` | `openai` or `local` |
| `TTS_PROVIDER` | `edge` | `edge`, `elevenlabs`, or `openai` |
| `DEV_GUILD_ID` | — | Your server ID for instant slash sync |

4. Run database migrations:

Open your Supabase dashboard → **SQL Editor** → run the contents of `src/gaming_ai/database/migrations/001_initial.sql`.

5. Start the bot:

```bash
python -m gaming_ai
```

## Project Structure

```
src/
└── gaming_ai/
    ├── bot/          Bot orchestration, lifecycle, runner
    ├── voice/        Audio capture, VAD, STT, TTS pipeline
    ├── discord/      Bot client, cogs, voice manager
    ├── behavior/     Turn-taking, mood, social norms
    ├── memory/       Long-term and episodic memory engine
    ├── database/     Supabase repo layer + migrations
    ├── services/     Conversation, LLM, response generation
    ├── models/       Shared dataclasses and types
    ├── config/       Pydantic settings management
    ├── utils/        Logging, environment, helpers
    └── prompts/      LLM prompt templates
```

## Database

Migrations live at:

`src/gaming_ai/database/migrations/001_initial.sql`

Tables are auto-managed through the repository layer. If tables don't exist, the bot gracefully falls back to in-memory operation — no crashes, just vibes.

## Development

```bash
# Lint
ruff check src/

# Type-check
mypy src/

# Test
pytest
```

## Voice Pipeline

```
Discord Voice → Opus → PCM → VAD (energy threshold)
    → Speech segment → Resample (48kHz→16kHz)
    → STT (Whisper / faster-whisper)
    → Conversation Engine
    → Response Generator (LLM / rule-based fallback)
    → TTS (Edge / ElevenLabs / OpenAI)
    → Discord Voice Output
```

How it works
 - Create a Discord application and invite the bot to your server.
 - Clone this repository and run it on your PC.
 - Use /join to have LilBro join your Discord voice channel.
 - Hop into voice with your friends.
 - The bot listens to the conversation, remembers context, and (with Humalike) decides when to speak and when to stay silent instead of replying to everything.

Note: This project is still an experiment. I don't currently have paid LLM API credits, so the full behavior pipeline (especially Humalike + high-quality LLM responses) hasn't been tested to its full potential yet. If you have an OpenAI or Gemini API key, feel free to try it out and share your results!

## License

MIT

---

— Light0777
