# IR Deck Audit: v13 → v14

**Purpose**: Slide-by-slide audit of IR Deck v13 against NARRATIVE.md (six beats, vocabulary rules, anti-patterns). This document is the edit spec for producing v14.

**Date**: 2026-03-01

---

## Executive Summary

The v13 deck has strong content — the ClawdBot origin story, compounding loop diagram, moat argument, and before/after demo are all keepers. But three structural problems prevent it from landing with full force:

1. **The product appears too late.** The product screenshot (slide 13) comes after moat, architecture, positioning, and market. Per NARRATIVE.md, "Meet the Product" is Beat 3 — it should land immediately after proof of demand.

2. **TP is undersold.** "Thinking Partner" appears in isolation repeatedly (slides 5, 6, 13) instead of "TP, your autonomous agent." The four-pillar footer on slide 13 presents TP as one feature among four, violating the anti-pattern of feature-list presentation and the IC Analysis finding that "TP is undersold as Day 1 hero."

3. **Agent framing is inconsistent.** The problem slides say "AI tool" when they should say "AI agent" — we're positioning against the agent wave, not the generic AI landscape. The old two-path separation (Thinking Partner vs. Deliverable Engine) persists when ADR-080 established "one agent, two modes."

---

## Slide-by-Slide Audit

### Slide 1 — Title
**Current**: "yarnnn — AI that works autonomously — and gets smarter the longer you use it"
**Beat**: Preamble (sets up the deck)
**Verdict**: ✅ KEEP with minor edit

The one-liner is strong and matches GTM_POSITIONING.md. One adjustment: the word "agent" doesn't appear anywhere on the title slide. For a deck entering a market where "agent" is the category keyword, this is a missed positioning opportunity.

**Recommended change**: Subtitle becomes: "Your autonomous AI agent — it connects to your tools, learns your world, and works while you don't." This introduces the agent category claim on slide 1.

---

### Slide 2 — "I use AI every day. Every day, it forgets everything."
**Current**: First-person visceral problem statement. "My clients. My projects. How I like things done. Gone every session." → "I'm the memory. I'm the context. The AI is just the typist." → "What if AI could actually work for me — not just with me?"
**Beat**: Beat 1 (The Problem — Visceral)
**Verdict**: ✅ KEEP as-is

This is the strongest slide in the deck. First-person, emotionally resonant, universally recognized. The punchline "I'm the memory. I'm the context. The AI is just the typist." is perfect. The bridge question to solution is exactly right.

**No changes needed.**

---

### Slide 3 — "Every AI tool forgets. None of them work autonomously."
**Current**: Structured problem with four failure modes (Stateless by design / You are the context / Assistance not autonomy / Generic agents). Bottom callout: "The gap no one has filled: No product combines persistent cross-platform context WITH autonomous output."
**Beat**: Beat 1 (The Problem — Structured)
**Verdict**: ⚠️ REWORD — vocabulary alignment

Content is right but vocabulary is off. Per NARRATIVE.md, we position against the *agent* landscape, not the "AI tool" landscape.

**Recommended changes**:
- Title: "Every AI tool forgets" → **"Every AI agent disappoints. Here's why."**
- Row 4 "Generic agents" is good — keep
- The gap statement is excellent — keep verbatim
- Consider: is having two problem slides (2 + 3) worth the real estate? The visceral slide (2) does the work. Slide 3 could be compressed into slide 2's lower half, freeing a slide for product demo. **Decision needed.**

---

### Slide 4 — "ClawdBot proved people want this."
**Current**: 17,830 GitHub stars in 24 hours / fastest single-day growth / testimonial / "But 95% of people can't use it" with three barriers.
**Beat**: Beat 2 (Proof of Demand)
**Verdict**: ✅ KEEP as-is

This is the second strongest slide. The demand → barrier → opening structure is exactly what NARRATIVE.md Beat 2 prescribes. The "but 95% can't use it" is the perfect bridge to the product.

**No changes needed.** This slide already maps perfectly to the narrative.

---

### Slide 5 — "yarnnn: Autonomous AI powered by your accumulated work context"
**Current**: Day 1 / Day 30 / Day 90 cards showing "Thinking Partner" → "Autonomous Deliverables" → "Compounding Moat". Bottom: "Connect → Accumulate → Automate → Supervise" + deliverable examples list.
**Beat**: Currently trying to be Beat 3 + Beat 4 + Beat 5 simultaneously
**Verdict**: 🔴 RESTRUCTURE — this slide does too much

This is the slide that needs the most work. It's trying to introduce the product, explain the compounding thesis, AND preview the moat — all in one frame. The result is that none of these land with force.

**Problems**:
- "Thinking Partner" appears in isolation — violates vocabulary rule ("TP, your autonomous agent")
- Day 1/30/90 timeline treats TP as one feature among three, not as the primary product identity
- "Deliverable Engine" as a separate concept contradicts ADR-080 (one agent, two modes)
- The deliverable examples list at bottom is feature-list presentation (anti-pattern)

**Recommended restructure**: Split into two slides:
- **New Slide 5**: "Meet TP — your autonomous AI agent." Hero product introduction. TP is the product. It already knows your work. It produces deliverables on schedule. It gets smarter every cycle. You supervise. This is Beat 3 — pure product identity.
- The compounding timeline (Day 1/30/90) moves to or near the Insight slide (Beat 4) where it belongs — it explains *why* this works, not *what* the product is.

---

### Slide 6 — "Your Thinking Partner knows your context from the start."
**Current**: Before/after comparison — ChatGPT (5 min explaining, generic output) vs. TP after first sync (5 seconds, contextual output from real data).
**Beat**: Beat 3 (Meet the Product — demonstration)
**Verdict**: ⚠️ REWORD title + reposition

The before/after content is gold — it viscerally demonstrates the value difference. But the framing has issues:

**Problems**:
- Title says "Your Thinking Partner" — should be "TP, your autonomous agent"
- Labels: "Without Yarn (ChatGPT)" positions against ChatGPT directly — NARRATIVE.md anti-pattern: "'Better ChatGPT' positioning"
- The comparison inadvertently frames TP as a chatbot (just a faster chatbot) rather than as an agent that works autonomously

**Recommended changes**:
- Title: **"TP already knows your work."** (matches vocabulary rule: "Already knows your work" instead of passive "context-aware")
- Left label: "Without Yarn (ChatGPT)" → **"Without context"** or **"Any AI today"** (positions against the category gap, not one product)
- Right label: "With Yarn TP (after first sync)" → **"With TP (after first sync)"**
- Bottom line about Day 90 is good — keep

---

### Slide 7 — "Context is what makes autonomy meaningful."
**Current**: The Insight. Compounding loop diagram (Connect → Accumulate → Produce → Learn → Context Compounds). "Your AI after 90 days is incomparably better than day one. That's the moat."
**Beat**: Beat 4 (The Insight — Thesis as Revelation)
**Verdict**: ✅ KEEP with one small edit

This is perfectly placed and perfectly worded. It matches NARRATIVE.md Beat 4 almost verbatim. The compounding loop diagram is a visual anchor that should persist across all surfaces.

**One suggested edit**: The closing line "That's the moat" slightly steps on Beat 5 (which is the moat slide). Consider: "That's the compounding advantage." — let Beat 5 own the word "moat."

---

### Slide 8 — "Accumulated context creates real switching costs."
**Current**: The Moat. Five defensibility bullets + three-column incumbent comparison (ChatGPT/Claude, Agent startups, Workspace AI).
**Beat**: Beat 5 (The Moat — Defensibility)
**Verdict**: ✅ KEEP with minor tightening

Well-aligned with NARRATIVE.md Beat 5. The incumbent comparison is the right content for this position. Two items to consider:

- Bullet 4 ("Content retained indefinitely with provenance tracking across all platforms") is getting into architecture language. Simplify: **"All content retained with full provenance — nothing is forgotten."**
- Bullet 5 ("User edits and feedback train memory extraction") is technical. Simplify: **"Your edits teach the system — context improves as a byproduct of normal use."**

---

### Slide 9 — "Four-layer intelligence model."
**Current**: Under the Hood. Architecture diagram with Memory Layer (user_context), Activity Layer (activity_log), Context Layer (platform_content), Work Layer (deliverables). "72 Architecture Decision Records document every design choice."
**Beat**: Beat 5 (The Moat — Architecture as defensibility)
**Verdict**: ⚠️ SIMPLIFY or MERGE with slide 8

Per NARRATIVE.md: "Architecture appears here — not in the product introduction — because its role is to answer the defensibility question, not to describe the product experience." The placement is correct. But the level of technical detail (table names like `user_context`, `activity_log`, `platform_content`, `pgvector`) is too much for a general audience deck.

**Two options**:
- **Option A (Recommended)**: Simplify the diagram. Keep the four layers but remove table names and technical tags. The four layers become: "What it knows about you / What it's done / What's in your platforms / What it's produced." Add the 72+ ADRs and "80+" claim as proof of engineering rigor. This keeps the slide as a standalone.
- **Option B**: Merge key points into slide 8 (moat) and remove this as a standalone slide. The freed slide can be used for the product demo that's currently too late.

---

### Slide 10 — "Not another chatbot. Not another agent framework."
**Current**: Positioning comparison table — ChatGPT/Claude vs. Agent Startups vs. Workspace AI vs. yarnnn. Five rows: Persistent context, Cross-platform sync, Autonomous output, Improves with tenure, Context-aware agent. Bottom: "The only product that combines persistent context accumulation with autonomous output."
**Beat**: Beat 5 (The Moat — Competitive positioning)
**Verdict**: ⚠️ REWORD + REPOSITION

The headline is excellent. The comparison table is useful but has two issues:

1. **Row labels are feature-centric, not experience-centric.** Per vocabulary rules, translate: "Persistent context" → "Already knows your work." "Autonomous output" → "Produces deliverables on schedule." "Improves with tenure" → "Gets smarter every cycle."

2. **Position**: Three consecutive moat/defensibility slides (8, 9, 10) is heavy. Consider whether this table can be merged into slide 8 or whether slide 9 (architecture) gets cut to keep the rhythm tighter.

**Also**: The closing line is strong but consider the NARRATIVE.md version: **"Not another chatbot. Not another agent framework. The only agent that combines accumulated context with autonomous output."** (adds "agent" framing)

---

### Slide 11 — "Starting with solo consultants. Expanding from there."
**Current**: Market. TAM $4.35B / SAM $1.14B / Entry SOM $11.4M. Expansion path: Now → Next → Then → Scale.
**Beat**: Beat 6 (The Opportunity — Market)
**Verdict**: ✅ KEEP as-is

Clean, well-structured, honest sizing. The entry wedge framing (solo consultants with recurring obligations) is exactly right per GTM_POSITIONING.md.

**No changes needed.**

---

### Slide 12 — "Context-powered AI is becoming infrastructure."
**Current**: Comparable Valuations table — Notion ($11B), Glean ($7.2B), Granola ($250M), Mem.ai ($110M), TwinMind ($60M), Limitless (Acquired). "What yarnnn adds" column shows the gap each leaves.
**Beat**: Beat 6 (The Opportunity — Social proof / market validation)
**Verdict**: ✅ KEEP with one consideration

Strong slide that shows yarnnn's category is investable. The "What yarnnn adds" column is smart positioning. One consideration: check if valuations are still current (Granola, TwinMind may have updated since deck was made).

---

### Slide 13 — "Built and live at yarnnn.com"
**Current**: Product screenshot + four pillars (01 Thinking Partner / 02 Deliverable Engine / 03 4 Integrations / 04 Signal Processing).
**Beat**: Currently Beat 3 but positioned as slide 13
**Verdict**: 🔴 MOVE EARLIER + REFRAME

This is the biggest structural problem in the deck. The live product screenshot — the most concrete, convincing proof that this is real — doesn't appear until slide 13. By that point the audience has sat through problem, demand, solution overview, day 1 value, insight, moat, architecture, positioning, market, and comps. The product should anchor the story, not arrive as an afterthought.

**Problems**:
- **Position**: Should be slides 5-6 range (immediately after ClawdBot proof of demand)
- **Four pillars**: "01 Thinking Partner / 02 Deliverable Engine / 03 4 Integrations / 04 Signal Processing" is the feature-list anti-pattern. It also preserves the old two-path architecture (ADR-061) instead of ADR-080's "one agent, two modes."
- **Title**: "Built and live" is a traction claim, not a product identity statement

**Recommended changes**:
- Move to slide 5 position (right after ClawdBot)
- Title: **"Meet TP — your autonomous AI agent."** or **"TP is your autonomous agent. It's live."**
- Replace four-pillar footer with: **"One agent. Two modes. TP works with you in conversation and works for you in the background."** (This is the ADR-080 framing)
- The screenshot is great — keep it. Consider adding a brief label showing connected sources on the left panel.

---

### Slide 14 — "Three tiers. Sync frequency is the lever."
**Current**: Pricing. Free $0 / Starter $9/mo / Pro $19/mo with feature breakdowns.
**Beat**: Beat 6 (The Opportunity — Business model)
**Verdict**: ⚠️ KEEP but consider position

Fine content, but "sync frequency is the lever" is smart messaging that shows you've thought about monetization mechanics. The main question is whether pricing needs its own slide in a 17-slide deck. In many seed decks, pricing is a single line on the business model or appended to market. For a wider-audience deck, it's useful.

**Keep, but ensure it stays in the back half (Beat 6 territory).**

---

### Slide 15 — "MVP live. Testing two core hypotheses."
**Current**: Traction & Hypotheses. MVP Live / 72 ADRs / 4 Platforms. Two hypotheses + validation signals.
**Beat**: Beat 6 (The Opportunity — Traction & validation)
**Verdict**: ⚠️ REWORD for consistency

Good content. The hypotheses framework is honest and VC-friendly. Two issues:

1. "72 ADRs" is now outdated — should be **"80+ ADRs"** (or current count)
2. Hypothesis 1 says "TP with synced platform context solves the cold-start problem" — uses passive technical language. Reframe: **"TP already knows your work from Day 1 — no cold start."**

---

### Slide 16 — "I've been on both sides of the context problem."
**Current**: Why Me. Personal narrative + credentials + solo founder stats + first hires plan.
**Beat**: Beat 6 (The Opportunity — Team / Founder)
**Verdict**: ✅ KEEP as-is

Strong founder slide. The personal narrative connects the 10-year CRM/GTM experience to the product thesis. "The ClawdBot demand signal confirmed what a decade of CRM work taught me: context is everything" is a clean throughline.

**No changes needed.**

---

### Slide 17 — "The Ask: $500K–$1M seed round at $5–10M valuation."
**Current**: Use of funds (Tech Lead, GTM Lead, 12-18 months runway) + Why now (ClawdBot, category unclaimed, architecture built). Closing: "AI that works for you — not just with you."
**Beat**: Beat 6 (The Opportunity — Ask)
**Verdict**: ✅ KEEP with one edit

Clean, clear ask. The "Why now" section nails urgency. Closing line matches GTM_POSITIONING.md.

**One suggested edit**: Add one line to "Why now": **"No one owns context-powered autonomy yet — this is a category-defining moment."** (strengthens the urgency beyond just timing)

---

## Proposed v14 Slide Order

Based on the audit, here's the recommended restructure mapped to NARRATIVE.md beats:

| # | Beat | Slide Title (v14) | Source |
|---|------|--------------------|--------|
| 1 | — | Title: yarnnn | Slide 1 (edited) |
| 2 | Beat 1 | "I use AI every day. Every day, it forgets everything." | Slide 2 (as-is) |
| 3 | Beat 1 | "Every AI agent disappoints. Here's why." | Slide 3 (reworded) |
| 4 | Beat 2 | "ClawdBot proved people want this." | Slide 4 (as-is) |
| 5 | Beat 3 | **"Meet TP — your autonomous AI agent."** | Slide 13 (moved + reframed) |
| 6 | Beat 3 | "TP already knows your work." (before/after) | Slide 6 (reworded) |
| 7 | Beat 3 | How value compounds: Day 1 → Day 30 → Day 90 | Slide 5 (reframed as journey, not feature list) |
| 8 | Beat 4 | "Context is what makes autonomy meaningful." | Slide 7 (minor edit) |
| 9 | Beat 5 | "Accumulated context creates real switching costs." | Slide 8 (tightened) |
| 10 | Beat 5 | "Not another chatbot. Not another agent framework." | Slide 10 (reworded rows) |
| 11 | Beat 6 | "Starting with solo consultants. Expanding from there." | Slide 11 (as-is) |
| 12 | Beat 6 | "Context-powered AI is becoming infrastructure." | Slide 12 (as-is) |
| 13 | Beat 6 | "Three tiers. Sync frequency is the lever." | Slide 14 (as-is) |
| 14 | Beat 6 | "MVP live. Testing two core hypotheses." | Slide 15 (reworded) |
| 15 | Beat 6 | "I've been on both sides of the context problem." | Slide 16 (as-is) |
| 16 | Beat 6 | "$500K–$1M seed round at $5–10M valuation." | Slide 17 (minor edit) |

**Key changes from v13 → v14 order**:
- Product screenshot (old slide 13) **moves to slide 5** — right after ClawdBot
- Architecture slide (old slide 9) **removed as standalone** — key points absorbed into moat slide
- Three-slide moat section (8+9+10) compressed to **two slides** (8+10), keeping rhythm tighter
- Day 1/30/90 timeline (old slide 5) **repositioned** as the transition between product and insight
- Total slides: **16** (down from 17 — tighter is better)

---

## Open Decisions

1. **Two problem slides or one?** Slides 2+3 are both strong. Compressing to one would free a slide. Current recommendation: keep both — the visceral (slide 2) creates emotion, the structured (slide 3) creates intellectual clarity. Together they're worth 2 slides.

2. **Architecture slide fate**: Recommended removing as standalone. But if the audience is technical VCs, it might be worth keeping. This is audience-dependent. Could have two versions of the deck (with/without architecture slide).

3. **ADR count**: Currently says "72 ADRs" in multiple places. Update to current count (80+).

---

## Vocabulary Edits Summary (Global Find-Replace)

| Current text | Replace with |
|---|---|
| "Thinking Partner" (in isolation) | "TP, your autonomous agent" |
| "AI tool" (in problem framing) | "AI agent" |
| "Deliverable Engine" | "TP works for you in the background" or "autonomous deliverables" |
| "Context-aware AI agent" | "TP already knows your work" |
| "Human-in-the-loop" | "You supervise, TP operates" |
| "72 ADRs" | "80+ ADRs" (verify current count) |
| "Yarn" (product reference) | "yarnnn" (consistent branding) |

---

## Next Steps

1. Align on this audit (confirm decisions on open items)
2. Execute v14 edits on the .pptx file
3. Use v14 as source for 1-minute video script
4. Use v14 as source for VC application supplements
