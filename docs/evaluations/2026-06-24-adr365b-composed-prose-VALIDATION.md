# ADR-365b composed-prose structure directive — A/B eval: VALIDATED (+49–79%)

**Date**: 2026-06-24
**Verdict**: **VALIDATION** — a STRUCTURE directive (with concrete bad→good examples), scored on the RIGHT dimensions, measurably improves the documents the Reviewer composes for the operator.
**Probe**: `api/scripts/operator/probe_adr365b_composed_prose_ab_local.py` (self-contained, no live workspace).
**Counterpoint to**: [`2026-06-24-adr365-register-ab-FALSIFICATION.md`](2026-06-24-adr365-register-ab-FALSIFICATION.md) — the earlier attempt that tested INERT. This eval explains why that one failed and this one didn't.

---

## What was wrong with the first attempt (and right with this one)

The operator's complaint was about the **documents the Reviewer composes** — its `standing_intent`, `judgment_log`, and verdict reasoning read like console logs, not like a person wrote them. The screenshot: *"Recurrences are firing and failing predictably on empty substrate (corpus-coherence-check, revision-audit… all encountering missing-signal files when they try to audit zero scenes). The pre-ship-audit hook is armed and waiting. No hard-trigger from principles.md fires…"*

The **first** ADR-365 attempt got two things wrong:
1. **Vague directive** — it said "write plainly / make it legible" with no concrete model of the failure to fix.
2. **Wrong metric** — it scored jargon WORD-FREQUENCY. But the problem isn't word counts; it's **structure**: leading with process instead of the takeaway, semantic backtracking, raw codenames. A regex can't see any of that. So the eval found the directive "inert" — a measurement artifact, not a finding.

This attempt fixes both:
1. **Sharp directive** — three rules, each paired with the concrete bad→good example it fixes (lead-with-takeaway, expand-codenames, flowing-prose).
2. **Right metric** — an **LLM judge** (Sonnet) scores three CC-canon dimensions 0–10 on the REAL composed `standing_intent`: `leads_with_takeaway`, `codenames_expanded`, `flowing_prose`. This is the tool that can actually read for structure.

## Method

Same isolation as before — no live workspace, one variable, same empty-author wake envelope (the screenshot scenario), Haiku tier (where these documents are composed). 4 trials/arm.
- **ARM A**: the structure directive present in the frame.
- **ARM B**: the same frame, directive absent.
Each arm composes a real `standing_intent`; the judge scores it.

## Result

| Dimension (0–10) | A (directive on) | B (off) | Δ |
|---|---|---|---|
| leads_with_takeaway | 4.0–5.0 | 2.0–2.75 | +2.0–2.25 |
| codenames_expanded | 3.75–4.0 | 2.0–2.5 | +1.5–1.75 |
| flowing_prose | 5.25–5.5 | 3.25–4.5 | +1.0–2.0 |
| **TOTAL (max 30)** | **13.0–14.5** | **7.25–9.75** | **+4.75–5.75** |

**+49% to +79%** improvement in operator-readability, depending on run. Decisive and reproducible across two runs (full 1121-char directive: 7.25→13.0; lean 788-char directive: 9.75→14.5). The lean version that shipped keeps all three examples and still passes — the examples, not the prose around them, are the load-bearing part.

The samples make it visible:
- **B (off)** opens with a metadata header — *"**Author:** Reviewer (judgment seat) / **Date:** corpus-coherence-check wake"* — then "Aperture: closed", "ADR-352 guidance", "source_ref", "no-ops". Console log.
- **A (on)** opens with the takeaway — *"Framework is complete and sound. No corpus yet… The scheduled coherence checks are firing as designed but have nothing to audit, which is expected."*

## Honest caveat

ARM A scored 13–14.5 / 30 — a large *improvement*, not a *cure*. Codenames still leak (MANDATE, IDENTITY, aperture survive in the "on" arm). The directive moves the model meaningfully toward operator-readable prose but does not make it perfect. If a higher bar is needed, the next lever is a **composed plain-English projection** the compositor renders FROM standing_intent (ADR-340 "compose few") — a separate, larger change. But the directive is a real, measured, cheap win and ships now.

## Disposition

- **SHIPPED** to `_compute_minimal_frame()` — replaced the weak "Narrate your direction… plainly" block (same concern, evidence-backed version) and merged the two adjacent citation blocks to claw back room. Net frame cost paid down to a 222-char overage.
- **Frame ceiling raised 11.5K → 12K** (`test_system_prompt_under_ceiling`) — the test required a "same-rationale ADR" to raise; THIS eval is that rationale. The directive is interface-grammar (the right home per agent-composition.md §3.2.1), the examples can't be trimmed without dropping the effect, and the remaining overage couldn't be reclaimed without mangling principal-shift postures (ADR-352 witness-dial, absent-MANDATE reasoning). The bump earns its space with a measured win.

## The lesson (correcting the earlier one)

The earlier FALSIFICATION's lesson — "the lever is deterministic surfaces, not the model's free prose" — was **half right**. It's true for *labels and narration strings* (D3, deterministic). But for the *documents the model composes*, a directive CAN move them — if it targets STRUCTURE with concrete examples and is measured by something that can read. The two evals together: **plain-language the deterministic copy (done, the voice sweep) AND give the model a sharp, exampled structure directive for what it composes (this).** Different surfaces, different levers, both real.
