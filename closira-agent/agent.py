import os
import json
import time
from groq import Groq


class ClosiraAgent:
    def __init__(self, sop_path: str = None):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found. Add it to your .env file.")

        self.client = Groq(api_key=api_key)
        self.model  = "llama-3.3-70b-versatile"

        # Load SOP — use custom path if provided, else default sop.json
        resolved = sop_path or os.path.join(os.path.dirname(__file__), "sop.json")
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"SOP file not found: {resolved}")
        with open(resolved) as f:
            self.sop = json.load(f)

        self.sop_text = self._format_sop()

    # ── SOP formatting ────────────────────────────────────────────────────────

    def _format_sop(self) -> str:
        s = self.sop
        conditions = "\n   - ".join(s.get("escalate_conditions", []))
        last_slot  = s.get("last_appointment_slot", "6:45pm")
        closed     = ", ".join(s.get("closed_days", ["Sunday"]))
        return (
            f"Business : {s['business_name']}\n"
            f"Hours    : {s['hours']}  (last slot: {last_slot})\n"
            f"Closed   : {closed}\n"
            f"Services :\n"
            f"  - Botox        : {s['services']['botox']}\n"
            f"  - Fillers      : {s['services']['fillers']}\n"
            f"  - Consultation : {s['services']['consultation']}\n"
            f"Booking  : {s['booking']}\n"
            f"Website  : {s.get('website', 'N/A')}\n"
            f"Escalate if:\n   - {conditions}"
        )

    # ── System prompt builder ─────────────────────────────────────────────────

    def _build_system_prompt(self, stage: str, qualification_data: dict) -> str:
        base = f"""You are Aria, a warm and professional AI receptionist for Bloom Aesthetics Clinic.

=== CLINIC SOP — YOUR ONLY SOURCE OF TRUTH ===
{self.sop_text}

=== CRITICAL RULES ===
1. ONLY answer using the SOP above. NEVER invent or guess facts not in the SOP.
2. If a question is not covered, honestly say you don't have that information and offer to connect with a human team member.
3. Be warm, concise, and professional — like a friendly clinic receptionist.
4. If a customer requests an appointment time AFTER {self.sop.get('last_appointment_slot','6:45pm')} or on a closed day, politely inform them of the correct hours.
5. ALWAYS respond in this exact JSON format — raw JSON only, no markdown, no preamble:
{{
  "response": "your message to the customer",
  "escalate": false,
  "escalate_reason": null,
  "qualification_data": {{}}
}}
6. Set "escalate" to true and fill "escalate_reason" when ANY escalation condition is met.
"""
        if stage == "faq":
            base += """
=== STAGE: FAQ ===
Answer questions warmly and accurately from the SOP only. Keep answers to 2-3 sentences.
"""
        elif stage == "qualify":
            collected = json.dumps(qualification_data, indent=2) if qualification_data else "{}"
            base += f"""
=== STAGE: LEAD QUALIFICATION ===
Collect answers to 3 questions, one at a time. Already collected:
{collected}

Ask the next unanswered question in this order:
1. "Which treatment are you most interested in — Botox, Fillers, or a free consultation first?"
2. "Have you had aesthetic treatments before, or would this be your first time?"
3. "When are you looking to book — this week, or a bit further ahead?"

Acknowledge each answer warmly before asking the next.
Fill "qualification_data" with collected answers:
{{
  "treatment_interest": "Botox / Fillers / Consultation / Not specified",
  "prior_experience"  : "Yes / No / Not specified",
  "booking_timeframe" : "This week / Next week / Next month / Further ahead / Not specified"
}}
"""
        elif stage == "done":
            base += """
=== STAGE: WRAP-UP ===
Qualification is complete. Confirm details are noted and the team will follow up.
Prompt the customer to type 'bye' or 'done' to end the session.
"""
        return base

    # ── Core respond ─────────────────────────────────────────────────────────

    def respond(self, conversation_history: list, stage: str, qualification_data: dict) -> dict:
        system_prompt = self._build_system_prompt(stage, qualification_data)
        return self._call_with_retry(
            messages=[{"role": "system", "content": system_prompt}, *conversation_history],
            max_tokens=500,
            temperature=0.3,
        )

    # ── Summary generation ────────────────────────────────────────────────────

    def generate_summary(
        self,
        conversation_history: list,
        qualification_data: dict,
        escalated: bool = False,
        escalate_reason: str = None,
    ) -> dict:
        prompt = f"""You are a session summarizer for Bloom Aesthetics Clinic.
Review the conversation and return ONLY raw JSON — no markdown, no preamble:
{{
  "customer_intent"         : "One sentence describing what the customer wanted",
  "key_details_collected"   : {{
    "treatment_interest" : "...",
    "prior_experience"   : "...",
    "booking_timeframe"  : "..."
  }},
  "sop_gaps"                : ["Questions the AI couldn't answer from SOP, or empty list"],
  "escalated"               : {str(escalated).lower()},
  "escalation_reason"       : {json.dumps(escalate_reason)},
  "recommended_next_action" : "Specific action the clinic/agent should take"
}}

Qualification data collected so far:
{json.dumps(qualification_data, indent=2)}
"""
        result = self._call_with_retry(
            messages=[
                {"role": "system", "content": prompt},
                *conversation_history,
                {"role": "user", "content": "Generate the session summary now."},
            ],
            max_tokens=600,
            temperature=0.2,
        )
        # Ensure required summary keys exist
        result.setdefault("customer_intent", "Unable to determine")
        result.setdefault("key_details_collected", qualification_data)
        result.setdefault("sop_gaps", [])
        result.setdefault("escalated", escalated)
        result.setdefault("escalation_reason", escalate_reason)
        result.setdefault("recommended_next_action", "Review session log manually")
        return result

    # ── API call with retry ───────────────────────────────────────────────────

    def _call_with_retry(self, messages: list, max_tokens: int, temperature: float, retries: int = 2) -> dict:
        last_error = None
        for attempt in range(retries + 1):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                raw = completion.choices[0].message.content.strip()
                return self._parse_response(raw)
            except Exception as e:
                last_error = e
                if attempt < retries:
                    time.sleep(1.5 ** attempt)   # 1.5s, 2.25s back-off
        return self._fallback(str(last_error))

    # ── JSON parsing ──────────────────────────────────────────────────────────

    def _parse_response(self, raw: str) -> dict:
        import re
        cleaned = raw.strip()

        # Strip markdown fences
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        # Direct parse
        try:
            return self._validate(json.loads(cleaned))
        except json.JSONDecodeError:
            pass

        # Extract embedded JSON block (handles mixed text + JSON output)
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            try:
                return self._validate(json.loads(match.group()))
            except json.JSONDecodeError:
                pass

        # Last resort — treat raw as plain response text
        return self._validate({"response": cleaned})

    def _validate(self, data: dict) -> dict:
        data.setdefault("response", "")
        data.setdefault("escalate", False)
        data.setdefault("escalate_reason", None)
        data.setdefault("qualification_data", {})
        return data

    def _fallback(self, error: str) -> dict:
        return {
            "response": (
                "I'm sorry, I'm experiencing a brief technical issue. "
                "Please try again or contact us directly via WhatsApp."
            ),
            "escalate": False,
            "escalate_reason": None,
            "qualification_data": {},
            "_error": error,
        }
