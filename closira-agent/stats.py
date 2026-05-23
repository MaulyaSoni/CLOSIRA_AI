"""
stats.py — Closira Admin Stats Dashboard
-----------------------------------------
Reads all session logs and renders an aggregated dashboard in the terminal.

Usage:
  python stats.py
"""
import os
import json
import sys
from collections import Counter
from utils import (
    RESET, BOLD, GREEN, CYAN, YELLOW, RED, MAGENTA, WHITE, DIM, ORANGE,
    classify_escalation, read_session_stats, LOGS_DIR,
)

def load_raw_sessions():
    if not os.path.exists(LOGS_DIR):
        return []
    sessions = []
    for fname in sorted(os.listdir(LOGS_DIR)):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(LOGS_DIR, fname)) as fp:
                    sessions.append(json.load(fp))
            except Exception:
                pass
    return sessions


def render_bar(count: int, total: int, width: int = 20) -> str:
    filled = int((count / total) * width) if total else 0
    return f"{'█' * filled}{'░' * (width - filled)}"


def print_dashboard(sessions: list):
    total = len(sessions)

    if total == 0:
        print(f"\n{YELLOW}  No sessions recorded yet.")
        print(f"  Run  python main.py  to start a session.{RESET}\n")
        return

    escalated       = [s for s in sessions if s.get("escalated")]
    clean           = total - len(escalated)
    esc_rate        = round(len(escalated) / total * 100, 1)

    esc_types = [
        classify_escalation(s.get("summary", {}).get("escalation_reason") or "")
        for s in escalated
    ]
    type_counts = Counter(esc_types)

    all_gaps = []
    for s in sessions:
        all_gaps.extend(s.get("summary", {}).get("sop_gaps", []))
    gap_counts = Counter(all_gaps)

    turn_counts = [
        len([m for m in s.get("conversation", []) if m.get("role") == "user"])
        for s in sessions
    ]
    avg_turns = round(sum(turn_counts) / len(turn_counts), 1) if turn_counts else 0

    # ── Header ────────────────────────────────────────────────────────────────
    print(f"\n{MAGENTA}{BOLD}{'═' * 62}")
    print(f"   CLOSIRA  ·  ADMIN SESSION DASHBOARD")
    print(f"   Client : Bloom Aesthetics Clinic")
    print(f"{'═' * 62}{RESET}")

    # ── Overview ──────────────────────────────────────────────────────────────
    print(f"\n{WHITE}{BOLD}  OVERVIEW{RESET}")
    print(f"  {'Total Sessions':<22} {CYAN}{BOLD}{total}{RESET}")
    print(f"  {'Clean (no escalation)':<22} {GREEN}{clean}{RESET}")
    print(f"  {'Escalated':<22} {RED}{len(escalated)}  ({esc_rate}%){RESET}")
    print(f"  {'Avg Turns / Session':<22} {CYAN}{avg_turns}{RESET}")

    # ── Escalation breakdown ──────────────────────────────────────────────────
    if type_counts:
        print(f"\n{WHITE}{BOLD}  ESCALATION BREAKDOWN{RESET}")
        color_map = {
            "medical":       RED,
            "complaint":     RED,
            "pricing":       YELLOW,
            "human_request": MAGENTA,
            "out_of_scope":  CYAN,
            "general":       WHITE,
        }
        for etype, count in type_counts.most_common():
            col   = color_map.get(etype, WHITE)
            bar   = render_bar(count, len(escalated))
            label = etype.replace("_", " ").title()
            print(f"  {col}{label:<18}{RESET}  {col}{bar}{RESET}  {count}")

    # ── SOP gaps ──────────────────────────────────────────────────────────────
    if gap_counts:
        print(f"\n{WHITE}{BOLD}  TOP SOP GAPS  {DIM}(questions AI couldn't answer){RESET}")
        for i, (gap, count) in enumerate(gap_counts.most_common(5), 1):
            bar = render_bar(count, total)
            print(f"  {YELLOW}{i}.{RESET} {gap[:48]:<48}  {DIM}{count}x{RESET}")
    else:
        print(f"\n  {GREEN}✓  No SOP gaps recorded — all questions answered from SOP{RESET}")

    # ── Recent sessions ───────────────────────────────────────────────────────
    print(f"\n{WHITE}{BOLD}  RECENT SESSIONS  {DIM}(last 5){RESET}")
    print(f"  {DIM}{'Timestamp':<18}  {'Status':<12}  {'Customer Intent'}{RESET}")
    print(f"  {DIM}{'─'*58}{RESET}")
    for s in sessions[-5:]:
        ts     = (s.get("timestamp") or "")[:16].replace("T", " ")
        esc    = f"{RED}ESCALATED  {RESET}" if s.get("escalated") else f"{GREEN}COMPLETE   {RESET}"
        intent = (s.get("summary", {}).get("customer_intent") or "—")[:38]
        print(f"  {DIM}{ts:<18}{RESET}  {esc}  {intent}")

    # ── Log files ─────────────────────────────────────────────────────────────
    json_logs = [f for f in os.listdir(LOGS_DIR) if f.endswith(".json")]
    txt_logs  = [f for f in os.listdir(LOGS_DIR) if f.endswith(".txt")]
    print(f"\n  {DIM}Logs directory: ./{LOGS_DIR}/   "
          f"({len(json_logs)} JSON  ·  {len(txt_logs)} TXT){RESET}")

    print(f"\n{MAGENTA}{BOLD}{'═' * 62}{RESET}\n")


def main():
    print(f"\n{CYAN}{BOLD}Loading session logs from ./{LOGS_DIR}/ …{RESET}")
    sessions = load_raw_sessions()
    print_dashboard(sessions)


if __name__ == "__main__":
    main()
