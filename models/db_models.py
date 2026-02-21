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


# ── Hormone Log ───────────────────────────────────────────────────

class HormoneLog(Base):
    __tablename__ = "hormone_logs"

    id = Column(String, primary_key=True, default=_uid)
    hormone_name = Column(String, nullable=False)
    emitter_organ = Column(String, default="unknown")
    payload = Column(Text, default="{}")                   # JSON dict
    processed = Column(Boolean, default=False)
    created_at = Column(Float, default=_now)
