# findings.md — Reviewer Clarify silenced from Feed surface

**Captured**: 2026-05-25T04:28Z. Hat-B observation.

## Expected behavior

When the Reviewer calls `Clarify(question=..., options=...)` during a wake, the operator should see a Feed entry on the cockpit surface containing the Reviewer's question, attributed to the Reviewer's persona voice (per ADR-247's three-party narrative model where `role='reviewer'` is the Reviewer's verdict/question bubble shape). Without that surfacing, a Clarify is silent autonomy — the Reviewer believes it has handed control back to the operator, but the operator has no signal that anything is awaiting them.

## Observed behavior

Over the 7-day window 2026-05-18 → 2026-05-25:

- **15 Reviewer wakes called `Clarify`** across 5 of 6 active workspaces. Each produced `tool=Clarify success=True` in the scheduler logs and an entry in the cycle's `actions_taken` audit list. Each cycle then closed with `ReturnVerdict(verdict='stand_down')` per the persona-frame nudge (`reviewer_agent.py:1614-1622` — *"Your Clarify question has been surfaced to the operator. Now call ReturnVerdict..."*).

- **0 of these 15 wakes produced a `session_messages` row.** Cross-check: `SELECT count(*) FROM session_messages WHERE metadata->'tools_used' ? 'Clarify' AND created_at > '2026-05-18'` returns 0.

Per-workspace breakdown:

| Workspace | Silenced Clarify wakes (last 7d) |
|---|---:|
| alpha-trader-2 | 6 |
| netflix-script-author | 4 |
| korea-thriller-shorts | 3 |
| seulkim88 | 1 |
| kvkthecreator (alpha) | 1 |
| yarnnn-author | 0 |
| **Total** | **15** |

The trigger observation: kvk's 2026-05-24T18:08Z `weekly-performance-review` wake called `ReadFile + ListFiles + ReadFile + Clarify` and exited. The operator viewed `yarnnn.com/desktop` the next morning and saw nothing newer than Saturday on the Feed. The 4 wake actions were silent by construction.

## Root cause

Three concurrent gaps in the Reviewer chat-surfacing layer:

### Gap 1 — `Clarify` is in `REVIEWER_COGNITION_TOOLS`

`api/services/reviewer_chat_surfacing.py:174-179`:

```python
REVIEWER_COGNITION_TOOLS = frozenset({
    "ReadFile", "ListFiles", "SearchFiles", "ListRevisions",
    "ReadRevision", "DiffRevisions", "GetSystemState", "SearchEntities",
    "LookupEntity", "list_integrations", "WebSearch", "QueryKnowledge",
    "DiscoverAgents", "ReadAgentFile", "ListEntities", "Clarify",
})
```

Both surface paths gate against this frozenset:
- Reactive path (`surface_reviewer_actions`, line 395): `if tool in REVIEWER_COGNITION_TOOLS: continue`
- Addressed path (`wake.py::stream_addressed_wake` lines 1691-1702 + 1717-1728): `if tool not in _COGNITION_ONLY: yield agent_narration`

The taxonomy's stated purpose (3-bucket comment at line 174-207) is to silence side-effect-free substrate reads. Clarify is the structural opposite — its entire purpose is operator-facing communication with a side effect (operator's attention + future response). It was misclassified.

### Gap 2 — `_summarize_result` has no Clarify branch

`api/agents/reviewer_agent.py:1732-1770`. The helper checks for `slug + action`, `proposal_id`, `slug`, `path` in result dicts. Clarify returns `{success, question, options, ui_action}` — none of those keys. So `action_record["summary"]` becomes `"ok"` for every Clarify call. Even if Gap 1 were closed, the existing `narrate_reviewer_action(tool, summary)` would render `"Executed Clarify on Reviewer's direction. ok"` — non-readable.

### Gap 3 — dead `clarify_alert` lineage gate

`api/services/reviewer_audit.py:186-188`:

```python
if tool_name == "Clarify":
    if tool_input.get("clarify_alert") is True:
        clarify_alert = True
```

The `CLARIFY_TOOL` schema (`api/services/primitives/registry.py:133-147`) declares only `question` (required) + `options` (optional). No `clarify_alert` field exists. This gate is structurally unreachable — Clarify never enters the lineage stream as a material outcome. The judgment_log.md for any cycle whose only consequential action was Clarify ends up empty.

### Gap 4 — addressed-path role hardcoded to `system_agent`

`api/routes/feed.py:1199-1207` writes the `agent_narration` event as `role='system_agent'` unconditionally. The Reviewer asking the operator a question is structurally Reviewer-attributed (ADR-258 D1 + ADR-247 §"Three-Party Narrative Model"), not System Agent narration. If we surface Clarify but render it as System Agent, the persona attribution lies — the operator sees "System Agent says X" when in fact the Reviewer authored the question.

## Why this is the more important finding

This isn't a one-workspace bug. **15/15 silent Clarify wakes across 5 of 6 workspaces over 7 days** — Reviewers actively asking the operators for input, operators completely unaware. Every silenced Clarify is an operator decision the system is waiting on without telling them. Cumulatively that's the difference between "operator-supervised autonomy" and "autonomous in the dark."

It is the same class of failure as the 2026-05-22 schedule self-misdiagnosis (sibling observation `2026-05-24-045348-…`): a Reviewer-substrate-or-action that the operator should see but doesn't. The schedule case was operator-perception of "system silent when it wasn't." The Clarify case is operator-perception of "system silent when it's literally asking them a question." Both erode the Variant F line's "operator-supervised" clause.

## Hat-A recommendation — singular fix with role propagation

Per Singular Implementation, the fix is one cohesive change across four surfaces:

1. **`api/services/reviewer_chat_surfacing.py:174-179`** — remove `"Clarify"` from `REVIEWER_COGNITION_TOOLS`. The frozenset becomes 15 tools, all of which are genuine cognition (no-side-effect substrate reads).

2. **`api/services/reviewer_chat_surfacing.py::narrate_reviewer_action`** — add a Clarify branch returning the question text bare (no `"Executed Clarify on Reviewer's direction"` prefix). The Reviewer is asking; the operator reads the question.

3. **`api/agents/reviewer_agent.py::_summarize_result`** — add a Clarify branch returning the question (plus `[options]` suffix when present). This populates `action_record["summary"]` so it flows through the narration template.

4. **`api/services/reviewer_chat_surfacing.py::surface_reviewer_actions`** + **`api/services/wake.py::stream_addressed_wake`** — propagate a `role` hint through the `agent_narration` event envelope. When `tool == "Clarify"`, `role = "reviewer"`; otherwise `role = "system_agent"` (preserving the post-ADR-258 default). Both surfaces share the same one-line conditional — singular policy, two consumers.

5. **`api/routes/feed.py:1199-1207`** — read `event.get("role", "system_agent")` instead of hardcoding. The wake source decides the role; the route honors it.

6. **`api/services/reviewer_audit.py:185-197`** — delete the dead `clarify_alert` gate (Condition 4). Replace with a simple presence check: any Clarify call counts as `lineage_kind = "clarify"`. Operator-acknowledgment requests are operation-shaping moments — they belong in the judgment_log audit ledger.

7. **`extra_metadata.clarify_question` + `clarify_options`** stamped on the session_messages row so a future FE affordance (response buttons) has structured data without re-parsing the narration body.

**This is a code-only fix, not an ADR amendment.** ADR-289's 3-bucket taxonomy never named Clarify; ADR-247 already classifies Clarify as operator-addressed; ADR-258 role taxonomy already differentiates reviewer vs system_agent bubble shapes. The fix honors all three.

**Test gate** (`api/test_clarify_surfacing.py`):
- `Clarify` NOT in `REVIEWER_COGNITION_TOOLS`
- `_summarize_result({"success": True, "question": "X?"})` returns `"X?"` (or `"X? [opt1, opt2]"`)
- `narrate_reviewer_action("Clarify", "X?")` returns `"X?"` bare (no prefix)
- Mock `surface_reviewer_actions(actions_taken=[{"tool": "Clarify", "input": {"question": "Did signal-eval fire?"}, "success": True}])` writes 1 row with `role="reviewer"`, content containing the question, `metadata.clarify_question` set
- Regression: mock `actions_taken=[{"tool": "ReadFile", ...}]` → still skipped
- Dead-gate removal: `_detect_outcome_kind({"actions_taken": [{"tool": "Clarify", "input": {"question": "X?"}}]})` returns `"clarify"`

## Cross-finding implication

The two operator-perceived-silence observations this week (schedule self-misdiagnosis + Clarify silencing) share a deeper pattern: **the Feed surface has structural gaps where substantive Reviewer judgment fails to reach the operator.** Yesterday's fix (ADR-301 pulse envelope) closed the schedule case at the substrate layer; today's fix closes the Clarify case at the surface layer. A follow-on Hat-B observation cadence item: spot-check other Reviewer tool outputs for similar surface gaps (e.g. `ReturnVerdict` reasoning that contains an open question — does the reviewer-bubble render it?).

## Status

**Hat-B finding captured.** Hat-A fix being landed in same-session commit per CLAUDE.md "Crossing hats inside one session" (operator authorization: "the hat analogy and discipline shouldn't be what prevents you as thats directional guidance only"). Three-commit shape: this observation (Commit 1) → Hat-A fix (Commit 2) → RESOLUTION addendum after live-validation (Commit 3).
