"""
Sahayak — Catalyst Basic I/O Function (self-contained, no external imports).
Handles: health, chat (NL→SQL via Qwen), hotspots, trends, network.
DB: ksp_crime.db bundled alongside this file.
"""
import os, sys, json, sqlite3, re, urllib.request, urllib.parse, urllib.error

# ── DB path ──────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ksp_crime.db")

# ── Qwen config (read from env, set in catalyst-config.json) ─────────────────
QWEN_ENDPOINT = os.environ.get("APP_QWEN_ENDPOINT",
    "https://api.catalyst.zoho.in/quickml/v2/project/50328000000013024/llm/chat")
QWEN_MODEL    = os.environ.get("APP_QWEN_MODEL", "crm-di-qwen_coder_7b-it")
ZOHO_DC       = os.environ.get("APP_DC", "in")
ORG_ID        = os.environ.get("APP_ORG_ID", "60074201340")
CLIENT_ID     = os.environ.get("APP_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("APP_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("APP_REFRESH_TOKEN", "")

_access_token = None

def get_token():
    global _access_token
    if _access_token:
        return _access_token
    url = f"https://accounts.zoho.{ZOHO_DC}/oauth/v2/token"
    payload = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
    }).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    _access_token = d["access_token"]
    return _access_token

# ── NL→SQL prompt ─────────────────────────────────────────────────────────────
SYSTEM = """You are a SQLite query engine. OUTPUT ONLY SQL — no words, no explanation, no markdown.
RULE: Your ENTIRE response must be a single SQL SELECT statement ending with semicolon.
If not a crime data question, output exactly: CANNOT_ANSWER

Schema:
firs(id,fir_number,police_station_id,district_id,reported_date,occurrence_date,crime_head,status,investigating_officer,latitude,longitude)
districts(id,name,region,population)
police_stations(id,name,district_id)
persons(id,full_name,gender,age,income_band,is_repeat_offender,district_id)
fir_persons(fir_id,person_id,role)
arrests(person_id,fir_id,arrest_date,bail_status)
associations(person_a_id,person_b_id,association_type,gang_name,strength)
fir_sections(fir_id,legal_section_id)
legal_sections(id,act,section_code,crime_head)
properties(fir_id,type,value_inr,status)
transactions(from_account_id,to_account_id,amount_inr,txn_date,is_flagged)
financial_accounts(id,person_id,bank)
investigation_events(fir_id,event_date,event_type,note)

Examples:
Q:theft count
SELECT COUNT(*) AS theft_cases FROM firs WHERE crime_head='Theft' LIMIT 200;
Q:top 5 districts
SELECT d.name AS district,COUNT(*) AS firs FROM firs f JOIN districts d ON d.id=f.district_id GROUP BY d.id ORDER BY firs DESC LIMIT 5;
Q:repeat offenders
SELECT p.full_name,COUNT(*) AS cases FROM fir_persons fp JOIN persons p ON p.id=fp.person_id WHERE fp.role='Accused' GROUP BY p.id ORDER BY cases DESC LIMIT 10;
Q:FIR trend by year
SELECT substr(occurrence_date,1,4) AS year,COUNT(*) AS firs FROM firs GROUP BY year ORDER BY year LIMIT 200;
Q:bail status
SELECT bail_status,COUNT(*) AS n FROM arrests GROUP BY bail_status ORDER BY n DESC LIMIT 200;"""

META_REPLY = ("I answer questions about the KSP crime database. Ask me things like:\n"
              "— \"How many theft cases in Bengaluru?\"\n"
              "— \"Which district has the most FIRs?\"\n"
              "— \"Show top 5 repeat offenders\"\n"
              "— \"FIR trend by year\"\n"
              "— \"Which gangs are linked to robbery cases?\"")

GREETING_RE = re.compile(r"^\s*(hi+|hello+|hey+|namaste|good\s*(morning|evening|afternoon)|bye+|goodbye)\s*[!?.]*\s*$", re.I)
META_RE = re.compile(r"^\s*(what\s+can|why\s+not|ok+ay?|sure|thanks?|test|ping|[\?!.\s]+)\s*$", re.I)
SHORTCUTS = {
    "fir": "SELECT f.fir_number,f.crime_head,f.occurrence_date,f.status,d.name AS district FROM firs f JOIN districts d ON d.id=f.district_id ORDER BY f.reported_date DESC LIMIT 20;",
    "firs": "SELECT f.fir_number,f.crime_head,f.occurrence_date,f.status,d.name AS district FROM firs f JOIN districts d ON d.id=f.district_id ORDER BY f.reported_date DESC LIMIT 20;",
    "theft": "SELECT COUNT(*) AS theft_cases FROM firs WHERE crime_head='Theft' LIMIT 200;",
    "robbery": "SELECT COUNT(*) AS robbery_cases FROM firs WHERE crime_head='Robbery' LIMIT 200;",
    "districts": "SELECT d.name,COUNT(*) AS firs FROM firs f JOIN districts d ON d.id=f.district_id GROUP BY d.id ORDER BY firs DESC LIMIT 16;",
    "accused": "SELECT p.full_name,COUNT(*) AS cases FROM fir_persons fp JOIN persons p ON p.id=fp.person_id WHERE fp.role='Accused' GROUP BY p.id ORDER BY cases DESC LIMIT 20;",
    "gangs": "SELECT gang_name,COUNT(DISTINCT person_a_id) AS members FROM associations WHERE gang_name IS NOT NULL GROUP BY gang_name ORDER BY members DESC LIMIT 15;",
    "trends": "SELECT substr(occurrence_date,1,4) AS year,COUNT(*) AS firs FROM firs GROUP BY year ORDER BY year LIMIT 200;",
    "data": "SELECT f.fir_number,f.crime_head,f.occurrence_date,f.status,d.name AS district FROM firs f JOIN districts d ON d.id=f.district_id ORDER BY f.reported_date DESC LIMIT 50;",
}

def qwen_sql(question):
    """Call Qwen Coder to generate SQL for a question."""
    token = get_token()
    payload = json.dumps({
        "model": QWEN_MODEL,
        "prompt": f"Q:{question}\n",
        "system_prompt": SYSTEM,
        "top_p": 0.9, "top_k": 50, "temperature": 0.0, "max_tokens": 2048,
    }).encode()
    req = urllib.request.Request(QWEN_ENDPOINT, data=payload, method="POST",
        headers={"Authorization": f"Zoho-oauthtoken {token}",
                 "Content-Type": "application/json", "CATALYST-ORG": ORG_ID})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read().decode())
    return d.get("response", "")

def extract_sql(text):
    if not text: return None
    text = text.strip()
    fence = re.search(r"```(?:sql)?\s*([\s\S]+?)```", text, re.I)
    if fence: text = fence.group(1).strip()
    m = re.search(r"((?:WITH|SELECT)\b[\s\S]+?;)", text, re.I)
    if m: return m.group(1).strip()
    if re.match(r"^\s*(SELECT|WITH)\b", text, re.I): return text
    return None

def run_sql(sql):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Safety: read-only
    if re.search(r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|ATTACH)\b", sql, re.I):
        conn.close()
        raise ValueError("Read-only: write operations not allowed")
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return cols, rows

def chat(question):
    q = question.strip()

    # Greetings
    if GREETING_RE.match(q):
        return {"answer": "Hello. Ask me about crime data — FIRs, districts, accused, trends.", "sql": None, "columns": [], "rows": [], "row_count": 0}

    # Meta
    if META_RE.match(q):
        return {"answer": META_REPLY, "sql": None, "columns": [], "rows": [], "row_count": 0}

    # Shortcuts
    key = q.lower().rstrip("s?!")
    sql = SHORTCUTS.get(q.lower()) or SHORTCUTS.get(key)

    if not sql:
        raw = qwen_sql(q)
        if not raw or raw.strip().upper() == "CANNOT_ANSWER":
            return {"answer": META_REPLY, "sql": None, "columns": [], "rows": [], "row_count": 0}
        sql = extract_sql(raw)
        if not sql:
            # retry
            raw2 = qwen_sql(f"Write a SQLite SELECT query for: {q}\nOutput ONLY the SQL, starting with SELECT.")
            sql = extract_sql(raw2 or "")
        if not sql:
            return {"answer": META_REPLY, "sql": None, "columns": [], "rows": [], "row_count": 0}

    try:
        cols, rows = run_sql(sql)
    except Exception as e:
        return {"answer": f"Query error: {e}", "sql": sql, "columns": [], "rows": [], "row_count": 0}

    rc = len(rows)
    if rc == 0:
        answer = "No records found."
    elif rc == 1 and len(cols) == 1:
        answer = f"**{list(rows[0].values())[0]}**"
    else:
        answer = f"**{rc}** record(s) found. Expand the evidence trail to see the query and source rows."

    return {"answer": answer, "sql": sql, "columns": cols, "rows": rows[:50], "row_count": rc, "error": None}

# ── Main handler ──────────────────────────────────────────────────────────────

def handler(context, basicio):
    try:
        raw = basicio.get_argument("input") or "{}"
        try:
            body = json.loads(raw)
        except Exception:
            body = {}

        action = body.get("action", "health")

        if action == "health":
            result = {"status": "ok", "db": os.path.exists(DB_PATH), "model": QWEN_MODEL}

        elif action == "chat":
            question = body.get("question", "").strip()
            if not question:
                result = {"error": "question is required"}
            else:
                result = chat(question)

        elif action == "hotspots":
            crime_head = body.get("crime_head")
            sql = ("SELECT ps.name,d.name AS district,COUNT(*) AS firs,AVG(f.latitude) AS lat,AVG(f.longitude) AS lng "
                   "FROM firs f JOIN police_stations ps ON ps.id=f.police_station_id JOIN districts d ON d.id=f.district_id "
                   + (f"WHERE f.crime_head='{crime_head}' " if crime_head else "")
                   + "GROUP BY ps.id ORDER BY firs DESC LIMIT 20;")
            cols, rows = run_sql(sql)
            result = {"hotspots": rows, "summary": f"{len(rows)} hotspot stations"}

        elif action == "trends":
            crime_head = body.get("crime_head")
            group_by = body.get("group_by", "year")
            period = "substr(occurrence_date,1,7)" if group_by == "month" else "substr(occurrence_date,1,4)"
            sql = (f"SELECT {period} AS period,COUNT(*) AS count FROM firs "
                   + (f"WHERE crime_head='{crime_head}' " if crime_head else "")
                   + "GROUP BY period ORDER BY period LIMIT 200;")
            cols, rows = run_sql(sql)
            result = {"trend": rows, "summary": f"{sum(r['count'] for r in rows)} total FIRs"}

        elif action == "network":
            crime_head = body.get("crime_head")
            gang_name = body.get("gang_name")
            if gang_name:
                sql = (f"SELECT DISTINCT p.id,p.full_name,COUNT(*) AS cases "
                       f"FROM associations a JOIN persons p ON p.id IN (a.person_a_id,a.person_b_id) "
                       f"JOIN fir_persons fp ON fp.person_id=p.id "
                       f"WHERE a.gang_name='{gang_name}' AND fp.role='Accused' GROUP BY p.id LIMIT 50;")
            elif crime_head:
                sql = (f"SELECT DISTINCT p.full_name,a.gang_name,COUNT(*) AS cases "
                       f"FROM fir_persons fp JOIN firs f ON f.id=fp.fir_id "
                       f"JOIN persons p ON p.id=fp.person_id "
                       f"LEFT JOIN associations a ON a.person_a_id=fp.person_id AND a.gang_name IS NOT NULL "
                       f"WHERE f.crime_head='{crime_head}' AND fp.role='Accused' GROUP BY p.id ORDER BY cases DESC LIMIT 30;")
            else:
                sql = ("SELECT p.full_name,COUNT(*) AS cases FROM fir_persons fp JOIN persons p ON p.id=fp.person_id "
                       "WHERE fp.role='Accused' GROUP BY p.id ORDER BY cases DESC LIMIT 20;")
            cols, rows = run_sql(sql)
            result = {"nodes": rows, "summary": f"{len(rows)} nodes"}

        else:
            result = {"error": f"Unknown action: {action}"}

        basicio.write(json.dumps(result, default=str))

    except Exception as e:
        basicio.write(json.dumps({"error": str(e)}))
    finally:
        context.close()
