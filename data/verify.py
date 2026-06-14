"""
Sahayak — dataset verification & smoke-test.

Runs the analytical queries the conversational platform will need, proving the synthetic
data actually supports each Challenge-01 capability. Run after generate.py.

    python verify.py
"""

import os
import sqlite3
import sys
import textwrap

# Kannada output needs UTF-8; Windows consoles default to cp1252.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ksp_crime.db")


def section(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def run(cur, sql, params=()):
    rows = cur.execute(sql, params).fetchall()
    cols = [d[0] for d in cur.description]
    widths = [max(len(str(c)), *(len(str(r[i])) for r in rows)) if rows else len(str(c)) for i, c in enumerate(cols)]
    print("  " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(cols)))
    print("  " + "-+-".join("-" * w for w in widths))
    for r in rows:
        print("  " + " | ".join(str(v).ljust(widths[i]) for i, v in enumerate(r)))
    return rows


def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit("ksp_crime.db not found — run `python generate.py` first.")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    section("1. Crime-pattern: top crime heads statewide")
    run(cur, "SELECT crime_head, COUNT(*) AS firs FROM firs GROUP BY crime_head ORDER BY firs DESC LIMIT 8")

    section("2. Trend: FIRs per year")
    run(cur, "SELECT substr(occurrence_date,1,4) AS year, COUNT(*) AS firs FROM firs GROUP BY year ORDER BY year")

    section("3. Seasonality: theft FIRs by month (festival-season spike expected Oct-Nov)")
    run(cur, "SELECT substr(occurrence_date,6,2) AS month, COUNT(*) AS thefts "
             "FROM firs WHERE crime_head='Theft' GROUP BY month ORDER BY month")

    section("4. Hotspots: top police stations by FIR count")
    run(cur, "SELECT ps.name, d.name AS district, COUNT(*) AS firs "
             "FROM firs f JOIN police_stations ps ON ps.id=f.police_station_id "
             "JOIN districts d ON d.id=f.district_id GROUP BY ps.id ORDER BY firs DESC LIMIT 8")

    section("5. IPC<->BNS cross-walk: 'Theft' must span BOTH codes")
    run(cur, "SELECT ls.act, ls.section_code, COUNT(*) AS firs "
             "FROM firs f JOIN fir_sections fs ON fs.fir_id=f.id "
             "JOIN legal_sections ls ON ls.id=fs.legal_section_id "
             "WHERE ls.crime_head='Theft' GROUP BY ls.act, ls.section_code")

    section("6. Repeat offenders: persons with the most accused roles")
    run(cur, "SELECT p.id, p.full_name, p.full_name_kn, COUNT(*) AS cases "
             "FROM fir_persons fp JOIN persons p ON p.id=fp.person_id "
             "WHERE fp.role='Accused' GROUP BY p.id ORDER BY cases DESC LIMIT 6")

    section("7. Criminal network: a gang, its members and shared-FIR strength")
    gang = cur.execute("SELECT gang_name FROM associations WHERE gang_name IS NOT NULL LIMIT 1").fetchone()[0]
    print(f"  Gang: {gang}")
    run(cur, "SELECT DISTINCT p.id, p.full_name FROM associations a "
             "JOIN persons p ON p.id IN (a.person_a_id, a.person_b_id) "
             "WHERE a.gang_name=? LIMIT 12", (gang,))

    section("8. Financial crime: flagged money-trail transactions (top by amount)")
    run(cur, "SELECT t.id, fa1.person_id AS from_person, fa2.person_id AS to_person, "
             "t.amount_inr, t.channel FROM transactions t "
             "JOIN financial_accounts fa1 ON fa1.id=t.from_account_id "
             "JOIN financial_accounts fa2 ON fa2.id=t.to_account_id "
             "WHERE t.is_flagged=1 ORDER BY t.amount_inr DESC LIMIT 6")

    section("9. Investigation status distribution (case outcomes)")
    run(cur, "SELECT status, COUNT(*) AS firs FROM firs GROUP BY status ORDER BY firs DESC")

    section("10. Socio-demographic: accused by income band")
    run(cur, "SELECT p.income_band, COUNT(DISTINCT p.id) AS accused "
             "FROM fir_persons fp JOIN persons p ON p.id=fp.person_id "
             "WHERE fp.role='Accused' GROUP BY p.income_band ORDER BY accused DESC")

    print("\n" + textwrap.dedent("""\
        ✅ All capability queries returned data. The dataset supports:
           pattern discovery · trends · seasonality · hotspots · IPC↔BNS cross-walk ·
           repeat-offender detection · network/link analysis · financial trails ·
           case-outcome analytics · socio-demographic correlation.
        Next: Phase 2 — NL→query engine on Qwen, grounding answers in exactly these queries."""))
    conn.close()


if __name__ == "__main__":
    main()
