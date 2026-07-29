# yarnnn — The ICP

**Status**: Active (v1.0)
**Date**: 2026-07-29
**Authority**: This document owns the ICP. It exists because the ICP previously lived as §2 of a positioning doc and drifted invisibly while ADRs re-cut the buyer four times (`GTM-RECUT-PROPOSAL-2026-07-29.md` §3.3 — *"the ICP has no owning document"*). Where any other doc's buyer description disagrees with this one, this one wins.
**Derived from**: [CANON-LOCK-2026-07-29](CANON-LOCK-2026-07-29.md) §2 (operator-ratified) · ADR-465 · ADR-445 · ADR-460 · ADR-490.
**Supersedes**: GTM_POSITIONING v4 §2 (the solo-operator psychographic) · `ICP_ANALYSIS_APRIL_2026.md` (archived) · the three ICP Deep-Dive `.docx` files (archived).

---

## 1. The premise — the unit of value is a commons; the unit of arrival is a person

ADR-465 states it without hedging: **"a one-member commons is a diary."** `trace`, correction-compounding, *diverge privately, settle publicly* — all of it is latent until someone else is in the room. The act that creates the second principal is the act that switches the moat on; it is a constitutive act of the product, not a peripheral convenience.

But nobody arrives as a commons. A **person** signs up, alone, with a grievance. The ICP's job is therefore two-sided:

1. describe the person who arrives, and
2. describe the second principal that makes their workspace worth paying for — and how fast it can exist.

The old ICP (GTM v4 §2: *theirs to run · can't be present · refuses to reset*) filtered **for** solitude. Taken literally, it described a diary owner. This document inverts that.

## 2. The qualifying triad

> **Plural · Consequential · Continuing**

| Qualifier | Meaning | What it filters for |
|---|---|---|
| **Plural** | They already use more than one AI. | **The load-bearing qualifier.** It is the grievance (the hook: *"Every AI keeps its own copy of your work. You don't."*), the moat's entry condition (a second principal can exist on day one, no invite needed), and the usage-revenue predictor (a 30% PAYG margin needs volume — ADR-490). |
| **Consequential** | The output goes to someone who matters — a client, a team, a public. | Willingness to pay. |
| **Continuing** | The work repeats or accumulates. | Tenure — the condition under which the record compounds. |

**Why *plural* carries the weight.** The other two qualifiers describe most knowledge workers; *plural* is the one that selects for the person whose pain yarnnn uniquely resolves. A single-AI user has no fragmentation to heal. A plural-AI user is, in their own words, *"the only thing connecting them"* — the RECOGNITION sentence (CANON-LOCK §1) is this qualifier spoken in first person.

**Register**: **AI power user doing real work.** Prosumer and small-team — not the scarce senior operator of the v4 psychographic. This is deliberate: it is the register the ADR-490 price list can actually serve (two humans free, $20/head from the third, thin usage margin that needs volume).

## 3. The second principal — three species

The moat turns on with the second principal (ADR-465). The second principal is usually **not a person**; it is usually a **second surface**.

| Species | Arrives | Cost | Function |
|---|---|---|---|
| **An external AI** — `foreign-llm` / `a2a` over the interop face (ADR-445) | Day one, no invite, no seat | Free, unlimited | **Activation** |
| **Agents at the desk** — `Scout · Gemini` et al. | Out of the box | Free | **Engagement** |
| **A human colleague** — invite or `/s/{token}` (ADR-465) | When invited | 2 free, then $20/head (ADR-490) | **Revenue** |

### The binding honesty rule

Agents at the desk are **the member's hands, not principals** — ADR-460, and the ledger says so (`member:kvk via gemini/gemini-2.5-pro`). They are **never** marketed as colleagues, teammates, or a second principal. The species that make the ledger genuinely multi-principal are the **external AI** and the **human**. Any copy that counts a desk Agent as a second principal is a claim the ledger contradicts.

(The external AI's principal status is itself a kernel invariant this ICP depends on — see [ADR-504](../../adr/ADR-504-the-interop-principal-invariant.md), drafted from CANON-LOCK §7.)

## 4. The anti-ICP

> **The single-AI user.**

No fragmentation grievance, no second principal, no reason to leave a vendor whose memory is already good enough. **yarnnn is a worse ChatGPT for that person.**

**Posture: implicit qualification.** No gating question, no qualification form, no "how many AIs do you use?" survey step. Naming three LLMs in the subhead does the filtering — a single-AI user reads the hero and correctly concludes it isn't for them. The funnel stays wide and conversion data tells us who was right.

## 5. Concrete demographics — `OWED — requires founder validation`

> **This section is a stub, deliberately.** The three archived ICP Deep-Dives died holding unanswered validation questions — concreteness was hypothesised, never validated, and the docs rotted around the hypotheses. This section stays empty until it can be filled with validated answers, and the doc is honest about that rather than decorative.

What must be filled, per CANON-LOCK §2.4:

| Dimension | Status |
|---|---|
| Age band | OWED |
| Income | OWED |
| Company size | OWED |
| Current AI spend ($/mo) | OWED |
| **Which AIs, and how many** — the qualifier no prior doc captured | OWED |
| Tool stack (beyond the AIs) | OWED |
| Switch trigger (what makes them move) | OWED |
| Decision-influence channels (where they hear about tools) | OWED |

And the two validation questions CANON-LOCK §9 arms:

1. **Three real instances of a multi-principal ledger** — any species. Until they exist, §3 is theory.
2. **Whether fragmentation registers as a grievance or as normal life.** The entire triad rests on *plural* being **felt**, not merely true.

## 6. Update when

This document must be re-read — and its triad re-verified — whenever an ADR touches one of these FOUNDATIONS dimensions:

- **Identity (Axiom 2)** — who acts in the workspace: principal roles, grants, species rules (the ADR-460/465-class decisions that inverted the last ICP).
- **Purpose (Axiom 3)** — why the workspace exists: mandate, program, activation model.
- **Channel (Axiom 6)** — where the product meets the person: surfaces, the interop face, the share link.

Also re-read when: pricing shape changes (the register in §2 is derived from ADR-490); a §5 validation answer lands (promote it from OWED and date it); either CANON-LOCK §9 question is answered.
