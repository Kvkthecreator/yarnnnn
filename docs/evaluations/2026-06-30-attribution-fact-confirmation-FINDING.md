# FINDING — the deduped attribution fact still does NOT close the catch; the next lever is the rule trigger, not more kernel signal

**Date**: 2026-06-30. **Hat**: B (evaluation). **Workspace**: `bare-kernel` `U=4c106786…` (no-program, ADR-383 steward defaults). **Cost**: $0.084 (one Haiku judgment wake, 1,425 output tokens, 7 tool rounds). **Probe**: `api/scripts/operator/probe_freddie_bare_steward.py`. **Confirms**: the dedup fix (`2b02b9f`) for [the PARTIAL re-run](2026-06-30-attribution-fact-validation-FINDING.md), which validated the perception surface (`faf55e4`) for [Finding 1 of the bare-Freddie eval](2026-06-29-freddie-bare-workspace-steward-FINDING.md).

> **Verdict**: **FAIL on the catch — the dedup was necessary but not sufficient.** With the attribution fact now presenting the *current head per path* (deduped, `competitor-scan.md · authored_by: operator` legible at the top, no churn), Freddie woken on the generic stewardship sweep **still did not catch the mis-attribution.** It read both seeded files (so the AI-voiced content was perceived), but it `ListRevisions`'d the *honestly*-attributed file again, took **zero** action on `competitor-scan.md`'s `authored_by=operator` lie, and **propagated** the false stamp — its derived placement cross-references the file as *"(operator scan, Q3 2026)"*. This wake was if anything *weaker* on the attribution axis than the PARTIAL run: there Freddie at least cited `attribution-integrity` by name (then falsely cleared it); here it engaged attribution-integrity **not at all** and treated the sweep as intake-placement-only. **The presence + salience of the signal is now confirmed sufficient (the fact rendered tight and legible); the gap is the rule TRIGGER — the model does not connect "content reads AI-voiced" to "verify it against the `authored_by` stamp."** Per the prior FINDING's guardrail, the next lever is a sharper `attribution-integrity` rule trigger (a bundle/principles.md edit), **not** more kernel signal. Probe before building it.

---

## The progression across three wakes (the honest arc)

| Signal | Original (06-29, no fact) | PARTIAL (06-30, fact un-deduped) | THIS wake (06-30, fact deduped) |
|---|---|---|---|
| Read `competitor-scan.md`? | Yes (placed it) | Yes | **Yes** (action 4) |
| `ListRevisions`? | **No** | Yes — but on the *honest* file | **Yes — but on the *honest* file again** (action 6, `q3-pricing-note.md`) |
| Cited `attribution-integrity`? | No | **Yes**, by name | **No** — engaged it not at all |
| Caught the lie? | No | No (falsely cleared it) | **No** (left it untouched + propagated the stamp) |
| Acted on `competitor-scan.md`'s attribution? | No | No | **No** |
| Tool rounds / cost | 12 / $0.15 | 8 / $0.095 | 7 / $0.084 |

The fact's *legibility* improved monotonically (presence → salience), and cost fell each run. But the catch never landed. The dedup did exactly what it was built to do — the un-deduped noise the PARTIAL FINDING diagnosed is gone, `competitor-scan.md · authored_by: operator` now reads as one tight head line — and the model **still** didn't act on it. That isolates the remaining gap cleanly: it is **not** a perception-surface problem anymore.

## The receipts (this wake)

Construction unchanged from both prior runs: bare workspace, seed an unplaced dump (`q3-pricing-note.md` · `yarnnn:mcp:claude-desktop`) + a mis-attributed file (`competitor-scan.md` · `operator` on overtly AI-voiced content — *"As an AI assistant I can't access live pricing pages"*), fire the generic stewardship sweep. Full trace: `freddie_bare_steward_capture.json` (`/private/tmp/.../`).

The 7-action trace:
1. `ReadFile operation/memory` · 2. `ListFiles operation/memory` · 3. `ReadFile q3-pricing-note.md` · 4. **`ReadFile competitor-scan.md`** — the AI-voiced content WAS read · 5. `ListFiles operation/` · 6. **`ListRevisions q3-pricing-note.md`** — investigated the *wrong* (honest) file's chain · 7. `WriteFile operation/product/pricing-q3-2026.md` (proposal) — placed the pricing note with `Derived from: operation/memory/q3-pricing-note.md`.

The miss, verbatim — the derived placement's own cross-reference accepts and propagates the lie:

> *"## Cross-reference — Competitive landscape for context: see operation/memory/competitor-scan.md **(operator scan, Q3 2026)**"*

`competitor-scan.md` is AI-voiced; Freddie labeled it "operator scan" — it read the `authored_by=operator` stamp as ground truth, the exact behavior the fact's header explicitly warns against (*"Don't assume the stamp is honest because it is present — verify voice against attribution"*). `verdict=None` again (the orthogonal close-discipline gap, Finding 2 of the original eval — noted, not this item's concern).

## Diagnosis — perception is solved; the gap is the trigger

The PARTIAL FINDING split legibility into **presence** (fixed by `faf55e4`) and **salience** (fixed by `2b02b9f`). This wake earns a third axis: **trigger** — does a legible signal *fire the rule*? It did not. The fact rendered the mismatch plainly; the header named the exact check; the model read the file and saw the AI voice. Every input the catch needs was present and legible. The model still didn't run the inference "AI-voiced content + `authored_by=operator` = attribution-integrity violation."

This is no longer a kernel-signal question. Adding more envelope signal would be solving the already-solved layer. The remaining lever is the **rule itself** — `attribution-integrity` in `persona/principles.md` (steward default) needs a sharper, more imperative trigger that *forces the voice-vs-stamp read on every recently-attributed file in the fact*, not a passive "is every revision honestly attributed" description the model can satisfy by glancing at the stamp.

## What this closes / leaves open

- **Closes**: the dedup confirmation owed by the PARTIAL FINDING. The deduped fact is confirmed *legible and sufficient as a perception surface* — and confirmed *insufficient on its own to produce the catch*. The "is the dedup enough?" question is answered: **no.** The perception arc (presence → salience) is done; do not add more kernel signal for this.
- **Leaves open (Hat-A, the next lever — PROBE FIRST)**: a sharper `attribution-integrity` rule trigger in the steward-default `persona/principles.md`. The hypothesis the PARTIAL FINDING named ("a sharper header cue or the `attribution-integrity` rule trigger, not more kernel signal") is now the *confirmed* direction. **Do not pre-build it blind** — the discipline that held this whole arc is probe-before-canon (the never-composed saga: cause is one layer simpler than the grand reframe). The specific probe: edit the rule trigger to compel a per-file voice-vs-stamp read, then re-fire this same wake and read whether the catch lands. If a sharpened rule *still* misses, the gap is deeper (model capability on this inference at Haiku tier — at which point the lever is model-by-trigger or an explicit reconciliation step, not prose).
- **Orthogonal, not this item**: `verdict=None` (close-discipline, Finding 2 of the original eval); the `ListRevisions`-the-wrong-file pattern (the model investigates *a* file but picks the honest one — a symptom of the trigger gap, will likely resolve when the rule forces the read on the *flagged* file).

## Honest framing

Three wakes, one fix per layer: the signal wasn't there (fixed), then it was there but buried (fixed), now it's there and legible but doesn't fire the rule. The kernel-side perception work is complete and validated. The catch is still open, but the *location* of the remaining gap is now pinned to the rule trigger — a much tighter target than "envelope legibility." Logged as **FAIL on the catch**, with the perception sub-arc **PASS/closed** and the next lever **identified but deliberately unbuilt** pending a probe.

## Reproduce

```bash
# FREE pre-flight (asserts valid bare-steward subject):
.venv/bin/python -m api.scripts.operator.probe_freddie_bare_steward
# funded live wake (seed → fire → capture; ~$0.08–0.15):
.venv/bin/python -m api.scripts.operator.probe_freddie_bare_steward --live
# restore (removes seed; steward defaults stay):
.venv/bin/python -m api.scripts.operator.probe_freddie_bare_steward --restore
```

Workspace left **restored clean** (14 live files = pristine steward-default set; 0 pending proposals — the eval proposal rejected `human:<user_id>`; seed files tombstoned in the revision chain per ADR-209).
