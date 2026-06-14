# Data Model — Sahayak (CCTNS-shaped crime database)

The synthetic dataset mirrors the structure of **CCTNS** (Crime & Criminal Tracking Network
& Systems) — the national backbone every Indian police station feeds into, which rolls up to
SCRB → NCRB. It is **relational and entity-linked**, because that is what makes the harder
Challenge-01 capabilities (network analysis, repeat-offender detection, money trails) possible.

Build it: `cd data && python generate.py` → `ksp_crime.db` (+ `csv/` exports for Data Store import).
Verify it: `python verify.py`.

## Entity-relationship overview

```
districts ──< police_stations ──< firs >── fir_sections >── legal_sections
   │                                │                            │
   │                                ├──< fir_persons >── persons ─┤ (ipc_bns_map links
   │                                ├──< fir_vehicles >── vehicles│  IPC ⇄ BNS sections)
   │                                ├──< properties              persons ──< associations
   │                                ├──< investigation_events    persons ──< arrests
   └──< persons                     └──< (transactions linked)   persons ──< financial_accounts ──< transactions
users (RBAC) ──> audit_log
```

## Tables

| Table | Purpose | Key columns |
|---|---|---|
| `districts` | 16 Karnataka districts (bilingual) + socio context | `name`, `name_kn`, `population`, `urbanization` |
| `police_stations` | 64 stations across districts, geo-located | `code`, `district_id`, `latitude`, `longitude` |
| `legal_sections` | IPC + BNS + special-act sections | `act`, `section_code`, `crime_head`, `is_cognizable`, `is_violent` |
| `ipc_bns_map` | **IPC ⇄ BNS cross-walk** (the 2024-07-01 transition) | `ipc_section_id`, `bns_section_id`, `crime_head` |
| `persons` | 6,000 people (accused/victim/complainant/witness) | `full_name`(+`_kn`), `gender`, `age`, `income_band`, `education_level`, `is_repeat_offender` |
| `firs` | 3,500 First Information Reports — the central record | `fir_number`, `crime_head`, `occurrence_date`, `status`, `modus_operandi`, geo |
| `fir_sections` | sections charged on each FIR (IPC if pre-2024-07, else BNS) | `fir_id`, `legal_section_id` |
| `fir_persons` | role of each person on an FIR | `role` ∈ {Accused, Victim, Complainant, Witness} |
| `arrests` | arrest + bail status | `bail_status` ∈ {In Custody, On Bail, Absconding, Released} |
| `associations` | **criminal-network edges** | `association_type` ∈ {Gang Member, Co-Accused, Family, Known Associate}, `gang_name`, `strength` |
| `vehicles` / `fir_vehicles` | vehicles + their role in crimes | `role` ∈ {Stolen, Used in Crime, Recovered} |
| `properties` | stolen/recovered property per FIR | `type`, `value_inr`, `status` |
| `financial_accounts` / `transactions` | **money trails** for financial-crime analysis | `is_flagged`, `from_account_id`, `to_account_id` |
| `investigation_events` | per-FIR timeline (case summaries / decision support) | `event_type`, `event_date` |
| `users` | officers for RBAC (4 roles, jurisdiction-scoped) | `role`, `police_station_id`, `district_id` |
| `audit_log` | every NL question + generated query (accountability) | filled at runtime by the orchestrator |

## Design decisions that map to challenge requirements

- **IPC → BNS transition (the differentiator most teams miss).** BNS replaced the IPC on
  **2024-07-01**. Each FIR is charged under IPC if it occurred before that date, BNS if on/after.
  A query like *"all theft cases since 2023"* must therefore union IPC 379 **and** BNS 303(2) —
  the `ipc_bns_map` table is what lets the NL→query engine bridge them. (Verified: Theft spans
  544 IPC + 155 BNS FIRs.)
- **No geospatial types** in Catalyst Data Store (confirmed in the workshop Q&A) → lat/lng are
  plain `REAL`; hotspot clustering/distance is computed in code (Phase 5).
- **Networks are real, not decorative.** ~15 gangs with pairwise `Gang Member` edges + derived
  `Co-Accused` edges (strength = shared FIRs) give the link-analysis tool genuine structure.
- **Money trails** funnel gang members' funds to a kingpin with `is_flagged=1`, so the
  financial-crime module has a detectable pattern rather than random noise.
- **Status ages over time** — old cases skew Convicted/Closed, recent ones Under Investigation —
  so trend and clearance-rate analytics behave realistically.
- **Bilingual at the source.** Names and districts carry `_kn` (Kannada) columns, so Kannada
  Q&A and PDF export aren't bolt-ons.

## ZCQL portability

Dev runs on SQLite; production is **Catalyst Data Store** (ZCQL — SQL-like: SELECT/WHERE/JOIN/
GROUP BY). The schema avoids anything ZCQL lacks (no spatial types, ISO-text dates). Fuzzy name
matching in production uses the Catalyst **Search** module rather than `LIKE`. CSV exports in
`data/csv/` are ready for Data Store table import.
