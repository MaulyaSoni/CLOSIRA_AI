import os
import json
import re
from datetime import datetime

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

ESCALATION_CATEGORY_COLORS = {
    "medical": RED,
    "complaint": YELLOW,
    "pricing": CYAN,
    "human": WHITE,
    "other": MAGENTA,
}


# ── Print helpers ─────────────────────────────────────────────────────────────

def print_banner():
    print(f"""
{MAGENTA}{BOLD}
╔══════════════════════════════════════════════════════════╗
║        CLOSIRA — AI Customer Support Agent               ║
║        Client: Bloom Aesthetics Clinic                   ║
║        Model : Groq · LLaMA 3.3 70B Versatile           ║
╚══════════════════════════════════════════════════════════╝
{RESET}{CYAN}  Commands: type your message and press Enter
            type  'bye' / 'done' / 'exit'  to end session{RESET}
{DIM}  ──────────────────────────────────────────────────────────{RESET}
""")


def print_bot(msg: str):
    """Print a message from Aria."""
    print(f"\n{CYAN}{BOLD}Aria:{RESET} {msg}")


def print_stage_transition(msg: str):
    """Print a system-level stage transition notice."""
    print(f"\n{YELLOW}{DIM}[system] {msg}{RESET}")


def print_escalation_alert(reason: str):
    """Print a prominent escalation warning."""
    category = classify_escalation_reason(reason)
    category_color = ESCALATION_CATEGORY_COLORS.get(category, MAGENTA)
    print(f"\n{RED}{BOLD}{'─' * 56}")
    print(f"  ⚠️  ESCALATION TRIGGERED")
    print(f"  Type: {category_color}{category.upper()}{RESET}")
    print(f"  Reason: {category_color}{reason}{RESET}")
    print(f"{'─' * 56}{RESET}")


def print_debug_turn(stage: str, faq_turns: int, qualification_data: dict, result: dict):
    """Print a compact debug block for a single turn."""
    print(f"\n{DIM}[debug] stage={stage} faq_turns={faq_turns} qualification_keys={list(qualification_data.keys())}{RESET}")
    if result.get("_policy_flag"):
        print(f"{DIM}[debug] policy_flag={result.get('_policy_flag')}{RESET}")
    if result.get("_usage"):
        print(f"{DIM}[debug] usage={json.dumps(result.get('_usage'), ensure_ascii=True)}{RESET}")
    if result.get("_raw_output"):
        print(f"{DIM}[debug] raw_output={result.get('_raw_output')}{RESET}")


def classify_escalation_reason(reason: str) -> str:
    """Map an escalation reason into a display category."""
    if not reason:
        return "other"

    lowered = reason.lower()
    if any(token in lowered for token in ("medical", "health", "pain", "swelling", "asymmetry", "treatment concern")):
        return "medical"
    if any(token in lowered for token in ("complaint", "dissatisfied", "angry", "frustrated", "upset", "negative feedback")):
        return "complaint"
    if any(token in lowered for token in ("price", "pricing", "discount", "cheap", "negotiat")):
        return "pricing"
    if "human" in lowered or "agent" in lowered:
        return "human"
    return "other"


def should_count_faq_turn(user_input: str) -> bool:
    """Return True when a user message should count toward the FAQ stage."""
    text = (user_input or "").strip().lower()
    if not text:
        return False

    meta_patterns = (
        r"^(hi|hello|hey|good morning|good afternoon|good evening)\b",
        r"^(who are you|what are you|tell me about yourself)\b",
        r"^(thanks|thank you|thx)\b",
    )
    if any(re.search(pattern, text) for pattern in meta_patterns):
        return False

    clinic_keywords = (
        "hour", "open", "close", "price", "pricing", "botox", "filler", "consultation",
        "book", "booking", "appointment", "cancel", "cancellation", "website", "whatsapp", "service",
    )
    return any(keyword in text for keyword in clinic_keywords) or "?" in text


def qualification_complete(qualification_data: dict) -> bool:
    """Return True when all lead qualification fields are populated."""
    required_keys = ("treatment_interest", "prior_experience", "booking_timeframe")
    return all(qualification_data.get(key) not in (None, "", "Not specified", "Unknown") for key in required_keys)


def detect_booking_hours_conflict(user_input: str, hours_text: str) -> dict:
    """Detect a booking request that conflicts with clinic opening hours."""
    text = (user_input or "").lower()
    booking_intent = any(
        keyword in text
        for keyword in ("book", "booking", "appointment", "availability", "available", "schedule", "slot")
    )
    if not booking_intent:
        return {}

    closing_match = _extract_last_time(hours_text)
    if not closing_match:
        return {}

    requested_times = _extract_times(text)
    if not requested_times:
        return {}

    close_minutes = _time_to_minutes(*closing_match)
    for requested in requested_times:
        if _time_to_minutes(*requested) >= close_minutes:
            closing_label = _format_time(*closing_match)
            requested_label = _format_time(*requested)
            return {
                "flag": "booking_outside_hours",
                "response": (
                    f"We’re open {hours_text}, so {requested_label} would be outside our appointment hours. "
                    "If you’d like, I can help with an earlier time."
                ),
            }

    return {}


def collect_session_stats(log_dir: str = "logs") -> dict:
    """Aggregate simple stats across saved JSON session logs."""
    stats = {
        "total_sessions": 0,
        "escalated_sessions": 0,
        "escalation_rate": 0.0,
        "escalation_categories": {"medical": 0, "complaint": 0, "pricing": 0, "human": 0, "other": 0},
    }

    if not os.path.isdir(log_dir):
        return stats

    for filename in os.listdir(log_dir):
        if not filename.startswith("session_") or not filename.endswith(".json"):
            continue

        path = os.path.join(log_dir, filename)
        try:
            with open(path, "r") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue

        stats["total_sessions"] += 1
        if payload.get("escalated"):
            stats["escalated_sessions"] += 1
            summary = payload.get("summary") or {}
            category = classify_escalation_reason(summary.get("escalation_reason"))
            stats["escalation_categories"][category] = stats["escalation_categories"].get(category, 0) + 1

    if stats["total_sessions"]:
        stats["escalation_rate"] = round((stats["escalated_sessions"] / stats["total_sessions"]) * 100, 1)

    return stats


def _extract_times(text: str):
    pattern = re.compile(r"\b(?P<hour>1[0-2]|0?[1-9])(?::(?P<minute>[0-5]\d))?\s*(?P<meridiem>am|pm)\b", re.IGNORECASE)
    matches = []
    for match in pattern.finditer(text or ""):
        hour = int(match.group("hour"))
        minute = int(match.group("minute") or 0)
        meridiem = match.group("meridiem").lower()
        matches.append(_normalize_time(hour, minute, meridiem))
    return matches


def _extract_last_time(text: str):
    times = _extract_times(text)
    return times[-1] if times else None


def _normalize_time(hour: int, minute: int, meridiem: str):
    if meridiem == "am":
        hour = 0 if hour == 12 else hour
    else:
        hour = 12 if hour == 12 else hour + 12
    return hour, minute


def _time_to_minutes(hour: int, minute: int) -> int:
    return hour * 60 + minute


def _format_time(hour: int, minute: int) -> str:
    suffix = "am" if hour < 12 else "pm"
    display_hour = hour % 12
    if display_hour == 0:
        display_hour = 12
    if minute:
        return f"{display_hour}:{minute:02d}{suffix}"
    return f"{display_hour}{suffix}"


def _render_session_text(session_log: list, summary: dict, stats: dict, escalated: bool) -> str:
    lines = []
    lines.append("CLOSIRA SESSION LOG")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Escalated: {'yes' if escalated else 'no'}")
    lines.append("")
    lines.append("SUMMARY")
    lines.append(f"Customer intent: {summary.get('customer_intent', 'N/A')}")
    details = summary.get("key_details_collected", {}) or {}
    if details:
        lines.append("Details collected:")
        for key, value in details.items():
            lines.append(f"  - {key}: {value}")
    gaps = summary.get("sop_gaps", []) or []
    lines.append(f"SOP gaps: {', '.join(gaps) if gaps else 'none'}")
    lines.append(f"Escalation reason: {summary.get('escalation_reason') or 'none'}")
    lines.append(f"Recommended next action: {summary.get('recommended_next_action', 'N/A')}")
    lines.append("")
    lines.append("SESSION STATS")
    lines.append(f"Total sessions: {stats['total_sessions']}")
    lines.append(f"Escalated sessions: {stats['escalated_sessions']}")
    lines.append(f"Escalation rate: {stats['escalation_rate']}%")
    lines.append("Escalation categories:")
    for key, value in stats["escalation_categories"].items():
        lines.append(f"  - {key}: {value}")
    lines.append("")
    lines.append("CONVERSATION")
    for entry in session_log:
        role = entry.get("role", "unknown").upper()
        stage = entry.get("stage", "n/a")
        lines.append(f"[{role} | stage={stage}]")
        content = entry.get("content", "")
        lines.append(content)
        if entry.get("escalated"):
            lines.append(f"[escalated] {entry.get('escalate_reason', 'unspecified')}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def print_summary_box(summary: dict):
    """Render the session summary in a formatted box."""
    print(f"\n{MAGENTA}{BOLD}{'═' * 56}")
    print("  SESSION SUMMARY")
    print(f"{'═' * 56}{RESET}")

    intent = summary.get("customer_intent", "N/A")
    print(f"\n{WHITE}{BOLD}Customer Intent:{RESET}\n  {intent}")

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
        print(f"\n{GREEN}SOP Gaps:{RESET} None — all questions answered from SOP")

    escalated = summary.get("escalated", False)
    if escalated:
        print(f"\n{RED}{BOLD}Escalated: Yes{RESET}")
        reason = summary.get("escalation_reason") or "Not specified"
        print(f"{RED}  Reason: {reason}{RESET}")
    else:
        print(f"\n{GREEN}Escalated:{RESET} No")

    action = summary.get("recommended_next_action", "N/A")
    print(f"\n{GREEN}{BOLD}Recommended Next Action:{RESET}\n  {action}")

    print(f"\n{MAGENTA}{BOLD}{'═' * 56}{RESET}\n")


# ── Session logging ───────────────────────────────────────────────────────────

def save_session_log(session_log: list, summary: dict, escalated: bool = False):
    """Persist the full session to a JSON file in the logs/ directory."""
    os.makedirs("logs", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "_ESCALATED" if escalated else ""
    filename = f"logs/session_{timestamp}{suffix}.json"
    text_filename = f"logs/session_{timestamp}{suffix}.txt"

    payload = {
        "timestamp": datetime.now().isoformat(),
        "escalated": escalated,
        "conversation": session_log,
        "summary": summary,
    }

    with open(filename, "w") as f:
        json.dump(payload, f, indent=2)

    stats = collect_session_stats("logs")
    with open(text_filename, "w") as f:
        f.write(_render_session_text(session_log, summary, stats, escalated))

    print(f"\n{DIM}Session log saved → {filename}{RESET}")
    print(f"{DIM}Text log saved → {text_filename}{RESET}")

    return {
        "json_path": filename,
        "text_path": text_filename,
        "stats": stats,
    }
