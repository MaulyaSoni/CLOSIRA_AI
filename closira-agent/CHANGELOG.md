# Changelog — Closira AI Agent

All notable changes are documented here.

---

## v2.0.0 — Current

### New Files
- **`api.py`** — FastAPI REST server wrapping the same agent logic as the CLI. Supports concurrent sessions via in-memory store. Endpoints: start, chat, end, state, sessions, stats, health.
- **`stats.py`** — Admin CLI dashboard. Reads all `logs/*.json` files and renders: total sessions, escalation rate, escalation breakdown by type (with bar chart), top SOP gaps, and recent session list.
- **`sop_template.json`** — Starter template for multi-clinic SOP support.
- **`PROJECT.md`** — Master project documentation (this project's source of truth).

### Bug Fixes
- **JSON leak fix** (`agent.py`): Model sometimes returned mixed text + JSON. `_parse_response()` now tries direct parse first, then regex-extracts the JSON block from mixed content, then falls back to raw text as response — in that order.
- **Smart FAQ turn counting** (`utils.py`, `main.py`): `is_substantive()` filters out greetings and identity questions ("hi", "who are you", "okay", etc.) so they no longer advance the FAQ counter toward qualification.
- **Booking conflict pre-check** (`main.py`): Before calling the API, the input is scanned for after-hours times (7pm+) and closed days (Sunday). A system note is displayed immediately if detected, with no API call needed.

### Improvements
- **`--debug` flag** (`main.py`): Shows raw API response, stage state, FAQ/qualify turn counts, and qualification data on every turn. Also shows session stats at start and end.
- **`--sop <path>` flag** (`main.py`, `agent.py`): Load any custom SOP JSON file. Agent accepts `sop_path` at construction. Enables multi-clinic support.
- **`--channel <cli|whatsapp>` flag** (`main.py`): WhatsApp mode strips markdown formatting and caps responses at 1000 characters. API server uses `channel` parameter in POST body.
- **Exponential back-off retry** (`agent.py`): Groq API calls retry up to 2 times (delays: 1.5s, 2.25s) before falling back gracefully.
- **Colour-coded escalation** (`utils.py`): Escalation alerts now show type-specific colours and labels: 🔴 complaint/medical, 🟡 pricing, 🟣 human request, 🔵 out-of-scope.
- **Dual session logging** (`utils.py`): Each session now writes both `.json` (machine-readable) and `.txt` (human-readable) log files to `logs/`.
- **Session stats function** (`utils.py`): `read_session_stats()` is shared between `stats.py` (CLI dashboard) and `api.py` (`GET /stats` endpoint).
- **`last_appointment_slot` + `closed_days`** (`sop.json`): SOP now includes last booking slot and closed days. Agent uses these in the system prompt for appointment time validation.

### Updated Files
- `agent.py` — retry, better parsing, multi-SOP, `last_appointment_slot` in prompt
- `main.py` — all new flags, booking conflict check, debug stats, WhatsApp formatter
- `utils.py` — classify_escalation, is_substantive, dual logging, read_session_stats
- `requirements.txt` — added `fastapi>=0.110.0`, `uvicorn>=0.27.0`
- `sop.json` — added `last_appointment_slot`, `closed_days`
- `README.md` — updated with all new usage instructions

---

## v1.0.0 — Initial Submission

### Files
- `main.py` — CLI loop with 4-stage state machine
- `agent.py` — Groq API wrapper with stage-specific prompts
- `utils.py` — Terminal helpers, basic session logging
- `sop.json` — Bloom Aesthetics Clinic SOP
- `prompt_design.md` — Prompt design document
- `README.md` — Setup instructions
- `requirements.txt` — `groq`, `python-dotenv`
- `test_transcripts/` — 5 sample conversation files

### Core behaviour
- FAQ answering strictly from SOP
- 3-question lead qualification
- Escalation detection via model-reported boolean field
- Session summary on exit
- Session log saved to `logs/*.json`
