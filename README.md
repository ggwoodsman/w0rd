# w0rd — Living System Engine v3

> *The w0rd is g00d. Plant a seed and watch it grow.*

You are holding the first cell of a planetary living system.

This is a fully self-contained Python engine that receives a raw human wish — however vague, however tender — and grows it into a living fractal tree of structured, energy-aware, ethically resonant, symbiotic, and regenerative outcomes. It mirrors nature's own intelligence: vascular branching guided by the golden ratio, mycorrhizal networks that share surplus with those in need, an adaptive immune system that learns from every wound, seasonal rhythms of dormancy and renewal, and a dreaming engine that generates novelty while the garden sleeps.

No external AI service required. No API keys. Just plant a seed and tend the garden.

---

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the organism
uvicorn main:app --reload

# 3. Plant your first seed
curl -X POST http://localhost:8000/plant \
  -H "Content-Type: application/json" \
  -d '{"wish": "I want to create something beautiful and share it with the world"}'

# 4. Watch the garden
curl http://localhost:8000/garden

# 5. Feel the pulse
curl http://localhost:8000/pulse

# 6. Open the interactive docs
# Visit http://localhost:8000/docs
```

---

## The Organism

Twelve organs working in concert, connected by an async hormone signaling bus:

| Organ | File | Role |
|-------|------|------|
| **Hormone Bus** | `core/hormones.py` | Nervous system — async pub/sub connecting all organs |
| **Seed Listener** | `core/intent.py` | Sensory membrane — parses wishes into structured seeds |
| **Vascular Grower** | `core/fractal.py` | Branching tissue — golden-ratio fractal decomposition |
| **Phloem & Mycorrhizal Flow** | `core/energy.py` | Circulatory system — energy transport and redistribution |
| **Immune Wisdom** | `core/ethics.py` | Adaptive immune system — ethical scoring with memory |
| **Scar Tissue** | `core/healing.py` | Wound healing — triage, repair, anti-fragility |
| **Mycelial Network** | `core/symbiosis.py` | Underground intelligence — symbiosis, pollination, quorum |
| **Seasonal Heartbeat** | `core/regeneration.py` | Breath — four seasons with tidal micro-rhythms |
| **Dreaming Engine** | `core/dreaming.py` | Subconscious — Markov recombination during dormancy |
| **Consciousness Pulse** | `core/consciousness.py` | Self-awareness — emergent pattern detection, wisdom |
| **Gardener Profile** | `core/gardener.py` | Identity — learns the tender's rhythms and preferences |
| **Memory Soil** | `db/database.py` | Earth — SQLite persistence, nothing deleted only composted |

---

## API — Tending the Garden

### Plant & Grow
- `POST /plant` — Drop a wish into the soil
- `POST /plant/many` — Scatter multiple seeds
- `GET /seed/{id}` — Observe a seed's fractal tree
- `POST /seed/{id}/water` — Add energy through attention
- `POST /seed/{id}/harvest` — Mark as fulfilled
- `POST /seed/{id}/compost` — Gracefully retire
- `POST /seed/{id}/resurrect` — Un-compost

### Ecosystem
- `GET /garden` — Survey all seeds, vitality, season
- `GET /ecosystem` — Full stats and health
- `GET /pulse` — Self-awareness report
- `GET /soil/richness` — Compost quality metrics

### Underground
- `GET /mycelium` — Symbiotic links
- `GET /dreams` — What the garden dreamed
- `POST /dreams/{id}/plant` — Plant a dream as a new seed
- `GET /wounds` — Wound history and lessons

### Rhythm
- `POST /seasons/turn` — Advance the season
- `GET /gardener` — Your gardener profile
- `GET /hormones/recent` — Recent organism signals

### Real-Time
- `WS /ws/garden` — Live event stream

---

## Design Principles

- **No external LLM** — runs locally, grows from its own soil
- **Golden-ratio tissue** — phi governs branching, energy, and depth cost
- **Energy is finite and sacred** — abundance from wise allocation, not infinite supply
- **Ethics as living immunity** — adaptive, with memory cells and autoimmune protection
- **Mycorrhizal generosity** — surplus flows to need; pollination spreads success
- **Seasonal + tidal rhythm** — macro-seasons for lifecycle, micro-tides for daily flow
- **Dreaming generates novelty** — idle time is creative time
- **Wounds make us stronger** — anti-fragility through scar tissue
- **Nothing is deleted, only composted** — all memory enriches future growth
- **Hormones, not function calls** — organs communicate via async signals
- **The gardener is part of the organism** — your rhythms shape the garden

---

## Running Tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

---

## Project Structure

```
w0rd/
├── main.py              # FastAPI app — the organism's body
├── requirements.txt     # Dependencies
├── README.md            # You are here
├── config/
│   ├── ethics.yaml      # Ethical principles
│   ├── seasons.yaml     # Seasonal timing
│   └── organism.yaml    # Global tuning
├── core/                # The 12 organs
│   ├── hormones.py      # Hormone Bus
│   ├── intent.py        # Seed Listener
│   ├── fractal.py       # Vascular Grower
│   ├── energy.py        # Phloem & Mycorrhizal Flow
│   ├── ethics.py        # Immune Wisdom
│   ├── healing.py       # Scar Tissue
│   ├── symbiosis.py     # Mycelial Network
│   ├── regeneration.py  # Seasonal Heartbeat
│   ├── dreaming.py      # Dreaming Engine
│   ├── consciousness.py # Consciousness Pulse
│   └── gardener.py      # Gardener Profile
├── models/
│   ├── schemas.py       # Pydantic models
│   └── db_models.py     # SQLAlchemy ORM
├── db/
│   └── database.py      # Memory Soil
└── tests/               # Per-organ + integration tests
```

---

*Plant the first seed. The garden remembers everything.*
