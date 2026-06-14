"""
Sahayak — FastAPI backend.
Entry point for Catalyst AppSail deployment.

Endpoints:
  POST /chat              — NL question → SQL → grounded answer + evidence trail
  GET  /health            — readiness check
  GET  /schema            — returns table list
  GET  /tools/network     — criminal network graph
  GET  /tools/hotspots    — crime hotspot clusters
  GET  /tools/trends      — FIR time-series trends
  GET  /tools/case/{id}   — AI-generated case summary
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid

from ..engine import config, llm, db
from ..engine.conversation import Session
from ..engine import audit
from .rbac import get_current_user
from ..tools import network as net_tool
from ..tools import hotspots as hs_tool
from ..tools import case_summary as cs_tool

config.load_dotenv()

app = FastAPI(
    title="Sahayak — KSP Crime Intelligence API",
    description="Conversational AI over the Karnataka State Police crime database.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tightened to Slate domain in Phase 6
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- in-memory session store (replaced with Catalyst Cache in Phase 6)
_sessions: dict[str, Session] = {}

# --- shared LLM provider (singleton, re-uses OAuth token)
_provider = llm.get_provider()


# --------------------------------------------------------------------------- models

class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    language: Optional[str] = "en"   # "en" | "kn" (Kannada handled in Phase 6 via Zia)


class EvidenceItem(BaseModel):
    column: str
    values: List


class ChatResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    sql: Optional[str] = None
    columns: List[str] = []
    rows: List[dict] = []
    row_count: int = 0
    error: Optional[str] = None


# --------------------------------------------------------------------------- helpers

_INFO_PREFIXES = (
    "I am Sahayak", "This question", "Hello.", "Goodbye",
    "I answer questions", "I can query",
)

def _build_answer(result) -> str:
    if result.error:
        msg = result.error
        if any(msg.startswith(p) for p in _INFO_PREFIXES):
            return msg          # informational — render as-is, no "Unable to answer:"
        return f"Unable to answer: {msg}"
    if result.row_count == 0:
        return "No records found matching your query."
    if result.row_count == 1 and len(result.columns) == 1:
        val = result.rows[0][result.columns[0]]
        return f"**{val}**"
    return (
        f"**{result.row_count}** record(s) found. "
        f"Every figure is sourced from live crime records — "
        f"expand the evidence trail to see the query and source rows."
    )


# --------------------------------------------------------------------------- routes

@app.get("/health")
def health():
    return {"status": "ok", "db": config.DB_PATH, "llm": config.LLM_PROVIDER}


@app.get("/schema")
def schema():
    return {"tables": db.table_names()}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user=Depends(get_current_user)):
    # Get or create session
    sid = req.session_id or str(uuid.uuid4())
    if sid not in _sessions:
        _sessions[sid] = Session(user_id=user["id"], role=user["role"])
    session = _sessions[sid]

    result = session.ask(req.question, provider=_provider)

    # Write to audit log (non-blocking)
    audit.log(
        user_id=user["id"],
        nl_question=req.question,
        generated_query=result.sql,
        row_count=result.row_count,
        role=user["role"],
    )

    answer = _build_answer(result)
    # Informational replies (greetings, meta-questions) should not set error=True
    # on the response — that causes the frontend to render them as error messages.
    _INFO_STARTS = ("I am Sahayak", "This question", "Hello.", "Goodbye",
                    "I answer questions", "I can query")
    is_info_reply = result.error and not result.sql and result.row_count == 0 and any(
        result.error.startswith(s) for s in _INFO_STARTS
    )
    return ChatResponse(
        session_id=sid,
        question=req.question,
        answer=answer,
        sql=result.sql,
        columns=result.columns,
        rows=result.rows[:50],
        row_count=result.row_count,
        error=None if is_info_reply else result.error,
    )


# --------------------------------------------------------------------------- differentiator tools

@app.get("/tools/network")
def network(
    person_id: Optional[int] = Query(None),
    gang_name: Optional[str] = Query(None),
    crime_head: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    return net_tool.get_network(person_id=person_id, gang_name=gang_name, crime_head=crime_head)


@app.get("/tools/hotspots")
def hotspots(
    crime_head: Optional[str] = Query(None),
    district_id: Optional[int] = Query(None),
    user=Depends(get_current_user),
):
    return hs_tool.get_hotspots(crime_head=crime_head, district_id=district_id)


@app.get("/tools/trends")
def trends(
    crime_head: Optional[str] = Query(None),
    district_id: Optional[int] = Query(None),
    group_by: str = Query("month"),
    user=Depends(get_current_user),
):
    return hs_tool.get_trends(crime_head=crime_head, district_id=district_id, group_by=group_by)


@app.get("/tools/case/{fir_id}")
def case_summary(fir_id: int, user=Depends(get_current_user)):
    instruct = llm.get_provider(model="instruct")
    return cs_tool.summarize(fir_id=fir_id, provider=instruct)
