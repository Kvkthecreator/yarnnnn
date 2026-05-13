# 2026-05-13 — kvk — Iteration 2: Three-layer trade-execution gap (why weeks of "no trades")

> **Type**: Steered-session observation — investigation, no code fix shipped this session. Successor to [iter-1](./2026-05-13-iter1-e2e-aliveness-kvk.md). Sets up iter-3 work.
> **Persona**: `kvk` — `user_id=2abf3f96-118b-4987-9d95-40f2d9be9a18`, paper Alpaca EE8K
> **Why this iter exists**: KVK named the lived reality — "weeks of wait-and-see, multiple attempts, no real trade ever executed." Iter-1 closed E2E aliveness; this iter answers the harder question of why aliveness still doesn't produce trades.

---

## Classification

- **Objective:** A-system (primary), B-product (the absence of trades is itself the B-product friction)
- **Within-A scope:** systematic-workflow + qualitative-agent-behavior (the load-bearing path crosses both)
- **FOUNDATIONS dimension:** Trigger (which recurrences fire when) + Mechanism (specialist sub-call wiring) + Substrate (bundle YAML declarations)
- **Severity:** dead-stop (zero trades ever executed; load-bearing for entire alpha-1 product proposition)
- **Resolution path:** ADR-candidate + component-patch (multi-file feature-wiring across Recurrence dataclass, dispatcher, Reviewer prompt, DispatchSpecialist schema, bundle YAML)
- **Money impact:** decision-impact (system has been unable to produce trade decisions at all; the impact-on-capital is "zero capital deployed in alpha-1" which is the inverse of the product hypothesis)

---

## Stated objective (this iter)

Investigate the tool-surface gap that surfaced in iter-1 Phase 7 retry. The Reviewer's first post-trilogy-fix wake reported "the platform bar-fetching tool is not available in my tool surface." Iter-2 answers: **why is it not available, and what would it take to make it available structurally**.

The deeper question driving iter-2: with iter-1 confirming the Reviewer can engage and reason properly post-trilogy-fix, why does KVK's lived experience over weeks remain "no trade ever executed"?

---

## What happened

Walked the trade-producing path from recurrence YAML → Reviewer → DispatchSpecialist → specialist sub-LLM → platform tools end-to-end. Found **three independent broken layers**, of which iter-1 only fixed the first.

### L1 — Reviewer dispatcher trilogy (✅ FIXED in iter-1)

The trilogy commits (`e55d201`, `85c9736`, `6027459`) shipped earlier today and were validated in iter-1. Reviewer now writes prose reasoning to decisions.md; token_usage carries proper slug metadata; context-shape contract enforced. This was layer 1 of the gap.

### L2 — DispatchSpecialist signature bug (❌ BROKEN since 2026-05-10)

[api/services/primitives/dispatch_specialist.py:184-186](../../api/services/primitives/dispatch_specialist.py#L184) calls:

```python
tools = await get_headless_tools_for_agent(
    db_client, user_id, agent_role=role,
)
```

But [api/services/primitives/registry.py:540-547](../../api/services/primitives/registry.py#L540) signature is:

```python
async def get_headless_tools_for_agent(
    client, user_id,
    agent: Optional[dict] = None,
    agent_sources: Optional[list] = None,
    coordinator_agent_id: Optional[str] = None,
    task_required_capabilities: Optional[list[str]] = None,
) -> list[dict]:
```

**No `agent_role` parameter exists.** Python raises `TypeError: ...unexpected keyword argument 'agent_role'`. The broad `try/except` in dispatch_specialist (line 187–196) catches and returns `{success: False, error: "tool_resolution_failed"}`. **Every DispatchSpecialist invocation since 2026-05-10 (PR #9 squash `42725c6`) has failed at the tool-resolution step.** The specialist's LLM call has never executed in production.

Even if this signature gets fixed (1-line change), it's only half the fix because of L3 below.

### L3 — `required_capabilities` flow is an unfinished feature (❌ NEVER WIRED end-to-end)

The architecture per ADR-176 (universal specialist roster, ICP-agnostic) + ADR-227 (recurrences declare program-specific capabilities) is sound. **None of the universal specialist roles declare `read_trading` or `write_trading`** in their capability lists — researcher/analyst/tracker capabilities are `web_search`, `read_workspace`, `search_knowledge`, `read_slack/notion/github`, `investigate`, `produce_markdown`. By design, trading capabilities flow from `task_required_capabilities` declared on the recurrence YAML.

But every link in that chain is missing:

1. **Bundle `_recurrences.yaml` doesn't declare them**: alpha-trader's `track-universe`, `signal-evaluation`, `trade-proposal`, `outcome-reconciliation` recurrences have no `required_capabilities:` block. The architectural docs in prompts (`api/agents/prompts/chat/workspace.py:301`, `api/agents/prompts/platforms.py:46`) explicitly call out `required_capabilities: ["read_trading"]` for trading recurrences — but the actual bundle YAML doesn't include them.

2. **Recurrence dataclass drops them**: [api/services/recurrence.py::Recurrence](../../api/services/recurrence.py) has fields `{slug, schedule, prompt, mode, paused, options}`. **No `required_capabilities` field.** Even if the bundle YAML declared them, the parser would drop them.

3. **Reviewer never sees them**: `api/agents/reviewer_agent.py` has zero references to `required_capabilities`. The Reviewer's context envelope (built by invocation_dispatcher around line 230) doesn't carry capabilities.

4. **DispatchSpecialist input schema doesn't accept them**: [dispatch_specialist.py:91-118](../../api/services/primitives/dispatch_specialist.py#L91) defines properties `{role, brief, model}`. **No `required_capabilities` field.** Even if the Reviewer knew the capabilities, it couldn't pass them to the specialist via the tool call.

5. **`get_headless_tools_for_agent` accepts `task_required_capabilities`** as a parameter (registry.py:546) but **dispatch_specialist doesn't pass it** (line 184–186 passes only `agent_role` which doesn't even exist).

**The capability-flow design exists in prompts and helper signatures, but the runtime path is never wired through.** It's a half-finished feature.

### The composite effect

The trade-producing path:

```
signal-evaluation cron fires
    → invocation_dispatcher.dispatch(trigger="reactive")
    → invoke_reviewer with recurrence_prompt context [L1 fixed today]
    → Reviewer reads bars from /workspace/context/trading/{ticker}.yaml
    → bars come from track-universe which needs platform_trading_get_market_data
    → track-universe Reviewer calls DispatchSpecialist(role="researcher", brief="fetch bars...")
    → dispatch_specialist tries to resolve tools [L2 broken: signature error]
    → IF L2 were fixed: specialist would get HEADLESS_PRIMITIVES, no platform tools [L3: capability never flows]
    → result: substrate never gets fresh bars → signal-evaluation has no data to evaluate → no signal fires → no trade-proposal → no paper order
```

**Three layers, each one of which alone is enough to block the entire trade-producing loop.** The trilogy fix unblocked layer 1. Layers 2 and 3 remain.

## Friction

The investigation itself was clean — about 30 min of code reading produced full traceability. The friction is the *finding*: a 3-layer-deep structural gap that's been silently broken for 3+ days, layered on top of a prior corruption pattern that hid these layers for the prior week. KVK's "weeks of wait-and-see" is structurally consistent with what we now see — the system has never been *able* to produce a trade, not for lack of trying or patience.

The deeper friction is that L3 isn't a bug per se — it's an unfinished implementation. The architectural docs in YARNNN's prompts describe `required_capabilities` correctly. The parameter exists in the helper function signature. The bundle's prompt-architecture (workspace.py:300-304) describes the pattern. But the actual data path from YAML to specialist never got plumbed. Whoever last shipped DispatchSpecialist (PR #9 squash `42725c6`) shipped both halves — the dispatch primitive *and* the capability-flow gap — together, and no test exercised the trade-producing path end-to-end to catch it.

## Hypothesis

**For the "no trades" surface on kvk's workspace, all four F1 hypotheses are in play in layers:**

- **F1-A (environmental)** — partially relevant: the trade-producing recurrences fire on US-market crons (signal-evaluation at 08:05 UTC = 17:05 KST), so KVK's lived "I check in the morning, nothing happened" maps to a structurally-correct daily-cycle pattern. NOT the load-bearing cause.
- **F1-B (systematic-dispatcher)** — FIXED today by trilogy. Was 100% load-bearing pre-fix on this workspace. Now resolved.
- **F1-C (systematic-judgment: Reviewer correctly declined)** — UNTESTED because the system never reached the judgment stage (L2/L3 block before bars are even fetched).
- **F1-D (systematic-config)** — **NEW shape**: the gap isn't tightness of `_risk.md` or AUTONOMY ceiling — those would matter only after a proposal exists. The config gap is at the bundle level (`_recurrences.yaml` missing `required_capabilities:` blocks) AND at the framework level (Recurrence dataclass + Reviewer prompt + DispatchSpecialist schema all missing the capability-flow plumbing).

**The right framing**: F1-D is structural-config not operator-config. The operator hasn't authored anything wrong; the bundle and framework haven't completed the wiring. Per the access matrix, fixing L2 is Claude code-level work; fixing L3 needs operator-authored bundle changes + framework-level wiring decisions.

## Counterfactual (Objective B)

If L1 + L2 + L3 are all fixed, kvk's next morning would actually produce trade activity for the first time. Without these fixes, **another week of wait-and-see produces another week of nothing.** The B-product hypothesis (autonomous trade execution with Reviewer-gated discipline) cannot be tested at all until the data flow reaches the Reviewer's decision surface — currently it doesn't.

The harsher counterfactual: **the alpha-1 SCOPE.md success contract (money-truth + cost-truth convergence over 90 days) requires the trade-producing loop to work**. Until L2 + L3 ship, the 90-day clock cannot meaningfully start. The trilogy fix shipped today moves us from "the loop is corrupted" to "the loop is structurally incomplete." That's progress, but it's not "trades are now flowing."

## What iter-3 needs to ship

Sized for a focused session, in order:

1. **L2 minimal fix** — `dispatch_specialist.py:184-186` proper call: pass `agent={"role": role}` (instead of `agent_role=role`) so the function at least doesn't TypeError. Specialist will get base HEADLESS_PRIMITIVES even without capabilities — this is a precondition for L3 to matter.

2. **L3a feature-wiring** (the harder part) — pick a design:
   - **Option A** (minimal): plumb `required_capabilities` field through Recurrence dataclass → dispatcher context → invoke_reviewer → reviewer system prompt mention → DispatchSpecialist tool schema accepts it → dispatch_specialist passes it through. Reviewer LLM is responsible for choosing which capabilities to pass when dispatching.
   - **Option B** (auto-derive): dispatcher passes capabilities into the Reviewer's context but the Reviewer doesn't have to pass them through — dispatch_specialist receives them via the auth/context object the Reviewer's tool calls inherit. Less Reviewer-prompt-burden, more implicit data flow.
   - Option B is probably the right shape — capabilities are a property of the recurrence, not a Reviewer judgment. But this is a design decision that wants a small ADR (or amendment to ADR-227) before code.

3. **L3b bundle authoring** — add `required_capabilities: [read_trading]` (and `write_trading` for trade-proposal) to `track-universe`, `signal-evaluation`, `trade-proposal`, `outcome-reconciliation` in `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml`. Then propagate to kvk's live `/workspace/_recurrences.yaml` (since a bundle re-fork would purge operator-authored MANDATE).

4. **End-to-end test** — manually fire `track-universe` post-fix; expect to see actual Alpaca bars land in `/workspace/context/trading/{ticker}.yaml`. Then manually fire `signal-evaluation`; expect either signal-fire+trade-proposal OR a Reviewer prose decline against `principles.md` (F1-C). Either outcome closes the gap.

**Iter-3 scope estimate**: 1-2 hours focused work + the small ADR pass for L3 design. Not session-fatigued patchwork.

## Links

- **Iter-1 (predecessor)**: [2026-05-13-iter1-e2e-aliveness-kvk.md](./2026-05-13-iter1-e2e-aliveness-kvk.md)
- **L2 root cause**: [api/services/primitives/dispatch_specialist.py:184-186](../../api/services/primitives/dispatch_specialist.py#L184) — `agent_role=role` kwarg mismatch
- **L2 receiving function**: [api/services/primitives/registry.py:540-573](../../api/services/primitives/registry.py#L540) — no `agent_role` parameter; expects `agent: dict` + `task_required_capabilities: list[str]`
- **L3a Recurrence dataclass**: [api/services/recurrence.py::Recurrence](../../api/services/recurrence.py) — missing `required_capabilities` field
- **L3a DispatchSpecialist schema**: [api/services/primitives/dispatch_specialist.py:91-118](../../api/services/primitives/dispatch_specialist.py#L91) — missing `required_capabilities` property
- **L3a Reviewer prompt**: `api/agents/reviewer_agent.py` — zero references to `required_capabilities`
- **L3b bundle YAML**: [docs/programs/alpha-trader/reference-workspace/_recurrences.yaml](../../docs/programs/alpha-trader/reference-workspace/_recurrences.yaml) — trading recurrences missing `required_capabilities:` blocks
- **Architectural docs that describe the intended flow** (where the design lives but the wiring doesn't): `api/agents/prompts/chat/workspace.py:300-304`, `api/agents/prompts/platforms.py:39-46`, `api/services/platform_tools.py::get_platform_tools_for_agent` docstring
- **Origin commit of L2 bug**: `42725c6` (PR #9 squash, 2026-05-10) — DispatchSpecialist introduced
- **F1 failure class doc**: [DUAL-OBJECTIVE-DISCIPLINE.md §"Named failure classes"](../DUAL-OBJECTIVE-DISCIPLINE.md#named-failure-classes) — this iter refines F1-D from "operator-config" to "structural-config-or-config-gap"
- **Related observation** (echo of the symptom): [2026-04-28-tracker-tool-surface-defect.md](./2026-04-28-tracker-tool-surface-defect.md) — same shape ("tool not in surface") surfaced previously on a different code path; that fix shipped as `fa660f7` but doesn't cover the specialist-sub-call path
