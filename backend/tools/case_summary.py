"""
Investigator decision support — automated case summary.

Given a FIR ID or FIR number, pulls all structured data and asks the Qwen 14B Instruct
model to generate a concise case summary with investigation leads.
"""

import sqlite3
from .. engine import config, llm


def _fetch_case(fir_id: int = None, fir_number: str = None):
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    if fir_id:
        fir = conn.execute("SELECT * FROM firs WHERE id = ?", (fir_id,)).fetchone()
    else:
        fir = conn.execute("SELECT * FROM firs WHERE fir_number = ?", (fir_number,)).fetchone()

    if not fir:
        conn.close()
        return None, {}

    fid = fir["id"]

    accused = conn.execute(
        "SELECT p.full_name, p.age, p.occupation, p.income_band, p.is_repeat_offender, a.bail_status "
        "FROM fir_persons fp JOIN persons p ON p.id = fp.person_id "
        "LEFT JOIN arrests a ON a.person_id = fp.person_id AND a.fir_id = fp.fir_id "
        "WHERE fp.fir_id = ? AND fp.role = 'Accused'", (fid,)
    ).fetchall()

    victims = conn.execute(
        "SELECT p.full_name, p.age FROM fir_persons fp JOIN persons p ON p.id = fp.person_id "
        "WHERE fp.fir_id = ? AND fp.role = 'Victim'", (fid,)
    ).fetchall()

    sections = conn.execute(
        "SELECT ls.act, ls.section_code, ls.title FROM fir_sections fs "
        "JOIN legal_sections ls ON ls.id = fs.legal_section_id WHERE fs.fir_id = ?", (fid,)
    ).fetchall()

    props = conn.execute(
        "SELECT type, value_inr, status FROM properties WHERE fir_id = ?", (fid,)
    ).fetchall()

    events = conn.execute(
        "SELECT event_date, event_type, note FROM investigation_events WHERE fir_id = ? ORDER BY event_date", (fid,)
    ).fetchall()

    conn.close()
    return fir, {"accused": accused, "victims": victims, "sections": sections, "properties": props, "events": events}


def summarize(fir_id: int = None, fir_number: str = None, provider=None):
    fir, related = _fetch_case(fir_id, fir_number)
    if not fir:
        return {"error": "FIR not found.", "fir_id": fir_id}

    # Build a structured text block for the model
    accused_text = "; ".join(
        f"{a['full_name']} (age {a['age']}, {a['occupation']}, {'repeat offender' if a['is_repeat_offender'] else 'first time'}, bail: {a['bail_status'] or 'unknown'})"
        for a in related["accused"]
    ) or "Unknown"

    props_text = "; ".join(
        f"{p['type']} worth ₹{p['value_inr']:,.0f} ({p['status']})" for p in related["properties"]
    ) or "None recorded"

    events_text = "\n".join(
        f"  {e['event_date']} — {e['event_type']}: {e['note']}" for e in related["events"]
    ) or "  No events recorded"

    case_text = f"""FIR: {fir['fir_number']}
Crime: {fir['crime_head']}
Date: {fir['occurrence_date']} at {fir['occurrence_time'] or 'unknown time'}
Station: (ID {fir['police_station_id']}) | Status: {fir['status']}
Modus Operandi: {fir['modus_operandi']}
Accused: {accused_text}
Victims: {'; '.join(v['full_name'] for v in related['victims']) or 'Unknown'}
Property: {props_text}
Sections charged: {'; '.join(f"{s['act']} {s['section_code']}" for s in related['sections'])}
Investigation timeline:
{events_text}"""

    system = (
        "You are an expert police case analyst. Given structured case data, produce a concise "
        "investigation summary with: (1) brief facts, (2) current status and gaps, "
        "(3) two or three specific next investigation steps. Be factual. Under 200 words."
    )

    provider = provider or llm.get_provider(model="instruct")
    summary_text = provider.complete(system, case_text, temperature=0.3, max_tokens=1024)

    return {
        "fir_number": fir["fir_number"],
        "crime_head": fir["crime_head"],
        "status": fir["status"],
        "summary": summary_text,
        "accused_count": len(related["accused"]),
        "case_data": case_text,
    }
