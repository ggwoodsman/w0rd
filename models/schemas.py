"""
Pydantic Schemas — The Cell Walls

Request/response models for the Garden Gate API.
Validates everything entering and leaving the organism.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ── Requests ──────────────────────────────────────────────────────

class PlantRequest(BaseModel):
    wish: str = Field(..., min_length=1, description="A raw human wish — the seed")
    gardener_id: str | None = Field(None, description="Optional gardener identity")


class PlantManyRequest(BaseModel):
    wishes: list[str] = Field(..., min_length=1, description="Multiple wishes to plant")
    gardener_id: str | None = None


class WaterRequest(BaseModel):
    feedback: str = Field("", description="Optional words of encouragement or direction")
    energy_boost: float = Field(5.0, ge=0, le=100, description="Energy to add")
    attention_seconds: float = Field(1.0, ge=0, description="How long the gardener spent attending")


class GardenerUpdateRequest(BaseModel):
    name: str | None = None
    preference_vector: list[float] | None = None


# ── Responses ─────────────────────────────────────────────────────

class SeedResponse(BaseModel):
    id: str
    raw_text: str
    essence: str
    themes: list[str]
    tone_valence: float
    tone_arousal: float
    resonance: float
    energy: float
    ethical_score: float
    vitality: float
    season_born: str
    version: int
    status: str
    created_at: float
    sprouts: list[SproutResponse] = []

    model_config = ConfigDict(from_attributes=True)


class SproutResponse(BaseModel):
    id: str
    seed_id: str
    parent_id: str | None
    depth: int
    label: str
    description: str
    energy: float
    ethical_score: float
    pressure: float
    resonance: float
    warmth: float
    status: str
    created_at: float

    model_config = ConfigDict(from_attributes=True)


class GardenerResponse(BaseModel):
    id: str
    name: str
    preference_vector: list[float]
    interaction_count: int
    created_at: float

    model_config = ConfigDict(from_attributes=True)


class GardenStateResponse(BaseModel):
    total_energy: float
    vitality: float
    season: str
    tidal_phase: float
    cycle_count: int
    wisdom_score: float
    antifragility_score: float
    dream_count: int
    soil_richness: float
    last_pulse: float


class GardenOverview(BaseModel):
    state: GardenStateResponse
    seeds: list[SeedResponse]
    seed_count: int


class SymbioticLinkResponse(BaseModel):
    id: str
    sprout_a_id: str
    sprout_b_id: str
    relationship_type: str
    synergy_score: float
    nutrient_flow: float
    pollen_transferred: bool
    created_at: float

    model_config = ConfigDict(from_attributes=True)


class DreamResponse(BaseModel):
    id: str
    source_seed_ids: list[str]
    insight: str
    temperature: float
    perplexity: float
    planted: bool
    created_at: float

    model_config = ConfigDict(from_attributes=True)


class WoundResponse(BaseModel):
    id: str
    wound_type: str
    severity: str
    source_hormone: str
    healing_action: str
    scar_lesson: str
    antifragility_gained: float
    created_at: float
    healed_at: float | None

    model_config = ConfigDict(from_attributes=True)


class PulseResponse(BaseModel):
    id: str
    cycle: int
    summary: str
    thriving: list[str]
    struggling: list[str]
    healing: list[str]
    dreaming: list[str]
    emergent: list[str]
    created_at: float

    model_config = ConfigDict(from_attributes=True)


class HormoneLogResponse(BaseModel):
    id: str
    hormone_name: str
    emitter_organ: str
    payload: dict
    processed: bool
    created_at: float

    model_config = ConfigDict(from_attributes=True)


class EcosystemResponse(BaseModel):
    state: GardenStateResponse
    seed_count: int
    sprout_count: int
    link_count: int
    wound_count: int
    dream_count: int
    recent_hormones: list[HormoneLogResponse]


class SoilRichnessResponse(BaseModel):
    richness: float
    total_composted: int
    theme_diversity: int
    garden_age_days: float


class AgentNodeResponse(BaseModel):
    id: str
    name: str
    agent_type: str
    status: str
    parent_id: str | None
    seed_id: str | None
    task_description: str
    capability: dict
    context: dict
    result: str
    error: str
    created_at: float
    started_at: float | None
    completed_at: float | None
    retired_at: float | None

    model_config = ConfigDict(from_attributes=True)


class AgentApprovalRequest(BaseModel):
    approved: bool = Field(..., description="Whether to approve the gated action")


# Forward reference resolution
SeedResponse.model_rebuild()
