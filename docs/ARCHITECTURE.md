# Architecture — Sahayak (Catalyst-native)

**Hard constraint:** deployment is **mandatory on Zoho Catalyst**, and using a third-party
service where a Catalyst equivalent exists "may affect validity." So the stack is largely
*prescribed* — which we lean into. (Source: organizer submission rules + Catalyst workshop.)

## Thesis

One **conversational agent is the single front door** that *orchestrates* the other modules as
tools. The agent decides, per question, whether to run a DB query, render a network graph, pull
a forecast, or summarize a case. Build ~3 tools deeply; the breadth of the 10-module framework
emerges from one coherent UX instead of 10 disjoint tabs.

## Flow

```
 EN / ಕನ್ನಡ  +  voice
      │  (Catalyst NLP: STT / translation)
      ▼
 React SPA  ──REST──►  API Gateway  ──►  Orchestrator (AppSail / Functions)
 (Slate)                                   │  RBAC + audit log + evidence assembler
                                           │
                                           ▼  routes question → TOOL
   ┌──────────────┬──────────────┬──────────────┬───────────────┬──────────────┐
   │ NL→ZCQL      │ network      │ hotspot /    │ case summary  │ risk / forecast│
   │ (Qwen Coder) │ graph        │ trends       │ (Qwen 14B +   │ (QuickML ML)   │
   │              │              │ (code)       │  RAG)         │                │
   └──────┬───────┴──────┬───────┴──────┬───────┴───────┬───────┴───────┬────────┘
          ▼              ▼              ▼               ▼               ▼
                 Catalyst Data Store (ZCQL) + Search module
   Grounding/citations: QuickML RAG + Knowledge Base (legal codes, SOPs, case law)
```

## Capability → Catalyst service mapping

| Capability | Catalyst service | Phase |
|---|---|---|
| Frontend SPA (React) | **Slate** (auto-detect + GitHub auto-deploy) | 4 |
| Backend / orchestrator | **AppSail** (Express) or **Functions** (advanced I/O) | 3 |
| Relational crime data | **Data Store** (ZCQL) | 6 |
| Fuzzy / full-text name search | **Search** module | 6 |
| LLM (NL→query, summaries) | **QuickML LLM Serving** — Qwen 14B-Instruct / 7B-Coder | 2,6 |
| Grounding + citations | **QuickML RAG + Knowledge Base** | 6 |
| Voice (STT/TTS) + Kannada translation | **Catalyst NLP / Zia Services** | 6 |
| PDF export of conversation | **SmartBrowz** (headless browser) | 6 |
| Auth + RBAC | **Catalyst Authentication** | 3,6 |
| Risk scoring / forecasting / anomaly | **QuickML** (classification/regression/time-series/anomaly) | 6 |
| Scheduled early-warning jobs | **Catalyst Cron / Job Scheduling** | 6 |
| Multi-step tool orchestration | **Circuits** (optional; else in-code) | 5,6 |
| Object storage (exports, attachments) | **Stratus** | 6 |
| API auth / throttling | **API Gateway** | 6 |

## LLM strategy

Production LLM = **Qwen via Catalyst QuickML** (open-source; we tune temperature/top-k, not
weights — no external LLMs allowed). To avoid tuning prompts for the wrong model, we develop
against the **same Qwen family locally** (Ollama) behind a swappable `LLMProvider`:

```
LLMProvider
 ├── mock          deterministic canned SQL — tests & CI, no model needed
 ├── ollama-qwen   qwen2.5-coder / qwen2.5:14b locally — dev parity with prod
 └── catalyst-qwen QuickML LLM-serving endpoint (OAuth) — production
```

The NL→query engine is **schema-aware** (the prompt carries the table dictionary), emits a
**read-only** SQL/ZCQL `SELECT`, validates it (no writes, table allow-list), executes on real
rows, and returns the query + source rows so the answer is always **grounded and auditable**.

## Non-negotiables (police-grade)

- **No invented numbers** — every figure traces to a query + source FIRs.
- **Audit trail** — `audit_log` records who asked what, the generated query, and row count.
- **RBAC** — jurisdiction scoping (station officer ≠ state analyst) enforced before query execution.
