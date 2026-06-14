# Sahayak — Pitch Deck Script
## Datathon 2026 Grand Finale | 5-minute demo

---

### SLIDE 1 — The Problem (30s)
"An investigator at a Karnataka police station wants to know: how many chain-snatching cases on two-wheelers in this PS limit in the last 6 months where the accused is out on bail?
Today, they either wait days for the SCRB data cell, or click through static dashboards that can't answer that question.
3,500+ FIRs filed daily. 1100+ stations. The intelligence is there — it's just inaccessible."

### SLIDE 2 — Our Solution (30s)
"Sahayak — ಸಹಾಯಕ — is a conversational crime intelligence platform.
Ask a question. In plain English, or Kannada, or by voice.
Get an answer backed by real records — with the exact SQL query and source FIRs shown transparently.
The AI never invents facts. Everything is grounded, auditable, and explainable."

### SLIDE 3 — LIVE DEMO (2 min)
**[Open http://localhost:5173]**
1. "How many theft cases are there?" → Answer: 699. Click 'Show evidence' → show SQL + rows
2. "Which district has the most robbery cases?" → Bengaluru Urban. Evidence shown.
3. "Show me the top repeat offenders" → Suresh Naik, 33 cases. "Is he currently on bail?" → follow-up works
4. **Switch to Network tab** → Show criminal network graph for Robbery — 138 nodes, 187 links, gangs highlighted
5. **Switch to Hotspots tab** → Show theft clusters on Bengaluru map, Oct-Nov festival spike
6. **Case summary** → Click any FIR → AI-generated investigation brief in 5 seconds

### SLIDE 4 — The Differentiator (30s)
"Three things most teams won't have:
ONE: IPC↔BNS cross-walk. Every query spans both legal code systems automatically — the July 2024 transition is invisible to the investigator.
TWO: Evidence trail. Every number traces back to exact FIRs. That's what law enforcement accountability requires.
THREE: Built entirely on Catalyst — QuickML Qwen, AppSail, Slate, Zia voice, Data Store. Zoho's infrastructure, production-ready."

### SLIDE 5 — Architecture (30s)
[Show ARCHITECTURE.md diagram]
"One conversational agent orchestrating 5 tools — NL→SQL, network analysis, hotspot detection, case summarization, and forecasting — as a single interface. Not 10 disjoint tabs. One question box."

### SLIDE 6 — Impact & Scale (30s)
"Every investigator becomes a data analyst. The SCRB data cell bottleneck disappears.
Criminal networks that took weeks to map appear in seconds.
Role-based access means a station officer sees their jurisdiction; the IGP sees the state.
Every query is logged — full audit trail for court and accountability requirements.
Ready to scale to all 1100+ Karnataka police stations."

---

## Demo Q&A Prep

**Q: What if the LLM generates wrong SQL?**
A: "Two safeguards. First, every generated query is validated — read-only, known tables only, no write operations possible at the driver level. Second, every answer shows the SQL and source rows so the investigator can verify. We never present a number without its evidence."

**Q: Why Catalyst/Qwen instead of GPT-4?**
A: "The organizer requirement and deployment mandate. We built the LLM as a swappable interface — if a more capable model becomes available on Catalyst, it's a config change."

**Q: Does it work in Kannada?**
A: "Yes — via Catalyst Zia's translation and STT/TTS services. The bilingual design is in the core data model (every person has both English and Kannada name fields). We built it in, not bolted on."

**Q: What about real CCTNS data?**
A: "Our dataset mirrors CCTNS structure exactly — same entities, same relationships, same IPC/BNS section codes. The platform is data-agnostic; plugging in real SCRB data is a CSV import into Catalyst Data Store."
