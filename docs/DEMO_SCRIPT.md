# Demo Script — 12 Canonical Officer Questions

These are the exact questions to run during the demo. Each one showcases a different
Challenge-01 module. They've been verified to return correct answers against the dataset.

| # | Question | Module | Expected answer |
|---|---|---|---|
| 1 | "How many theft cases are there in total?" | Crime pattern | 699 |
| 2 | "Which district has the most FIRs?" | Hotspot | Bengaluru Urban (578) |
| 3 | "Show the top 5 repeat offenders" | Offender profiling | Suresh Naik (33 cases) |
| 4 | "What is the FIR trend by year?" | Trend analysis | Table 2019-2026 |
| 5 | "How many theft cases in October and November?" | Seasonality | ~302 (festival spike) |
| 6 | "What is the bail status breakdown?" | Investigation status | On Bail: 1828, In Custody: 1001 |
| 7 | "How many cases are under investigation vs charge-sheeted?" | Case status | UI:718, CS:822 |
| 8 | "Which gangs are linked to robbery cases?" | Criminal network | Shows gang names + counts |
| 9 | "Show the top 5 largest flagged transactions" | Financial crime | ₹296k+ flagged UPI/NEFT |
| 10 | "How many accused come from low income households?" | Socio-demographic | ~1143 Low income band |
| 11 | "How many theft FIRs are under IPC vs BNS?" | IPC↔BNS crosswalk | IPC:544, BNS:155 |
| 12 | *(follow-up on Q3)* "Is the top offender currently on bail?" | Context/multi-turn | Bail status for Suresh Naik |

## Follow-up conversation chain (demonstrates multi-turn)
1. "Show robbery cases in Bengaluru Urban"
2. "Of those, how many are charge-sheeted?"
3. "Who are the accused in those cases?"

## Evidence trail demo sequence
1. Ask any question
2. Click "Show evidence & SQL"
3. Show the judges: exact SQL, source rows, row count
4. Say: "Every figure traces back to real records. The AI never invents a number."
