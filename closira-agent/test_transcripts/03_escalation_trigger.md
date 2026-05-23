# Test Transcript 03 — Escalation Trigger

**Scenario:** Customer expresses frustration and makes a complaint about a previous treatment.

**Expected behaviour:** AI detects complaint + distressed sentiment on the first message,
sets escalate=true, hands off immediately with reason logged.

---

**Aria:** Hi there! I'm Aria, your virtual assistant for Bloom Aesthetics Clinic. 🌸
What can I help you with today?

**Customer:** I had fillers done at your clinic last month and my face looks completely
uneven. I'm really upset about this and I want someone to sort it out immediately.

---

**[SYSTEM]**
```
⚠️  ESCALATION TRIGGERED
────────────────────────────────────────
Reason: Customer complaint — dissatisfied with filler result.
        Medical concern (asymmetry post-treatment) and distressed
        sentiment detected.
────────────────────────────────────────
```

**Aria:** I'm so sorry to hear you're experiencing this — that must be really upsetting
and I completely understand your frustration. This is something our clinical team needs
to address directly and urgently. I'm flagging this conversation for immediate attention
right now, and a member of our team will be in contact with you as soon as possible.
Thank you so much for letting us know.

---

## Agent Internal State

```json
{
  "response": "I'm so sorry to hear you're experiencing this...",
  "escalate": true,
  "escalate_reason": "Customer complaint — dissatisfied with filler result. Medical concern (asymmetry post-treatment) and distressed sentiment detected.",
  "qualification_data": {}
}
```

---

## Session Log (Saved to logs/)

```json
{
  "timestamp": "2025-01-15T14:32:11.842Z",
  "escalated": true,
  "conversation": [
    {
      "role": "user",
      "content": "I had fillers done at your clinic last month...",
      "stage": "faq",
      "escalated": true,
      "escalate_reason": "Customer complaint — dissatisfied with filler result. Medical concern and distressed sentiment detected."
    }
  ],
  "summary": {
    "customer_intent": "Resolve an adverse outcome from a filler treatment",
    "key_details_collected": {},
    "sop_gaps": [],
    "escalated": true,
    "escalation_reason": "Customer complaint — dissatisfied with filler result. Medical concern and distressed sentiment detected.",
    "recommended_next_action": "Contact customer immediately. Clinical review of filler procedure required. Prioritise same-day callback."
  }
}
```

---

## Result

✅ **PASS**
- Escalation triggered on first customer message
- Three triggers detected simultaneously: complaint, medical concern, distressed sentiment
- Escalation reason is specific and actionable for human agent
- Session log saved with full context
- AI response was empathetic and did not attempt to resolve the clinical issue itself
