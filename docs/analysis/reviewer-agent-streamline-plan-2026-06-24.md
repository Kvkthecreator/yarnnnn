# reviewer_agent.py — streamline plan (behavior-preserving, pre-Stage-4)

**Date**: 2026-06-24
**Hat**: A (system code). **Scope**: a behavior-preserving refactor of `api/agents/reviewer_agent.py` (1,970 lines) that isolates the ADR-360 Stage-4 deletion target behind clean seams, WITHOUT changing any behavior. The behavioral deletion (removing the recovery net + terminal-move contract) stays gated on the E2E. This doc is the map + plan for your approval; no edit is made until you approve.

---

## 1. The file's regions (authoritative skeleton, with line numbers)

| Lines | Region | Role | Stage-4 relevance |
|---|---|---|---|
| 1–66 | Module docstring + imports | ADR lineage, re-exports from `occupant_contract` (ADR-315) | none |
| 76–83 | Model/caller constants (`_SONNET`/`_HAIKU`) | trigger→model selection | none |
| 101–170 | `RETURN_VERDICT_TOOL` | the verdict tool schema (enum incl. `stand_down`) | **target** — verdict surface shrinks |
| 186 | `build_operating_context_block` re-export | ADR-301 singular-envelope shim | none |
| 262–411 | `_compute_minimal_frame()` | the persona frame (system prompt prose) | **target** — terminal-move contract prose (384–389) + standing-obligation prose |
| 425–443 | `_PERSONA_FRAME_SECTIONS` | section registry binding the frame | none (structural) |
| 446–550 | `_TRIGGER_FRAMING` | reactive/addressed framing text | minor — `stand_down`-as-last-option prose |
| 554–597 | `_build_system_prompt` / `_system_prompt` | cache-marked system prompt composition | none |
| 604–918 | `_build_user_message` | the ~20-section envelope renderer | (envelope simplification — separate deliverable, NOT this plan) |
| 920–995 | `_validate_context_shape` | boundary contract enforcement | none (keep — load-bearing guard) |
| 997–1664 | **`invoke_reviewer`** | the bounded tool-use loop | **the core target region** |
| 1667–1709 | `_looks_like_verdict` + regexes | verdict-in-prose detection | **target** — only the recovery path uses it |
| 1712–1829 | `_dispatcher_write_silent_exit_standing_intent` | fabricates a standing_intent on silent exit | **target** — the recovery synthesizer |
| 1831–1969 | `_summarize_result` / `_compact_result_for_model` / cancellation helpers | result formatting + cancellation | none (keep) |

## 2. The Stage-4 target, precisely located (3 inlined recovery sites + 2 prose blocks)

The "recovery synthesizer + terminal-move contract" ADR-360 Stage 4 deletes is **not one block** — it's scattered across the loop, which is exactly why it's hard to delete cleanly today:

**Behavioral (in `invoke_reviewer`):**
1. **Silent-exit recovery, mid-loop** (1275–1348): when a round yields no tool calls, it (a) detects verdict-in-prose (`_looks_like_verdict`), (b) gives a one-shot nudge, (c) on unrecovered exit calls `_dispatcher_write_silent_exit_standing_intent` + synthesizes `verdict_raw = {recovered or "stand_down", ...}`.
2. **Budget-exhaustion fallback** (1540–1582): when the loop ends with `verdict_raw is None`, it calls `_dispatcher_write_silent_exit_standing_intent` again + synthesizes `verdict_raw = {"stand_down", ...}`. **Near-duplicate of site 1's tail.**
3. **Cancellation early-return** (1170–1188): returns a `stand_down` ReviewerOutput. (Distinct concern — operator pressed Stop. KEEP; not part of the inaction-default deletion.)

**Supporting (module-level):**
4. `_dispatcher_write_silent_exit_standing_intent` (1712–1829) — the fabrication helper itself.
5. `_looks_like_verdict` + `_VERDICT_TOKEN_RE` + `_AUDIT_STRUCTURE_RE` (1667–1709) — used ONLY by site 1.

**Prose (in `_compute_minimal_frame`):**
6. The terminal-move contract paragraph (384–389: "Close every cycle with a verdict or a standing_intent write… Without one of those, you have observed, not judged").

## 3. The streamline (behavior-preserving — what changes, what does NOT)

The goal: collapse the scattered recovery logic into ONE named seam, so Stage-4's eventual deletion is a single-function removal instead of surgery across 5 sites. **Zero behavior change** — same verdicts, same substrate writes, same telemetry.

### Refactor R1 — unify the two synthesize-terminal-verdict sites (1343 + 1576)

Sites 1 and 2 both do: call `_dispatcher_write_silent_exit_standing_intent(...)` then set `verdict_raw = {verdict, reasoning, confidence}`. Extract a single helper:

```python
async def _synthesize_silent_exit_verdict(*, client, user_id, exit_class, exit_round,
    max_rounds, trigger, slug, prose, recovered_verdict) -> dict:
    """The dispatcher's safety-net close when the model exits without ReturnVerdict.
    Writes the fabricated standing_intent + returns the synthesized verdict_raw.
    ADR-360 Stage 4 will DELETE this whole function (the inaction-default net);
    today it is the single seam both silent-exit paths route through."""
    await _dispatcher_write_silent_exit_standing_intent(...)
    return {"verdict": recovered_verdict or "stand_down",
            "reasoning": prose[:1000], "confidence": "medium" if recovered_verdict else "low"}
```

Both call sites become one line: `verdict_raw = await _synthesize_silent_exit_verdict(...)`. **The Stage-4 deletion then = delete this one function + its 2 call sites + the helper it wraps.** (Note: sites currently differ slightly — site 1 uses confidence "medium", site 2 "low"; preserve each by passing the value, so behavior is byte-identical.)

### Refactor R2 — name the recovery-machinery cluster with a section comment + co-locate

Move `_looks_like_verdict`, the two regexes, `_dispatcher_write_silent_exit_standing_intent`, and the new `_synthesize_silent_exit_verdict` under one banner comment:
`# === SILENT-EXIT RECOVERY NET (ADR-360 Stage 4 deletion target) ===`
so the deletion boundary is visually unambiguous. Pure move + comment; no logic change.

### Refactor R3 — extract the cancellation early-return (1170–1188) into `_cancelled_output(...)`

Small clarity win: the inline 13-line `ReviewerOutput(verdict="stand_down", ...)` for cancellation is a distinct concern (operator Stop) that currently reads as "another stand_down site." Extracting + naming it `_cancelled_output()` separates it from the recovery net so Stage 4 doesn't accidentally touch it. Behavior identical.

### What this plan does NOT touch (out of scope, by design)

- **No behavioral deletion.** The recovery net still fires identically after R1–R3; we've only given it one name and one home. Removing it waits for the E2E (it's the silent-exit observability net — deleting it before proving the agent reliably answers the ask would make silent wakes vanish without a record).
- **No envelope change.** `_build_user_message`'s ~20 sections (604–918) are the separate "envelope simplification toward CC" deliverable — explicitly not this plan.
- **No frame prose change.** The terminal-move paragraph (384–389) stays until Stage 4 — editing prose is a behavior change (it's the model's instruction).
- **No verdict-enum change.** `stand_down` stays in `RETURN_VERDICT_TOOL` until Stage 4.

## 4. Validation for the refactor (behavior-preserving proof)

- `git diff` must read as pure refactor: extracted functions + moved blocks + one banner comment. No new branches, no changed conditionals.
- AST-parse + import-resolve all reviewer modules.
- Run the reviewer test gates: `test_reviewer_context_contract`, `test_reviewer_formalization` (the 1 pre-existing bundle-prompt failure stays, unrelated), `test_reviewer_round_budget*` if present. Green = behavior held.
- The diff is small enough to eyeball each hunk against "did any conditional change?" — the bar for a behavior-preserving refactor.

## 5. Net effect

After R1–R3: the file is the same length ±~10 lines (extraction adds a signature, removes duplication — roughly net-neutral), but the **Stage-4 deletion surface collapses from 5 scattered sites to 1 named cluster behind a banner comment.** When the E2E gate passes, Stage 4 becomes: delete the `# === SILENT-EXIT RECOVERY NET ===` cluster + its 2 call sites + the terminal-move prose paragraph + the `stand_down` enum value — a clean, reviewable deletion instead of surgery. That is the value of doing this now: **it converts the gated deletion from risky to trivial, without spending the E2E gate.**

## 6. Recommendation

Approve R1–R3 (behavior-preserving). They make the file clearer now and de-risk Stage 4 for later. Hold R-deletion (the behavioral removal) for after the E2E. If you want even less now, R1 alone (unify the two synthesize sites) captures most of the de-risking value in the smallest diff.
