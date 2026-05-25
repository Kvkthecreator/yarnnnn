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

## Status

**OPEN** — Hat-A correction commit follows next; Hat-B resolution + canary v4 validation after.

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
