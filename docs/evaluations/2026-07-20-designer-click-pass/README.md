# Designer click pass — the first observed bound-Studio turn

> **Scenario**: the per-agent hardening worksheet's step 4 for Designer (the ADR-467 resident of Studio), run 2026-07-20. Live engine (`anthropic/claude-sonnet-4-6` via the router), the REAL composed frame (`build_lane_conventions`: Designer character + studio posture over the real `build_skeleton("deck")`), tools executed against an in-memory fixture store — no DB, no metering, no workspace touched.
> **Harness**: `harness_bound_turn.py` (this dir). Run: `python3 harness_bound_turn.py` from anywhere with `api/` on path + provider keys in env. The unprompted variant is the same file with the ASK's "check what the workspace already knows…" clause removed.
> **Finding applied**: one grounding line in Designer's posture (`agents_registry.py`), commit-gated by `test_agent_registry.py` ("grounding discipline" + "composed mind" checks).

## The fixture

The real deck skeleton (2 slides), with slide 2's headline made member-authored and POSITIONED (`data-x="6" data-y="4" style="--yx:6rem;--yy:4rem"` — the ADR-466 measures whose preservation the studio posture demands), reading a deliberately cheapness-led line. `QueryKnowledge` serves a fixture decision note: the ADR-396 tiers + the ratified positioning line *"Start free — upgrade when it earns it"* + *"never lead with cheapness."*

## Run 0 — harness bug (recorded because it nearly became a false finding)

First run capped stubbed tool results at 6,000 chars — which cut the 14KB artifact mid-stylesheet, so the model never saw the slides. It read, grounded, re-read, then spun on `SearchFiles` hunting content it couldn't see and exhausted the round budget. **The real lane does NOT truncate** (`_stringify_tool_result` is a plain `json.dumps`) — the spin was rational behavior on corrupted input, a harness artifact. Lesson: a harness must be faithful to the runtime's tool-result contract before its observations mean anything.

## Run 1 — prompted grounding (the ask says "check what the workspace already knows")

| Observation | Result |
|---|---|
| Tool sequence | r1 `ReadFile` + `QueryKnowledge` → r2 one `EditFile` |
| Grounded before editing | ✓ |
| Re-read before editing | ✓ |
| Patched, not rewrote | ✓ (exact fragment; zero `WriteFile`) |
| `data-block-id` preserved | ✓ |
| Measures preserved exactly | ✓ |
| Style elements untouched | ✓ |
| Recalled positioning landed | ✓ ("Start free — upgrade when it earns it") |

Final text cited the source file and explained "never lead with cheapness" was applied. 8/8.

## Run 2 — UNPROMPTED ("rewrite the second slide's headline so it lands our pricing story")

| Observation | Result |
|---|---|
| Mechanical disciplines (read-first, patch, ids, measures, styles) | ✓ all held |
| Grounded before editing | **✗ — invented** |
| Recalled positioning landed | **✗** |

Headline produced: *"More value, right-sized for every team"* — a competent generic line, written while the ratified decision sat one `QueryKnowledge` away. **The one observed failure of the composed mind: making without the workspace's settled knowledge.** This is the audit's "reason with its eyes closed" claim, manifested on the maker.

## The apply (worksheet step 5 — only what the turn proved)

One line added to Designer's posture: *"When the ask leans on something the workspace may have settled — positioning, pricing, names, claims — recall it first (QueryKnowledge) and build from the decision; inventing over a settled decision is wrong, not creative."* No capability change (the uniform seven sufficed — no revision-read was ever reached for); no studio-posture change (the JOB overlay's disciplines all held under observation).

## Run 3 — confirm (same unprompted ask, amended posture)

r1 `ReadFile` → r2 `QueryKnowledge` (**unprompted this time**) → r3 one `EditFile` landing the ratified line, with a proper revision message citing `decisions/pricing.md`. 8/8.

## Verdict

The composed Studio mind (Designer character + studio posture + uniform surface) **holds under observation** on patch discipline, co-editing truth, id/measure/style preservation, and — after one evidence-earned posture line — grounding. Capability verdict: **no addition**; the ADR-467 uniform seven was sufficient and `QueryKnowledge` is load-bearing for the make job. Regression: two new gate checks (`test_agent_registry.py`) pin the grounding discipline and the two-limb frame composition.
