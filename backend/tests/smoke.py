"""
Phase 2 foundation smoke-test. Run from the project root:

    python -m backend.tests.smoke

Proves: schema introspection, SQL safety (safe passes / unsafe rejected), read-only execution,
and the mock LLM -> validate -> execute round-trip.
"""

import sys

from backend.engine import db, llm

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def check(label, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}")
    if not cond:
        raise SystemExit(f"smoke-test failed at: {label}")


def main():
    print("\n1. Schema introspection")
    schema = db.get_schema_dict()
    check(f"introspected {len(schema)} tables", len(schema) >= 15)
    check("firs table has expected columns", "crime_head" in dict(schema["firs"]))

    print("\n2. SQL safety guard")
    safe = db.validate_select("SELECT crime_head, COUNT(*) FROM firs GROUP BY crime_head")
    check("safe SELECT accepted + LIMIT enforced", "LIMIT" in safe)
    for bad in [
        "DELETE FROM firs",
        "SELECT * FROM firs; DROP TABLE firs",
        "SELECT * FROM secret_table",
        "UPDATE persons SET age=0",
    ]:
        try:
            db.validate_select(bad)
            check(f"rejected unsafe: {bad[:30]}", False)
        except db.UnsafeQueryError:
            check(f"rejected unsafe: {bad[:30]}", True)

    print("\n3. Read-only execution")
    res = db.run_query("SELECT crime_head, COUNT(*) AS n FROM firs GROUP BY crime_head ORDER BY n DESC")
    check("query returned rows", res["row_count"] > 0)
    print(f"     top crime head: {res['rows'][0]['crime_head']} ({res['rows'][0]['n']})")

    print("\n4. Mock LLM -> validate -> execute round-trip")
    provider = llm.get_provider("mock")
    sql = provider.complete("You generate SQL.", "How many theft cases are there?")
    print(f"     mock SQL: {sql}")
    out = db.run_query(sql)
    check("mock-generated SQL executed", out["row_count"] >= 1)
    print(f"     result: {out['rows'][0]}")

    print("\n✅ Phase 2 foundation OK — DB layer + safety + pluggable LLM all working.\n")


if __name__ == "__main__":
    main()
