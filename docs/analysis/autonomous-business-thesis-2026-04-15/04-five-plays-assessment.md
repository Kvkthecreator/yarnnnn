# Five Plays Comparative Assessment (Revised)

> **Date**: 2026-04-15 (revised after founder challenge)
> **Parent**: [README.md](README.md)

---

## Revised Scoring Framework

The initial assessment scored plays through the lens of the consultant/intelligence-hungry ICP, which biased toward "lowest trust barrier" (agency backend). The revised assessment scores through the lens of the **business-ambitious builder** — someone creating new work, not automating existing work.

| Dimension | What it measures (revised) |
|-----------|--------------------------|
| **Architecture fit** | How much of the existing stack supports this play |
| **Moat expression** | Does accumulated context produce measurably better output in this play? (revenue as moat measurement) |
| **Builder alignment** | Does this play attract the business-ambitious builder ICP? |
| **Autonomy ceiling** | How much of the business can agents actually run? (higher = better for this ICP) |
| **Compounding visibility** | Can the user *see* the output getting better over time? |

Scale: Strong / Moderate / Weak

---

## Play 1: Intelligence Subscription

**Description**: Agents produce research reports, competitive briefs, or market intelligence. Sell access as a subscription. Niche CB Insights — "weekly fintech competitive signals," "climate tech funding tracker."

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| Architecture fit | **Strong** | `market-report`, `competitor-brief`, `track-*` task types. Context domains. Everything exists. |
| Moat expression | **Strong** | Purest accumulation play. Day 90 entity intelligence is measurably better than day 1. Revenue directly tracks context depth. |
| Builder alignment | **Strong** | Domain experts who want to monetize their knowledge without a team. Ex-analysts, ex-journalists, niche experts. |
| Autonomy ceiling | **Strong** | Research + analysis + writing + tracking + delivery — all within agent capability. The business-ambitious builder sets the niche and editorial direction; agents run the rest. |
| Compounding visibility | **Strong** | Subscribers see reports getting richer, entity coverage expanding, pattern detection improving. The intelligence product IS the accumulated context made visible. |

**Revised verdict**: **Strongest overall play.** Under the business-ambitious builder lens, the distribution problem (identified as the killer in the initial assessment) is the user's problem to solve, not YARNNN's. YARNNN handles production; the builder handles distribution. This is the same division Lovable has — Lovable builds the app; the founder markets it.

The intelligence subscription is where YARNNN's architectural moat is most directly expressed as the product. The accumulated context *is* the intelligence product. Every cycle, the product gets better because the filesystem gets richer. Revenue tracks workspace depth with the least indirection.

---

## Play 2: Agency Backend

**Description**: YARNNN agents do production work for a productized service business. The user is account manager and editor. Clients pay the user, not YARNNN.

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| Architecture fit | **Strong** | Multi-task setup, delivery, context domains. All exists. |
| Moat expression | **Strong** | Per-client context accumulation. Switching cost scales with client count × tenure. |
| Builder alignment | **Weak** | The agency owner is not a builder — they already have a business model. They're automating existing work, not creating new work. The automation paradox applies: they can't risk wrong data with clients. |
| Autonomy ceiling | **Low** | The agency owner must review everything before client delivery. This is supervision as friction — it's what they already do manually. YARNNN makes production faster but doesn't fundamentally change the agency model. |
| Compounding visibility | **Moderate** | Per-client improvement visible to the agency owner but not to their clients (the agency owner doesn't say "AI made this"). The compounding is real but hidden. |

**Revised verdict**: **Weaker than initially assessed.** The initial analysis gave this play the highest score because it had the "lowest trust barrier." But the founder's challenge reveals: the trust barrier isn't low — it's just disguised as supervision. The agency owner reviews everything, which means they're doing the same quality-gate work they already do. The value prop is "faster production" which is incremental, not transformative.

More fundamentally: the agency backend doesn't attract the business-ambitious builder. It attracts the existing business owner looking for efficiency. That's ICP-A (consultant) repackaged. The same automation paradox applies: high-stakes client work can't tolerate errors, so the human stays in the loop fully, which limits the autonomy ceiling.

---

## Play 3: Client Reporting as a Service

**Description**: Subset of Play 2 — auto-generate recurring client reports specifically.

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| Architecture fit | **Strong** | Same as Play 2. |
| Moat expression | **Strong** | Same as Play 2. |
| Builder alignment | **Weak** | Same problem — automating existing work, not enabling new work. |
| Autonomy ceiling | **Low** | Same — every report reviewed before client sees it. |
| Compounding visibility | **Moderate** | Same — hidden from clients. |

**Revised verdict**: Same as Play 2 but narrower. Not the right play for the business-ambitious builder ICP.

---

## Play 4: Vertical Signal Tracker

**Description**: Specific domain tracking sold as a subscription. Job postings, funding rounds, pricing changes, regulatory filings. The agent tracks, filesystem accumulates, analyst synthesizes.

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| Architecture fit | **Strong** | `track-*` task types, context domains, entity-level tracking. Purpose-built for this. |
| Moat expression | **Strong** | Purest accumulation play alongside intelligence subscription. 6 months of regulatory filing patterns is irreproducible. |
| Builder alignment | **Strong** | A niche expert who sees a tracking gap can build a signal product without a team. "I spent 10 years in fintech compliance — I know what signals matter, I just can't track them all manually." YARNNN tracks; the expert curates and directs. |
| Autonomy ceiling | **Strong** | Tracking is high-confidence autonomous work. The agent monitors sources, records changes, detects patterns. The human sets what to track and interprets the implications. |
| Compounding visibility | **Strong** | Subscribers see entity coverage expanding, pattern detection improving, historical baselines deepening. The tracker product IS the accumulated context. |

**Revised verdict**: **Strong play, parallel to intelligence subscription.** The vertical signal tracker is actually a variant of Play 1 (intelligence subscription) with a narrower, more focused wedge. The builder alignment is strong for the same reason — domain experts creating new value from their expertise, with agents handling the scale they can't manage alone.

---

## Play 5: Paid Community Intelligence Layer

**Description**: Run a paid community where the value is agent-curated intelligence on top.

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| Architecture fit | **Moderate** | Synthesis exists. Community management doesn't. |
| Moat expression | **Moderate** | Community moat (outside YARNNN) + context moat (inside YARNNN). Split. |
| Builder alignment | **Moderate** | Community builders are business-ambitious, but the bottleneck is building the community, not the intelligence layer. |
| Autonomy ceiling | **Moderate** | Intelligence curation can be autonomous. Community management cannot. |
| Compounding visibility | **Moderate** | Members see intelligence improving, but community dynamics dominate the experience. |

**Revised verdict**: Interesting but the value proposition is split between community building (outside YARNNN) and intelligence curation (inside YARNNN). Not the cleanest play.

---

## Revised Comparative Summary

| Play | Arch Fit | Moat | Builder | Autonomy | Compounding | **Overall** |
|------|---------|------|---------|----------|-------------|-------------|
| 1. Intelligence Subscription | Strong | Strong | Strong | Strong | Strong | **Strongest** |
| 2. Agency Backend | Strong | Strong | Weak | Low | Moderate | **Weak (revised down)** |
| 3. Client Reporting | Strong | Strong | Weak | Low | Moderate | **Weak (subset of #2)** |
| 4. Vertical Signal Tracker | Strong | Strong | Strong | Strong | Strong | **Strong (parallel to #1)** |
| 5. Community Intelligence | Moderate | Moderate | Moderate | Moderate | Moderate | **Moderate** |

---

## The Emerging Pattern

Plays 1 and 4 score highest because they share a structural property: **the accumulated context IS the product.** The intelligence subscription and the vertical signal tracker don't have a gap between "what the workspace accumulates" and "what the subscriber receives." The workspace is the product. The delivery is a window into the workspace.

This is exactly the STRATEGIC-REFRAME conclusion — "the output is the filesystem" — but now with a business model attached. The filesystem accumulates domain intelligence. The subscription sells access to it. Revenue tracks workspace depth with minimal indirection.

Plays 2 and 3 score lowest because they have a structural gap: the accumulated context helps production but the agency owner *hides* it from clients. The compounding is real but invisible to the people paying. The moat works for YARNNN (the agency owner can't switch) but doesn't create value the end customer perceives.

---

## Strategic Recommendation (Revised)

### Primary: Intelligence Subscription / Vertical Signal Tracker (Plays 1 & 4)

These are the same play at different specificity levels. The recommendation is to start with a specific vertical (Play 4) that expands into a broader intelligence product (Play 1).

**Reference implementation**: Kevin builds one — an AI agent landscape tracker, a competitive intelligence product, or a market signal service in a domain he has authority in. This:
- Validates the quality floor for revenue-grade content
- Demonstrates the accumulation advantage (month 6 vs. month 1)
- Generates proof-of-thesis content for marketing
- Serves as the demo substrate for investor conversations
- Tests whether the business-ambitious builder ICP is real (Kevin IS the ICP)

### Secondary: Generalized Platform

If the reference implementation succeeds, YARNNN's positioning becomes: "We built this for ourselves. Then we realized anyone can do this." The platform story emerges from a proven use case, not from a theoretical category.

### Deprioritized: Agency Backend (Plays 2 & 3)

Not eliminated — agency owners who discover YARNNN will still use it this way. But it's not the lead ICP or the positioning anchor. The automation paradox is real for this segment. Let them self-select rather than targeting them.
