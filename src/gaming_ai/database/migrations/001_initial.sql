-- 001_initial.sql
-- Gaming AI — Initial database schema

-- ── Players ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discord_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_players_discord_id ON players(discord_id);

-- ── Sessions ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    game_name TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    turn_count INTEGER NOT NULL DEFAULT 0,
    speaker_count INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_guild_id ON sessions(guild_id);

-- ── Events ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    player_id UUID REFERENCES players(id) ON DELETE SET NULL,
    type TEXT NOT NULL,
    data JSONB DEFAULT '{}'::jsonb,
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id);

-- ── Conversations (turns) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    player_id UUID REFERENCES players(id) ON DELETE SET NULL,
    text TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    is_interruption BOOLEAN DEFAULT FALSE,
    silence_before REAL DEFAULT 0.0,
    response_text TEXT,
    emotion TEXT DEFAULT 'neutral',
    turn_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);

-- ── Relationships ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID UNIQUE REFERENCES players(id) ON DELETE CASCADE,
    familiarity REAL DEFAULT 0.0 CHECK (familiarity >= 0 AND familiarity <= 1),
    trust REAL DEFAULT 0.5 CHECK (trust >= 0 AND trust <= 1),
    rapport REAL DEFAULT 0.5 CHECK (rapport >= 0 AND rapport <= 1),
    total_interactions INTEGER DEFAULT 0,
    last_interaction_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_relationships_player_id ON relationships(player_id);

-- ── Memories ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID REFERENCES players(id) ON DELETE CASCADE,
    type TEXT NOT NULL DEFAULT 'fact',
    content TEXT NOT NULL,
    importance REAL DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
    context JSONB DEFAULT '{}'::jsonb,
    last_recalled_at TIMESTAMPTZ,
    recall_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_player_id ON memories(player_id);

-- ── Opinions ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS opinions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID REFERENCES players(id) ON DELETE CASCADE,
    target_player_id UUID REFERENCES players(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    sentiment REAL DEFAULT 0.0 CHECK (sentiment >= -1 AND sentiment <= 1),
    confidence REAL DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    source TEXT DEFAULT 'observed',
    context JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, target_player_id, topic)
);

CREATE INDEX IF NOT EXISTS idx_opinions_player_id ON opinions(player_id);
