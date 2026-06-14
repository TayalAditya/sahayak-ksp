# Sahayak — Intelligent Conversational AI for the KSP Crime Database

> **Datathon 2026 · Karnataka State Police · Challenge 01**
> A conversational crime-intelligence platform that lets investigators, analysts, and
> policymakers query the state crime database in natural language (English + ಕನ್ನಡ),
> with every answer grounded in real records and a transparent evidence trail.

*Sahayak* (ಸಹಾಯಕ, "assistant/helper") is built on the principle that **the AI never invents facts** —
it writes a verifiable query against the crime database, runs it on real rows, and shows
its work: the query it ran and the source FIRs behind every answer.

---

## The problem (Challenge 01)

The State Crime Records Bureau (SCRB) manages crime data from **1100+ police stations**
across Karnataka. Today, insight is locked behind static dashboards and manual SQL.
Sahayak turns the whole database into a question box — and goes beyond retrieval to
crime-pattern discovery, criminal-network analysis, offender profiling, and predictive
early-warning intelligence.

## What makes this win

| Most teams will… | Sahayak does… |
|---|---|
| Let the LLM "reason" over data → hallucinated numbers | LLM writes a **verifiable query**; answers computed on real rows |
| Bolt on translation at the end | **Bilingual (EN + Kannada) + voice** designed in from day 1 |
| Build a slick chat with no sourcing | **Evidence trail** — every answer cites its FIRs + shows the query |
| Flat Q&A, miss the graph | **Criminal-network** link analysis surfaced as a tool |
| 10 shallow disjoint tabs | One **conversational agent that orchestrates** every module as a tool |

## Architecture (Catalyst-native — deployment is mandatory on Zoho Catalyst)

```
                ┌─────────────────────────────────────────────┐
   EN / ಕನ್ನಡ   │  React SPA (Slate)  — chat · evidence panel  │
   voice ⇄ text │  voice ⇄ Catalyst NLP (STT/TTS/translation)  │
                └───────────────────────┬─────────────────────┘
                                        │  REST (API Gateway)
                ┌───────────────────────▼─────────────────────┐
                │  Orchestrator (AppSail / Functions)          │
                │  • RBAC + audit log   • evidence assembler   │
                │  • Agent: routes a question to a TOOL ↓      │
                └───┬──────────┬──────────┬──────────┬─────────┘
            NL→ZCQL │   network │  hotspot │  case-   │  risk / forecast
           (Qwen    │   graph   │  trends  │  summary │  (QuickML ML)
           Coder)   │           │          │ (Qwen14B)│
                ┌───▼──────────▼──────────▼──────────▼─────────┐
                │  Catalyst Data Store (ZCQL) + Search          │
                │  CCTNS-shaped crime records                   │
                └───────────────────────────────────────────────┘
   Grounding/citations: QuickML RAG + Knowledge Base (legal codes, SOPs)
```

**LLM:** Catalyst QuickML serves open-source **Qwen** (14B-Instruct / 7B-Coder). We develop
locally against Qwen-via-Ollama for production parity, behind a swappable `LLMProvider`.

See [docs/PHASES.md](docs/PHASES.md) for the build roadmap and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the Catalyst service mapping.

---

## Repo layout

```
data/        synthetic CCTNS-shaped dataset + generator + schema   (Phase 1 ✅)
backend/     orchestrator, NL→query engine, tools                  (Phase 2–3)
frontend/    React chat SPA                                        (Phase 4)
docs/        architecture, phases, schema, demo script
```

## Quick start (Phase 1 — data)

```bash
cd data
python -m pip install -r requirements.txt
python generate.py            # builds data/ksp_crime.db (+ CSV exports)
python verify.py              # prints summary stats + sample queries
```

## Status

Phase 1 (data foundation) — **in progress**. See [docs/PHASES.md](docs/PHASES.md).
