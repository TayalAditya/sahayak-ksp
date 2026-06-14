# Build Roadmap — Sahayak (Challenge 01)

Timeline: today **2026-06-14** → prototype submission closes **2026-07-26 23:59 IST** (~6 weeks).
Deliverables: public GitHub repo + **Catalyst-deployed** live app + demo video + pitch deck (official template).

Guiding thesis: **one conversational agent that orchestrates a few well-built tools.** Build the
core spine + 3 differentiator tools deeply; show the rest of the 10-module framework as tools the
agent *can* call. Focused **and** comprehensive.

---

## Phase 1 — Data Foundation  ⏳ in progress
A realistic, defensible dataset is the bedrock — without it nothing downstream can be demoed.
- [x] Repo scaffold, README, docs
- [ ] CCTNS-shaped relational schema (ZCQL/Data-Store-compatible)
- [ ] Synthetic Karnataka crime dataset generator — bilingual (EN+ಕನ್ನಡ) names, real districts,
      **IPC→BNS** section cross-walk spanning the 2024-07-01 transition, criminal networks/gangs,
      vehicles, property, financial transactions, arrests + bail status
- [ ] Local **SQLite** dev DB (mirrors Data Store) + verification script

## Phase 2 — NL→Query core (on Qwen)
The heart. Must transfer to deployed Catalyst Qwen, so dev against Qwen-via-Ollama.
- `LLMProvider` abstraction: `ollama-qwen` (dev) / `catalyst-qwen` (prod) / `mock` (tests)
- Schema-aware **NL→SQL/ZCQL** with few-shot, **read-only** guardrails, query validation
- **Evidence trail**: return the executed query + the exact source rows for every answer
- Context-aware multi-turn conversation
- Eval harness: the canonical officer-question set (see docs/DEMO_SCRIPT.md) with expected behavior

## Phase 3 — Backend API (AppSail / Functions)
- `/chat` orchestrator endpoint (routes question → tool), tool endpoints
- **RBAC** middleware (Investigator / Analyst / Supervisor / Policymaker; jurisdiction scoping)
- **Audit log** (who asked what, when, what query ran) — law-enforcement accountability

## Phase 4 — Frontend (React on Slate)
- Chat UI + **evidence panel** (query + cited FIRs side-by-side)
- **EN / ಕನ್ನಡ** toggle, **voice** mic button, **PDF export** of conversation
- Role-aware views

## Phase 5 — Differentiator tools (wired as agent tools)
- **Criminal-network graph** (link analysis: accused ↔ co-accused ↔ gangs ↔ locations)
- **Crime hotspots & trends** (time/geo/crime-type; clustering computed in code — no geo types in ZCQL)
- **Investigator decision support** (case summaries, similar-past-cases via RAG)

## Phase 6 — Catalyst integration & deploy
- Port SQLite → **Catalyst Data Store** (DDL → tables; queries → ZCQL); wire **Search** for fuzzy names
- Swap LLMProvider → **QuickML LLM serving (Qwen)**; **RAG + Knowledge Base** (legal codes, SOPs) for grounding
- **Zia / NLP models** for voice (STT/TTS) + Kannada translation
- **SmartBrowz** for PDF export; **Catalyst Authentication** for RBAC
- **QuickML** classical ML for offender risk-scoring + crime forecasting/anomaly (stretch modules)
- Deploy: frontend → **Slate**, backend → **AppSail**, fronted by **API Gateway**
- Pull in Zoho's **Catalyst agent-skills for Claude Code** to generate correct Catalyst code

## Phase 7 — Submission
- Demo video (problem → working prototype → key workflows)
- Pitch deck on the **official template**; 1024-char prototype brief; README polish; verify all links live

---

### Scope tiers (the 10-module framework)
🟢 **Core:** 1 Conversational interface · 9 Explainable AI/evidence · 10 RBAC+audit
🔵 **Differentiators:** 2 Criminal network · 3 Pattern/trend/hotspots · 6 Investigator decision support
⚪ **Stretch:** 4 Sociological · 5 Offender risk-scoring · 7 Financial/transaction links · 8 Forecasting/early-warning
