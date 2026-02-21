"""
SQLAlchemy ORM Models — The Cell Structures

Every entity in the living system, persisted in Memory Soil.
Nothing is truly deleted — only composted.
"""

from __future__ import annotations

import time
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _uid() -> str:
    return uuid.uuid4().hex[:16]


def _now() -> float:
    return time.time()


class Base(DeclarativeBase):
    pass


# ── Gardener ──────────────────────────────────────────────────────

class Gardener(Base):
    __tablename__ = "gardeners"

    id = Column(String, primary_key=True, default=_uid)
    name = Column(String, nullable=False, default="Anonymous Gardener")
    preference_vector = Column(Text, default="[]")       # JSON list of floats
    rhythm_profile = Column(Text, default="{}")           # JSON dict
    pheromone_trails = Column(Text, default="{}")         # JSON dict
    interaction_count = Column(Integer, default=0)
    created_at = Column(Float, default=_now)

    seeds = relationship("Seed", back_populates="gardener")


# ── Seed ──────────────────────────────────────────────────────────

class Seed(Base):
    __tablename__ = "seeds"

    id = Column(String, primary_key=True, default=_uid)
    gardener_id = Column(String, ForeignKey("gardeners.id"), nullable=True)
    raw_text = Column(Text, nullable=False)
    essence = Column(Text, default="")
    embedding = Column(Text, default="[]")                # JSON list of floats
    themes = Column(Text, default="[]")                   # JSON list of strings
    tone_valence = Column(Float, default=0.0)             # -1 negative .. +1 positive
    tone_arousal = Column(Float, default=0.5)             # 0 calm .. 1 excited
    resonance = Column(Float, default=0.0)
    energy = Column(Float, default=10.0)
    ethical_score = Column(Float, default=1.0)
    vitality = Column(Float, default=1.0)
    season_born = Column(String, default="spring")
    version = Column(Integer, default=1)
    lineage = Column(Text, default="[]")                  # JSON list of version snapshots
    status = Column(String, default="planted")            # planted, growing, harvested, composted
    is_composted = Column(Boolean, default=False)
    created_at = Column(Float, default=_now)

    gardener = relationship("Gardener", back_populates="seeds")
    sprouts = relationship("Sprout", back_populates="seed", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_seeds_status", "status"),
        Index("ix_seeds_is_composted", "is_composted"),
        Index("ix_seeds_status_composted", "status", "is_composted"),
        Index("ix_seeds_gardener_id", "gardener_id"),
    )


# ── Sprout ────────────────────────────────────────────────────────

class Sprout(Base):
    __tablename__ = "sprouts"

    id = Column(String, primary_key=True, default=_uid)
    seed_id = Column(String, ForeignKey("seeds.id"), nullable=False)
    parent_id = Column(String, ForeignKey("sprouts.id"), nullable=True)
    depth = Column(Integer, default=0)
    label = Column(String, nullable=False)
    description = Column(Text, default="")
    energy = Column(Float, default=1.0)
    ethical_score = Column(Float, default=1.0)
    pressure = Column(Float, default=0.5)
    resonance = Column(Float, default=0.0)
    warmth = Column(Float, default=0.0)
    version = Column(Integer, default=1)
    lineage = Column(Text, default="[]")
    status = Column(String, default="budding")            # budding, growing, blooming, wilting, composted
    is_composted = Column(Boolean, default=False)
    created_at = Column(Float, default=_now)
    apoptosis_at = Column(Float, nullable=True)

    seed = relationship("Seed", back_populates="sprouts")
    children = relationship("Sprout", backref="parent", remote_side=[id])

    __table_args__ = (
        Index("ix_sprouts_seed_id", "seed_id"),
        Index("ix_sprouts_is_composted", "is_composted"),
    )


# ── Symbiotic Link ────────────────────────────────────────────────

class SymbioticLink(Base):
    __tablename__ = "symbiotic_links"

    id = Column(String, primary_key=True, default=_uid)
    # NOTE: columns named sprout_*_id for legacy compat, but actually store seed IDs
    sprout_a_id = Column(String, nullable=False)
    sprout_b_id = Column(String, nullable=False)
    relationship_type = Column(String, default="mutualism")  # mutualism, commensalism, parasitism
    synergy_score = Column(Float, default=0.0)
    nutrient_flow = Column(Float, default=0.0)
    pollen_transferred = Column(Boolean, default=False)
    created_at = Column(Float, default=_now)

    __table_args__ = (
        Index("ix_symlinks_sprout_a", "sprout_a_id"),
        Index("ix_symlinks_sprout_b", "sprout_b_id"),
        Index("ix_symlinks_pair", "sprout_a_id", "sprout_b_id"),
    )


# ── Garden State (singleton-ish) ──────────────────────────────────

class GardenState(Base):
    __tablename__ = "garden_state"

    id = Column(String, primary_key=True, default=lambda: "garden")
    total_energy = Column(Float, default=100.0)
    vitality = Column(Float, default=1.0)
    season = Column(String, default="spring")
    tidal_phase = Column(Float, default=0.0)              # 0..1 oscillation
    cycle_count = Column(Integer, default=0)
    wisdom_score = Column(Float, default=0.0)
    antifragility_score = Column(Float, default=0.0)
    dream_count = Column(Integer, default=0)
    soil_richness = Column(Float, default=0.0)
    last_pulse = Column(Float, default=_now)


# ── Ethical Memory ────────────────────────────────────────────────

class EthicalMemory(Base):
    __tablename__ = "ethical_memories"

    id = Column(String, primary_key=True, default=_uid)
    pattern_hash = Column(String, nullable=False)
    dimension = Column(String, nullable=False)             # harm, fairness, sustainability, etc.
    resolution = Column(Text, default="")
    strength = Column(Float, default=1.0)
    false_positive_count = Column(Integer, default=0)
    created_at = Column(Float, default=_now)


# ── Dream ─────────────────────────────────────────────────────────

class Dream(Base):
    __tablename__ = "dreams"

    id = Column(String, primary_key=True, default=_uid)
    source_seed_ids = Column(Text, default="[]")           # JSON list
    insight = Column(Text, default="")
    archetype_vector = Column(Text, default="[]")          # JSON list of floats
    temperature = Column(Float, default=0.7)
    perplexity = Column(Float, default=0.0)
    planted = Column(Boolean, default=False)
    created_at = Column(Float, default=_now)


# ── Pulse Report ──────────────────────────────────────────────────

class PulseReport(Base):
    __tablename__ = "pulse_reports"

    id = Column(String, primary_key=True, default=_uid)
    cycle = Column(Integer, default=0)
    summary = Column(Text, default="")
    thriving = Column(Text, default="[]")                  # JSON list of seed ids
    struggling = Column(Text, default="[]")
    healing = Column(Text, default="[]")
    dreaming = Column(Text, default="[]")
    emergent = Column(Text, default="[]")
    pheromone_snapshot = Column(Text, default="{}")
    created_at = Column(Float, default=_now)


# ── Wound Record ──────────────────────────────────────────────────

class WoundRecord(Base):
    __tablename__ = "wound_records"

    id = Column(String, primary_key=True, default=_uid)
    wound_type = Column(String, nullable=False)            # sprout_failure, branch_collapse, energy_crash
    severity = Column(String, default="minor")             # minor, moderate, severe
    source_hormone = Column(String, default="")
    affected_ids = Column(Text, default="[]")              # JSON list
    healing_action = Column(Text, default="")
    scar_lesson = Column(Text, default="")
    antifragility_gained = Column(Float, default=0.0)
    created_at = Column(Float, default=_now)
    healed_at = Column(Float, nullable=True)


# ── Agent Node ────────────────────────────────────────────────────

class AgentNode(Base):
    __tablename__ = "agent_nodes"

    id = Column(String, primary_key=True, default=_uid)
    name = Column(String, nullable=False)                   # e.g. "analyzer_01"
    agent_type = Column(String, nullable=False)             # analyze, code_gen, code_exec, web_search, file_read, file_write, summarize, decompose, planner
    status = Column(String, default="spawning")             # spawning, idle, working, completed, retired, awaiting_approval
    parent_id = Column(String, ForeignKey("agent_nodes.id"), nullable=True)
    seed_id = Column(String, ForeignKey("seeds.id"), nullable=True)
    task_description = Column(Text, default="")             # what this agent is supposed to do
    capability = Column(Text, default="{}")                 # JSON — capability config
    context = Column(Text, default="{}")                    # JSON — working memory / state
    result = Column(Text, default="")                       # final output
    error = Column(Text, default="")                        # error message if failed
    created_at = Column(Float, default=_now)
    started_at = Column(Float, nullable=True)
    completed_at = Column(Float, nullable=True)
    retired_at = Column(Float, nullable=True)

    children = relationship("AgentNode", backref="parent", remote_side=[id])

    __table_args__ = (
        Index("ix_agents_status", "status"),
        Index("ix_agents_seed_id", "seed_id"),
        Index("ix_agents_type", "agent_type"),
    )


# ── Emotional State ───────────────────────────────────────────────

class EmotionalState(Base):
    __tablename__ = "emotional_states"

    id = Column(String, primary_key=True, default=_uid)
    joy = Column(Float, default=0.5)
    curiosity = Column(Float, default=0.5)
    anxiety = Column(Float, default=0.1)
    pride = Column(Float, default=0.3)
    grief = Column(Float, default=0.0)
    wonder = Column(Float, default=0.4)
    dominant_emotion = Column(String, default="curiosity")
    intensity = Column(Float, default=0.5)                  # 0..1 overall emotional intensity
    trigger_event = Column(String, default="")               # what caused this state
    created_at = Column(Float, default=_now)


# ── Inner Thought ────────────────────────────────────────────────

class InnerThought(Base):
    __tablename__ = "inner_thoughts"

    id = Column(String, primary_key=True, default=_uid)
    thought_type = Column(String, default="reflection")      # reflection, question, observation, rumination, wonder
    content = Column(Text, nullable=False)
    emotional_context = Column(Text, default="{}")           # JSON snapshot of emotional state
    trigger = Column(String, default="")                     # what prompted this thought
    depth = Column(Integer, default=0)                       # 0=surface, 1=deeper, 2=profound
    salience = Column(Float, default=0.5)                    # how important/memorable 0..1
    created_at = Column(Float, default=_now)

    __table_args__ = (
        Index("ix_thoughts_type", "thought_type"),
        Index("ix_thoughts_salience", "salience"),
    )


# ── Autobiographical Memory ──────────────────────────────────────

class EpisodicMemory(Base):
    __tablename__ = "episodic_memories"

    id = Column(String, primary_key=True, default=_uid)
    narrative = Column(Text, nullable=False)                 # 1-2 sentence memory
    event_type = Column(String, nullable=False)              # harvest, wound, dream, season_change, etc.
    emotional_valence = Column(Float, default=0.0)           # -1..+1
    emotional_intensity = Column(Float, default=0.5)         # 0..1
    themes = Column(Text, default="[]")                      # JSON list of themes
    related_seed_ids = Column(Text, default="[]")            # JSON list
    is_core_memory = Column(Boolean, default=False)          # consolidated as deeply significant
    recall_count = Column(Integer, default=0)                # how often this memory is accessed
    last_recalled = Column(Float, nullable=True)
    created_at = Column(Float, default=_now)

    __table_args__ = (
        Index("ix_memories_event_type", "event_type"),
        Index("ix_memories_core", "is_core_memory"),
        Index("ix_memories_valence", "emotional_valence"),
    )


# ── Prediction ───────────────────────────────────────────────────

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(String, primary_key=True, default=_uid)
    prediction_type = Column(String, nullable=False)         # seed_outcome, dream_topic, energy_trend, season_event
    subject_id = Column(String, default="")                  # seed/dream id being predicted about
    predicted_outcome = Column(Text, nullable=False)         # what was predicted
    actual_outcome = Column(Text, default="")                # what actually happened
    confidence = Column(Float, default=0.5)                  # 0..1 how confident
    surprise_score = Column(Float, default=0.0)              # 0..1 how surprised (prediction error)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(Float, nullable=True)
    created_at = Column(Float, default=_now)

    __table_args__ = (
        Index("ix_predictions_type", "prediction_type"),
        Index("ix_predictions_resolved", "resolved"),
        Index("ix_predictions_surprise", "surprise_score"),
    )


# ── Self-Model ───────────────────────────────────────────────────

class SelfModelSnapshot(Base):
    __tablename__ = "self_model_snapshots"

    id = Column(String, primary_key=True, default=_uid)
    harvest_rate = Column(Float, default=0.0)                # % of seeds that get harvested
    compost_rate = Column(Float, default=0.0)                # % of seeds composted
    dream_accuracy = Column(Float, default=0.0)              # % of dreams that became good seeds
    theme_affinities = Column(Text, default="{}")            # JSON {theme: success_rate}
    decision_accuracy = Column(Text, default="{}")           # JSON {decision_type: accuracy}
    personality_traits = Column(Text, default="{}")          # JSON {trait: strength} emergent personality
    bias_warnings = Column(Text, default="[]")               # JSON list of detected biases
    identity_narrative = Column(Text, default="")            # "who I am" summary
    created_at = Column(Float, default=_now)


# ── Hormone Log ───────────────────────────────────────────────────

class HormoneLog(Base):
    __tablename__ = "hormone_logs"

    id = Column(String, primary_key=True, default=_uid)
    hormone_name = Column(String, nullable=False)
    emitter_organ = Column(String, default="unknown")
    payload = Column(Text, default="{}")                   # JSON dict
    processed = Column(Boolean, default=False)
    created_at = Column(Float, default=_now)
