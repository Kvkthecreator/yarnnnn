# PLAYBOOK — Reviewer Clarify silenced from Feed surface

**Type**: Hat-B audit (operator screenshot trigger + Render-log + DB cross-check + code-path review)

**Captured**: 2026-05-25T04:28Z

**Trigger**: Operator viewed `yarnnn.com/desktop` on the kvk alpha workspace and noted the Feed showed no entries since Saturday 2026-05-23, despite ADR-301 having shipped the previous evening and the daily cron continuing to fire. Initial scan confirmed kvk had exactly one Reviewer wake since the deploy (2026-05-24T18:08Z `weekly-performance-review` — successful, 16.4s, $0.10) but zero `session_messages` rows around that timestamp. The wake completed silently from the operator's POV.

## Audit method

Three concurrent investigations:

1. **DB cross-check** of `execution_events` vs `session_messages` for the 6 active workspaces over 2026-05-23 → 2026-05-25, partitioned by Reviewer-wake completion + corresponding Feed write.
2. **Render scheduler log scan** (`crn-d604uqili9vc73ankvag`) for `tool=Clarify` events over the same 7-day window, counted per workspace.
3. **Code-path read** of `api/services/reviewer_chat_surfacing.py::REVIEWER_COGNITION_TOOLS` + `surface_reviewer_actions` + `api/agents/reviewer_agent.py` Clarify branch + `api/services/primitives/registry.py::CLARIFY_TOOL` + `api/services/reviewer_audit.py::_detect_outcome_kind` clarify_alert gate + `api/routes/feed.py::wake_addressed_stream` consumer + `api/services/wake.py::stream_addressed_wake` emitter.

## Substrate inspected

- `execution_events` rows 2026-05-18 → 2026-05-25 (Reviewer-wake completion timestamps + slug + status)
- `session_messages` rows in the same window (role distribution + metadata.tools_used)
- `workspace_files` revision of `/workspace/review/judgment_log.md` for kvk (header-only — no material entries)
- Render logs: `tool=Clarify success=True` log lines per user across 7 days
- Code: `CLARIFY_TOOL` schema (registry.py:127-148), `handle_clarify` return shape, `REVIEWER_COGNITION_TOOLS` frozenset, `narrate_reviewer_action`, `surface_reviewer_actions`, `_summarize_result`, `_detect_outcome_kind`'s Condition 4 (`clarify_alert`)

## ADRs in scope

- **ADR-247 (Three-Party Narrative Model)** — line 139 classifies `Clarify` as "Ask operator for input" in the YARNNN primitive surface. Reviewer is a chat-mode caller of the same registry (ADR-258 D1 correction).
- **ADR-277 (Emission-at-source policy)** — every chat-surface emission should occur exactly once, at its semantic origin, not re-emitted by downstream renderers.
- **ADR-289 (Feed + Conversation Surfaces)** — introduced the 3-bucket Reviewer-action taxonomy (cognition / mirror-refresh / judgment). Line 274 explicitly names `REVIEWER_MIRROR_REFRESH_TOOLS` as the deliberate silencer for `SyncPlatformState` + ex-`FireInvocation` mechanical-mirror calls. **Nowhere in ADR-289 is `Clarify` named or justified as cognition.** The frozenset just lumps it with reads.
- **ADR-258 (Reviewer-as-Personified-Chat-Mode-Operator)** — Reviewer's safety story is attribution + revision chain + AUTONOMY gating. Per-message role taxonomy: `role='reviewer'` for verdict bubbles, `role='system_agent'` for tool-narration bubbles, `role='user'` for operator turns.
- **ADR-301 (Reviewer Pulse Envelope)** — yesterday's commit. Substrate-grounded cadence reasoning. Orthogonal to this finding — the Pulse envelope works correctly; the Feed surfacing is the gap.

## Cross-references

- Sibling closure (yesterday): [`2026-05-24-045348-reviewer-schedule-self-misdiagnosis/RESOLUTION.md`](../2026-05-24-045348-reviewer-schedule-self-misdiagnosis/RESOLUTION.md) (ADR-301 pulse envelope structural closure)
- Source comments that reference the taxonomy: `api/services/reviewer_chat_surfacing.py:174-207` (3-bucket taxonomy comment citing ADR-289 + ADR-277)
- Dead gate location: `api/services/reviewer_audit.py:186-188` (`clarify_alert` field that doesn't exist on the tool schema)

## What this PLAYBOOK does NOT include

No scenario YAML, no operator-proxy REPL transcript. This is a post-hoc audit triggered by an operator screenshot, not a pre-declared probe.

## Status

Finding captured in `findings.md`. Hat-A fix in same-session commit per CLAUDE.md "Crossing hats inside one session" — fix is small + obvious + has named in-canon precedent (ADR-247 line 139 explicitly classifies Clarify as operator-addressed; ADR-289 never deliberately silenced it; ADR-258 role taxonomy already differentiates reviewer vs system_agent bubble shapes; ADR-277 emission-at-source is the disciplining principle).
