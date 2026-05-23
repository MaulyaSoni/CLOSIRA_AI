# Closira AI Agent — Bloom Aesthetics Clinic

AI-powered customer support CLI + REST API. Built with Groq + LLaMA 3.3 70B.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env        # add GROQ_API_KEY
python main.py              # run CLI
```

## Run Modes

| Command | Description |
|---|---|
| `python main.py` | Standard CLI |
| `python main.py --debug` | Show raw API output + stage state |
| `python main.py --channel whatsapp` | WhatsApp formatting mode |
| `python main.py --sop custom.json` | Use a custom SOP file |
| `uvicorn api:app --reload --port 8000` | Start REST API server |
| `python stats.py` | Admin stats dashboard |

## REST API (Quick Reference)

```bash
# Start session
curl -X POST http://localhost:8000/session/start -H "Content-Type: application/json" -d '{"channel":"api"}'

# Chat (use session_id from above)
curl -X POST http://localhost:8000/session/SESSION_ID/chat -H "Content-Type: application/json" -d '{"message":"What are your Botox prices?"}'

# End session
curl -X POST http://localhost:8000/session/SESSION_ID/end

# Stats
curl http://localhost:8000/stats
```

**Interactive docs:** http://localhost:8000/docs

## Project Docs

See **PROJECT.md** for the full documentation:
- Complete folder structure
- Feature matrix (v1 + v2)
- Stage flow diagram
- REST API reference
- SOP format spec
- Escalation types
- Design decisions
- Known limitations
