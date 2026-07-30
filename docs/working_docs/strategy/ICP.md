# yarnnn — The ICP

**Status**: Active (v2.0 — working canon: locked in full, subject to evolve by discourse)
**Date**: 2026-07-30 (v1.0: 2026-07-29)
**Authority**: This document owns the ICP. It exists because the ICP previously lived as §2 of a positioning doc and drifted invisibly while ADRs re-cut the buyer four times (`GTM-RECUT-PROPOSAL-2026-07-29.md` §3.3). Where any other doc's buyer description disagrees with this one, this one wins.
**Derived from**: [CANON-LOCK-2026-07-30](CANON-LOCK-2026-07-30.md) §0 + §2 (operator-ratified) · ADR-465 · ADR-445 · ADR-460 · ADR-490 · ADR-378.
**Supersedes**: v1.0 (the plural·consequential·continuing triad — its center, plural-AI fragmentation, was flagged un-validated by the 07-29 lock's own §9.2 and did not survive the operator's first re-read) · GTM_POSITIONING v4 §2 · the archived ICP analyses and Deep-Dives.

---

## 1. The premise — the unit of value is a commons; the unit of arrival is a person

ADR-465 states it without hedging: **"a one-member commons is a diary."** `trace`, correction-compounding, *diverge privately, settle publicly* — all latent until someone else is in the room. The act that creates the second principal is the act that switches the moat on.

But nobody arrives as a commons. A **person** signs up, alone, with a felt gap. The ICP's job is two-sided: describe the person who arrives, and describe the second principal that makes their workspace worth paying for — and how fast it can exist.

**The v2 correction to v1's premise**: the second principal never required *plural AIs*. One human plus their one connected ChatGPT is already a two-principal ledger. v1 conflated "uses many AIs" with "second principal exists" — the ledger needs the latter only.

## 2. The psychographic center

> **The small team (2–5 heads, starting at 1) that already works with AI every day — and for whom getting that work in front of each other is still copy-paste.**

The felt Tuesday-morning state: the real work happens in a private AI chat window; the shared work lives somewhere else; the bridge between them is paste. The hook names the loss (*"Made with AI. Lost in the chat."*); the recognition sentence is the buyer's own confession (*"I'm the human clipboard between my AI and my team."*).

**Ease is not a feature preference for this buyer — it is the adoption condition.** They will not sit through setup, and nobody has to approve the purchase. This is deliberate strategy, not accident: a solo founding team without enterprise privacy/compliance accommodations cannot serve procurement — and doesn't need to. The workspace-as-outermost-unit ceiling (ADR-378) makes the constraint the position: **a room, not an org tree**; teams, not enterprises; bottom-up, self-serve, the product does the selling.

## 3. The qualifying triad

> **AI-first · Shared · Self-serve**

| Qualifier | Meaning | The job it carries |
|---|---|---|
| **AI-first** | They work with AI daily; the AI output *is* the work, not a garnish. | The capability register, and the usage-revenue leg — volume of AI work → PAYG (ADR-490's 30% margin needs volume). |
| **Shared** | At least one other principal touches the work — a teammate, or their own connected AI. | The moat's entry condition (ADR-465) and the seat-revenue leg. A single-AI user qualifies: their one connected AI is a real second principal (while [ADR-504](../../adr/ADR-504-the-interop-principal-invariant.md) holds). |
| **Self-serve** | They adopt tools that work in the first session — no procurement, no pilot, no admin. | The GTM motion fit (free-to-value, bottom-up) and the implicit enterprise filter. |

**Disposition of the v1 triad**: *plural* demotes to a common trait of the segment — real for targeting and analytics, absent from copy. *Consequential* and *continuing* demote from qualifiers to expected traits — still true of the buyer, no longer the filter.

**Register**: prosumer duos and small teams, 2–5 heads, arriving as one person who invites. This is the ADR-490 price shape read backwards — **two free seats *is* the ICP**: the duo is the free product; the third head is the business.

## 4. The second principal — three species

The moat turns on with the second principal (ADR-465). It is usually **not a person**; it is usually a **second surface**.

| Species | Arrives | Cost | Function |
|---|---|---|---|
| **An external AI** — `foreign-llm` / `a2a` over the interop face (ADR-445) | Day one, no invite, no seat | Free, unlimited | **Activation** |
| **Agents at the desk** — the member's hands | Out of the box | Free | **Engagement** |
| **A human colleague** — invite or `/s/{token}` (ADR-465) | When invited | 2 free, then $20/head (ADR-490) | **Revenue** |

### The binding honesty rule

Agents at the desk are **the member's hands, not principals** — ADR-460, and the ledger says so (`member:kvk via gemini/gemini-2.5-pro`). They are **never** marketed as colleagues, teammates, or a second principal. The species that make the ledger genuinely multi-principal are the **external AI** and the **human**. Any copy that counts a desk Agent as a second principal is a claim the ledger contradicts.

(The external AI's principal status is a kernel invariant this ICP depends on — [ADR-504](../../adr/ADR-504-the-interop-principal-invariant.md), Proposed, ratification owed. Under v2 it is *more* load-bearing than under v1: the **Shared** qualifier counts a connected AI as a principal at N=1 AIs.)

## 5. The anti-ICP — two-sided, both psychographic

1. **The procurement buyer.** Needs SSO, compliance, an admin console, an org tree. Deliberately unserved — by architecture (ADR-378), not merely by staffing. Never named in copy; the self-serve posture filters them.
2. **The AI-dabbler.** AI as occasional autocomplete; their real work is happy in Google Docs. No felt gap for the hook to press.

The v1 anti-ICP (*the single-AI user*) is **retired** — under this center they are a qualified buyer (§3, Shared).

**Posture: implicit qualification.** No gating question, no survey step. The copy and the self-serve motion do the filtering; the funnel stays wide and conversion data tells us who was right.

## 6. Concrete demographics — `OWED — requires founder validation`

> **This section is a stub, deliberately.** The three archived ICP Deep-Dives died holding unanswered validation questions. This section stays empty until it can be filled with validated answers.

| Dimension | Status |
|---|---|
| Age band | OWED |
| Income | OWED |
| Company / team size (the 2–5 register — verify it) | OWED |
| Current AI spend ($/mo) | OWED |
| Which AIs, and how many (targeting datum, no longer the qualifier) | OWED |
| Tool stack (beyond the AIs) | OWED |
| Switch trigger (what makes them move) | OWED |
| Decision-influence channels | OWED |

And the validation questions [CANON-LOCK-2026-07-30](CANON-LOCK-2026-07-30.md) §9 arms:

1. **A third, non-founder multi-principal ledger instance.** §9.1 was answered with production receipts on 2026-07-30 — two same-file co-work instances exist, both founder-adjacent; one workspace holds five principals across all three species. Status: **demonstrated, not validated.**
2. **Whether the copy-paste seam registers as a grievance** — do real AI-first workers feel *"made with AI, lost in the chat,"* and do they recognize themselves as the clipboard? (Replaces v1's fragmentation question, which answered itself in the negative.)

## 7. Update when

Re-read — and re-verify the triad — whenever an ADR touches:

- **Identity (Axiom 2)** — principal roles, grants, species rules (the ADR-460/465-class decisions that inverted the v0 ICP; ADR-504's disposition).
- **Purpose (Axiom 3)** — mandate, program, activation model.
- **Channel (Axiom 6)** — surfaces, the interop face, the share link.

Also re-read when: pricing shape changes (the §3 register derives from ADR-490); a §6 validation answer lands (promote from OWED and date it); either §9 question in the lock is answered; enterprise-grade accommodations ever ship (the §2 constraint-as-position would need re-derivation).
