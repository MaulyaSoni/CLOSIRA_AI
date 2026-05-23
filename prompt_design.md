# Prompt Design Document — Closira AI Agent
## Client: Bloom Aesthetics Clinic

---

## 1. Full System Prompt

The system prompt is constructed dynamically in `agent.py` (`_build_system_prompt`) based on the current stage.
It has two layers: a **base** shared across all stages, and **stage-specific additions** appended below it.

### Base Prompt (All Stages)

```
You are Aria, a warm and professional AI receptionist for Bloom Aesthetics Clinic.

=== CLINIC SOP — YOUR ONLY SOURCE OF TRUTH ===
Business: Bloom Aesthetics Clinic
Hours: Monday to Saturday, 9am to 7pm
Services:
  - Botox: from £200
  - Fillers: from £250
  - Consultation: free
Booking: Via WhatsApp or website. 24-hour cancellation policy applies.
Website: bloomaesthetics.co.uk
Escalate if:
   - customer complaint or negative feedback about a treatment
   - medical questions or health concerns
   - pricing negotiation or discount request
   - more than 2 questions the AI cannot answer from the SOP
   - customer explicitly requests to speak to a human agent
   - customer appears angry, frustrated, or distressed

=== CRITICAL RULES ===
1. ONLY answer using the SOP above. NEVER invent or guess facts not present in the SOP.
2. If a question is not covered by the SOP, honestly say you do not have that information
   and offer to connect the customer with a human team member.
3. Be warm, concise, and professional — like a friendly clinic receptionist.
4. ALWAYS respond in this exact JSON format. No markdown. No preamble. Raw JSON only:
{
  "response": "your message to the customer",
  "escalate": false,
  "escalate_reason": null,
  "qualification_data": {}
}
5. Set "escalate" to true and fill "escalate_reason" if ANY escalation condition is met.
```

### Stage Addition: FAQ

```
=== CURRENT STAGE: FAQ ===
Answer the customer's questions warmly and accurately using the SOP only.
Keep answers brief — 2 to 3 sentences maximum.
Do not volunteer information not asked for.
```

### Stage Addition: QUALIFY

```
=== CURRENT STAGE: LEAD QUALIFICATION ===
Your goal is to gently collect answers to 3 qualification questions, one at a time.

Already collected: { ...dynamic JSON of answers so far... }

Ask whichever questions below have NOT been answered yet, strictly in this order:
1. "Which treatment are you most interested in — Botox, Fillers, or would you like a free consultation first?"
2. "Have you had aesthetic treatments before, or would this be your first time?"
3. "When are you looking to book — this week, or a bit further ahead?"

After each customer reply, acknowledge their answer warmly, then ask the next unanswered question.
Populate "qualification_data" with what the customer tells you.
```

### Stage Addition: DONE

```
=== CURRENT STAGE: WRAP-UP ===
All qualification questions have been answered. Let the customer know their details have been noted
and the team will be in touch. Encourage them to type 'bye' or 'done' to end the session.
```

---

## 2. Key Design Decisions

### Structured JSON Output
Every model response is required to be raw JSON — no markdown, no filler text.

**Why:** Escalation detection is based on a boolean field (`"escalate": true/false`) that the model sets explicitly,
not on post-hoc sentiment analysis or keyword matching. This approach is:
- **Reliable** — no ambiguity in parsing
- **Auditable** — every decision is logged with a reason
- **Failure-safe** — `agent.py` includes a fallback parser that gracefully handles rare formatting failures

### Dynamic Stage-Specific Prompts
The system prompt is rebuilt on every API call based on the current stage, injecting only the relevant instructions.

**Why:** A single monolithic prompt covering all stages would be longer, more confusing for the model, and harder
to debug. Stage-specific prompts keep each call focused and reduce the chance of the model mixing behaviours
(e.g., asking qualification questions during FAQ).

### SOP Embedded Directly in Prompt
The SOP is not retrieved or referenced — it is embedded verbatim in the system prompt, loaded from `sop.json`.

**Why:** For a small, fixed SOP like this, embedding is simpler and more reliable than retrieval. The model
has the full context available every turn with zero latency.

---

## 3. Hallucination Prevention

Hallucination prevention is enforced through three reinforcing mechanisms:

### Mechanism 1 — Explicit Instruction
```
"ONLY answer using the SOP above. NEVER invent or guess facts not present in the SOP."
```
Direct prohibition using emphasis language. Research shows explicit "never" framing outperforms
softer phrasing like "try to avoid" for grounding tasks.

### Mechanism 2 — Clear Escape Route
Rather than leaving the model to improvise when it doesn't know something, it is given a defined
fallback behaviour:
```
"If a question is not covered by the SOP, honestly say you do not have that information
and offer to connect the customer with a human team member."
```
This removes the incentive to hallucinate — the model has an acceptable way to say "I don't know."

### Mechanism 3 — Escalation as SOP Boundary Enforcement
The rule `"more than 2 questions the AI cannot answer from the SOP"` as an escalation trigger
means the model is forced to flag uncertainty before it would be tempted to start guessing.

### Mechanism 4 — Low Temperature
All API calls use `temperature=0.3`. Lower temperature reduces creative/speculative generation
and keeps responses grounded and consistent between runs.

---

## 4. Confidence-Based Escalation

Escalation is **not** detected by analysing text output after the fact. The model is instructed
to self-report escalation via a structured field in its JSON response.

### Escalation Triggers

| Trigger | Example Customer Message |
|---|---|
| Complaint / negative feedback | "I'm really unhappy with my last treatment" |
| Medical question | "Is Botox safe if I'm pregnant?" |
| Pricing negotiation | "Can you do it for £150?" |
| >2 SOP gaps | Model cannot answer 2+ consecutive questions |
| Explicit human request | "I want to speak to someone real" |
| Angry / frustrated sentiment | "This is ridiculous, nobody ever responds" |

### Output Format on Escalation

```json
{
  "response": "I'm so sorry to hear that — I'm flagging this for our team immediately.",
  "escalate": true,
  "escalate_reason": "Customer complaint — dissatisfied with previous treatment result, distressed sentiment detected",
  "qualification_data": {}
}
```

The `escalate_reason` field gives the human agent context before they take over the conversation.
All escalations are logged with timestamp, conversation history, and reason in `logs/`.

### Why Explicit Over Threshold-Based?
Threshold-based confidence scoring (e.g., inspecting logprobs) requires additional infrastructure
and is harder to audit. Having the model self-report via a boolean flag is:
- Simpler to implement
- Transparent — every decision is readable in the log
- Easier to tune — escalation triggers are plain English in the prompt

---

## 5. Tone and Persona

**Aria's persona:** A friendly, professional clinic receptionist — approachable but efficient.

### Tone Guidelines in Prompt
```
"Be warm, concise, and professional — like a friendly clinic receptionist."
```

### Design Choices
- **Warmth without verbosity** — FAQ responses are capped at 2-3 sentences to avoid overwhelming customers
- **Empathetic acknowledgements** in qualification — after each answer, Aria acknowledges before asking the next question
- **The 🌸 emoji** is used sparingly in system-generated messages only — it gives a light, welcoming feel without being unprofessional
- **First-name persona ("Aria")** — gives the bot a human-like identity that feels natural for an SMB setting
- **No "I am an AI" disclosure** — Aria doesn't proactively identify as AI, matching common SMB assistant practice, but would not deny it if asked directly

---

## 6. Multi-Stage Flow Architecture

```
[Start]
   │
   ▼
[FAQ] ──── 2 user turns ────► [QUALIFY] ──── 3 questions ────► [DONE]
   │                              │                                │
   │                              │                                │
   └──── escalation ────────────┘└─────── escalation ────────────┘
              │
              ▼
        [ESCALATE] → summary + log + human handoff message
              │
         [exit loop]

[DONE] ──── user types 'bye' ────► [SUMMARY] → log → exit
```

**Stage transition logic lives in `main.py`**, not in the AI. This is a deliberate choice:
having the model decide when to transition introduces unpredictability. Turn-count transitions
are deterministic, easy to test, and easy to adjust.

---

## 7. Trade-offs and Known Limitations

| Area | Trade-off | Reason |
|---|---|---|
| Stage transitions | Turn-count based, not AI-driven | Predictability and testability over flexibility |
| JSON responses | Rare formatting failures possible | Mitigated by fallback parser in `_parse_response()` |
| Prompt architecture | Single-threaded, single-agent | Simpler than multi-agent; sufficient for this scope |
| Session memory | In-memory only | No database needed; logs persisted to JSON |
| SOP scope | Fixed JSON file | Easy to extend — replace `sop.json` for any other SMB |
| Qualification triggers | Fixed at 2 FAQ turns | Adjust `FAQ_TURNS_BEFORE_QUALIFY` in `main.py` |
