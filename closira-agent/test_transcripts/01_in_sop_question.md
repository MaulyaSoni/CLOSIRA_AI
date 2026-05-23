# Test Transcript 01 — In-SOP Question

**Scenario:** Customer asks about Botox pricing — information that is directly in the SOP.

**Expected behaviour:** AI answers accurately from SOP only, no hallucination, no escalation.

---

**Aria:** Hi there! I'm Aria, your virtual assistant for Bloom Aesthetics Clinic. 🌸
I'm here to help with questions about our services, pricing, and bookings.
What can I help you with today?

**Customer:** Hi, what are your Botox prices?

**Aria:** Our Botox treatments start from £200. If you'd like to find out more about
what's included or explore the right option for you, I'd recommend starting with a
free consultation — it's a great way to talk through your goals with one of our specialists.
Shall I tell you how to book one?

**Customer:** And are consultations actually free?

**Aria:** Yes, absolutely! Consultations at Bloom Aesthetics Clinic are completely
free of charge. You can book one via WhatsApp or our website, any time during our
opening hours — Monday to Saturday, 9am to 7pm. 😊

---

## Agent Internal State

```json
{
  "response": "Yes, absolutely! Consultations at Bloom Aesthetics Clinic are completely free...",
  "escalate": false,
  "escalate_reason": null,
  "qualification_data": {}
}
```

---

## Result

✅ **PASS**
- Both questions answered directly from SOP
- No information invented or extrapolated
- Escalation not triggered
- Tone warm and concise (under 3 sentences per reply)
