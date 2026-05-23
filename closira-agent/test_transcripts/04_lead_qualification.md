# Test Transcript 04 — Lead Qualification

**Scenario:** Customer has completed the FAQ stage and is now being qualified through
3 structured clinic-specific questions.

**Expected behaviour:** AI asks one question at a time, acknowledges each answer warmly,
collects and stores all three qualification fields.

---

## FAQ Stage (Turns 1–2)

**Aria:** Hi there! I'm Aria, your virtual assistant for Bloom Aesthetics Clinic. 🌸
What can I help you with today?

**Customer:** Hi, I'm thinking about getting some work done. What fillers do you offer?

**Aria:** We offer filler treatments starting from £250. We also provide a free
consultation where our specialists can recommend the right filler type and placement
for your goals. Would you like to know how to book?

**Customer:** Yes, that sounds great actually.

---

## Qualify Stage (Questions 1–3)

**[SYSTEM] Moving to lead qualification…**

**Aria:** I'd love to learn a little more so we can prepare for your visit!
Which treatment are you most interested in — Botox, Fillers, or would you like
a free consultation first?

**Customer:** Fillers — specifically lip fillers.

**Agent internal state:**
```json
{
  "qualification_data": { "treatment_interest": "Fillers (lip fillers)" }
}
```

**Aria:** Lovely choice — lip fillers are one of our most popular treatments!
Have you had aesthetic treatments before, or would this be your first time?

**Customer:** It would be my first time, I'm a bit nervous to be honest.

**Agent internal state:**
```json
{
  "qualification_data": {
    "treatment_interest": "Fillers (lip fillers)",
    "prior_experience": "No — first time"
  }
}
```

**Aria:** That's completely understandable — first-time nerves are very normal!
Our team are incredibly experienced and will walk you through every step before
anything happens. One last question: when are you looking to book — this week,
or a bit further ahead?

**Customer:** Probably within the next two weeks.

**Agent internal state:**
```json
{
  "qualification_data": {
    "treatment_interest": "Fillers (lip fillers)",
    "prior_experience": "No — first time",
    "booking_timeframe": "Next two weeks"
  }
}
```

---

## Wrap-Up

**[SYSTEM] Qualification complete!**

**Aria:** Wonderful! I've noted all your details. 📋
Our team will be in touch to confirm everything with you.
Type 'bye' or 'done' whenever you're ready — I'll put together a session summary for you.

**Customer:** done

---

## Final Qualification Data

```json
{
  "treatment_interest": "Fillers (lip fillers)",
  "prior_experience": "No — first time",
  "booking_timeframe": "Next two weeks"
}
```

---

## Result

✅ **PASS**
- All 3 questions asked strictly in order
- Each answer warmly acknowledged before the next question
- First-timer nervousness handled empathetically
- All qualification fields populated correctly
- No information invented beyond SOP scope
