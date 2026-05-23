"""
api.py — Closira FastAPI REST Server
-----------------------------------
Wraps the same agent logic as main.py in a REST API.

Run:
  python -m uvicorn api:app --reload --port 8000

Docs:
  http://localhost:8000/docs
"""

import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from agent import ClosiraAgent
from utils import (
    classify_escalation_reason,
    should_count_faq_turn,
    collect_session_stats,
    save_session_log,
)

FAQ_TURNS_BEFORE_QUALIFY = 3
QUALIFY_QUESTIONS = 3

OPENING_GREETING = (
    "Hi there! I'm Aria, your virtual assistant for Bloom Aesthetics Clinic. 🌸 "
    "I'm here to help with questions about our services, pricing, and bookings. "
    "What can I help you with today?"
)

WHATSAPP_GREETING = "Hi! I'm Aria from Bloom Aesthetics Clinic 🌸 How can I help you today?"

app = FastAPI(
    title="Closira AI Agent API",
    description=(
        "AI-powered customer support REST API for Bloom Aesthetics Clinic.\n\n"
        "Workflow: POST /session/start -> POST /session/{id}/chat -> POST /session/{id}/end"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = ClosiraAgent()
sessions: dict[str, dict] = {}


class StartRequest(BaseModel):
    channel: str = "api"


class ChatRequest(BaseModel):
    message: str


class StartResponse(BaseModel):
    session_id: str
    response: str
    stage: str
    channel: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    stage: str
    escalated: bool
    escalate_reason: Optional[str]
    escalation_type: Optional[str]
    qualification_data: dict
    channel: str


class SummaryResponse(BaseModel):
    session_id: str
    summary: dict


class StateResponse(BaseModel):
    session_id: str
    stage: str
    faq_turns: int
    qualify_turns: int
    qualification_data: dict
    escalated: bool
    channel: str
    total_user_turns: int


def _new_session(channel: str = "api") -> dict:
    greeting = WHATSAPP_GREETING if channel == "whatsapp" else OPENING_GREETING
    return {
        "stage": "faq",
        "conversation_history": [{"role": "assistant", "content": greeting}],
        "qualification_data": {},
        "faq_turns": 0,
        "qualify_turns": 0,
        "session_log": [],
        "escalated": False,
        "channel": channel,
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
        if should_count_faq_turn(user_input):
            session["faq_turns"] += 1
        if session["faq_turns"] >= FAQ_TURNS_BEFORE_QUALIFY:
            session["stage"] = "qualify"
    elif session["stage"] == "qualify":
        if any(session["qualification_data"].get(key) for key in ("treatment_interest", "prior_experience", "booking_timeframe")):
            session["qualify_turns"] += 1
        if session["qualify_turns"] >= QUALIFY_QUESTIONS:
            session["stage"] = "done"


@app.get("/", tags=["Info"])
def root():
    return {
        "service": "Closira AI Agent API",
        "version": "1.0.0",
        "client": agent.sop.get("business_name"),
        "model": agent.model,
        "docs": "/docs",
    }


@app.get("/health", tags=["Info"])
def health():
    return {
        "status": "ok",
        "model": agent.model,
        "sop_loaded": agent.sop.get("business_name"),
        "active_sessions": len(sessions),
    }


@app.get("/stats", tags=["Info"])
def stats():
    return collect_session_stats()


@app.get("/sessions", tags=["Session"])
def list_sessions():
    return {"active_sessions": len(sessions), "session_ids": list(sessions.keys())}


@app.post("/session/start", response_model=StartResponse, tags=["Session"])
def start_session(request: StartRequest = StartRequest()):
    channel = request.channel if request.channel in {"api", "whatsapp"} else "api"
    session_id = str(uuid.uuid4())
    sessions[session_id] = _new_session(channel)
    greeting = _format_for_channel(WHATSAPP_GREETING if channel == "whatsapp" else OPENING_GREETING, channel)
    return StartResponse(session_id=session_id, response=greeting, stage="faq", channel=channel)


@app.post("/session/{session_id}/chat", response_model=ChatResponse, tags=["Session"])
def chat(session_id: str, request: ChatRequest):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found or already ended.")

    session = sessions[session_id]
    if session["escalated"]:
        raise HTTPException(400, "Session already escalated. Please start a new session.")

    channel = session["channel"]
    user_input = request.message.strip()

    session["conversation_history"].append({"role": "user", "content": user_input})
    session["session_log"].append({"role": "user", "content": user_input, "stage": session["stage"]})

    result = agent.respond(session["conversation_history"], session["stage"], session["qualification_data"])
    bot_response = _format_for_channel(result.get("response", "I'm sorry, could you rephrase that?"), channel)

    if result.get("escalate"):
        reason = result.get("escalate_reason") or "Unspecified"
        etype = classify_escalation_reason(reason)
        session["escalated"] = True
        session["conversation_history"].append({"role": "assistant", "content": bot_response})
        session["session_log"].append({
            "role": "assistant",
            "content": bot_response,
            "stage": session["stage"],
            "escalated": True,
            "escalate_reason": reason,
        })
        return ChatResponse(
            session_id=session_id,
            response=bot_response,
            stage=session["stage"],
            escalated=True,
            escalate_reason=reason,
            escalation_type=etype,
            qualification_data=session["qualification_data"],
            channel=channel,
        )

    session["conversation_history"].append({"role": "assistant", "content": bot_response})
    session["session_log"].append({"role": "assistant", "content": bot_response, "stage": session["stage"]})

    for key, value in (result.get("qualification_data") or {}).items():
        if value and value not in ("Not specified", "Unknown", ""):
            session["qualification_data"][key] = value

    _advance_stage(session, user_input)

    return ChatResponse(
        session_id=session_id,
        response=bot_response,
        stage=session["stage"],
        escalated=False,
        escalate_reason=None,
        escalation_type=None,
        qualification_data=session["qualification_data"],
        channel=channel,
    )


@app.get("/session/{session_id}/state", response_model=StateResponse, tags=["Session"])
def session_state(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found.")

    session = sessions[session_id]
    return StateResponse(
        session_id=session_id,
        stage=session["stage"],
        faq_turns=session["faq_turns"],
        qualify_turns=session["qualify_turns"],
        qualification_data=session["qualification_data"],
        escalated=session["escalated"],
        channel=session["channel"],
        total_user_turns=len([m for m in session["session_log"] if m.get("role") == "user"]),
    )


@app.post("/session/{session_id}/end", response_model=SummaryResponse, tags=["Session"])
def end_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found.")

    session = sessions.pop(session_id)
    summary = agent.generate_summary(
        session["conversation_history"],
        session["qualification_data"],
        escalated=session["escalated"],
    )
    save_session_log(session["session_log"], summary, escalated=session["escalated"])
    return SummaryResponse(session_id=session_id, summary=summary)
