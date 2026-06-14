"""
Sahayak eval harness — 12 canonical officer questions.

These are the demo questions judges will see. Running this gives confidence the
NL→SQL pipeline handles every Challenge-01 use case category correctly.

Usage:
    python -m backend.tests.eval_harness            # mock provider (fast, offline)
    python -m backend.tests.eval_harness --live     # Catalyst Qwen (takes ~3-4 min)
"""

import sys, os, json, argparse
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from backend.engine import config, llm
from backend.engine.nl2sql import ask
config.load_dotenv()

QUESTIONS = [
    # --- crime pattern (Module 1 + 3)
    ("Crime distribution",       "What are the top 10 crime types by number of FIRs?"),
    ("Theft trend",              "Show theft FIRs by year"),
    ("Festival spike",           "How many theft cases occurred in October and November?"),
    # --- hotspots (Module 3)
    ("Hotspot stations",         "Which 5 police stations have the most FIRs?"),
    ("District hotspot",         "Which district has the most robbery cases?"),
    # --- investigator status (Module 6)
    ("Case status",              "How many cases are currently under investigation vs charge-sheeted?"),
    ("Bail status",              "What is the breakdown of bail status for arrested accused?"),
    # --- repeat offenders / network (Module 2 + 5)
    ("Repeat offenders",         "Show the top 5 repeat offenders by number of cases"),
    ("Gang link",                "Which gangs are linked to the most FIRs?"),
    # --- financial crime (Module 7)
    ("Flagged transactions",     "Show the top 5 largest flagged financial transactions"),
    # --- socio-demographic (Module 4)
    ("Income band crime",        "How many accused come from each income band?"),
    # --- IPC / BNS cross-walk (differentiator)
    ("IPC vs BNS",               "How many theft FIRs are registered under IPC vs BNS?"),
]


def run(provider, label):
    print(f"\n{'='*70}")
    print(f"Sahayak eval — {label} ({len(QUESTIONS)} questions)")
    print(f"{'='*70}")
    passed = failed = 0
    for category, q in QUESTIONS:
        result = ask(q, provider=provider)
        ok = not result.error and result.row_count > 0
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"\n[{status}] {category}")
        print(f"  Q: {q}")
        if result.sql:
            print(f"  SQL: {result.sql}")
        if result.rows:
            print(f"  Top rows: {json.dumps(result.rows[:2], ensure_ascii=False)}")
        if result.error:
            print(f"  ERROR: {result.error}")
    print(f"\n{'='*70}")
    print(f"Results: {passed}/{len(QUESTIONS)} passed  ({failed} failed)")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="Use Catalyst Qwen instead of mock")
    args = ap.parse_args()
    provider_name = "catalyst-qwen" if args.live else "mock"
    model = "coder" if args.live else None
    run(llm.get_provider(provider_name, model=model),
        label="Catalyst Qwen (live)" if args.live else "Mock provider")
