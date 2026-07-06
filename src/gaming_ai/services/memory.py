import re
from collections import Counter
from typing import Any

from gaming_ai.database.repositories.memory import MemoryRepository
from gaming_ai.database.repositories.session import SessionRepository
from gaming_ai.models import Utterance
from gaming_ai.models.conversation import TurnRecord
from gaming_ai.utils.logging import logger

HIGH_IMPORTANCE_KEYWORDS: set[str] = {
    "love", "hate", "best", "worst", "amazing", "terrible",
    "incredible", "horrible", "awesome", "awful",
    "excited", "frustrated", "angry", "happy", "sad",
    "win", "loss", "victory", "defeat", "champion",
    "never", "always", "remember", "important", "critical",
}

FACT_KEYWORDS: set[str] = {
    "plays", "uses", "likes", "prefers", "main", "favorite",
    "good at", "bad at", "is", "are", "has", "have",
}

MEMORY_TYPE_HEURISTICS: dict[str, set[str]] = {
    "preference": {"like", "love", "hate", "prefer", "favorite", "enjoy"},
    "skill_assessment": {"good at", "bad at", "amazing at", "terrible at", "skilled"},
    "observation": {"saw", "noticed", "observed", "seems", "looks", "appears"},
}

STOP_WORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "this", "that", "these", "those", "and", "or", "but", "if",
    "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "up", "about", "into", "over", "after", "before",
    "do", "does", "did", "done", "have", "has", "had",
    "not", "no", "yes", "yeah", "okay", "ok", "oh", "ah",
    "like", "just", "really", "very", "well", "right",
    "get", "got", "go", "went", "going", "say", "said",
    "know", "think", "see", "want", "come", "let", "can", "will",
}


class MemoryEngine:
    def __init__(
        self,
        memory_repo: MemoryRepository,
        session_repo: SessionRepository | None = None,
    ) -> None:
        self._memory_repo = memory_repo
        self._session_repo = session_repo

    # ── Importance scoring ──────────────────────────────────────────

    async def evaluate_importance(
        self, content: str, context: dict[str, Any] | None = None,
    ) -> float:
        score = 0.3
        words = content.lower().split()
        word_count = len(words)
        text_lower = content.lower()

        if word_count > 20:
            score += 0.1
        elif word_count > 10:
            score += 0.05

        keyword_hits = sum(1 for kw in HIGH_IMPORTANCE_KEYWORDS if kw in text_lower)
        score += min(keyword_hits * 0.05, 0.2)

        proper_nouns = len(re.findall(r'\b[A-Z][a-z]+\b', content))
        score += min(proper_nouns * 0.02, 0.1)

        excitement = content.count("!") + content.count("?")
        score += min(excitement * 0.02, 0.06)

        if context and "topic" in context and context["topic"]:
            topic_words = context["topic"].lower().split()
            overlap = sum(1 for tw in topic_words if tw in text_lower)
            score += min(overlap * 0.03, 0.1)

        if context:
            recall_count = context.get("recall_count", 0) or 0
            if recall_count > 5:
                score *= 0.8

        return min(max(score, 0.0), 1.0)

    # ── Memory type detection ───────────────────────────────────────

    def _detect_memory_type(self, content: str) -> str:
        text_lower = content.lower()
        best_type = "fact"
        best_score = 0
        for mem_type, keywords in MEMORY_TYPE_HEURISTICS.items():
            hits = sum(1 for kw in keywords if kw in text_lower)
            if hits > best_score:
                best_score = hits
                best_type = mem_type
        return best_type

    # ── Memory creation ─────────────────────────────────────────────

    async def store_memory(
        self,
        player_id: str,
        content: str,
        memory_type: str | None = None,
        importance: float | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        try:
            mem_type = memory_type or self._detect_memory_type(content)
            importance_score = (
                importance if importance is not None
                else await self.evaluate_importance(content, context)
            )

            existing = await self._memory_repo.find_by_player(player_id, limit=50)
            for mem in existing:
                existing_content = mem.get("content", "") or ""
                if self._text_similarity(content, existing_content) > 0.85:
                    return mem

            memory_data: dict[str, Any] = {
                "player_id": player_id,
                "type": mem_type,
                "content": content,
                "importance": importance_score,
            }
            if context:
                memory_data["context"] = context

            result = await self._memory_repo.insert(memory_data)
            logger.debug(
                "Stored {} memory for player {} (importance={:.2f})",
                mem_type, player_id, importance_score,
            )
            return result
        except Exception:
            logger.warning("Failed to store memory for {} (DB not ready?)", player_id)
            return None

    async def store_interaction_memory(
        self,
        utterance: Utterance,
        response: str | None,
        topic: str,
        session_id: str,
    ) -> None:
        content_text = utterance.text.strip()
        if not content_text:
            return

        context: dict[str, Any] = {
            "session_id": session_id,
            "topic": topic,
            "source": "conversation",
            "timestamp": utterance.timestamp,
        }

        await self.store_memory(
            player_id=utterance.player_id,
            content=content_text,
            memory_type="interaction",
            context=context,
        )

        if response:
            await self.store_memory(
                player_id=utterance.player_id,
                content=f"Bot responded: {response}",
                memory_type="interaction",
                context={**context, "is_response": True},
            )

    # ── Text utilities ──────────────────────────────────────────────

    def _tokenize(self, text: str) -> list[str]:
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in STOP_WORDS and len(w) > 1]

    def _text_similarity(self, a: str, b: str) -> float:
        tokens_a = set(self._tokenize(a))
        tokens_b = set(self._tokenize(b))
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    # ── Retrieval ───────────────────────────────────────────────────

    async def recall_relevant(
        self,
        query: str,
        player_id: str,
        limit: int = 5,
        min_importance: float = 0.1,
    ) -> list[dict[str, Any]]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        try:
            memories = await self._memory_repo.find_by_player(player_id, limit=100)
        except Exception:
            logger.warning("Failed to recall memories for {} (DB not ready?)", player_id)
            return []

        if not memories:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []
        for mem in memories:
            if (mem.get("importance", 0) or 0) < min_importance:
                continue

            mem_tokens = self._tokenize(mem.get("content", "") or "")
            if not mem_tokens:
                continue

            query_set = set(query_tokens)
            mem_set = set(mem_tokens)
            overlap = len(query_set & mem_set)
            jaccard = overlap / len(query_set | mem_set) if query_set | mem_set else 0

            importance = mem.get("importance", 0.5) or 0.5
            recall_count = mem.get("recall_count", 0) or 0
            recency_boost = 1.0 / (1.0 + recall_count * 0.2)

            final_score = (jaccard * 0.6 + importance * 0.3 + 0.1) * recency_boost
            if final_score > 0:
                scored.append((final_score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = scored[:limit]

        for _, mem in results:
            try:
                await self._memory_repo.mark_recalled(mem["id"])
            except Exception:
                pass

        return [mem for _, mem in results]

    async def recall_for_context(
        self, query: str, player_id: str, limit: int = 5,
    ) -> str:
        memories = await self.recall_relevant(query, player_id, limit=limit)
        if not memories:
            return ""

        lines: list[str] = []
        for mem in memories:
            mem_type = mem.get("type", "fact")
            content = mem.get("content", "")
            importance = mem.get("importance", 0.5)
            lines.append(f"[{mem_type} (imp:{importance:.1f})] {content}")

        return "\n".join(lines)

    async def remember_player(self, player_id: str) -> str:
        try:
            memories = await self._memory_repo.find_by_player(player_id, limit=200)
        except Exception:
            logger.warning("Failed to remember player {} (DB not ready?)", player_id)
            return ""
        if not memories:
            return ""

        by_type: dict[str, list[str]] = {}
        for mem in memories:
            mem_type = mem.get("type", "fact")
            content = mem.get("content", "") or ""
            by_type.setdefault(mem_type, []).append(content)

        parts: list[str] = []

        if "preference" in by_type:
            parts.append("Preferences:")
            for c in by_type["preference"][:5]:
                parts.append(f"  - {c}")

        if "skill_assessment" in by_type:
            parts.append("Skill observations:")
            for c in by_type["skill_assessment"][:5]:
                parts.append(f"  - {c}")

        if "fact" in by_type:
            parts.append("Known facts:")
            for c in by_type["fact"][:10]:
                parts.append(f"  - {c}")

        if "interaction" in by_type:
            parts.append(f"Total interactions stored: {len(by_type["interaction"])}")

        return "\n".join(parts)

    # ── Summarization ───────────────────────────────────────────────

    async def summarize_session(
        self, turns: list[TurnRecord], game_name: str | None = None,
    ) -> str:
        if not turns:
            return ""

        speakers: set[str] = {t.utterance.player_id for t in turns if t.utterance.player_id}
        total_turns = len(turns)

        topics: Counter[str] = Counter()
        all_text = ""
        for turn in turns:
            text = turn.utterance.text or ""
            all_text += " " + text
            topics.update(self._tokenize(text))

        common_topics = [w for w, _ in topics.most_common(5) if w]
        parts: list[str] = [
            f"Session: {total_turns} turns, {len(speakers)} speakers.",
        ]
        if game_name:
            parts.append(f" Game: {game_name}.")
        if common_topics:
            parts.append(f" Key topics: {', '.join(common_topics[:3])}.")
        if len(all_text) > 200:
            parts.append(f" Dialogue preview: {all_text[:200]}...")

        return " ".join(parts)

    async def extract_facts(
        self, turns: list[TurnRecord], player_id: str,
    ) -> list[str]:
        stored: list[str] = []
        for turn in turns:
            uid = turn.utterance.player_id
            if uid != player_id:
                continue

            text = turn.utterance.text.strip()
            if not text:
                continue

            text_lower = text.lower()
            if not any(pattern in text_lower for pattern in FACT_KEYWORDS):
                continue
            if len(text.split()) < 5:
                continue

            importance = await self.evaluate_importance(text)
            if importance < 0.3:
                continue

            mem_type = self._detect_memory_type(text)
            await self.store_memory(
                player_id=player_id,
                content=text,
                memory_type=mem_type,
                importance=importance,
                context={"source": "conversation"},
            )
            stored.append(text)

        return stored

    async def end_session_summary(
        self,
        session_id: str,
        guild_id: int,
        turns: list[TurnRecord],
        game_name: str | None = None,
    ) -> None:
        if not self._session_repo:
            return

        summary = await self.summarize_session(turns, game_name)
        try:
            await self._session_repo.end_session(session_id, summary=summary)
        except Exception:
            logger.warning("Failed to end session {} (DB not ready?)", session_id)

        for turn in turns:
            await self.store_interaction_memory(
                utterance=turn.utterance,
                response=turn.utterance.text,
                topic=summary,
                session_id=session_id,
            )
