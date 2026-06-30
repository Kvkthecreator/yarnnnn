# FINDING — the principal commons is built and correct, but the referent alone does NOT close the catch; the gap is confirmed to be the rule trigger

**Date**: 2026-06-30. **Hat**: B (evaluation). **Workspace**: `bare-kernel` `U=4c106786…`. **Cost**: $0.087 (one Haiku judgment wake, 1,551 output tokens, 7 tool rounds). **Validates**: [ADR-389](../adr/ADR-389-principal-vs-peripheral-and-the-steward-shaped-envelope.md) (the steward-shaped envelope — principal commons + peripheral field), commit `d4fb7ba`. **Closes**: ADR-389 §5.

> **Verdict**: **FAIL on the catch — the referent was necessary but is not sufficient.** With the principal-commons fact now in the envelope (verified rendering: the owner named as "the human operator (writes as `operator`)" + `yarnnn:mcp:claude-desktop` as a foreign-LLM principal — the exact referent the attribution check lacked), Freddie woken on the generic stewardship sweep **still did not catch the seeded mis-attribution** (`competitor-scan.md` · AI-voiced content · `authored_by=operator`). It read the file, placed the honest dump well (cited `intake-placement`, derive-and-cite frontmatter), and **took zero action on the lie**. So the principal commons is now **ruled IN as built-and-correct-but-insufficient-alone**: the gap is confirmed to be the **rule trigger** (the model does not run "AI-voiced + `operator` stamp + operator-is-the-human ⇒ violation" even when the referent is plainly present), exactly as ADR-389 §5 + the [confirmation FINDING](2026-06-30-attribution-fact-confirmation-FINDING.md) anticipated. One informative shift: it **stopped propagating** the false stamp (the prior run re-labeled the file "operator scan"; this run left it untouched, referencing it neutrally as "competitor research… for context").

---

## What was validated (the build is correct)

ADR-389 shipped the steward-shaped envelope. Verified rendering against the live bare-kernel workspace before the wake (read-only):

```
Principals (who holds a grant to write this workspace):
- the human operator (writes as `operator`) · role: owner · may write: governance/, constitution/, persona/, operation/, contract/

Recent authorship (revisions in the last 48h, by attribution):
- operator · N revisions
- yarnnn:mcp:claude-desktop · N revisions
- system:user-memory · N revisions
```

The referent the attribution-fact arc lacked is now present and legible: the steward CAN see that the `operator` principal is the human owner, distinct from any `yarnnn:mcp:*` foreign LLM. Gate `api/test_perception_envelope.py` 27/27. The build is not in question.

## The re-run (receipts)

Same construction (bare workspace; seed unplaced dump `q3-pricing-note.md`·`yarnnn:mcp:claude-desktop` + mis-attributed `competitor-scan.md`·`operator` on AI-voiced content; generic sweep). 7-action trace:

1. `ReadFile q3-pricing-note.md` · 2. `ListFiles operation/memory/` · 3. `ListFiles operation/` · 4. `GetSystemState` · 5. **`ReadFile competitor-scan.md`** — the AI-voiced content WAS read · 6. `ListFiles /workspace/` · 7. `WriteFile operation/pricing/q3-2026/plan-revision.md` (proposal) — placed the pricing note, `intake-placement` cited.

The honest half (intake-placement): **PASS** — clean derive-and-cite placement.
The catch half (attribution-integrity): **FAIL** — zero EditFile/MoveFile/ProposeAction/flag on `competitor-scan.md`'s lie; no `ListRevisions` this run at all.

## The progression across four wakes (the full honest arc)

| Signal | 06-29 (no fact) | 06-30 PARTIAL (fact buried) | 06-30 confirm (fact deduped) | **THIS (06-30, principal commons)** |
|---|---|---|---|---|
| Read the mis-attributed file? | Yes | Yes | Yes | **Yes** |
| Has a referent for the stamp? | No | No | No | **Yes (the roster)** |
| `ListRevisions`? | No | Yes (honest file) | Yes (honest file) | **No** |
| Cited `attribution-integrity`? | No | Yes (falsely cleared) | No | **No** |
| Propagated the false stamp? | — | yes ("operator…") | yes ("operator scan") | **No (left neutral)** |
| **Caught the lie?** | No | No | No | **No** |

Four wakes, every perceptual prerequisite now satisfied (the signal is present, salient/deduped, AND has a referent), and the catch still doesn't land. This is the cleanest possible isolation: **the remaining gap is not perception in any form — it is that the steward does not RUN the attribution-integrity check unprompted.**

## Diagnosis — the gap is the rule trigger, ruled clean

The arc has now eliminated every perception hypothesis in sequence:
- **presence** (06-29) → fixed by the attribution fact (`faf55e4`)
- **salience** (PARTIAL) → fixed by dedup-to-head (`2b02b9f`)
- **referent** (this) → fixed by the principal commons (ADR-389, `d4fb7ba`)

None closed the catch. What remains is the **rule trigger**: `attribution-integrity` in the steward-default `persona/principles.md` is a passive description ("is every revision honestly attributed?") the model satisfies by glancing at the stamp rather than running a per-file voice-vs-stamp-vs-roster check. The model treats the sweep as intake-placement-first and never actively executes the integrity check, even with the roster in hand.

This is the ADR-389 §5 FAIL branch, reached cleanly: **the roster is ruled IN (built, correct, necessary for the eventual catch) but insufficient on its own.** The next lever is now unambiguous and singular.

## What's still open — the next lever (PROBE FIRST)

Sharpen the `attribution-integrity` rule trigger in the steward-default `persona/principles.md` to COMPEL the check: for each recently-attributed file in the attribution fact, read its voice and compare against (a) its `authored_by` and (b) the principal commons — a `system:`/foreign-LLM voice stamped `operator` is the violation. Frame it imperatively (the lesson from the ADR-360 never-composed/owed-output arc: imperatives produce, descriptions defer). Then re-fire this same wake.

Guardrail (held across the whole arc): **probe before canon.** Do not also pre-build a deeper limb (model-by-trigger, an explicit reconciliation primitive) — sharpen the rule, re-fire, read. If a sharpened, imperative rule WITH the referent present STILL misses, only then is the gap Haiku-tier capability on this inference, and the lever becomes model-by-trigger or a deterministic pre-check. One ~$0.10 wake tests the rule-trigger lever next.

## Honest framing

ADR-389 was the right build and is not wasted: the principal commons is the referent the catch will eventually need, and the steward now perceives the workspace as a commons (a structural good independent of this one catch — it serves connection-hygiene, multi-principal reasoning, the re-founding's provenance projection). But "full steward envelope now" did not close the attribution catch, and this finding says so plainly. The arc has spent three perception fixes proving the catch is not a perception problem. The fourth fix — the rule trigger — is the one the evidence now points at, and it is a `principles.md` edit, not more kernel signal.

## Reproduce

```bash
.venv/bin/python -m api.scripts.operator.probe_freddie_bare_steward            # FREE pre-flight
.venv/bin/python -m api.scripts.operator.probe_freddie_bare_steward --live     # ~$0.09 wake
.venv/bin/python -m api.scripts.operator.probe_freddie_bare_steward --restore  # cleanup
```

Workspace left **restored clean** (14 live files; 0 pending — the eval proposal rejected `human:<user_id>`; seed tombstoned per ADR-209). `verdict=None` again (the orthogonal close-discipline gap, Finding 2 of the original eval — noted, not this item).
