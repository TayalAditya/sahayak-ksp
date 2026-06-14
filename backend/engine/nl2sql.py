"""
NL→SQL pipeline: the core of Sahayak.

Flow per question:
  1. Build a schema-aware system prompt (table list + key columns)
  2. Send to LLM (Qwen Coder) with few-shot examples
  3. Extract the SQL from the response
  4. Validate (read-only guard) + execute on the real DB
  5. Return answer + evidence trail (query + source rows)

The LLM never sees raw data — it only generates a query. The answer is always computed
on real rows, never invented. This is what makes every response auditable.
"""

import re

from . import config, db, llm

# --------------------------------------------------------------------------- schema summary
# Kept deliberately compact — max_tokens in Catalyst QuickML = TOTAL context budget
# (input + output), so every token saved here is a token available for the SQL output.
_SYSTEM_PROMPT = """You are a SQLite query engine. OUTPUT ONLY SQL — no words, no explanation, no markdown.

RULE: Your ENTIRE response must be a single SQL SELECT statement ending with semicolon.
If the question is not about crime data, output exactly: CANNOT_ANSWER
Never output greetings, explanations, or any text that is not SQL.

Schema (KSP crime database):
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

Examples (ONLY output the SQL, nothing else):
Q:theft count
SELECT COUNT(*) AS theft_cases FROM firs WHERE crime_head='Theft' LIMIT 200;
Q:top 5 districts by FIR count
SELECT d.name AS district,COUNT(*) AS firs FROM firs f JOIN districts d ON d.id=f.district_id GROUP BY d.id ORDER BY firs DESC LIMIT 5;
Q:repeat offenders
SELECT p.full_name,COUNT(*) AS cases FROM fir_persons fp JOIN persons p ON p.id=fp.person_id WHERE fp.role='Accused' GROUP BY p.id ORDER BY cases DESC LIMIT 10;
Q:FIR trend by year
SELECT substr(occurrence_date,1,4) AS year,COUNT(*) AS firs FROM firs GROUP BY year ORDER BY year LIMIT 200;
Q:bail status breakdown
SELECT bail_status,COUNT(*) AS n FROM arrests GROUP BY bail_status ORDER BY n DESC LIMIT 200;
Q:IPC vs BNS
SELECT ls.act,COUNT(*) AS firs FROM fir_sections fs JOIN legal_sections ls ON ls.id=fs.legal_section_id GROUP BY ls.act LIMIT 200;"""

# Greetings / farewells — short friendly response
_GREETING_RE = re.compile(
    r"^\s*(hi+|hello+|hey+|namaste|good\s*(morning|evening|afternoon|day)|"
    r"bye+|goodbye|see\s*you|ciao|later)\s*[!?.]*\s*$",
    re.IGNORECASE
)
_GREETING_REPLY = (
    "Hello. I can query the KSP crime database — ask about FIRs, crime trends, "
    "accused persons, districts, or network links. "
    "Try: \"How many robbery cases this year?\" or \"Show repeat offenders.\""
)
_FAREWELL_RE = re.compile(r"^\s*(bye+|goodbye|see\s*you|ciao|later|quit|exit)\s*[!?.]*\s*$", re.IGNORECASE)
_FAREWELL_REPLY = "Goodbye. Stay safe."

# Meta / help questions — explain capabilities
_META_RE = re.compile(
    r"^\s*(what\s+can\s+(you|this)|what\s+do\s+you|"
    r"(who|what)\s+are\s+you|help(\s+me)?|"
    r"what\s+is\s+(this|sahayak)|how\s+do\s+(i|you)|"
    r"(can|will)\s+you\s+(show|tell|give|help|answer|do)|"
    r"what\s+(can|should)\s+i|why\s+not|why\s+can.t|"
    r"ok+|okay|sure|yes|no|thanks?|thank\s+you|test|ping|"
    r"[\?!.\s]+)\s*$",
    re.IGNORECASE
)
_META_REPLY = (
    "I answer questions about the KSP crime database. Ask me things like:\n"
    "— \"How many theft cases in Bengaluru Urban?\"\n"
    "— \"Which district has the most FIRs?\"\n"
    "— \"Show top 5 repeat offenders\"\n"
    "— \"What is the bail status breakdown?\"\n"
    "— \"FIR trend by year\"\n"
    "— \"Which gangs are linked to robbery cases?\""
)

# Short single-word queries that need clarification
_SHORT_QUERY_MAP = {
    "fir": "SELECT f.fir_number, f.crime_head, f.occurrence_date, f.status, d.name AS district FROM firs f JOIN districts d ON d.id=f.district_id ORDER BY f.reported_date DESC LIMIT 20;",
    "firs": "SELECT f.fir_number, f.crime_head, f.occurrence_date, f.status, d.name AS district FROM firs f JOIN districts d ON d.id=f.district_id ORDER BY f.reported_date DESC LIMIT 20;",
    "theft": "SELECT COUNT(*) AS theft_cases FROM firs WHERE crime_head='Theft' LIMIT 200;",
    "robbery": "SELECT COUNT(*) AS robbery_cases FROM firs WHERE crime_head='Robbery' LIMIT 200;",
    "murder": "SELECT COUNT(*) AS murder_cases FROM firs WHERE crime_head='Murder' LIMIT 200;",
    "districts": "SELECT d.name, COUNT(*) AS firs FROM firs f JOIN districts d ON d.id=f.district_id GROUP BY d.id ORDER BY firs DESC LIMIT 16;",
    "accused": "SELECT p.full_name, COUNT(*) AS cases FROM fir_persons fp JOIN persons p ON p.id=fp.person_id WHERE fp.role='Accused' GROUP BY p.id ORDER BY cases DESC LIMIT 20;",
    "arrests": "SELECT bail_status, COUNT(*) AS n FROM arrests GROUP BY bail_status ORDER BY n DESC LIMIT 200;",
    "gangs": "SELECT gang_name, COUNT(DISTINCT person_a_id) AS members FROM associations WHERE gang_name IS NOT NULL GROUP BY gang_name ORDER BY members DESC LIMIT 15;",
    "trends": "SELECT substr(occurrence_date,1,4) AS year, COUNT(*) AS firs FROM firs GROUP BY year ORDER BY year LIMIT 200;",
    "data": "SELECT f.fir_number, f.crime_head, f.occurrence_date, f.status, d.name AS district FROM firs f JOIN districts d ON d.id=f.district_id ORDER BY f.reported_date DESC LIMIT 50;",
}

_FEW_SHOT = ""


def _extract_sql(text):
    """Pull the first SQL SELECT out of a model response (handles markdown fences)."""
    if not text:
        return None
    text = text.strip()
    # Strip ```sql ... ``` fences
    fence = re.search(r"```(?:sql)?\s*([\s\S]+?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    # Take up to the first semicolon (inclusive)
    match = re.search(r"((?:WITH|SELECT)\b[\s\S]+?;)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # No semicolon — take the whole thing if it starts with SELECT/WITH
    if re.match(r"^\s*(SELECT|WITH)\b", text, re.IGNORECASE):
        return text
    return None


# --------------------------------------------------------------------------- public API

class NL2SQLResult:
    __slots__ = ("question", "sql", "columns", "rows", "row_count", "error", "raw_llm")

    def __init__(self, question, sql=None, columns=None, rows=None,
                 row_count=0, error=None, raw_llm=None):
        self.question = question
        self.sql = sql
        self.columns = columns or []
        self.rows = rows or []
        self.row_count = row_count
        self.error = error
        self.raw_llm = raw_llm

    def to_dict(self):
        return {
            "question": self.question,
            "sql": self.sql,
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "error": self.error,
        }


def ask(question, provider=None, conversation_context=""):
    """
    Turn a natural-language officer question into a verified, grounded answer.

    Returns an NL2SQLResult with:
      .sql        — the exact query that was run (evidence trail)
      .rows       — the source rows (grounding)
      .row_count  — how many rows
      .error      — non-None if something went wrong
    """
    provider = provider or llm.get_provider()
    q = question.strip()

    # ── Greetings / farewells ──────────────────────────────────────────────────
    if _FAREWELL_RE.match(q):
        return NL2SQLResult(question=question, error=_FAREWELL_REPLY, raw_llm="[intercepted]")
    if _GREETING_RE.match(q):
        return NL2SQLResult(question=question, error=_GREETING_REPLY, raw_llm="[intercepted]")

    # ── Meta / help / conversational ──────────────────────────────────────────
    if _META_RE.match(q):
        return NL2SQLResult(question=question, error=_META_REPLY, raw_llm="[intercepted]")

    # ── Single-word shortcut queries ──────────────────────────────────────────
    key = q.lower().rstrip("s?!")
    if q.lower() in _SHORT_QUERY_MAP or key in _SHORT_QUERY_MAP:
        prebuilt_sql = _SHORT_QUERY_MAP.get(q.lower()) or _SHORT_QUERY_MAP.get(key)
        try:
            res = db.run_query(prebuilt_sql)
            return NL2SQLResult(
                question=question,
                sql=res["sql"], columns=res["columns"],
                rows=res["rows"], row_count=res["row_count"],
            )
        except Exception:
            pass  # fall through to LLM

    # Build user prompt — lead with the question to anchor the model's first token on SQL.
    context_block = f"Previous context:\n{conversation_context}\n\n" if conversation_context else ""
    user_prompt = f"{context_block}Q:{question}\n"

    def _call(temp=0.0):
        return provider.complete(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=temp,
            max_tokens=2048,
        )

    raw = _call(0.0)

    if not raw or raw.strip().upper() == "CANNOT_ANSWER":
        return NL2SQLResult(
            question=question,
            error=_META_REPLY,
            raw_llm=raw,
        )

    sql = _extract_sql(raw)

    # If model returned chat text instead of SQL, retry once with a blunter prompt.
    if not sql:
        retry_prompt = (
            f"{context_block}"
            f"Write a SQLite SELECT query for: {question}\n"
            f"Output ONLY the SQL statement, starting with SELECT.\n"
        )
        raw2 = provider.complete(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=retry_prompt,
            temperature=0.0,
            max_tokens=2048,
        )
        sql = _extract_sql(raw2 or "")
        if raw2:
            raw = raw2

    if not sql:
        return NL2SQLResult(
            question=question,
            error=f"Model did not return a valid SQL query. Raw: {raw[:200]}",
            raw_llm=raw,
        )

    try:
        result = db.run_query(sql)
    except db.UnsafeQueryError as e:
        return NL2SQLResult(question=question, sql=sql, error=f"Safety check: {e}", raw_llm=raw)
    except Exception as e:
        return NL2SQLResult(question=question, sql=sql, error=f"Execution error: {e}", raw_llm=raw)

    return NL2SQLResult(
        question=question,
        sql=result["sql"],
        columns=result["columns"],
        rows=result["rows"],
        row_count=result["row_count"],
        raw_llm=raw,
    )
