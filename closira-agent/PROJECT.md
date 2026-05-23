# Closira AI Agent — Project Documentation
### Client: Bloom Aesthetics Clinic · Version 2.0.0

> A Python-based AI customer support workflow that handles inbound customer conversations
> across four stages: FAQ answering, lead qualification, escalation detection, and session
> summarisation. Built for the Closira AI Engineering Internship assignment.

---

## Table of Contents

1. [Stack](#1-stack)
2. [Folder Structure](#2-folder-structure)
3. [Feature Matrix](#3-feature-matrix)
4. [Stage Flow](#4-stage-flow)
5. [How to Run](#5-how-to-run)
6. [REST API Reference](#6-rest-api-reference)
7. [SOP Format](#7-sop-format)
8. [Escalation System](#8-escalation-system)
9. [Logging](#9-logging)
10. [Configuration Reference](#10-configuration-reference)
11. [Design Decisions](#11-design-decisions)
12. [Known Limitations](#12-known-limitations)

---

## 1. Stack

| Layer            | Technology                        | Why                                                 |
|------------------|-----------------------------------|-----------------------------------------------------|
| Language         | Python 3.10+                      | Async-capable, clean, widely supported              |
| LLM              | LLaMA 3.3 70B Versatile           | Best quality model available on Groq                |
| LLM API          | Groq API                          | Ultra-low latency inference, free tier available     |
| API framework    | FastAPI + Uvicorn                 | Auto-docs via /docs, async-ready, production-grade  |
| CLI              | argparse + ANSI colours           | No extra deps, works in any terminal                |
| Config           | python-dotenv                     | `.env` file keeps API keys out of code              |
| Data format      | JSON (SOP + logs)                 | Human-readable, easily editable                     |
| Session storage  | In-memory dict (CLI + API)        | Sufficient for single-session scope                 |
| Log persistence  | JSON + TXT files in `logs/`       | Machine-readable + human-readable side by side      |

**Full dependency list (`requirements.txt`):**
```
groq>=0.9.0
python-dotenv>=1.0.0
fastapi>=0.110.0
uvicorn>=0.27.0
```

---

## 2. Folder Structure

```
closira-agent/
│
├── main.py                  ← CLI entry point and state machine
│                              Flags: --debug, --sop <file>, --channel <cli|whatsapp>
│
├── api.py                   ← FastAPI REST server (NEW in v2)
│                              Run: uvicorn api:app --reload --port 8000
│
├── stats.py                 ← Admin stats dashboard CLI tool (NEW in v2)
│                              Run: python stats.py
│
├── agent.py                 ← Groq API wrapper
│                              - Stage-specific system prompts
│                              - JSON response parsing + regex fallback
│                              - Retry logic with exponential back-off (2 retries)
│                              - Multi-SOP support via sop_path param
│
├── utils.py                 ← Shared utilities (CLI + API)
│                              - ANSI colour printing helpers
│                              - Escalation classification + colour coding
│                              - is_substantive() for smart FAQ turn counting
│                              - Dual logging (JSON + TXT)
│                              - read_session_stats() for API /stats endpoint
│
├── sop.json                 ← Bloom Aesthetics Clinic SOP (default)
├── sop_template.json        ← Template for multi-clinic custom SOPs (NEW in v2)
│
├── prompt_design.md         ← Full prompt design document (required deliverable)
├── PROJECT.md               ← This file — master project documentation
├── CHANGELOG.md             ← Version history
├── README.md                ← Setup + quick-start
├── requirements.txt
├── .env.example             ← Copy to .env and add GROQ_API_KEY
│
├── logs/                    ← Auto-created on first session
│   ├── session_TIMESTAMP.json          ← Machine-readable log
│   ├── session_TIMESTAMP.txt           ← Human-readable log
│   ├── session_TIMESTAMP_ESCALATED.json
│   └── session_TIMESTAMP_ESCALATED.txt
│
└── test_transcripts/
    ├── 01_in_sop_question.md
    ├── 02_out_of_scope.md
    ├── 03_escalation_trigger.md
    ├── 04_lead_qualification.md
    └── 05_conversation_summary.md
```

---

## 3. Feature Matrix

### Core Features (v1)

| Feature                    | File(s)          | Status |
|----------------------------|------------------|--------|
| FAQ answering from SOP     | agent.py, main.py | ✅ Done |
| Lead qualification (3 Qs)  | agent.py, main.py | ✅ Done |
| Escalation detection       | agent.py, main.py | ✅ Done |
| Session summary on exit    | agent.py, main.py | ✅ Done |
| Session log (JSON)         | utils.py          | ✅ Done |
| Basic CLI                  | main.py           | ✅ Done |

### Hardening (v2 — Bug Fixes + Improvements)

| Feature                         | File(s)   | Status |
|---------------------------------|-----------|--------|
| JSON leak fix (regex extraction) | agent.py | ✅ Done |
| Exponential back-off retry (×2)  | agent.py | ✅ Done |
| Smart FAQ turns (skip small talk) | utils.py, main.py | ✅ Done |
| Booking conflict pre-check       | main.py  | ✅ Done |
| `--debug` mode                   | main.py  | ✅ Done |
| Colour-coded escalation by type  | utils.py | ✅ Done |
| Dual logging (JSON + TXT)        | utils.py | ✅ Done |
| Session stats in debug mode      | utils.py, main.py | ✅ Done |

### New Features (v2 — Tier 1 + Tier 2)

| Feature                          | File(s)          | Status |
|----------------------------------|------------------|--------|
| FastAPI REST server              | api.py           | ✅ Done |
| WhatsApp channel mode            | main.py, api.py  | ✅ Done |
| Admin stats dashboard CLI        | stats.py         | ✅ Done |
| Multi-clinic SOP (`--sop` flag)  | main.py, agent.py | ✅ Done |
| Auto-generated API docs (`/docs`) | api.py (FastAPI) | ✅ Done |
| `/stats` aggregation endpoint    | api.py, utils.py | ✅ Done |

---

## 4. Stage Flow

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    FAQ      │  Answers from SOP only
                    │ (3 turns)   │  Counts only substantive questions
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │     LEAD QUALIFY        │  3 questions, one at a time
              │  · Treatment interest   │  - Which treatment?
              │  · Prior experience     │  - First time?
              │  · Booking timeframe    │  - When to book?
              └────────────┬────────────┘
                           │
                    ┌──────▼──────┐
                    │    DONE     │  Details noted, prompts to exit
                    └──────┬──────┘
                           │
              user types 'bye'/'done'/'exit'
                           │
                    ┌──────▼──────┐
                    │   SUMMARY   │  Structured JSON summary + logs saved
                    └─────────────┘

       ⚠️  ESCALATION can interrupt ANY stage:
           complaint · medical · pricing · human request
           angry sentiment · >2 unanswered SOP questions
                           │
                    ┌──────▼──────┐
                    │  ESCALATE   │  Reason logged, summary generated,
                    │             │  human handoff message shown
                    └─────────────┘
```

**Stage transitions are deterministic (turn-count based), not AI-driven.**
This guarantees consistent, predictable behaviour across all sessions.

---

## 5. How to Run

### Setup (one-time)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API key
cp .env.example .env
# Edit .env and add: GROQ_API_KEY=your_key_here
# Get a free key at: https://console.groq.com
```

### CLI Mode

```bash
# Standard run
python main.py

# Debug mode — shows raw API responses, stage state, turn counts
python main.py --debug

# Custom SOP (multi-clinic support)
python main.py --sop sop_template.json

# WhatsApp channel mode — strips markdown, 1000 char limit
python main.py --channel whatsapp

# Combine flags
python main.py --debug --channel whatsapp --sop custom_sop.json
```

### REST API Mode

```bash
# Start the server
uvicorn api:app --reload --port 8000

# Auto-generated docs (interactive)
open http://localhost:8000/docs

# Quick test with curl:
curl -X POST http://localhost:8000/session/start \
  -H "Content-Type: application/json" \
  -d '{"channel": "api"}'

# Chat (replace SESSION_ID with value from start response)
curl -X POST http://localhost:8000/session/SESSION_ID/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are your Botox prices?"}'

# End session
curl -X POST http://localhost:8000/session/SESSION_ID/end
```

### Admin Stats Dashboard

```bash
# View aggregated stats across all logged sessions
python stats.py
```

---

## 6. REST API Reference

**Base URL:** `http://localhost:8000`

| Method | Endpoint                       | Description                                      |
|--------|--------------------------------|--------------------------------------------------|
| GET    | `/`                            | API info and endpoint list                       |
| GET    | `/health`                      | Health check — model, SOP, active session count  |
| POST   | `/session/start`               | Start a new session, returns `session_id`        |
| POST   | `/session/{id}/chat`           | Send message, get Aria's response                |
| POST   | `/session/{id}/end`            | End session, generate summary, save logs         |
| GET    | `/session/{id}/state`          | Inspect session state (stage, turns, qdata)      |
| GET    | `/sessions`                    | List all active in-memory sessions               |
| GET    | `/stats`                       | Aggregated stats from all saved log files        |

### POST `/session/start` — Request body

```json
{ "channel": "api" }
```
`channel` options: `"api"` (default) or `"whatsapp"` (strips markdown, 1000 char cap)

### POST `/session/{id}/chat` — Request body

```json
{ "message": "What are your Botox prices?" }
```

### POST `/session/{id}/chat` — Response

```json
{
  "session_id":         "uuid",
  "response":           "Our Botox treatments start from £200...",
  "stage":              "faq",
  "escalated":          false,
  "escalate_reason":    null,
  "escalation_type":    null,
  "qualification_data": {},
  "channel":            "api"
}
```

When `escalated: true`:
```json
{
  "escalated":        true,
  "escalate_reason":  "Customer complaint — dissatisfied with treatment result",
  "escalation_type":  "complaint"
}
```

### GET `/stats` — Response

```json
{
  "total_sessions":        12,
  "escalated_sessions":    3,
  "escalation_rate_pct":   25.0,
  "avg_turns_per_session": 6.2,
  "escalation_by_type": {
    "complaint":     2,
    "medical":       1
  },
  "top_sop_gaps": {
    "Is there parking nearby?": 4,
    "Do you offer payment plans?": 2
  }
}
```

---

## 7. SOP Format

The SOP is a JSON file loaded at startup. The default is `sop.json`.
To use a custom SOP: `python main.py --sop my_clinic.json`

**Required fields:**

```json
{
  "business_name": "Your Clinic Name",
  "hours":         "Monday to Saturday, 9am to 7pm",
  "last_appointment_slot": "6:45pm",
  "closed_days":   ["Sunday"],
  "services": {
    "service_key": "Description and price"
  },
  "booking":       "How customers book. Cancellation policy.",
  "website":       "yoursite.co.uk",
  "escalate_conditions": [
    "List of conditions that trigger human handoff"
  ]
}
```

Use `sop_template.json` as a starting point.

---

## 8. Escalation System

Escalation is **self-reported by the model** via a boolean field in its JSON output —
not detected by post-hoc text analysis. This is explicit, auditable, and reliable.

### Escalation Types + Colours

| Type           | Trigger keywords                          | Terminal colour |
|----------------|-------------------------------------------|-----------------|
| `medical`      | health, pregnant, allergy, pain, reaction | 🔴 Red          |
| `complaint`    | unhappy, dissatisfied, wrong, bad         | 🔴 Red          |
| `pricing`      | discount, cheaper, negotiate, deal        | 🟡 Yellow       |
| `human_request`| speak to, real person, human agent        | 🟣 Magenta      |
| `out_of_scope` | cannot answer, not in SOP, unanswered     | 🔵 Cyan         |
| `general`      | (catch-all)                               | ⚪ White        |

Classification lives in `utils.classify_escalation(reason: str) -> str`.

### Escalation Output (JSON)

```json
{
  "response":       "I'm so sorry to hear that...",
  "escalate":       true,
  "escalate_reason": "Customer complaint — dissatisfied with filler result, distressed sentiment detected",
  "qualification_data": {}
}
```

---

## 9. Logging

Every session saves two files to `logs/` on exit or escalation:

### JSON log (`session_TIMESTAMP.json`)

```json
{
  "timestamp":    "2025-01-15T14:32:11",
  "escalated":    false,
  "conversation": [
    { "role": "user",      "content": "...", "stage": "faq" },
    { "role": "assistant", "content": "...", "stage": "faq" }
  ],
  "summary": {
    "customer_intent":         "Book a Botox appointment next month",
    "key_details_collected":   { "treatment_interest": "Botox", ... },
    "sop_gaps":                [],
    "escalated":               false,
    "escalation_reason":       null,
    "recommended_next_action": "Follow up to confirm Botox booking for next month"
  }
}
```

### TXT log (`session_TIMESTAMP.txt`) — Human-readable

```
══════════════════════════════════════════════════════════
CLOSIRA SESSION LOG — 2025-01-15 14:32:11
Escalated: No
══════════════════════════════════════════════════════════

[faq] Customer : What are your Botox prices?
[faq] Aria     : Our Botox treatments start from £200...

[qualify] Customer : Botox please.
[qualify] Aria     : Great choice! Have you had Botox before...

──────────────────────────────────────────────────────────
SUMMARY
──────────────────────────────────────────────────────────
Intent              : Book a Botox appointment next month
Treatment Interest  : Botox
Prior Experience    : Yes
Booking Timeframe   : Next month
Next Action         : Follow up to confirm Botox booking
```

Escalated sessions are named `session_TIMESTAMP_ESCALATED.json/.txt`.

---

## 10. Configuration Reference

### Environment variables (`.env`)

| Variable        | Required | Description                    |
|-----------------|----------|--------------------------------|
| `GROQ_API_KEY`  | ✅ Yes    | Your Groq API key              |

### CLI flags (`main.py`)

| Flag               | Default | Description                                  |
|--------------------|---------|----------------------------------------------|
| `--debug`          | off     | Show raw API output + stage state each turn  |
| `--sop <path>`     | sop.json | Load a custom SOP file                      |
| `--channel <mode>` | cli     | `cli` (default) or `whatsapp`               |

### API parameters (`api.py`)

| Parameter | Where         | Description                     |
|-----------|---------------|---------------------------------|
| `channel` | POST /session/start body | `api` or `whatsapp` |

### Tuning constants (`main.py` and `api.py`)

| Constant                  | Default | Effect                                     |
|---------------------------|---------|--------------------------------------------|
| `FAQ_TURNS_BEFORE_QUALIFY`| 3       | Substantive turns before qualification     |
| `QUALIFY_QUESTIONS`       | 3       | Number of qualification questions to ask   |

---

## 11. Design Decisions

### JSON-only model output
The model is required to respond in a strict JSON schema every turn. This makes escalation
detection explicit (a boolean field the model sets) rather than requiring post-hoc sentiment
analysis. A fallback parser with regex extraction handles rare mixed-output cases.

### Deterministic stage transitions
Stage transitions are turn-count based (`faq_turns >= 3`, `qualify_turns >= 3`),
not model-driven. This makes behaviour predictable, testable, and easy to tune.

### Substantive turn filtering
Greetings and identity questions ("hi", "who are you", "how are you") do not advance the
FAQ counter. Only messages over 12 characters or containing a `?` are counted as substantive.
This prevents premature transition to qualification.

### Booking conflict pre-check
Before calling the API, `main.py` checks if the user mentioned a time after 6:45pm or
a closed day. If so, a system note is printed immediately (no API call needed). This saves
latency and ensures accuracy even if the model fails to catch it.

### Retry with back-off
All Groq API calls retry up to 2 times (1.5s then 2.25s delay) before falling back to a
graceful error message. This handles transient network issues without crashing the session.

### WhatsApp channel mode
A formatting layer strips markdown (`**`, `__`, backticks) and enforces a 1000-character
limit on responses. This mirrors real WhatsApp API constraints and can be extended to
other channels by adding cases to `format_for_channel()`.

### Multi-clinic SOP
The agent accepts a `sop_path` argument at construction time. Any JSON file following
the SOP schema (see `sop_template.json`) can be used, making the system reusable across
different SMB clients — which is Closira's core business model.

---

## 12. Known Limitations

| Limitation                  | Workaround / Notes                                           |
|-----------------------------|--------------------------------------------------------------|
| In-memory session state     | Sessions are lost on restart. Suitable for demo/assignment scope. Extend with Redis for production. |
| No persistent customer IDs  | Cannot recall returning customers. Extend by adding customer_id to session start and searching logs. |
| Single SOP per agent        | Agent loads one SOP at startup. Multi-tenant would require one agent instance per SOP or dynamic loading. |
| Turn-count stage transitions | May feel abrupt if the customer is still asking questions. Add `"suggest_qualify": true` field to model output for smoother transitions. |
| Groq rate limits            | Free tier: 30 req/min. Production: upgrade plan or add request queuing. |
| No authentication on API    | `/stats` and `/sessions` are open. Add API key auth middleware for production. |
