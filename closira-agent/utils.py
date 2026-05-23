import os
import json
from datetime import datetime
from collections import Counter

# ── ANSI colour codes ─────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
GREEN   = "\033[92m"
CYAN    = "\033[96m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
MAGENTA = "\033[95m"
WHITE   = "\033[97m"
DIM     = "\033[2m"
ORANGE  = "\033[38;5;208m"

LOGS_DIR = "logs"

# ── Escalation classification ─────────────────────────────────────────────────

ESCALATION_COLOR_MAP = {
    "medical":       RED,
    "complaint":     RED,
    "pricing":       YELLOW,
    "human_request": MAGENTA,
    "out_of_scope":  CYAN,
    "general":       WHITE,
}

ESCALATION_LABEL_MAP = {
    "medical":       "🏥  MEDICAL / HEALTH CONCERN",
    "complaint":     "⚠️   CUSTOMER COMPLAINT",
    "pricing":       "💰  PRICING NEGOTIATION",
    "human_request": "👤  HUMAN AGENT REQUESTED",
    "out_of_scope":  "🔍  OUT OF SCOPE",
    "general":       "⚠️   ESCALATION TRIGGERED",
}

def classify_escalation(reason: str) -> str:
    r = reason.lower()
    if any(w in r for w in ["medical", "health", "pregnant", "allergy", "pain", "side effect", "reaction", "clinical"]):
        return "medical"
    if any(w in r for w in ["complaint", "unhappy", "dissatisfied", "disappointed", "wrong", "bad experience", "upset"]):
        return "complaint"
    if any(w in r for w in ["price", "pricing", "discount", "cheaper", "negotiate", "cost", "deal"]):
        return "pricing"
    if any(w in r for w in ["human", "person", "agent", "speak to", "talk to", "real person"]):
        return "human_request"
    if any(w in r for w in ["scope", "unanswered", "cannot answer", "don't have", "not in sop"]):
        return "out_of_scope"
    return "general"

# ── Substantive turn check ────────────────────────────────────────────────────

SMALL_TALK = {
    "hi", "hello", "hey", "how are you", "who are you", "what are you",
    "ok", "okay", "great", "thanks", "thank you", "nice", "cool", "sure",
    "alright", "sounds good", "perfect", "awesome", "got it", "yep", "yes",
    "no", "nope", "fine", "good", "interesting"
}

def is_substantive(text: str) -> bool:
    lowered = text.lower().strip().rstrip("?!.,")
    if lowered in SMALL_TALK:
        return False
    if len(text) < 12 and "?" not in text:
        return False
    return True

# ── Print helpers ─────────────────────────────────────────────────────────────

def print_banner(debug: bool = False):
    mode_tag = f"  {YELLOW}[DEBUG MODE ACTIVE]{RESET}\n" if debug else ""
    print(f"""
{MAGENTA}{BOLD}
╔══════════════════════════════════════════════════════════╗
║        CLOSIRA — AI Customer Support Agent               ║
║        Client : Bloom Aesthetics Clinic                  ║
║        Model  : Groq · LLaMA 3.3 70B Versatile          ║
║        Mode   : CLI {'(debug)' if debug else '       '}                            ║
╚══════════════════════════════════════════════════════════╝
{RESET}{mode_tag}{CYAN}  Commands : type your message and press Enter
             type  'bye' / 'done' / 'exit'  to end session{RESET}
{DIM}  ──────────────────────────────────────────────────────────{RESET}
""")


def print_bot(msg: str):
    print(f"\n{CYAN}{BOLD}Aria:{RESET} {msg}")


def print_stage_transition(msg: str):
    print(f"\n{YELLOW}{DIM}[system] {msg}{RESET}")


def print_escalation_alert(reason: str, escalation_type: str = "general"):
    colour = ESCALATION_COLOR_MAP.get(escalation_type, WHITE)
    label  = ESCALATION_LABEL_MAP.get(escalation_type, "⚠️  ESCALATION TRIGGERED")
    print(f"\n{colour}{BOLD}{'─' * 58}")
    print(f"  {label}")
    print(f"  Reason : {reason}")
    print(f"{'─' * 58}{RESET}")


def print_summary_box(summary: dict):
    print(f"\n{MAGENTA}{BOLD}{'═' * 58}")
    print("  SESSION SUMMARY")
    print(f"{'═' * 58}{RESET}")

    print(f"\n{WHITE}{BOLD}Customer Intent:{RESET}\n  {summary.get('customer_intent', 'N/A')}")

    details = summary.get("key_details_collected", {})
    if details:
        print(f"\n{WHITE}{BOLD}Details Collected:{RESET}")
        labels = {
            "treatment_interest": "Treatment Interest",
            "prior_experience":   "Prior Experience",
            "booking_timeframe":  "Booking Timeframe",
        }
        for key, label in labels.items():
            val = details.get(key)
            if val and val not in ("Not specified", "Unknown", ""):
                print(f"  • {label}: {val}")

    gaps = summary.get("sop_gaps", [])
    if gaps:
        print(f"\n{YELLOW}{BOLD}SOP Gaps Identified:{RESET}")
        for gap in gaps:
            print(f"  • {gap}")
    else:
        print(f"\n{GREEN}SOP Gaps:{RESET} None")

    if summary.get("escalated"):
        etype  = classify_escalation(summary.get("escalation_reason") or "")
        colour = ESCALATION_COLOR_MAP.get(etype, RED)
        print(f"\n{colour}{BOLD}Escalated: Yes{RESET}")
        print(f"{colour}  Reason: {summary.get('escalation_reason', 'N/A')}{RESET}")
    else:
        print(f"\n{GREEN}Escalated:{RESET} No")

    print(f"\n{GREEN}{BOLD}Recommended Next Action:{RESET}\n  {summary.get('recommended_next_action', 'N/A')}")
    print(f"\n{MAGENTA}{BOLD}{'═' * 58}{RESET}\n")


# ── Debug helpers ─────────────────────────────────────────────────────────────

def print_debug_info(stage: str, faq_turns: int, qualify_turns: int, qdata: dict):
    print(f"\n{DIM}{'·' * 58}")
    print(f"  [DEBUG] stage={stage}  faq_turns={faq_turns}  qualify_turns={qualify_turns}")
    if qdata:
        print(f"  [DEBUG] qdata={json.dumps(qdata)}")
    print(f"{'·' * 58}{RESET}")


def print_raw_result(result: dict):
    print(f"{DIM}  [DEBUG] raw result → {json.dumps(result, indent=2)}{RESET}")


# ── Session logging ───────────────────────────────────────────────────────────

def save_session_log(session_log: list, summary: dict, escalated: bool = False):
    os.makedirs(LOGS_DIR, exist_ok=True)
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix  = "_ESCALATED" if escalated else ""
    base    = f"{LOGS_DIR}/session_{ts}{suffix}"

    # JSON log
    payload = {
        "timestamp": datetime.now().isoformat(),
        "escalated": escalated,
        "conversation": session_log,
        "summary": summary,
    }
    with open(f"{base}.json", "w") as f:
        json.dump(payload, f, indent=2)

    # Human-readable TXT log
    with open(f"{base}.txt", "w", encoding="utf-8") as f:
        f.write("=" * 58 + "\n")
        f.write(f"CLOSIRA SESSION LOG — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Escalated: {'YES' if escalated else 'No'}\n")
        f.write("=" * 58 + "\n\n")
        for msg in session_log:
            role  = "Aria    " if msg["role"] == "assistant" else "Customer"
            stage = msg.get("stage", "")
            esc   = " [ESCALATED]" if msg.get("escalated") else ""
            f.write(f"[{stage}] {role}: {msg['content']}{esc}\n\n")
        f.write("-" * 58 + "\n")
        f.write("SUMMARY\n")
        f.write("-" * 58 + "\n")
        f.write(f"Intent  : {summary.get('customer_intent', 'N/A')}\n")
        details = summary.get("key_details_collected", {})
        for k, v in details.items():
            if v and v not in ("Not specified", "Unknown"):
                f.write(f"{k.replace('_',' ').title():<20}: {v}\n")
        gaps = summary.get("sop_gaps", [])
        if gaps:
            f.write(f"SOP Gaps: {'; '.join(gaps)}\n")
        f.write(f"Next Action: {summary.get('recommended_next_action', 'N/A')}\n")

    print(f"\n{DIM}Logs saved → {base}.json / .txt{RESET}")


# ── Session stats (read from logs/) ──────────────────────────────────────────

def read_session_stats() -> dict:
    if not os.path.exists(LOGS_DIR):
        return {"total_sessions": 0, "message": "No logs found."}

    sessions = []
    for fname in os.listdir(LOGS_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(LOGS_DIR, fname)) as fp:
                    sessions.append(json.load(fp))
            except Exception:
                pass

    if not sessions:
        return {"total_sessions": 0, "message": "No sessions recorded yet."}

    total     = len(sessions)
    escalated = [s for s in sessions if s.get("escalated")]
    esc_rate  = round(len(escalated) / total * 100, 1) if total else 0

    esc_types = [
        classify_escalation(s.get("summary", {}).get("escalation_reason") or "")
        for s in escalated
    ]

    all_gaps = []
    for s in sessions:
        all_gaps.extend(s.get("summary", {}).get("sop_gaps", []))

    turn_counts = [
        len([m for m in s.get("conversation", []) if m.get("role") == "user"])
        for s in sessions
    ]
    avg_turns = round(sum(turn_counts) / len(turn_counts), 1) if turn_counts else 0

    return {
        "total_sessions":       total,
        "escalated_sessions":   len(escalated),
        "escalation_rate_pct":  esc_rate,
        "avg_turns_per_session": avg_turns,
        "escalation_by_type":   dict(Counter(esc_types)),
        "top_sop_gaps":         dict(Counter(all_gaps).most_common(5)),
    }
