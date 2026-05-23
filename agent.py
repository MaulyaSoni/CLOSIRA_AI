import os
import json
import re
from groq import Groq


class ClosiraAgent:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found. Please add it to your .env file."
            )

        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

        # Load SOP from file
        sop_path = os.path.join(os.path.dirname(__file__), "sop.json")
        with open(sop_path, "r") as f:
            self.sop = json.load(f)

        self.sop_text = self._format_sop()

    # ── SOP Formatting ────────────────────────────────────────────────────────

    def _format_sop(self):
        s = self.sop
        conditions = "\n   - ".join(s["escalate_conditions"])
        return (
            f"Business: {s['business_name']}\n"
            f"Hours: {s['hours']}\n"
            f"Services:\n"
            f"  - Botox: {s['services']['botox']}\n"
            f"  - Fillers: {s['services']['fillers']}\n"
            f"  - Consultation: {s['services']['consultation']}\n"
            f"Booking: {s['booking']}\n"
            f"Website: {s['website']}\n"
            f"Escalate if:\n   - {conditions}"
        )

    # ── System Prompts ────────────────────────────────────────────────────────

    def _build_system_prompt(self, stage: str, qualification_data: dict) -> str:
        base = f"""You are Aria, a warm and professional AI receptionist for Bloom Aesthetics Clinic.

=== CLINIC SOP — YOUR ONLY SOURCE OF TRUTH ===
{self.sop_text}

=== CRITICAL RULES ===
1. ONLY answer using the SOP above. NEVER invent or guess facts not present in the SOP.
2. If a question is not covered by the SOP, honestly say you do not have that information and offer to connect the customer with a human team member.
3. Be warm, concise, and professional — like a friendly clinic receptionist.
4. ALWAYS respond in this exact JSON format. No markdown. No preamble. Raw JSON only:
{{
  "response": "your message to the customer",
  "escalate": false,
  "escalate_reason": null,
  "qualification_data": {{}}
}}
5. Set "escalate" to true and fill "escalate_reason" if ANY of these conditions are met:
   - Customer makes a complaint or expresses dissatisfaction
   - Medical question or health concern is raised
   - Customer attempts to negotiate pricing
   - More than 2 questions you cannot answer from the SOP
   - Customer explicitly asks for a human agent
   - Customer appears angry, frustrated, or distressed
"""

        if stage == "faq":
            base += """
=== CURRENT STAGE: FAQ ===
Answer the customer's questions warmly and accurately using the SOP only.
Keep answers brief — 2 to 3 sentences maximum.
Do not volunteer information not asked for.
"""

        elif stage == "qualify":
            collected = json.dumps(qualification_data, indent=2) if qualification_data else "{}"
            base += f"""
=== CURRENT STAGE: LEAD QUALIFICATION ===
Your goal is to gently collect answers to 3 qualification questions, one at a time.

Already collected:
{collected}

Ask whichever questions below have NOT been answered yet, strictly in this order:
1. "Which treatment are you most interested in — Botox, Fillers, or would you like a free consultation first?"
2. "Have you had aesthetic treatments before, or would this be your first time?"
3. "When are you looking to book — this week, or a bit further ahead?"

After each customer reply, acknowledge their answer warmly, then ask the next unanswered question.
Populate "qualification_data" with what the customer tells you:
{{
  "treatment_interest": "Botox / Fillers / Consultation / Not specified",
  "prior_experience": "Yes / No / Not specified",
  "booking_timeframe": "This week / Next week / Next month / Further ahead / Not specified"
}}
Only include keys for questions that have been answered.
"""

        elif stage == "done":
            base += """
=== CURRENT STAGE: WRAP-UP ===
All qualification questions have been answered. Let the customer know their details have been noted
and the team will be in touch. Encourage them to type 'bye' or 'done' to end the session.
"""

        return base

    # ── Core Respond Method ───────────────────────────────────────────────────

    def respond(
        self,
        conversation_history: list,
        stage: str,
        qualification_data: dict,
        debug: bool = False,
    ) -> dict:
        system_prompt = self._build_system_prompt(stage, qualification_data)

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *conversation_history,
                ],
                temperature=0.3,
                max_tokens=500,
            )

            raw = completion.choices[0].message.content.strip()
            result = self._parse_response(raw)
            if debug:
                result["_raw_output"] = raw
                result["_usage"] = self._serialize_usage(getattr(completion, "usage", None))
            return result

        except Exception as e:
            return self._fallback_response(str(e))

    # ── Summary Generation ────────────────────────────────────────────────────

    def generate_summary(
        self,
        conversation_history: list,
        qualification_data: dict,
        escalated: bool = False,
        escalate_reason: str = None,
        debug: bool = False,
    ) -> dict:
        summary_prompt = f"""You are a session summarizer for Bloom Aesthetics Clinic.

Review the conversation and generate a structured summary.
Respond ONLY with raw JSON — no markdown, no preamble:
{{
  "customer_intent": "One sentence describing what the customer wanted",
  "key_details_collected": {{
    "treatment_interest": "...",
    "prior_experience": "...",
    "booking_timeframe": "..."
  }},
  "sop_gaps": ["List questions the AI could not answer from the SOP, or empty list if none"],
  "escalated": {str(escalated).lower()},
  "escalation_reason": {json.dumps(escalate_reason)},
  "recommended_next_action": "Specific action the human agent or clinic should take next"
}}

Qualification data already collected:
{json.dumps(qualification_data, indent=2)}
"""

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": summary_prompt},
                    *conversation_history,
                    {"role": "user", "content": "Generate the session summary now."},
                ],
                temperature=0.2,
                max_tokens=600,
            )

            raw = completion.choices[0].message.content.strip()
            result = self._parse_response(raw)
            if debug:
                result["_raw_output"] = raw
                result["_usage"] = self._serialize_usage(getattr(completion, "usage", None))
            return result

        except Exception:
            return {
                "customer_intent": "Unable to determine — review conversation log",
                "key_details_collected": qualification_data,
                "sop_gaps": [],
                "escalated": escalated,
                "escalation_reason": escalate_reason,
                "recommended_next_action": "Review session log manually",
            }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _parse_response(self, raw: str) -> dict:
        """Parse JSON from model output, stripping markdown fences if present."""
        candidates = []
        cleaned = self._strip_code_fences(raw.strip())
        if cleaned:
            candidates.append(cleaned)

        extracted = self._extract_json_object(cleaned)
        if extracted and extracted not in candidates:
            candidates.insert(0, extracted)

        for candidate in candidates:
            try:
                result = json.loads(candidate)
                if not isinstance(result, dict):
                    continue

                response_text = result.get("response", "")
                result["response"] = self._clean_response_text(response_text)
                result.setdefault("escalate", False)
                result.setdefault("escalate_reason", None)
                result.setdefault("qualification_data", {})
                return result
            except json.JSONDecodeError:
                continue

        return {
            "response": self._clean_response_text(raw),
            "escalate": False,
            "escalate_reason": None,
            "qualification_data": {},
        }

    def _fallback_response(self, error: str) -> dict:
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

    def _strip_code_fences(self, text: str) -> str:
        if text.startswith("```"):
            parts = text.split("```", 2)
            if len(parts) >= 2:
                text = parts[1]
                if text.lstrip().startswith("json"):
                    text = re.sub(r"^\s*json\s*", "", text, flags=re.IGNORECASE)
        return text.strip()

    def _extract_json_object(self, text: str) -> str:
        start_index = None
        depth = 0
        in_string = False
        escaped = False

        for index, char in enumerate(text):
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue

            if char == "{":
                if depth == 0:
                    start_index = index
                depth += 1
            elif char == "}" and depth:
                depth -= 1
                if depth == 0 and start_index is not None:
                    return text[start_index : index + 1].strip()

        return text.strip()

    def _clean_response_text(self, value) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            return str(value)
        return self._strip_code_fences(value.strip())

    def _serialize_usage(self, usage):
        if usage is None:
            return None

        data = {}
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = getattr(usage, key, None)
            if value is not None:
                data[key] = value

        return data or None
