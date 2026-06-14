# Prototype Brief — Sahayak (ಸಹಾಯಕ)
## Datathon 2026 | Karnataka State Police | Challenge 01

### Problem Addressed
SCRB manages crime data from 1100+ stations locked behind static dashboards. Investigators waste hours on manual queries; pattern intelligence goes undiscovered.

### Solution (≤1024 chars for submission form)
Sahayak (ಸಹಾಯಕ, "assistant") is a conversational crime intelligence platform that lets KSP investigators ask questions in natural language (English + Kannada + voice) and get grounded answers backed by verifiable SQL evidence trails. The LLM never invents facts — it generates a read-only query, executes it on real records, and shows the exact source FIRs behind every answer. Key capabilities: NL→SQL on CCTNS-shaped data spanning IPC and BNS (post-2024-07-01 transition), criminal network link analysis, crime hotspot detection, AI-generated case summaries, multi-turn context, role-based access, and full audit logging for law-enforcement accountability. Built entirely on Catalyst (QuickML Qwen, AppSail, Slate, Data Store, Zia NLP).

### Key Features
1. Conversational Q&A — English + Kannada + voice (Catalyst Zia NLP)
2. Evidence trail — every answer shows the SQL + source FIRs (no hallucination)
3. Criminal network graph — link analysis across accused/gang/co-accused
4. Crime hotspot detection — geo-clustering from lat/lng (no special DB types)
5. AI case summaries — Qwen 14B Instruct generates investigation briefs
6. IPC↔BNS cross-walk — queries span both legal code systems automatically
7. Role-based access — Investigator/Analyst/Supervisor/Policymaker scoping
8. Audit log — every NL question + generated query logged for accountability
9. PDF export — conversation history (Catalyst SmartBrowz)
10. Fully deployed on Catalyst (AppSail backend + Slate frontend)

### Technology Stack
| Component | Technology |
|---|---|
| LLM (NL→SQL, summaries) | Catalyst QuickML — Qwen 2.5 Coder 7B + Instruct 14B |
| RAG / Knowledge Base | Catalyst QuickML RAG (legal codes, SOPs) |
| Voice + Kannada | Catalyst Zia Services (STT, TTS, translation) |
| Backend API | Python FastAPI → Catalyst AppSail |
| Frontend | React (Vite) → Catalyst Slate |
| Database | Catalyst Data Store (ZCQL) |
| Auth / RBAC | Catalyst Authentication |
| PDF export | Catalyst SmartBrowz |
| Audit + Events | Catalyst Signals + audit_log table |

### Impact
- Turns every investigator into a data analyst — no SQL knowledge needed
- Eliminates SCRB data cell bottleneck for ad-hoc queries
- Surfaces criminal network patterns invisible in flat dashboards
- Transparent evidence trail satisfies law-enforcement accountability requirements
- Scalable to all 1100+ Karnataka police stations
