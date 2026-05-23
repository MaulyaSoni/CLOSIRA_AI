"""
main.py — Closira AI Agent CLI
Usage:
  python main.py
  python main.py --debug
  python main.py --sop custom_sop.json
  python main.py --channel whatsapp
"""
import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

from agent import ClosiraAgent
from utils import (
    print_banner, print_bot, print_stage_transition,
    print_escalation_alert, print_summary_box,
    print_debug_info, print_raw_result,
    save_session_log, read_session_stats,
    classify_escalation, is_substantive,
    CYAN, BOLD, RESET, YELLOW, DIM,
)

# ── CLI args ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Closira AI Customer Support Agent")
parser.add_argument("--debug",   action="store_true", help="Show raw API responses and stage state")
parser.add_argument("--sop",     type=str, default=None, help="Path to custom SOP JSON file")
parser.add_argument("--channel", type=str, default="cli",
                    choices=["cli", "whatsapp"], help="Output channel formatting")
args = parser.parse_args()

DEBUG   = args.debug
CHANNEL = args.channel

# ── Constants ─────────────────────────────────────────────────────────────────
FAQ_TURNS_BEFORE_QUALIFY = 3
QUALIFY_QUESTIONS        = 3
EXIT_COMMANDS            = {"bye", "exit", "quit", "goodbye", "done", "end"}

WHATSAPP_GREETING = (
    "Hi! I'm Aria from Bloom Aesthetics Clinic 🌸\n"
    "How can I help you today?"
)
CLI_GREETING = (
    "Hi there! I'm Aria, your virtual assistant for Bloom Aesthetics Clinic. 🌸\n"
    "I'm here to help with questions about our services, pricing, and bookings.\n"
    "What can I help you with today?"
)

# ── WhatsApp formatter ────────────────────────────────────────────────────────
def format_for_channel(text: str) -> str:
    if CHANNEL == "whatsapp":
        for md in ["**", "__", "~~", "`"]:
            text = text.replace(md, "")
        if len(text) > 1000:
            text = text[:997] + "…"
    return text


# ── Booking conflict check ────────────────────────────────────────────────────
AFTER_HOURS_KEYWORDS = ["7pm", "7 pm", "8pm", "9pm", "10pm", "after 7"]
CLOSED_DAY_KEYWORDS  = ["sunday"]

def check_booking_conflict(text: str) -> str | None:
    lowered = text.lower()
    if any(k in lowered for k in AFTER_HOURS_KEYWORDS):
        return "⏰ Just to flag — our last appointment slot is 6:45pm. We're open Mon–Sat, 9am–7pm."
    if any(k in lowered for k in CLOSED_DAY_KEYWORDS):
        return "📅 We're closed on Sundays. We're open Mon–Sat, 9am–7pm — happy to find a slot that works!"
    return None


# ── Session stats display ────────────────────────────────────────────────────
def print_session_stats():
    stats = read_session_stats()
    if stats.get("total_sessions", 0) == 0:
        return
    print(f"\n{DIM}── Session History ──────────────────────────────────────")
    print(f"  Total sessions   : {stats['total_sessions']}")
    print(f"  Escalation rate  : {stats['escalation_rate_pct']}%")
    print(f"  Avg turns/session: {stats['avg_turns_per_session']}")
    if stats.get("top_sop_gaps"):
        gaps = list(stats["top_sop_gaps"].keys())[:3]
        print(f"  Common SOP gaps  : {' | '.join(gaps)}")
    print(f"──────────────────────────────────────────────────────{RESET}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print_banner(debug=DEBUG)
    if DEBUG:
        print_session_stats()

    try:
        agent = ClosiraAgent(sop_path=args.sop)
    except (ValueError, FileNotFoundError) as e:
        print(f"\n❌  Startup error: {e}\n")
        sys.exit(1)

    if args.sop:
        print(f"{YELLOW}[system] Custom SOP loaded: {args.sop}{RESET}\n")
    if CHANNEL == "whatsapp":
        print(f"{YELLOW}[system] WhatsApp channel mode active — markdown stripped, 1000 char limit{RESET}\n")

    # ── Session state ─────────────────────────────────────────────────────────
    stage                = "faq"
    conversation_history = []
    qualification_data   = {}
    faq_turns            = 0
    qualify_turns        = 0
    session_log          = []

    greeting = format_for_channel(CLI_GREETING if CHANNEL == "cli" else WHATSAPP_GREETING)
    print_bot(greeting)
    conversation_history.append({"role": "assistant", "content": greeting})

    # ── Conversation loop ─────────────────────────────────────────────────────
    while True:
        try:
            user_input = input(f"\n{'You' if CHANNEL == 'cli' else 'Customer'}: ").strip()
        except (KeyboardInterrupt, EOFError):
            user_input = "bye"

        if not user_input:
            continue

        # Exit
        if user_input.lower() in EXIT_COMMANDS:
            print_stage_transition("Generating session summary…")
            summary = agent.generate_summary(conversation_history, qualification_data)
            print_summary_box(summary)
            save_session_log(session_log, summary)
            if DEBUG:
                print_session_stats()
            print_bot("Thanks for reaching out to Bloom Aesthetics Clinic. We hope to see you soon! 🌸")
            break

        # Booking conflict pre-check (before calling API)
        conflict_note = check_booking_conflict(user_input)
        if conflict_note:
            print_stage_transition(conflict_note)

        conversation_history.append({"role": "user", "content": user_input})
        session_log.append({"role": "user", "content": user_input, "stage": stage})

        if DEBUG:
            print_debug_info(stage, faq_turns, qualify_turns, qualification_data)

        result       = agent.respond(conversation_history, stage, qualification_data)
        bot_response = format_for_channel(
            result.get("response", "I'm sorry, could you rephrase that?")
        )

        if DEBUG:
            print_raw_result(result)

        # ── Escalation ────────────────────────────────────────────────────────
        if result.get("escalate"):
            reason = result.get("escalate_reason") or "Unspecified"
            etype  = classify_escalation(reason)
            print_escalation_alert(reason, etype)
            print_bot(bot_response)

            session_log.append({
                "role": "assistant", "content": bot_response,
                "stage": stage, "escalated": True,
                "escalate_reason": reason, "escalation_type": etype,
            })
            conversation_history.append({"role": "assistant", "content": bot_response})

            summary = agent.generate_summary(
                conversation_history, qualification_data,
                escalated=True, escalate_reason=reason
            )
            print_summary_box(summary)
            save_session_log(session_log, summary, escalated=True)
            if DEBUG:
                print_session_stats()
            print_bot("A member of our team will be in touch shortly. Thank you for your patience. 🌸")
            break

        # ── Normal response ───────────────────────────────────────────────────
        print_bot(bot_response)
        conversation_history.append({"role": "assistant", "content": bot_response})
        session_log.append({"role": "assistant", "content": bot_response, "stage": stage})

        for k, v in (result.get("qualification_data") or {}).items():
            if v and v not in ("Not specified", "Unknown", ""):
                qualification_data[k] = v

        # ── Stage transitions ─────────────────────────────────────────────────
        if stage == "faq":
            if is_substantive(user_input):
                faq_turns += 1
            if faq_turns >= FAQ_TURNS_BEFORE_QUALIFY:
                stage = "qualify"
                print_stage_transition("Moving to lead qualification…")

        elif stage == "qualify":
            qualify_turns += 1
            if qualify_turns >= QUALIFY_QUESTIONS:
                stage = "done"
                print_stage_transition("Qualification complete!")
                print_bot(
                    "Wonderful! I've noted all your details. 📋\n"
                    "Our team will be in touch to confirm everything.\n"
                    "Type 'bye' or 'done' whenever you're ready for your session summary."
                )


if __name__ == "__main__":
    main()
