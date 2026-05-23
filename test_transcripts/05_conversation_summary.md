# Test Transcript 05 — Full Conversation + Session Summary

**Scenario:** Complete end-to-end session. Customer asks FAQ questions, goes through
qualification, then types 'bye' to trigger the summary.

**Expected behaviour:** Structured summary generated with customer intent, details
collected, SOP gaps identified, and a specific recommended next action.

---

## Full Conversation

**Aria:** Hi there! I'm Aria, your virtual assistant for Bloom Aesthetics Clinic. 🌸
I'm here to help with questions about our services, pricing, and bookings.
What can I help you with today?

**Customer:** Hi, what are your opening hours?

**Aria:** We're open Monday to Saturday, 9am to 7pm. Is there anything else you'd
like to know about our services or how to book?

**Customer:** And how do I cancel if I need to?

**Aria:** We ask for at least 24 hours' notice for any cancellations. You can cancel
via WhatsApp or through our website. Is there anything else I can help you with?

---

**[SYSTEM] Moving to lead qualification…**

**Aria:** I'd love to learn a bit more so we can prepare for your visit!
Which treatment are you most interested in — Botox, Fillers, or would you like
a free consultation first?

**Customer:** I'd like Botox, please.

**Aria:** Great choice! Have you had Botox before, or would this be your first time?

**Customer:** I've had it a couple of times before at a different clinic.

**Aria:** Wonderful — sounds like you know exactly what to expect! Last question:
when are you looking to book — this week, or further ahead?

**Customer:** Sometime next month works best for me.

**Aria:** Perfect, I've noted all your details. 📋
Our team will be in touch to confirm everything with you.
Type 'bye' or 'done' whenever you're ready — I'll put together a session summary for you.

**Customer:** bye

---

## Session Summary (Generated on exit)

```json
{
  "customer_intent": "Book a Botox appointment at Bloom Aesthetics Clinic next month",
  "key_details_collected": {
    "treatment_interest": "Botox",
    "prior_experience": "Yes — experienced, had Botox at a different clinic previously",
    "booking_timeframe": "Next month"
  },
  "sop_gaps": [],
  "escalated": false,
  "escalation_reason": null,
  "recommended_next_action": "Follow up with customer to schedule a Botox appointment for next month. Patient is experienced — no consultation required unless they request one. Confirm pricing (from £200) and availability."
}
```

---

## Terminal Output (Summary Box)

```
════════════════════════════════════════════════════════
  SESSION SUMMARY
════════════════════════════════════════════════════════

Customer Intent:
  Book a Botox appointment at Bloom Aesthetics Clinic next month

Details Collected:
  • Treatment Interest: Botox
  • Prior Experience: Yes — experienced, had Botox at a different clinic previously
  • Booking Timeframe: Next month

SOP Gaps: None — all questions answered from SOP

Escalated: No

Recommended Next Action:
  Follow up with customer to schedule a Botox appointment for next month.
  Patient is experienced — no consultation required unless they request one.
  Confirm pricing (from £200) and availability.

════════════════════════════════════════════════════════
```

---

## Result

✅ **PASS**
- All 4 stages completed successfully (FAQ → Qualify → Done → Summary)
- Summary fields fully populated: intent, details, gaps, next action
- SOP gaps list is empty — all questions were answerable
- Recommended next action is specific and immediately useful to a human agent
- Session log saved to logs/
