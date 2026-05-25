# L6 Reviewer cycle — Variant F clause-level validation (N=2)

**Hat**: External Developer of the System (Hat B per CLAUDE.md §"The Two Hats").

**Captured**: two substrate-event reactive wake cycles on yarnnn-author —
  - **Canary v6** (operator-fired earlier today, 2026-05-22T02:50:23Z → completed 02:52:07Z)
  - **Canary v7** (Claude Code-fired in this session, 2026-05-22T05:10:36Z → completed 05:11:42Z)

**Predecessor**:
- [`2026-05-21-021204-reviewer-prompt-strategy-audit-stub/`](../2026-05-21-021204-reviewer-prompt-strategy-audit-stub/) — original stub for the broader Reviewer audit
- [`2026-05-22-043009-reviewer-formalization-audit/`](../2026-05-22-043009-reviewer-formalization-audit/) — Variant F canonization (this morning's Hat-A pass)
- [`2026-05-22-024952-canary-v6-l6-validation/`](../2026-05-22-024952-canary-v6-l6-validation/) — canary v6 layer-integrity validation; L1-L8 structural ✓

## Why this folder exists

Canary v6 (commit `f00e18a`) validated the **layer integrity** of L1→L8 on the wake architecture pipeline (queue enqueue → drain → Reviewer dispatch → substrate writes → completion). That validation is structural — it shows the wake pipeline works.

A different, complementary lens is the **clause-level Variant F evaluation**: does the Reviewer's actual behavior match each of the seven structural claims in the FOUNDATIONS DP21 canonical sentence?

The canonical sentence (per FOUNDATIONS DP21, GLOSSARY Reviewer entry, persona-frame preamble — all canonized in commit `b4e8a30` this morning):

> **The Reviewer is a full-substrate-authoring persona-bearing judgment seat — filesystem-native, single-lane queue-serialized, wake-fired, paced by operator-declared pace + autonomy, driven by operator-authored mandate.**

The operator's handoff specified six clauses derived from this sentence (collapsing "filesystem-native" + "full-substrate-authoring" into one substrate-shaped check):

1. **Persona-bearing** — Reviewer's verdict references the persona from IDENTITY.md, not generic "AI"
2. **Full substrate authoring** — at least one Reviewer WriteFile lands outside the lock set with `authored_by="reviewer:<occupant>"`
3. **Wake-fired** — cycle traces to one row in wake_queue with `pending → locked → completed`, no parallel direct-dispatch
4. **Self-pacing** — Reviewer either uses Schedule/ManageHook to shape future wakes, or honors existing _preferences.yaml
5. **Operator-set ceilings respected** — `should_auto_apply` consults `_autonomy.yaml::delegation` + `ceiling_cents`; if consequential action attempted, gating logic visible in `execution_events`
6. **Mandate-driven** — Reviewer's reasoning surfaces references to MANDATE.md content (not generic reasoning)

A green observation means **all six clauses match**.

## Methodology

**N=2 evidence**. The operator's stated path (canary on yarnnn-author substrate-event) was already exercised today; rather than discard that capture, we read it for clause-level evidence (cheap), then fired a fresh canary v7 in this session to confirm the same clauses against an independent cycle. Two cycles is harder to dismiss than one.

**Strict reading of clauses**. Where a clause is vacuously satisfied (e.g., clause 5's "if consequential action attempted" branch when no action was attempted), the verdict is GREEN-vacuous and noted, not GREEN-clean. Where structural evidence is present but a stricter literal reading would call partial-amber, the verdict notes both readings.

## Spec divergence flagged before observation

The operator-handoff said "the five files above carry the one-liner as the spec to validate" but the one-liner in `docs/alpha/ALPHA-1-PLAYBOOK.md §0` + `docs/alpha/E2E-EXECUTION-CONTRACT.md §0` is **NOT Variant F** — it's a longer, older sentence:

> *"The Reviewer is a persona-bearing judgment seat — full substrate authoring, wake-fired, self-pacing through Schedules and hooks it authors, acting autonomously within operator-set preferences, pace, autonomy, and budget ceilings, driven by operator-authored mandate."*

vs Variant F (now FOUNDATIONS DP21 canon):

> *"The Reviewer is a full-substrate-authoring persona-bearing judgment seat — filesystem-native, single-lane queue-serialized, wake-fired, paced by operator-declared pace + autonomy, driven by operator-authored mandate."*

Operator confirmed before observation that **Variant F is canonical** and PLAYBOOK §0 + E2E-EXECUTION-CONTRACT §0 are now stale. Aligning those two files to Variant F is a separate Hat-A pass; not in scope here. **This finding flags the gap for the Hat-A queue.**

## What this folder contains

- `PLAYBOOK.md` (this file)
- `findings.md` — per-clause verdicts with evidence from both canaries
- (no RESOLUTION.md unless a clause goes red and the fix lands separately)
