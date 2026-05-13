# ADR-269: Capability-Flow Wiring — Recurrence → Reviewer → Specialist Tool Surface

**Status**: Proposed 2026-05-13. Implementation in same commit as the ADR (atomic).

**Companion**: this ADR closes iter-2's L3 (the third of three layers identified as blocking trade execution on kvk's workspace) per [iter-2 observation](../alpha/observations/2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md). L1 was iter-1's Reviewer dispatcher trilogy. L2 was iter-3's dispatch_specialist signature fix. L3 is this ADR.

**Supersedes**:
- The implicit "specialists inherit capabilities by role alone" model implied by ADR-176 read in isolation. The role-only model is correct for the *universal* identity layer but missing the program-specific overlay that ADR-227 promised but never wired end-to-end.

**Amends**:
- ADR-227 (per-task capability augmentation) — preserved as the design intent; this ADR ships the runtime wiring that ADR-227 described but didn't complete. ADR-227's docstring in `services/platform_tools.py::get_platform_tools_for_agent` explicitly says "task_required_capabilities" should flow from "the recurrence's required_capabilities: block declared on the YAML recurrence body per ADR-231 / ADR-261, ICP-specific" — the receiving function accepts the param; this ADR ships the chain that delivers it.
- ADR-258 (revised — Reviewer as personified chat-mode operator with curated REVIEWER_PRIMITIVES) — preserved. Reviewer still cannot call `platform_trading_*` directly; this ADR widens DispatchSpecialist's input schema so the Reviewer can dispatch a specialist with the right tool surface.
- ADR-261 D1 (recurrences shape `{slug, schedule, mode, prompt}`) — preserved as load-bearing fields. `required_capabilities` lands as an optional metadata field that does NOT alter execution shape; it's a tool-surface hint consumed at specialist-dispatch time.

**Preserves**:
- FOUNDATIONS Axiom 4 (Trigger) + Axiom 5 (Mechanism). The capability declaration doesn't change *when* recurrences fire or *what* dispatch mechanism runs; it adjusts the tool surface available during the specialist sub-LLM-call.
- ADR-176 universal specialist roster. The role-level capability list (researcher = web_search/read_workspace/...) stays as-is; this ADR adds a per-recurrence overlay merged into the union at dispatch time.
- ADR-264 SyncPlatformState mechanical mirrors — unchanged. They bypass the capability gate entirely (they call `handle_platform_tool` directly, with auth+platform_connections as the only gate).
- ADR-268 market-context-aware recurrences — unchanged. Schedule + capabilities are independent axes on the recurrence record.

---

## 1. Why this ADR

iter-2's observation identified that trade execution on kvk's workspace was blocked by three independent layers. Iter-1 fixed L1 (Reviewer dispatcher trilogy). Iter-3 fixed L2 (DispatchSpecialist signature) + the orthogonal market-hours problem. L3 — the capability-flow wiring — remained open.

The architecture per ADR-176 + ADR-227 is sound on paper:
- ADR-176 declares universal specialist roles (researcher, analyst, tracker, writer, designer, reporting) with ICP-agnostic capability lists. Trading tools (`platform_trading_*`) are not in any role's base capability list because trading is a program-specific concern, not a universal specialist trait.
- ADR-227 declares the overlay mechanism: recurrence YAML's `required_capabilities:` block declares the program-specific capabilities a specialist needs to do this recurrence's work. The framework merges role-level + recurrence-level into the union, and `get_platform_tools_for_capabilities` returns the matching tool definitions (filtered by the user's active `platform_connections`).

But the runtime path that delivers ADR-227's intent was never wired end-to-end. Five distinct gaps:

1. **Bundle `_recurrences.yaml` doesn't declare `required_capabilities:`** on the trading recurrences.
2. **`Recurrence` dataclass drops them** at parse time — the field doesn't exist.
3. **`invocation_dispatcher.dispatch` doesn't carry them** into the Reviewer's context envelope.
4. **`DispatchSpecialist` tool input schema doesn't accept them** — the Reviewer has no way to pass capability declarations to the specialist sub-LLM-call.
5. **`dispatch_specialist.handle_dispatch_specialist` doesn't pass `task_required_capabilities`** to `get_headless_tools_for_agent` (even though the receiving function accepts it).

Each gap alone breaks the chain. All five must close for a specialist dispatched by the Reviewer for a trading recurrence to receive `platform_trading_get_market_data` in its tool schema.

This ADR ships the chain.

---

## 2. The single principle

> **A recurrence may declare `required_capabilities: [list]` as program-specific tool requirements. The dispatcher carries the declaration into the Reviewer's context envelope. When the Reviewer dispatches a specialist (via `DispatchSpecialist`), the specialist's tool surface is the union of the specialist role's universal capabilities + the recurrence's declared capabilities. The Reviewer may extend the list per dispatch (e.g., add `web_search` for a specific brief) but cannot remove the recurrence's declared baseline.**

Three consequences:

1. **One new optional field on `Recurrence`**: `required_capabilities: list[str]`. Default `[]`. Operator-authored on the YAML.
2. **One new optional field on `DispatchSpecialist` input schema**: `required_capabilities: list[str]`. Reviewer fills it; the Reviewer's system prompt instructs it to include the recurrence's declared list at minimum.
3. **One union at the bottom of the chain**: `get_headless_tools_for_agent(agent={"role": role}, task_required_capabilities=union)` — already accepts the param; this ADR's job is to deliver it correctly.

---

## 3. Decision

### D1 — `Recurrence` dataclass gains `required_capabilities: list[str]`

```python
@dataclass
class Recurrence:
    slug: str
    schedule: Schedule = None
    prompt: str = ""
    mode: str = DEFAULT_RECURRENCE_MODE
    # ADR-269: program-specific capability declarations. Operator-authored
    # on the recurrence YAML body. When the Reviewer dispatches a specialist
    # for this recurrence, these capabilities are the floor of the
    # specialist's tool surface (specialist role caps + these). Empty list
    # for recurrences that don't need program-specific tools (housekeeping,
    # daily summaries, market-agnostic work).
    required_capabilities: list[str] = field(default_factory=list)
    paused: bool = False
    # ... existing fields ...
```

Parser at `parse_recurrences_yaml` accepts `required_capabilities:` as a list of strings. Invalid types (non-list, non-string members) get coerced to `[]` with a warning. Field is fully optional — every existing bundle continues to parse cleanly.

### D2 — `invocation_dispatcher.dispatch` threads capabilities into the Reviewer context

The dispatcher already builds a context envelope for `invoke_reviewer`. Extend the envelope:

```python
reviewer_output = await invoke_reviewer(
    client=client,
    user_id=user_id,
    trigger=trigger,
    context={
        "recurrence_prompt": prompt,
        "recurrence_slug": recurrence.slug,
        "recurrence_required_capabilities": list(recurrence.required_capabilities),  # NEW
        "options": dict(recurrence.options) if recurrence.options else {},
    },
)
```

The Reviewer reads this from its context envelope when composing its system prompt + when calling DispatchSpecialist. Threading is one-way: the dispatcher writes, the Reviewer reads. No mutation flows back through context.

### D3 — `DispatchSpecialist` input schema gains `required_capabilities`

```python
DISPATCH_SPECIALIST_TOOL = {
    "name": "DispatchSpecialist",
    "input_schema": {
        "type": "object",
        "properties": {
            "role": {...},
            "brief": {...},
            "model": {...},
            "required_capabilities": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Capabilities the specialist needs to do this brief. "
                    "Pass through the recurrence's declared "
                    "required_capabilities at minimum; you may extend the "
                    "list per dispatch (e.g., add web_search for a "
                    "brief that needs web research on top of the recurrence's "
                    "declared trading capabilities). The framework merges "
                    "these with the specialist role's universal capabilities."
                ),
            },
        },
        "required": ["role", "brief"],
    },
}
```

`required_capabilities` is optional in the schema. Missing/empty → specialist gets only the role's universal capabilities (no program-specific tools).

### D4 — `handle_dispatch_specialist` passes `task_required_capabilities`

```python
tools = await get_headless_tools_for_agent(
    db_client,
    user_id,
    agent={"role": role},
    task_required_capabilities=list(input.get("required_capabilities") or []),
)
```

This is the load-bearing wire. `get_headless_tools_for_agent` already merges role-level + task-level capabilities and calls `get_platform_tools_for_capabilities` which adds the platform-tool definitions filtered by the user's connected platforms. The chain has always been *capable* of working; ADR-269 is the wiring that delivers the input.

### D5 — Reviewer system prompt instructs capability pass-through

Add a short paragraph to `cockpit_awareness.py` or wherever the Reviewer's DispatchSpecialist usage is described:

> When dispatching a specialist via DispatchSpecialist, declare the
> capabilities the specialist needs by passing `required_capabilities`.
> The recurrence's own `required_capabilities` (if any) are surfaced to
> you in the context envelope as `recurrence_required_capabilities` —
> pass those through at minimum. You may extend the list per dispatch
> (e.g., add `web_search` if the specific brief needs web research on
> top of the recurrence's declared trading capabilities).

This makes the hybrid ownership explicit: recurrence declares the floor, Reviewer can extend per-dispatch.

### D6 — Alpha-trader bundle declares trading capabilities

```yaml
# docs/programs/alpha-trader/reference-workspace/_recurrences.yaml

- slug: track-universe
  required_capabilities: [read_trading]
  # ...

- slug: signal-evaluation
  required_capabilities: [read_trading]
  # ...

- slug: track-regime
  required_capabilities: [read_trading]
  # ...

- slug: outcome-reconciliation
  required_capabilities: [read_trading]
  # ...

- slug: trade-proposal
  required_capabilities: [read_trading, write_trading]
  # ...
```

Mechanical mirrors (`track-positions`/`track-orders`/`track-account`) do NOT declare `required_capabilities` because they bypass the gate entirely (SyncPlatformState calls `handle_platform_tool` directly per ADR-264). Adding the declaration there would be dead code.

Daily housekeeping (`narrative-digest`, `morning-reflection`, `morning-calibration`, `proposal-cleanup`, `pre-market-brief`, `weekly-performance-review`, `quarterly-signal-audit`) do NOT declare trading capabilities — they don't dispatch specialists with broker access. Reading `_money_truth.md` for calibration is filesystem access; ReadFile is in REVIEWER_PRIMITIVES already.

### D7 — AUTONOMY ceiling flipped to `autonomous` (operator-authored, in same iter-4 commit)

Per operator's iter-4 design call (2026-05-13 session), kvk's posture goes from `bounded @ $200` (Phase 0 paper-seed) to `autonomous` (no ceiling cap). This is an operator authorship change to `_autonomy.yaml` + matching prose update to `AUTONOMY.md`. **`never_auto: [close_position_market, cancel_other_orders]` survives** as a hard safety list regardless of `autonomous` posture.

Bundle defaults remain `bounded @ $200` for future alpha personas — the autonomous flip is operator-authored for kvk specifically, not bundle-default. (Implementation note: this means the operator-side edit happens after `reset.py kvk --confirm` re-forks the bundle. Operator either runs the edit manually OR we add an `--autonomy` flag to reset.py / a post-fork hook. For iter-4 simplicity, the operator-side AUTONOMY edit is applied via a small standalone script `scripts/apply_autonomous_posture.py` invoked once after reset.)

### D8 — Implementation surface

Atomic single commit (per Singular Implementation + iter-3 pattern):

1. **`api/services/recurrence.py`** — `Recurrence.required_capabilities` field + parser. ~10 LOC.
2. **`api/services/invocation_dispatcher.py`** — thread capabilities into invoke_reviewer context. ~3 LOC.
3. **`api/agents/reviewer_agent.py`** — read `recurrence_required_capabilities` from context envelope; surface to model via system prompt. ~5 LOC.
4. **`api/agents/cockpit_awareness.py`** (or equivalent prompt module) — add D5 capability-pass-through paragraph. ~10 LOC.
5. **`api/services/primitives/dispatch_specialist.py`** — `DISPATCH_SPECIALIST_TOOL` schema gains `required_capabilities`; handler passes to `get_headless_tools_for_agent`. ~10 LOC.
6. **`docs/programs/alpha-trader/reference-workspace/_recurrences.yaml`** — D6 declarations. ~10 line edits.
7. **`docs/programs/alpha-trader/reference-workspace/context/_shared/_autonomy.yaml`** — flip `delegation: bounded` → `delegation: autonomous`. ~1 LOC.
8. **`docs/programs/alpha-trader/reference-workspace/context/_shared/AUTONOMY.md`** — update Phase progression prose to reflect operator's autonomous posture decision + preserve the original Phase-0 → Phase-1 → Phase-2 framing as historical reference. ~20 LOC.
9. **`api/test_adr269_capability_flow.py`** (new regression gate) — assert: dataclass carries field, parser reads it, dispatcher threads it, schema accepts it, alpha-trader bundle declares correctly. ~80 LOC, ~6-8 assertions.

Total: ~150 LOC across 9 files. One commit.

### D9 — Operator-side post-deploy validation

After Render auto-deploys:

1. `reset.py kvk --confirm` — re-forks updated bundle (new required_capabilities + autonomous flip).
2. `connect.py kvk` — re-attach Alpaca paper EE8K.
3. `verify.py kvk` — expect 32/32 green.
4. **Observation window**: tonight 22:30 KST onward. Mechanical mirrors fire immediately. Signal-evaluation fires at 22:45 KST. If track-universe at 22:45 successfully calls `platform_trading_get_market_data` via a dispatched specialist and writes fresh bars to `/workspace/context/trading/{ticker}.yaml`, ADR-269 is validated end-to-end. The downstream signal-eval at the same minute will read those bars; if any of the 5 signals fire on the bar conditions, trade-proposal will emit a real ProposeAction; AI Reviewer will judge; under `autonomous`, approve → execute → paper Alpaca order.

---

## 4. Out of scope (explicit deferrals)

- **Capability inheritance across nested DispatchSpecialist calls**. The MVP wires one Reviewer-direct dispatch. If a specialist itself wanted to dispatch a sub-specialist (currently impossible — specialists don't have DispatchSpecialist in their tool surface), the inheritance shape would be its own design question. Not in scope.
- **Per-tool-name granularity** (e.g., `required_capabilities: [platform_trading_get_market_data]` instead of `[read_trading]`). Capability is the bundle's already-existing unit per MANIFEST.yaml's `capabilities:` block. Tool-name level would force operators to know exact tool names; capability is operator-readable.
- **Runtime cap validation** (e.g., dispatcher rejects a recurrence whose `required_capabilities` references a capability not in any active bundle). Surface that at YAML-edit time or at `_locks.yaml` validation; not at dispatch time where the failure shape is worse.
- **Reviewer-level capability declarations** for Reviewer's own tool surface (separate from specialist dispatch). REVIEWER_PRIMITIVES per ADR-258 is curated allowlist; widening would be its own ADR.
- **Workspace-level overrides** of bundle's `required_capabilities` declarations. Operator wanting different capabilities runs a different program; bundle-level is the right shape.

---

## 5. Dimensional classification (FOUNDATIONS Axiom 0)

**Primary**: **Mechanism** (Axiom 5) — refines the tool surface available during a specialist sub-LLM-call without changing the dispatch mechanism itself.

**Secondary**: **Identity** (Axiom 2) — preserves ADR-176 universal specialist roster while overlaying program-specific tool needs at the recurrence level (which is identity-of-work, not identity-of-actor).

**Tertiary**: **Substrate** (Axiom 1) — the `required_capabilities:` field is operator-authored filesystem-native declaration; the runtime resolves it at dispatch time.

---

## 6. Why this won't reinvent prior work

Audit done 2026-05-13:

- **ADR-227 (per-task capability augmentation)** — declared the design intent + ensured `get_platform_tools_for_agent` accepts `task_required_capabilities`. This ADR ships the wiring ADR-227 promised. **No conflict; this ADR is ADR-227's completion.**
- **`api/services/platform_tools.py::get_platform_tools_for_capabilities`** — existing function that takes a capability list + auth and returns matching tool definitions filtered by connected platforms. This ADR is the chain that delivers the capability list to that function with the right values.
- **`api/agents/prompts/chat/workspace.py:301`** + **`api/agents/prompts/platforms.py:46`** — existing prompt sections that document the `required_capabilities` pattern for the Reviewer / operator-via-chat (when they're authoring new recurrences). The pattern was described but never enforced. ADR-269 closes the loop: the documented pattern now does work at runtime.
- **No prior ADR has shipped capability-flow wiring**. ADR-176 + ADR-227 specified the architecture; ADR-269 is the implementation.

---

## 7. Revision history

| Date | Change |
|------|--------|
| 2026-05-13 | v1 Proposed. Same-day implementation alongside operator's autonomous-delegation flip. iter-4 of the steered closed-loop development pass. |
