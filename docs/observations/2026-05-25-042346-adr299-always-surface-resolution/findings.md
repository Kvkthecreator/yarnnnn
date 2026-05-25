# ADR-299 always-surface resolution — Hat-B finding (third-order)

**Hat**: External Developer of the System (Hat B).

**Captured**: 2026-05-25 by canary v3 evidence + DB inspection + source-level investigation.

**Trigger**: ADR-299 Phase 4 canary v3 produced a textbook-quality REJECT verdict in `judgment_log.md` (5 anti-pattern citations against a fresh test piece) but did NOT fire `platform_email_send_to_operator`. Operator inbox-check confirmed no email arrived. Empirical evidence: the Reviewer did real work, persona-frame teaches the opt-in awareness, `_preferences.yaml` had the opt-in active — yet the tool wasn't called.

**Predecessor (recursing one level deeper)**:
- [`2026-05-24-042952-adr299-class-naming-redundancy/`](../2026-05-24-042952-adr299-class-naming-redundancy/) — Discovery note 1 (class-naming)
- [`2026-05-24-050631-adr299-wire-redundancy/`](../2026-05-24-050631-adr299-wire-redundancy/) — Discovery note 2 (wire-pointing)
- [`2026-05-24-054214-adr299-phase4-canary-red/`](../2026-05-24-054214-adr299-phase4-canary-red/) — Phase 4 RED outcome (initial finding before resolution path investigation)

## Finding

**Kernel-universal capabilities (the `operator-addressing` class established in ADR-299 Discovery note 2) require explicit recurrence/hook `required_capabilities` opt-in to surface in the Reviewer's tool — contradicting the architectural commitment that they are "always available."**

The resolution path:

```python
# api/services/platform_tools.py::get_platform_tools_for_capabilities
allowed_tool_names: set[str] = set()
for capability in capabilities:  # <-- only loops over EXPLICITLY requested capabilities
    # ...kernel-CAPABILITIES dict no-wire-gate branch (corrected by Discovery note 2)
    # ...bundle-specific CAPABILITY_PROVIDER_MAP branch
```

The loop iterates `capabilities` — the list of capabilities the recurrence/hook explicitly requested via `required_capabilities`. **If the list is empty, NO capabilities resolve — including kernel-universal ones.**

The substrate-event wake path makes this worse: `api/services/wake.py:1464` hardcodes `recurrence_required_capabilities: []` when invoking the Reviewer for a substrate-event hook. So **every substrate-event Reviewer wake gets `capabilities=[]` regardless of what the hook declared** — and since the resolution path only surfaces tools for explicitly requested capabilities, **kernel-universal capabilities never reach substrate-event-wake Reviewer surfaces at all today**.

### Evidence chain from canary v3

1. ✅ ADR-299 Discovery note 2 fix landed (commit `f1f77e6`): `send_operator_email` in kernel CAPABILITIES dict with `platform_connection_requirement: None`
2. ✅ ADR-299 Phase 2 + Phase 3 landed (`50d37a8` + `0248b56`): `operator_notifications:` schema in `_preferences.yaml` + persona-frame awareness
3. ✅ Operator-proxy synthesized `pre_ship_audit_summary active: true` in live `_preferences.yaml` (canary v1, revision `f02d7c7b`)
4. ✅ Hooks updated to current bundle template with ReturnVerdict structural binding (canary v2, revision `8195faee`)
5. ✅ Reviewer wake fired on fresh piece with intentional voice issues (canary v3, dedup_key `92a19120`)
6. ✅ Reviewer rendered material REJECT verdict in `judgment_log.md` (revisions `53f1b342` + `9b15410a`)
7. ✅ Reviewer updated `standing_intent.md` per discipline contract (revision `c22618eb`)
8. ❌ **`platform_email_send_to_operator` not called** — no email in operator inbox
9. **Root cause traced**: substrate-event wake passes `recurrence_required_capabilities: []`; the resolution path only surfaces tools for capabilities in this list; kernel-universal capabilities like `send_operator_email` therefore don't surface; Reviewer cannot call a tool that isn't in its surface.

### Why the redundancy escaped Discovery notes 1 + 2

Discovery note 1 corrected class-naming (kernel-universal class lives in existing CAPABILITIES dict, not parallel registry). Discovery note 2 corrected wire-pointing (system-keyed Resend, not per-user OAuth). **Neither checked whether the resolution path actually surfaces kernel-universal capabilities to recurrence/hook wakes that don't explicitly request them.**

The capability is correctly registered. The wire is correctly pointed. **But the resolution path only loops over what the recurrence asked for** — and the recurrence has no reason to ask for `send_operator_email` because the persona-frame describes it as "always available via opt-in," implying the tool surface itself manages availability based on opt-in.

The contradiction: ADR-299 D1 says kernel-universal capabilities are "available across all bundle archetypes." ADR-299 D4 says opt-in via `_preferences.yaml` is the "standing approval." But the runtime resolution path treats kernel-universal capabilities the same as bundle-specific ones — opt-in by `required_capabilities` declaration on the recurrence/hook. The two layers contradict.

### Architectural fix shape (Path Y — recommended)

**Modify `get_platform_tools_for_capabilities` to auto-include ALL kernel-universal-no-wire-gate capabilities into the result, regardless of whether they appear in the requested `capabilities` list.**

Pseudo-shape:

```python
async def get_platform_tools_for_capabilities(auth, capabilities):
    # ... fetch connected_providers ...
    allowed_tool_names = set()

    # Auto-include kernel-universal-no-wire-gate capabilities — these are
    # "always available" per ADR-299 D1, NOT opt-in per-recurrence.
    # Wire-gated kernel capabilities still require explicit request (preserves
    # operator authority on third-party-affecting capabilities).
    for cap_name, cap_decl in KERNEL_CAPABILITIES.items():
        if cap_decl.get("platform_connection_requirement") is None:
            tools = PLATFORM_TOOLS_BY_CAPABILITY.get(cap_name)
            if tools:
                allowed_tool_names.update(tools)

    # Existing loop for explicitly-requested capabilities (wire-gated bundle +
    # wire-gated kernel) unchanged.
    for capability in capabilities:
        # ... kernel-dict-with-wire-gate + bundle-provider-map branches ...
```

**This is the same fix shape as Discovery note 2's "no-wire-gate kernel branch" addition — except applied universally instead of only when the capability is explicitly requested.**

### Hat-A correction details

Files:
- `api/services/platform_tools.py::get_platform_tools_for_capabilities` — add the auto-include loop before the existing capability-iteration loop. ~10 LOC.
- `api/test_adr299_kernel_universal_capability.py` — extend with assertion: when `capabilities=[]` (no explicit request) AND kernel-universal-no-wire-gate exists, the tool surfaces. Update existing test `test_resolution_surfaces_send_operator_email_unconditionally` accordingly.
- `docs/adr/ADR-299` — Discovery note 3 documenting the resolution-path correction.

### What this does NOT require

- No bundle template changes (Path Y is "always available" — bundles don't opt-in)
- No `wake.py` line 1464 change (passing `recurrence_required_capabilities: []` is fine because the always-available branch doesn't depend on it)
- No persona-frame prose change (the "always available" framing was correct; the runtime didn't honor it; runtime now will)
- No new env vars, no new schema, no new tables

### Recursive discipline lesson (fourth this session)

The four corrections this session, ordered by recursion depth:

1. **Discovery note 1 (yesterday)**: class-naming — prefer new field on existing class over new class when novelty fits
2. **Discovery note 2 (today AM)**: wire-pointing — when correcting a class, verify the wire each member points at, not just the abstract class
3. **Discovery note 3 (this finding)**: resolution-path — when correcting class + wire, verify the runtime resolution path actually surfaces the capability to callers that should have it, not just that the capability is registered with the right shape
4. **(Pre-emptive next discovery if it happens)**: surface verification ≠ behavior verification — surfacing the capability doesn't guarantee the Reviewer calls it; behavior may require additional prompt or feedback loop

Each lesson generalizes one level above the previous. The honest meta-lesson:

> **When verifying a capability's end-to-end correctness, walk the full chain in BOTH directions: from registry → wire → resolution → tool surface → prompt awareness → behavior. Verifying any single link doesn't validate the chain.**

The morning's Discovery note 2 named "verify load-bearing facts before designing on top of them" — that lesson was correct but scoped to research-on-existing-code. This session's evidence extends it: **verify load-bearing facts BIDIRECTIONALLY through the full execution chain**, not just the layer being corrected.

## Addendum — fourth-recursion discovery mid-fix (2026-05-25)

While implementing the Hat-A always-surface fix in `get_platform_tools_for_capabilities`, a **fourth-recursion redundancy** surfaced. The fix as originally scoped (Path Y operator-approved) **would not have made canary v4 close green either**, because:

**Discovery 4**: The Reviewer's tool surface is NOT built via `get_platform_tools_for_capabilities`. `api/agents/reviewer_agent.py:1373` reads:

```python
tools = list(REVIEWER_PRIMITIVES) + [RETURN_VERDICT_TOOL]
```

The Reviewer gets exactly `REVIEWER_PRIMITIVES` from `services/primitives/registry.py:394`, plus `RETURN_VERDICT_TOOL`. **Platform tools like `platform_email_send_to_operator` are NOT in `REVIEWER_PRIMITIVES`** and never were.

So ADR-299 Phase 1's wire-up was structurally incomplete from day one:
- ✅ Tool added to `EMAIL_TOOLS` (agent-path platform tools list)
- ✅ Capability registered in kernel `CAPABILITIES` dict
- ✅ Handler branch added to `_handle_email_tool`
- ✅ Resolution path extended (Discovery note 2)
- ❌ **Tool NEVER added to `REVIEWER_PRIMITIVES`** — the registry the Reviewer's surface is built from

**The Reviewer never had access to `platform_email_send_to_operator` at all**, regardless of operator opt-in, regardless of wire correctness, regardless of resolution-path always-surface fix. Four cascading corrections all addressing the wrong layer.

### Revised fix scope (Hat-A Commit 2)

Two changes, both load-bearing:

1. **`api/services/platform_tools.py`** — lift `platform_email_send_to_operator` tool definition out of the `EMAIL_TOOLS` list literal as a named module-level constant `EMAIL_SEND_TO_OPERATOR_TOOL`, declared BEFORE `EMAIL_TOOLS` so the list can reference it without forward-reference issues. Also update the tool description to reflect the system Resend wire (was still saying "operator's connected Resend account" — Discovery note 2 prose).

2. **`api/services/primitives/registry.py::REVIEWER_PRIMITIVES`** — add `EMAIL_SEND_TO_OPERATOR_TOOL` to the list. Tool count goes 21 → 22.

3. **Plus the always-surface fix** in `get_platform_tools_for_capabilities` from earlier work — KEEP it. Structurally correct for the agent path even if not the Reviewer-specific bug. Prevents the same class of bug from affecting agent tool surfaces in the future.

### Why this finally closes the Reviewer canary

After this fix:
- Reviewer's tool surface includes `platform_email_send_to_operator` (always, regardless of recurrence/hook capabilities request)
- Dispatch chain unchanged: `is_platform_tool("platform_email_send_to_operator")` returns True → routes to `handle_platform_tool` → routes to `_handle_email_tool::send_to_operator` early-return branch → `system_send_email` via deployed RESEND_API_KEY
- Operator's `pre_ship_audit_summary active: true` in `_preferences.yaml` is the standing approval per ADR-299 D4
- Persona-frame Phase 3 prose teaches the Reviewer to call the tool when judgment cycle produces material worth surfacing

Canary v4 with a fresh test piece (similar to canary v3's pattern) should now produce: REJECT verdict in judgment_log.md AND a fired `platform_email_send_to_operator` call AND an email in operator's inbox.

### Updated recursion-lesson table

| Depth | Lesson | This-session example |
|---|---|---|
| 1 | Class-naming redundancy: prefer new field on existing class over new class | Yesterday's `KERNEL_UNIVERSAL_CAPABILITIES` parallel registry → merged into existing `CAPABILITIES` dict |
| 2 | Wire-pointing: when correcting class, verify the wire each member points at | Today AM's per-user OAuth wire → corrected to system Resend wire |
| 3 | Resolution-path always-surface: when correcting class + wire, verify the resolution path actually surfaces the capability | This finding's `get_platform_tools_for_capabilities` always-include kernel-universal pass |
| **4** | **Tool surface for non-agent actors has DIFFERENT registries**: verify each actor-specific tool registry includes the capability separately | This addendum: `REVIEWER_PRIMITIVES` is the Reviewer's surface, NOT `get_platform_tools_for_capabilities` output |

### Meta-meta-lesson (the discipline rule named more precisely)

The morning's "walk the full chain" lesson stated: *"registry → wire → resolution → tool surface → prompt awareness → behavior."* That was correct in spirit but the **"tool surface" link is plural** — different actors have different surface-assembly paths:

- Agent's tool surface: `get_platform_tools_for_agent` → `get_platform_tools_for_capabilities` (kernel CAPABILITIES dict + bundle MANIFEST + platform_connections)
- Reviewer's tool surface: `REVIEWER_PRIMITIVES` (curated subset from `services/primitives/registry.py`)
- ChatAgent's tool surface: `CHAT_PRIMITIVES` (similar shape to REVIEWER_PRIMITIVES)
- Sub-LLM specialist (DispatchSpecialist): `HEADLESS_PRIMITIVES` or role-specific subset

**Adding a kernel-universal capability requires explicit inclusion in EACH actor's surface registry — they don't auto-flow from kernel `CAPABILITIES` dict to actor surfaces.**

This generalizes the morning's discipline rule to its load-bearing precise form:
> Verify the capability is in EVERY actor's surface that should be able to call it. The kernel `CAPABILITIES` dict is the registry of "what exists"; per-actor surface registries (REVIEWER_PRIMITIVES, CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, role-bundles) are the registries of "what each actor can call." A capability registered in the former without inclusion in the relevant latter is structurally unreachable from that actor.

## Status

**OPEN** — Hat-A correction commit follows next (combines: (a) lift tool to named constant, (b) always-surface in resolution path, (c) add to REVIEWER_PRIMITIVES, (d) update tests, (e) ADR-299 Discovery notes 3 + 4 in-place); Hat-B resolution + canary v4 validation after.

## Cross-references

- ADR-299 (post-Discovery-notes 1 + 2): [`docs/adr/ADR-299-...md`](../../adr/ADR-299-kernel-universal-operator-addressing-capability.md)
- Predecessor folders this stacks on (named above)
- Canary v3 evidence:
  - wake_queue row: `555dc57a-6b35-4b27-9ef0-e32f3456894c`
  - execution_events row: `252e75f6-44bc-47db-9403-9fdbf74416ae` (73s, $0.32, 52K input / 6K output)
  - Reviewer substrate writes: `53f1b342` + `9b15410a` (judgment_log) + `c22618eb` (standing_intent)
  - notifications table: zero rows (the empirical evidence this finding is rooted in)
  - operator inbox: empty (operator-confirmed)
- Resolution path source: `api/services/platform_tools.py::get_platform_tools_for_capabilities`
- Substrate-event wake invocation: `api/services/wake.py:1464` (hardcodes `recurrence_required_capabilities: []`)
