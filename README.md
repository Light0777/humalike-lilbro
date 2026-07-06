# Gaming AI

A social gaming AI teammate that joins Discord voice channels and behaves like a real player.

## Architecture

```
gaming-ai/
├── bot/          Bot orchestration and lifecycle
├── voice/        Audio capture, playback, VAD
├── behavior/     Turn-taking, social norms, mood, opinions
├── memory/       Long-term and episodic memory
├── database/     Supabase / PostgreSQL repository layer
├── discord/      Discord client wrappers
├── services/     Business logic (conversation, relationship, etc.)
├── models/       Shared dataclasses and types
├── prompts/      LLM prompt templates
├── utils/        Logging, environment, helpers
├── config/       Settings management
└── tests/        Unit and integration tests
```

## Requirements

- Python 3.12+
- uv (package manager)

## Setup

```bash
# Install uv if you haven't already
pip install uv

# Clone and enter the project
cd gaming-ai

# Create virtual environment and install deps
uv venv
uv pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your tokens

# Run the bot
python -m main
```

## Development

```bash
# Lint
ruff check .

# Type-check
mypy .

# Test
pytest
```

## Phases

| Phase | Component        | Status |
|-------|------------------|--------|
| 1     | Project setup    | ✅ Done |
| 2     | Discord bot      | ❌      |
| 3     | Voice pipeline   | ❌      |
| 4     | Conversation     | ❌      |
| 5     | Database         | ❌      |
| 6     | Memory engine    | ❌      |
| 7     | Behavior engine  | ❌      |
| 8     | LLM integration  | ❌      |
| 9     | Voice output     | ❌      |
| 10    | Humalike         | ❌      |
| 11    | Dashboard        | ❌      |
| 12    | Testing           | ❌      |
