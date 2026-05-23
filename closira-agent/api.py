"""
api.py — Closira FastAPI REST Server
-------------------------------------
Wraps the same agent logic as main.py in a REST API.
Supports multiple concurrent sessions via in-memory session store.

Run:
  uvicorn api:app --reload --port 8000

Docs (auto-generated):
  http://localhost:8000/docs
"""
import uuid
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import ClosiraAgent
from utils import (
    save_session_log, read_session_stats,
    classify_escalation, is_substantive,
)

# ── Constants ─────────────────────────────────────────────────────────────────
FAQ_TURNS_BEFORE_QUALIFY = 3
QUALIFY_QUESTIONS        = 3

OPENING_GREETING = (
    "Hi there! I'm Aria, your virtual assistant for Bloom Aesthetics Clinic. 🌸 "
    "I'm here to help with questions about our services, pricing, and bookings. "
    "What can I help you with today?"
)

WHATSAPP_GREETING = (
    "Hi! I'm Aria from Bloom Aesthetics Clinic 🌸 How can I help you today?"
)

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Closira AI Agent API",
    description=(
        "AI-powered customer support REST API for Bloom Aesthetics Clinic.\n\n"
        "**Workflow:** POST /session/start → POST /session/{id}/chat (repeat) → POST /session/{id}/end\n\n"
        "Supports `api` and `whatsapp` channel modes."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single shared agent instance (thread-safe for reads)
agent = ClosiraAgent()

# In-memory session store  { session_id: session_dict }
sessions: dict = {}


# ── Pydantic models ───────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    channel: str = "api"   # "api" | "whatsapp"

class StartResponse(BaseModel):
    session_id: str
    response: str
    stage: str
    channel: str

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    session_id:        str
    response:          str
    stage:             str
    escalated:         bool
    escalate_reason:   Optional[str]
    escalation_type:   Optional[str]
    qualification_data: dict
    channel:           str

class SummaryResponse(BaseModel):
    session_id: str
    summary:    dict

class StateResponse(BaseModel):
    session_id:        str
    stage:             str
    faq_turns:         int
    qualify_turns:     int
    qualification_data: dict
    escalated:         bool
    channel:           str
    total_user_turns:  int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _new_session(channel: str = "api") -> dict:
    greeting = WHATSAPP_GREETING if channel == "whatsapp" else OPENING_GREETING
    return {
        "stage":                "faq",
        "conversation_history": [{"role": "assistant", "content": greeting}],
        "qualification_data":   {},
        "faq_turns":            0,
        "qualify_turns":        0,
        "session_log":          [],
        "escalated":            False,
        "channel":              channel,
    }

def _format_for_channel(text: str, channel: str) -> str:
    if channel == "whatsapp":
        for md in ["**", "__", "~~", "`"]:
            text = text.replace(md, "")
        if len(text) > 1000:
            text = text[:997] + "…"
    return text

def _advance_stage(session: dict, user_input: str):
    if session["stage"] == "faq":
        if is_substantive(user_input):
            session["faq_turns"] += 1
        if session["faq_turns"] >= FAQ_TURNS_BEFORE_QUALIFY:
            session["stage"] = "qualify"

    elif session["stage"] == "qualify":
        session["qualify_turns"] += 1
        if session["qualify_turns"] >= QUALIFY_QUESTIONS:
            session["stage"] = "done"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    """API info and available endpoints."""
    return {
        "service": "Closira AI Agent API",
        "version": "2.0.0",
        "client":  agent.sop.get("business_name"),
        "model":   agent.model,
        "docs":    "/docs",
        "endpoints": {
            "start_session": "POST /session/start",
            "chat":          "POST /session/{session_id}/chat",
            "end_session":   "POST /session/{session_id}/end",
            "session_state": "GET  /session/{session_id}/state",
            "active":        "GET  /sessions",
            "stats":         "GET  /stats",
            "health":        "GET  /health",
        },
    }


@app.get("/health", tags=["Info"])
def health():
    """Service health check."""
    return {
        "status":          "ok",
        "model":           agent.model,
        "sop_loaded":      agent.sop.get("business_name"),
        "active_sessions": len(sessions),
    }


@app.post("/session/start", response_model=StartResponse, tags=["Session"])
def start_session(request: StartRequest = StartRequest()):
    """
    Start a new customer session.

    - **channel**: `api` (default) or `whatsapp` (strips markdown, 1000 char limit)

    Returns a `session_id` to use in subsequent calls.
    """
    session_id = str(uuid.uuid4())
    sessions[session_id] = _new_session(request.channel)
    channel  = request.channel
    greeting = _format_for_channel(
        WHATSAPP_GREETING if channel == "whatsapp" else OPENING_GREETING,
        channel
    )
    return StartResponse(
        session_id=session_id,
        response=greeting,
        stage="faq",
        channel=channel,
    )


@app.post("/session/{session_id}/chat", response_model=ChatResponse, tags=["Session"])
def chat(session_id: str, request: ChatRequest):
    """
    Send a customer message and receive Aria's response.

    - Automatically handles stage transitions (FAQ → Qualify → Done)
    - Returns `escalated: true` when handoff is triggered
    - Escalated sessions cannot receive further messages — start a new session
    """
    if session_id not in sessions:
        raise HTTPException(404, "Session not found or already ended.")

    session = sessions[session_id]

    if session["escalated"]:
        raise HTTPException(400, "Session already escalated. Please start a new session.")

    channel    = session["channel"]
    user_input = request.message.strip()

    session["conversation_history"].append({"role": "user", "content": user_input})
    session["session_log"].append({"role": "user", "content": user_input, "stage": session["stage"]})

    result       = agent.respond(session["conversation_history"], session["stage"], session["qualification_data"])
    bot_response = _format_for_channel(
        result.get("response", "I'm sorry, could you rephrase that?"), channel
    )

    # Escalation
    if result.get("escalate"):
        reason = result.get("escalate_reason") or "Unspecified"
        etype  = classify_escalation(reason)
        session["escalated"] = True
        session["conversation_history"].append({"role": "assistant", "content": bot_response})
        session["session_log"].append({
            "role": "assistant", "content": bot_response,
            "stage": session["stage"], "escalated": True,
            "escalate_reason": reason,
        })
        return ChatResponse(
            session_id=session_id, response=bot_response,
            stage=session["stage"], escalated=True,
            escalate_reason=reason, escalation_type=etype,
            qualification_data=session["qualification_data"], channel=channel,
        )

    # Normal
    session["conversation_history"].append({"role": "assistant", "content": bot_response})
    session["session_log"].append({"role": "assistant", "content": bot_response, "stage": session["stage"]})

    for k, v in (result.get("qualification_data") or {}).items():
        if v and v not in ("Not specified", "Unknown", ""):
            session["qualification_data"][k] = v

    _advance_stage(session, user_input)

    return ChatResponse(
        session_id=session_id, response=bot_response,
        stage=session["stage"], escalated=False,
        escalate_reason=None, escalation_type=None,
        qualification_data=session["qualification_data"], channel=channel,
    )


@app.post("/session/{session_id}/end", response_model=SummaryResponse, tags=["Session"])
def end_session(session_id: str):
    """
    End a session, generate a structured summary, and persist logs.

    Removes the session from memory after summarising.
    """
    if session_id not in sessions:
        raise HTTPException(404, "Session not found.")

    session = sessions[session_id]
    summary = agent.generate_summary(
        session["conversation_history"],
        session["qualification_data"],
        escalated=session["escalated"],
    )
    save_session_log(session["session_log"], summary, escalated=session["escalated"])
    del sessions[session_id]

    return SummaryResponse(session_id=session_id, summary=summary)


@app.get("/session/{session_id}/state", response_model=StateResponse, tags=["Session"])
def get_state(session_id: str):
    """Inspect the current state of an active session (for debugging / dashboards)."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found.")
    s = sessions[session_id]
    return StateResponse(
        session_id=session_id,
        stage=s["stage"],
        faq_turns=s["faq_turns"],
        qualify_turns=s["qualify_turns"],
        qualification_data=s["qualification_data"],
        escalated=s["escalated"],
        channel=s["channel"],
        total_user_turns=len([m for m in s["conversation_history"] if m["role"] == "user"]),
    )


@app.get("/sessions", tags=["Admin"])
def list_active_sessions():
    """List all currently active (in-memory) sessions."""
    return {
        "count": len(sessions),
        "sessions": [
            {
                "session_id": sid,
                "stage":      s["stage"],
                "escalated":  s["escalated"],
                "channel":    s["channel"],
                "turns":      len([m for m in s["conversation_history"] if m["role"] == "user"]),
            }
            for sid, s in sessions.items()
        ],
    }


@app.get("/stats", tags=["Admin"])
def get_stats():
    """
    Aggregated stats across all persisted sessions (reads from logs/ directory).

    Returns: total sessions, escalation rate, avg turns, escalation breakdown, top SOP gaps.
    """
    return read_session_stats()
