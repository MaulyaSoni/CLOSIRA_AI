# Test Transcript 02 — Out-of-Scope Question

**Scenario:** Customer asks about parking and disabled access — neither is in the SOP.

**Expected behaviour:** AI acknowledges the gap honestly, does NOT guess or invent information,
and offers to connect the customer with a human team member.

---

**Aria:** Hi there! I'm Aria, your virtual assistant for Bloom Aesthetics Clinic. 🌸
What can I help you with today?

**Customer:** Hi — do you have parking available near the clinic?

**Aria:** That's a great question! Unfortunately, I don't have parking details in my
current information — I wouldn't want to give you anything inaccurate. Your best bet
would be to reach out to our team directly via WhatsApp or through our website at
bloomaesthetics.co.uk and they'll be happy to help. Is there anything else I can assist with?

**Customer:** What about disabled access — is the clinic accessible?

**Aria:** I'm sorry, I don't have accessibility information available either. For accurate
details on this, please contact our team directly — they'll be best placed to advise.
I'll flag this as a useful addition to our FAQs. Can I help you with anything about
our services or booking process?

---

## Agent Internal State (Turn 2)

```json
{
  "response": "I'm sorry, I don't have accessibility information available either...",
  "escalate": false,
  "escalate_reason": null,
  "qualification_data": {}
}
```

> Note: Escalation was not triggered here because the customer was not frustrated —
> they were asking neutral questions. If this were a third unanswered question,
> the ">2 SOP gaps" escalation rule would activate.

---

## Result

✅ **PASS**
- AI did not hallucinate parking or accessibility details
- Acknowledged gap honestly on both occasions
- Directed customer to human team
- Flagged SOP gaps for follow-up
- No escalation triggered (customer tone was neutral)
