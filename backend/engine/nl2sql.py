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
_SYSTEM_PROMPT = """SQLite query generator for KSP crime database. Rules:
1. Return ONLY a SQL SELECT. No explanation, no markdown fences.
2. Always add LIMIT (max 200). Single quotes for strings.
3. For crime type queries use crime_head column (spans IPC+BNS automatically).
4. Cannot answer with SQL? Return: CANNOT_ANSWER

Tables:
firs(id,fir_number,police_station_id,district_id,reported_date,occurrence_date,crime_head,status,investigating_officer,latitude,longitude)
districts(id,name,region,population)
police_stations(id,name,district_id)
persons(id,full_name,gender,age,income_band,is_repeat_offender,district_id)
fir_persons(fir_id,person_id,role) -- role: Accused/Victim/Complainant/Witness
arrests(person_id,fir_id,arrest_date,bail_status) -- bail_status: In Custody/On Bail/Absconding
associations(person_a_id,person_b_id,association_type,gang_name,strength)
fir_sections(fir_id,legal_section_id)
legal_sections(id,act,section_code,crime_head)
properties(fir_id,type,value_inr,status)
transactions(from_account_id,to_account_id,amount_inr,txn_date,is_flagged)
financial_accounts(id,person_id,bank)
investigation_events(fir_id,event_date,event_type,note)

Examples:
Q:theft count -> SELECT COUNT(*) AS n FROM firs WHERE crime_head='Theft';
Q:top districts -> SELECT d.name,COUNT(*) c FROM firs f JOIN districts d ON d.id=f.district_id GROUP BY d.id ORDER BY c DESC LIMIT 10;
Q:repeat offenders -> SELECT p.full_name,COUNT(*) c FROM fir_persons fp JOIN persons p ON p.id=fp.person_id WHERE fp.role='Accused' GROUP BY p.id ORDER BY c DESC LIMIT 10;
Q:FIR trends by year -> SELECT substr(occurrence_date,1,4) yr,COUNT(*) n FROM firs GROUP BY yr ORDER BY yr;
Q:bail status -> SELECT bail_status,COUNT(*) n FROM arrests GROUP BY bail_status;"""

_FEW_SHOT = ""  # examples already in system prompt to save tokens


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

    # Build user prompt with optional conversation context for follow-ups.
    context_block = f"\nPrevious context:\n{conversation_context}\n" if conversation_context else ""
    user_prompt = f"{_FEW_SHOT}{context_block}\nQ: {question}\nA:"

    raw = provider.complete(
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.0,
        max_tokens=2048,
    )

    if not raw or raw.strip() == "CANNOT_ANSWER":
        return NL2SQLResult(
            question=question,
            error="This question cannot be answered with a database query.",
            raw_llm=raw,
        )

    sql = _extract_sql(raw)
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
