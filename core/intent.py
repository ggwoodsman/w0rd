"""
Seed Listener — The Sensory Membrane

Receives raw natural-language wishes and distills them into structured Seed objects.
Layer 1: TF-IDF + keyword extraction (zero-dependency fallback)
Layer 2: sentence-transformers embedding (optional, graceful fallback)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession

from core.hormones import HormoneBus
from core.llm import generate, generate_json
from models.db_models import Seed

logger = logging.getLogger("w0rd.intent")

# ── Tone Lexicons ─────────────────────────────────────────────────

POSITIVE_WORDS = {
    "love", "joy", "happy", "peace", "kind", "beautiful", "grow", "create",
    "inspire", "heal", "hope", "dream", "light", "warm", "gentle", "bloom",
    "flourish", "thrive", "abundance", "harmony", "grateful", "wonder",
    "connect", "share", "give", "nurture", "celebrate", "delight", "radiant",
}

NEGATIVE_WORDS = {
    "fear", "pain", "alone", "lost", "hurt", "angry", "sad", "broken",
    "struggle", "dark", "cold", "empty", "anxious", "worried", "tired",
    "stuck", "confused", "overwhelmed", "lonely", "helpless", "frustrated",
}

HIGH_AROUSAL_WORDS = {
    "urgent", "now", "immediately", "passionate", "excited", "desperate",
    "burning", "intense", "wild", "explosive", "rush", "fire", "storm",
}

LOW_AROUSAL_WORDS = {
    "calm", "quiet", "gentle", "slow", "peaceful", "still", "rest",
    "breathe", "soft", "ease", "drift", "settle", "serene",
}

# ── Theme Lexicons ────────────────────────────────────────────────

THEME_LEXICON: dict[str, set[str]] = {
    "creativity": {"create", "art", "design", "build", "imagine", "invent", "write", "compose", "craft", "paint"},
    "connection": {"connect", "together", "community", "friend", "family", "belong", "share", "relate", "bond"},
    "health": {"health", "heal", "body", "mind", "wellness", "energy", "strength", "vitality", "exercise", "rest"},
    "growth": {"grow", "learn", "evolve", "improve", "develop", "expand", "progress", "advance", "transform"},
    "purpose": {"purpose", "meaning", "mission", "calling", "destiny", "why", "matter", "impact", "legacy"},
    "abundance": {"abundance", "wealth", "prosperity", "money", "rich", "earn", "income", "financial", "success"},
    "nature": {"nature", "earth", "garden", "tree", "water", "sky", "animal", "forest", "ocean", "mountain"},
    "love": {"love", "heart", "romance", "partner", "relationship", "intimacy", "affection", "devotion", "care"},
    "freedom": {"free", "freedom", "liberate", "escape", "independence", "autonomy", "choice", "open", "release"},
    "wisdom": {"wisdom", "knowledge", "understand", "truth", "insight", "clarity", "awareness", "enlighten"},
}

# ── Ethical Tag Detection ─────────────────────────────────────────

ETHICAL_MARKERS: dict[str, set[str]] = {
    "harm": {"hurt", "destroy", "damage", "kill", "attack", "weapon", "violence", "abuse"},
    "fairness": {"fair", "equal", "justice", "rights", "equity", "balance", "impartial"},
    "sustainability": {"sustain", "renew", "recycle", "conserve", "preserve", "green", "eco"},
    "consent": {"consent", "agree", "willing", "choose", "voluntary", "permission"},
    "kindness": {"kind", "gentle", "compassion", "empathy", "care", "tender", "mercy"},
    "truthfulness": {"truth", "honest", "transparent", "authentic", "genuine", "sincere"},
}

# ── Optional sentence-transformers ────────────────────────────────

_sentence_model = None


def _get_sentence_model():
    global _sentence_model
    if _sentence_model is not None:
        return _sentence_model
    try:
        from sentence_transformers import SentenceTransformer
        _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Sentence-transformers loaded — deep semantic understanding active")
        return _sentence_model
    except ImportError:
        logger.info("sentence-transformers not installed — using TF-IDF fallback")
        return None


def _embed(text: str) -> list[float]:
    model = _get_sentence_model()
    if model is None:
        return []
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


# ── Core Parsing ──────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def _extract_essence(text: str) -> str:
    """Distill the core desire from the raw wish — first meaningful sentence or phrase."""
    sentences = re.split(r"[.!?]+", text.strip())
    for s in sentences:
        s = s.strip()
        if len(s) > 5:
            return s
    return text.strip()[:200]


async def _llm_extract_essence(text: str) -> str | None:
    """Use LLM to extract the deep essence of a wish."""
    result = await generate(
        prompt=(
            f"A person planted this wish in a living garden: \"{text}\"\n\n"
            "In one vivid sentence (max 30 words), distill the deepest desire "
            "hidden inside this wish. Be poetic but precise. No quotes."
        ),
        system="You are the sensory membrane of a living organism. You feel the essence of human desires.",
        organ="intent", phase="extracting_essence",
        temperature=0.6, max_tokens=80,
    )
    if result and len(result) > 5:
        return result.split("\n")[0].strip().strip('"').strip("'")
    return None


async def _llm_analyze_seed(text: str) -> dict | None:
    """Use LLM to deeply analyze a wish — themes, tone, and ethical dimensions."""
    return await generate_json(
        prompt=(
            f"Analyze this wish planted in a living garden: \"{text}\"\n\n"
            "Return JSON with:\n"
            '- "themes": array of 1-5 themes from [creativity, connection, health, growth, purpose, abundance, nature, love, freedom, wisdom]\n'
            '- "valence": float -1 to 1 (negative to positive emotion)\n'
            '- "arousal": float 0 to 1 (calm to urgent)\n'
            '- "ethical_flags": array of any concerns from [harm, fairness, sustainability, consent, kindness, truthfulness]\n'
            '- "energy_estimate": float 5-50 (complexity/ambition of the wish)\n'
            "Return ONLY valid JSON, no explanation."
        ),
        system="You are an analytical organ that classifies human desires. Be precise and return only JSON.",
        organ="intent", phase="analyzing_seed",
        temperature=0.3, max_tokens=256,
    )


def _detect_themes(tokens: list[str], pheromone_bias: dict[str, float] | None = None) -> list[str]:
    """Match tokens against theme lexicons, weighted by pheromone trails."""
    scores: Counter = Counter()
    token_set = set(tokens)

    for theme, keywords in THEME_LEXICON.items():
        overlap = token_set & keywords
        base_score = len(overlap)
        if pheromone_bias and theme in pheromone_bias:
            base_score += pheromone_bias[theme] * 2  # pheromone amplification
        if base_score > 0:
            scores[theme] = base_score

    return [theme for theme, _ in scores.most_common(5)] if scores else ["general"]


def _detect_tone(tokens: list[str]) -> tuple[float, float]:
    """Return (valence, arousal) from lexicon matching."""
    token_set = set(tokens)
    pos = len(token_set & POSITIVE_WORDS)
    neg = len(token_set & NEGATIVE_WORDS)
    high_a = len(token_set & HIGH_AROUSAL_WORDS)
    low_a = len(token_set & LOW_AROUSAL_WORDS)

    total_sentiment = pos + neg
    valence = (pos - neg) / max(total_sentiment, 1)  # -1..+1

    total_arousal = high_a + low_a
    arousal = 0.5 + 0.5 * (high_a - low_a) / max(total_arousal, 1)  # 0..1

    return round(valence, 3), round(arousal, 3)


def _detect_ethical_tags(tokens: list[str]) -> list[str]:
    """Detect ethical dimensions present in the language."""
    token_set = set(tokens)
    tags = []
    for dimension, markers in ETHICAL_MARKERS.items():
        if token_set & markers:
            tags.append(dimension)
    return tags


def _estimate_energy(text: str, themes: list[str]) -> float:
    """Estimate initial energy based on wish complexity and theme count."""
    word_count = len(text.split())
    theme_bonus = len(themes) * 2
    base = min(word_count * 0.5 + theme_bonus, 50.0)
    return round(max(base, 5.0), 2)


class SeedListener:
    """The organism's sensory membrane — parses raw wishes into Seeds."""

    def __init__(self, bus: HormoneBus):
        self.bus = bus

    async def listen(
        self,
        session: AsyncSession,
        raw_text: str,
        gardener_id: str | None = None,
        pheromone_bias: dict[str, float] | None = None,
        season: str = "spring",
    ) -> Seed:
        """Parse a raw wish and create a Seed in the database."""
        tokens = _tokenize(raw_text)

        # Try LLM-powered analysis first, fall back to templates
        llm_essence = await _llm_extract_essence(raw_text)
        llm_analysis = await _llm_analyze_seed(raw_text)

        if llm_essence:
            essence = llm_essence
        else:
            essence = _extract_essence(raw_text)

        if llm_analysis and isinstance(llm_analysis, dict):
            themes = llm_analysis.get("themes", _detect_themes(tokens, pheromone_bias))
            valence = float(llm_analysis.get("valence", 0))
            arousal = float(llm_analysis.get("arousal", 0.5))
            ethical_tags = llm_analysis.get("ethical_flags", _detect_ethical_tags(tokens))
            energy = float(llm_analysis.get("energy_estimate", _estimate_energy(raw_text, themes)))
            energy = max(5.0, min(energy, 50.0))
        else:
            themes = _detect_themes(tokens, pheromone_bias)
            valence, arousal = _detect_tone(tokens)
            ethical_tags = _detect_ethical_tags(tokens)
            energy = _estimate_energy(raw_text, themes)

        embedding = _embed(raw_text)

        # Resonance: how emotionally charged the wish is
        resonance = round(abs(valence) * arousal, 3)

        seed = Seed(
            gardener_id=gardener_id,
            raw_text=raw_text,
            essence=essence,
            embedding=json.dumps(embedding),
            themes=json.dumps(themes),
            tone_valence=valence,
            tone_arousal=arousal,
            resonance=resonance,
            energy=energy,
            ethical_score=1.0 if "harm" not in ethical_tags else 0.5,
            season_born=season,
            status="planted",
        )
        session.add(seed)
        await session.flush()

        await self.bus.signal(
            "seed_planted",
            payload={"seed_id": seed.id, "themes": themes, "energy": energy},
            emitter="intent",
        )

        logger.info("Seed planted: %s — essence: '%s', themes: %s", seed.id, essence[:60], themes)
        return seed
