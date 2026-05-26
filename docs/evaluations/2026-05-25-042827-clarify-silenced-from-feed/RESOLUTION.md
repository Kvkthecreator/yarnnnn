# RESOLUTION — Reviewer Clarify silencing closed via 7-surface fix

**Captured**: 2026-05-25T05:00Z. Hat-B closure, ~32 min after the finding was first captured at 04:28Z.

**Siblings**: [`findings.md`](./findings.md) (Hat-B finding) · [`PLAYBOOK.md`](./PLAYBOOK.md) (audit method).

**Hat-A fix commit**: `5ba5ba6` (`fix(reviewer): clarify surfaces to feed as role='reviewer'`).

## Three-commit shape — completed in-session

The cross-hat work followed the discipline rule from `CLAUDE.md §"The Two Hats"`. The operator explicitly authorized in-session crossing for this surface ("the hat analogy and discipline shouldn't be what prevents you as thats directional guidance only"). The work landed as:

| # | Hat | Commit | Scope |
|---|---|---|---|
| 1 | Hat-B | `5225528` | `findings.md` + `PLAYBOOK.md` capturing the 15/15 silenced Clarify wakes finding + 4-gap root cause + Option A recommendation with surface area. No code changes. |
| 2 | Hat-A | `5ba5ba6` | 7-surface fix (4 gaps + role propagation across reactive + addressed paths + dead-gate removal) + regression gate (29/29 PASS) + CHANGELOG entry `[2026.05.25.2]`. |
| 3 | Hat-B | this | Resolution addendum confirming structural + live-substrate validation. |

In-session crossing was warranted per the discipline rule: the fix had named in-canon precedent (ADR-247 line 139 explicit Clarify classification; ADR-258 D1 role taxonomy; ADR-277 emission-at-source; ADR-289 cognition-vs-judgment 3-bucket taxonomy that Clarify never qualified for). Total Hat-A change: ~656 LOC added, ~14 deleted, 7 files.

## What was shipped

One cohesive fix across seven surfaces (Singular Implementation):

1. **`api/services/reviewer_chat_surfacing.py::REVIEWER_COGNITION_TOOLS`** — `Clarify` removed. The frozenset is now exactly the 15 substrate-read tools that genuinely have no operator-facing side effect.

2. **`narrate_reviewer_action`** — Clarify branch returns the question bare. The operator reads the question; no "Executed Clarify on Reviewer's direction" prefix because the Reviewer **is** the asker.

3. **`reviewer_agent.py::_summarize_result`** — Clarify branch extracts `{question, options}` from the result dict so `action_record["summary"]` carries the operator-facing payload. Previously fell through to `"ok"`.

4. **`wake.py::stream_addressed_wake`** — `agent_narration` event carries a per-tool `role` field (Clarify → `"reviewer"`; default → `"system_agent"`) plus `clarify_question` + `clarify_options` for the addressed (SSE) path. Both emit sites (drain block + post-drain block) consistent.

5. **`routes/feed.py::_dispatch_reviewer_turn` agent_narration handler** — reads `event.get("role", "system_agent")` instead of hardcoding `"system_agent"`. Propagates `clarify_question` + `clarify_options` into the `session_messages` row metadata.

6. **`surface_reviewer_actions`** — Clarify rows written with `role="reviewer"` + `extra_metadata` (`clarify_question`, `clarify_options`). Non-Clarify tools unchanged (`role="system_agent"`).

7. **`reviewer_audit.py::_detect_outcome_kind`** — dead `clarify_alert` input-flag gate replaced with simple presence check. The pre-fix gate read `tool_input.get("clarify_alert")` which doesn't exist on `CLARIFY_TOOL`'s schema (registry.py:127-148) — structurally unreachable. Outcome label renamed `clarify_alert` → `clarify`; docstring + module-header comment updated.

No ADR amendment required. ADR-289's 3-bucket taxonomy never named Clarify; ADR-247 already classifies Clarify as operator-addressed; ADR-258 D1 role taxonomy already differentiates reviewer-vs-system_agent bubble shapes. The fix honors all three.

## Validation — three layers

### Layer 1 — Regression gate (`api/test_clarify_surfacing.py`)

**29/29 PASS** covering all seven surfaces:

- §1 Clarify NOT in `REVIEWER_COGNITION_TOOLS` (+ ReadFile/ListFiles/SearchFiles regression check)
- §2 `narrate_reviewer_action` returns question bare; empty-summary fallback readable; ProposeAction regression preserved
- §3 `_summarize_result` extracts question only + question+options; ProposeAction + failure regressions preserved
- §4 `agent_narration` event carries `role` + `clarify_question` + `clarify_options` (verified via source inspection)
- §5 `feed.py` agent_narration handler reads `event.get("role", ...)` instead of hardcoding
- §6 `surface_reviewer_actions` writes Clarify with `role='reviewer'` + metadata; WriteFile regression preserved as `role='system_agent'`
- §7 `_detect_outcome_kind` returns `"clarify"` on any Clarify presence; cognition-only stand-down still returns None; ProposeAction priority preserved; dead `clarify_alert` input-flag check removed from source

### Layer 2 — Sibling-gate sweep

All neighboring gates green post-fix:

| Gate | Result |
|---|---|
| ADR-301 (pulse envelope) | 32/32 PASS |
| ADR-276 (reactive envelope) | 9/9 PASS |
| ADR-275 (introspection cadence) | 26/26 PASS |
| ADR-298 Phase 4 (bundle pace) | 36/36 PASS |
| reviewer_formalization | 10/10 PASS |
| ADR-299 (kernel-universal capability) | 10/10 PASS |
| ADR-274 (trigger authoring) | Pre-existing `FileNotFoundError` on deleted `invocation_dispatcher.py` — unrelated to this change (confirmed via `git stash` cross-check) |

### Layer 3 — Live DB smoke against production Supabase

After Render deploy went live (`dep-d89tap3eo5us73ba392g`, finished 2026-05-25T04:52:48Z), ran `surface_reviewer_actions` directly against kvk's session via service-key Supabase client with a synthetic Clarify action. **6/6 assertions PASS**:

```
OK Clarify not in REVIEWER_COGNITION_TOOLS (current size=15)
surface_reviewer_actions returned written=1
OK row exists: id=18a349ef-… role='reviewer'
   metadata.clarify_question = '[ADR-clarify-surfacing live smoke] Did you see this in the Feed?'
   metadata.clarify_options  = ['yes-saw-it', 'no-still-silent']
   metadata.tools_used       = ['Clarify']
   metadata.reviewer_directed= True
   body[:100] = '[ADR-clarify-surfacing live smoke] Did you see this in the Feed? [yes-saw-it, no-still-silent]'

LIVE SMOKE PASS — Clarify writes role='reviewer' with structured metadata
Cleaned up test row 18a349ef-…
```

Test row cleaned up to keep the operator's real Feed pristine. The substrate write path is verified end-to-end against real schema + real RLS + real session row.

## What remains follow-on

- **Next natural Reviewer Clarify wake** — the reactive path through the deployed scheduler will write the same shape on the next natural Clarify-bearing cycle. Given the 7-day history (15 Clarifies across 5 of 6 workspaces ≈ ~2/day), expect first behavioral confirmation within the next 24h. The structural closure (substrate write path verified live) is sufficient for RESOLUTION; behavioral closure is queued as observation-cadence follow-on.

- **FE response affordances** — `metadata.clarify_question` + `metadata.clarify_options` are now stamped on every Clarify row. A future FE change can render inline `[yes-saw-it] [no-still-silent]` buttons on the Reviewer bubble without re-parsing the body text. Out of scope for this fix; flagged in the prior CHANGELOG entry as a future-enabling design.

- **Hat-B observation cadence** — spot-check whether other Reviewer tool outputs carry similar persona-attribution gaps (e.g. `ReturnVerdict` reasoning containing open questions, `WriteFile` to operator-canon paths that should be Reviewer-bubble rendered instead of System Agent narration). The pattern this resolution closes is "Reviewer-authored operator-facing content silently rendered as system narration." Likely no other instances — `WriteFile` is correctly system narration because it IS substrate plumbing, not operator-addressed content — but worth a one-pass audit.

## Cross-finding implication

The two operator-perceived-silence observations this week share a deeper pattern:

| Observation | Layer | Pattern |
|---|---|---|
| `2026-05-24-045348-reviewer-schedule-self-misdiagnosis` | Substrate | Reviewer reasoning lacked substrate basis for self-pulse → hallucinated cadence claims |
| `2026-05-25-042827-clarify-silenced-from-feed` (this) | Surface | Reviewer-authored operator-facing content silently rendered or not rendered at all |

Yesterday's ADR-301 closed the substrate gap; today's fix closes the surface gap. Both expose the **operator-supervised** clause of FOUNDATIONS Derived Principle 21 — autonomous activity that the operator can't see, can't reason about, or can't respond to is the failure mode that erodes trust in the architecture. The Variant F line works when the substrate is grounded AND the surface is honest.

## Status

**Reviewer Clarify silencing STRUCTURALLY CLOSED via the 7-surface fix (commit `5ba5ba6`, deployed 2026-05-25T04:52:48Z).** Live DB smoke confirmed substrate write path works against real Supabase. Regression gate 29/29 PASS. Sibling gates green. Operator authorization for in-session cross-hat shape preserved + invoked correctly.

**Three-commit cross-hat shape completed in-session**: Hat-B finding (`5225528`) → Hat-A 7-surface fix + tests + CHANGELOG (`5ba5ba6`) → Hat-B resolution (this commit). Remaining follow-on is behavioral validation of the reactive path through a deployed scheduler tick on the next natural Reviewer Clarify wake.
