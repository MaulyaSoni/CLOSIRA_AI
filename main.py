"""
main.py — Closira AI Agent · Bloom Aesthetics Clinic
-----------------------------------------------------
Entry point. Runs the 4-stage customer support workflow:
  Stage 1 · FAQ          Answer questions from SOP only
  Stage 2 · Qualify      Collect 3 lead qualification answers
  Stage 3 · Done         Wrap-up, prompt user to exit
  Stage 4 · Summary      Generated on exit or escalation

Usage:
    python main.py
    python main.py --debug
"""

import argparse
import os
import sys
from dotenv import load_dotenv

load_dotenv()  # Load GROQ_API_KEY from .env

from agent import ClosiraAgent
from utils import (
    detect_booking_hours_conflict,
    qualification_complete,
    print_banner,
    print_bot,
    print_debug_turn,
    should_count_faq_turn,
    print_stage_transition,
    print_escalation_alert,
    print_summary_box,
    save_session_log,
)

# ── Constants ─────────────────────────────────────────────────────────────────
FAQ_TURNS_BEFORE_QUALIFY = 2   # Number of meaningful user turns in FAQ before transitioning

EXIT_COMMANDS = {"bye", "exit", "quit", "goodbye", "done", "end"}


# ── Main ──────────────────────────────────────────────────────────────────────

def main(debug: bool = False):
    print_banner()

    # Initialise agent (validates API key and loads SOP)
    try:
        agent = ClosiraAgent()
    except (ValueError, FileNotFoundError) as e:
        print(f"\n❌  Startup error: {e}\n")
        sys.exit(1)

    # ── Session state ─────────────────────────────────────────────────────────
    stage               = "faq"
    conversation_history = []   # Full message history sent to Groq each turn
    qualification_data  = {}    # Accumulated qualification answers
    faq_turns           = 0     # User turns completed in FAQ stage
    session_log         = []    # Richer per-turn log (includes stage + metadata)

    # Opening greeting (injected directly — not via API to save a call)
    greeting = (
        "Hi there! I'm Aria, your virtual assistant for Bloom Aesthetics Clinic. 🌸\n"
        "I'm here to help with questions about our services, pricing, and bookings.\n"
        "What can I help you with today?"
    )
    print_bot(greeting)
    conversation_history.append({"role": "assistant", "content": greeting})

    # ── Conversation loop ─────────────────────────────────────────────────────
    while True:

        # Read user input
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            user_input = "bye"

        if not user_input:
            continue

        # ── Exit path ─────────────────────────────────────────────────────────
        if user_input.lower() in EXIT_COMMANDS:
            print_stage_transition("Generating session summary…")
            summary = agent.generate_summary(conversation_history, qualification_data, debug=debug)
            print_summary_box(summary)
            if debug:
                print_debug_turn(stage, faq_turns, qualification_data, summary)
            save_session_log(session_log, summary)
            print_bot(
                "Thanks for reaching out to Bloom Aesthetics Clinic. "
                "We hope to see you soon! 🌸"
            )
            break

        # Add user message to both tracking structures
        conversation_history.append({"role": "user", "content": user_input})
        session_log.append({"role": "user", "content": user_input, "stage": stage})

        # ── Call agent ────────────────────────────────────────────────────────
        booking_conflict = detect_booking_hours_conflict(user_input, agent.sop.get("hours", ""))
        if booking_conflict:
            result = {
                "response": booking_conflict["response"],
                "escalate": False,
                "escalate_reason": None,
                "qualification_data": {},
                "_policy_flag": booking_conflict.get("flag"),
            }
        else:
            result = agent.respond(conversation_history, stage, qualification_data, debug=debug)

        bot_response = result.get("response", "I'm sorry, I didn't quite catch that — could you rephrase?")

        # ── Escalation check ──────────────────────────────────────────────────
        if result.get("escalate"):
            reason = result.get("escalate_reason") or "Unspecified"
            print_escalation_alert(reason)
            print_bot(bot_response)

            # Log the escalated turn
            session_log.append({
                "role": "assistant",
                "content": bot_response,
                "stage": stage,
                "escalated": True,
                "escalate_reason": reason,
            })
            conversation_history.append({"role": "assistant", "content": bot_response})

            # Generate summary and exit
            summary = agent.generate_summary(
                conversation_history,
                qualification_data,
                escalated=True,
                escalate_reason=reason,
                debug=debug,
            )
            print_summary_box(summary)
            if debug:
                print_debug_turn(stage, faq_turns, qualification_data, summary)
            save_session_log(session_log, summary, escalated=True)
            print_bot(
                "A member of our team will be in touch with you shortly. "
                "Thank you for your patience. 🌸"
            )
            break

        # ── Normal response ───────────────────────────────────────────────────
        print_bot(bot_response)
        conversation_history.append({"role": "assistant", "content": bot_response})
        session_log.append(
            {"role": "assistant", "content": bot_response, "stage": stage}
        )

        # Merge any new qualification data
        new_qdata = result.get("qualification_data") or {}
        for key, val in new_qdata.items():
            if val and val not in ("Not specified", "Unknown", ""):
                qualification_data[key] = val

        # ── Stage transitions ─────────────────────────────────────────────────
        if stage == "faq":
            if should_count_faq_turn(user_input):
                faq_turns += 1
            if faq_turns >= FAQ_TURNS_BEFORE_QUALIFY:
                stage = "qualify"
                print_stage_transition("Moving to lead qualification…")

        elif stage == "qualify":
            if qualification_complete(qualification_data):
                stage = "done"
                print_stage_transition("Qualification complete!")
                print_bot(
                    "Wonderful! I've noted all your details. 📋\n"
                    "Our team will be in touch to confirm everything with you.\n"
                    "Type 'bye' or 'done' whenever you're ready — "
                    "I'll put together a session summary for you."
                )

        if debug:
            print_debug_turn(stage, faq_turns, qualification_data, result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Closira clinic receptionist agent.")
    parser.add_argument("--debug", action="store_true", help="Show raw model output and turn metadata.")
    args = parser.parse_args()
    main(debug=args.debug)
