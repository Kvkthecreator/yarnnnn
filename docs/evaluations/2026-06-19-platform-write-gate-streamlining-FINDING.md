# FINDING — consequential platform writes bypass the uniform ADR-307 gate; the correct streamlining is "one decision, family-shaped enqueue," not "one queue"

**Date:** 2026-06-19
**Hat:** B — surfaces a finding; recommends a Hat-A refactor (uniform-gate extension) + the feature that rides on it (kernel-universal Slack/Notion audience-writes). Does not itself change canon/code.
**Status:** **RESOLVED 2026-06-19** — all three recommended commits landed on `main`: (1) ADR-307 Phase 5 gate refactor (`f8b57a1`) — consequential platform writes engage the uniform gate; family-shaped enqueue (substrate/capital/**external-write**); the three trading writes' bespoke `mode == autonomous` branches deleted, `check_risk_limits` retained as a pre-gate domain check; an operator-approved replay (`_proposal_id`) applies without re-gating; live capital path verified unregressed (`test_adr307_platform_write_gate.py` 13/13 + `test_risk_gate_rule_battery.py` 14/14). (2) ADR-304 amendment (`bb51f16`) — `write_slack` / `write_notion` re-declared kernel-universal in `CAPABILITIES` (`feeds: action` → HIGH), Reviewer-exclusion preserved (`test_adr299_*` 16/16). (3) Tools built (`8d103a5`) — `platform_slack_send_to_channel` + `platform_notion_create_page` + `platform_notion_append_block` (new `notion_client` methods), registered in `PLATFORM_TOOLS_BY_CAPABILITY`, CHANGELOG `[2026.06.19.4]`. The measurement that grounded the deletion (§2 risk #1): no live caller ever set `_mode="autonomous"` on a trading tool — the autonomous-propose branch was dead in the post-ADR-296 architecture, so removing it was safe.

> **Original status (preserved):** Open — recommends the gate refactor as a focused session before building the writes, because the path touches live capital actions (`submit_order` + `risk_gate`).
**Trigger:** Operator request for first-class, kernel-universal (ambient, no per-program friction) Slack/Notion audience-writes → operator clarification: *"autonomy mode is the approval gating for agent execution… that logic should be streamlined."* The clarification is architecturally correct and names a real gap.

---

## 1. Expected vs observed

**Expected (ADR-307 D1, ratified + "Implemented + validated"):** *"One uniform gate at `execute_primitive()`. The permission decision moves out of individual primitives and into the single execute-by-name chokepoint… no primitive gates itself."*

**Observed:** two structural deviations, both load-bearing for the requested feature.

| | Expected (ADR-307 D1) | Observed |
|---|---|---|
| Platform tools go through the uniform gate | yes | **No** — `execute_primitive` early-returns at `is_platform_tool(name)` (`registry.py:681-683`) BEFORE `resolve_permission` (`registry.py:705`). Platform writes never reach the gate. |
| No primitive gates itself | yes | **No** — `submit_order` hand-rolls its own `mode == "autonomous"` → `ProposeAction` branch (`platform_tools.py:2137-2159`), because it bypasses the uniform gate and must gate itself. |
| The uniform gate engages for all consequential calls | (implied) | **No** — `resolve_permission` engages only for *Reviewer-authored* consequential calls (`permission.py:172, 211`: a consequential primitive not gate-owned returns `APPLY, "not_gate_owned"`). |

**Receipts:**
- `api/services/primitives/registry.py:681-683` — `if is_platform_tool(name): return await handle_platform_tool(...)` — the bypass, above the gate at `:705`.
- `api/services/platform_tools.py:2137-2159` — `submit_order`'s bespoke `if mode == "autonomous": handle_propose_action(action_type="trading.submit_order", …)` branch.
- `api/services/primitives/permission.py:211` — `return APPLY, f"consequential:{action_class_for(name)}:not_gate_owned"` (Reviewer-scoped engagement).

---

## 2. Why the naive streamlining is wrong (the measurement that matters)

The naive reading of "streamline the gating" — *delete the bespoke branches, force every consequential call through `_enqueue_substrate_proposal`* — would **break two live things**:

1. **It drops the capital risk gate.** `submit_order`'s bespoke branch runs `check_risk_limits` (`platform_tools.py:2132` — the trader's position-sizing / stops / VaR envelope) BEFORE proposing. The uniform gate's `_enqueue_substrate_proposal` (`registry.py:602`) knows nothing about risk limits. Routing capital actions through it naively = **live capital actions lose their risk envelope.** A real regression on irreversible money movement.
2. **It mis-shapes the proposal.** The uniform gate builds a `family='substrate'` proposal whose `decision_context` is `{diff, message}` — a *file-content diff* (`registry.py` `_enqueue_substrate_proposal` literally diffs current-vs-proposed file content for WriteFile). A Slack channel-post is **not a file mutation** — it has no diff. `submit_order`'s capital proposal carries `action_type`, `expected_effect`, `reversibility`, `risk_warnings` — a different shape entirely.

**There are three consequence families, not one:**
- `substrate` — file mutations (WriteFile + ADR-337 verbs). decision_context = `{diff, message}`.
- `capital` — irreversible money actions (submit_order). decision_context = `{action_type, expected_effect, reversibility, risk_warnings}` + a domain risk gate.
- `external-write` (NEW, what Slack/Notion audience-writes are) — consequential third-party-affecting writes that are neither file nor capital. decision_context = the effect (channel, recipient, content preview).

---

## 3. The correct streamlining (what the operator instruction actually implies)

> **One gate DECISION, family-shaped ENQUEUE.**
>
> Streamline the *decision* (autonomy_mode → apply/queue/deny) into the one place (`resolve_permission`); keep the *proposal shaping* family-aware below it.

Concretely:
1. **Extend `resolve_permission` to engage for consequential platform tools**, not only Reviewer-authored substrate. Remove the `is_platform_tool` early-return *for consequential platform tools* so they reach the gate (reads stay fast-pathed — `read_*` is non-consequential).
2. **Route the QUEUE outcome to a family-appropriate enqueue:** `substrate` → existing `_enqueue_substrate_proposal`; `capital` → the capital proposal shape (preserving `check_risk_limits` as a *pre-gate domain check*, not gating logic); `external-write` → a new external-effect proposal shape.
3. **`submit_order`'s autonomy DECISION moves into the uniform gate; its risk-gate + capital-proposal SHAPING stays** (domain logic, not gating logic). This deletes the duplicated `mode == autonomous` branch (Singular Implementation) without dropping the risk envelope.
4. **Then** `write_slack` / `write_notion` (kernel-universal CAPABILITIES, `feeds: action` → HIGH tier per the 2026-06-19 derived-tier gate) inherit the uniform gate for free — they declare *what they are* (consequential external-write) and the one gate queues them by autonomy mode. No per-tool gating.

This honors the operator's instruction precisely: the *gating logic* is one streamlined decision; the *pipeline* (capability declaration, tool surface, transport) is separate, as the operator drew the line.

---

## 4. Why this blocks the feature (and is its own session)

The requested feature (kernel-universal Slack/Notion writes) **cannot be built correctly without this refactor** — building it the bespoke way (copy `submit_order`'s hand-rolled branch) would add a *third* self-gating tool, deepening the exact duplication ADR-307 D1 exists to remove and the operator flagged. But the refactor touches the **live capital-action path** (`submit_order` + `risk_gate`), so it is its own focused, carefully-verified piece of work — not a tail-end addition. Verification must include: a live `submit_order` autonomous path still hits `check_risk_limits` and still produces a capital proposal of the same shape; the trader gate is not regressed.

---

## 5. Recommended next commits (Hat-A, separate)

1. **ADR-307 amendment + refactor** — extend the uniform gate to consequential platform tools; family-shaped enqueue (substrate/capital/external-write); delete `submit_order`'s bespoke autonomy branch, preserving `check_risk_limits` as a pre-gate domain check. Verified against the live trader path.
2. **ADR-304 amendment** — permit kernel-universal audience-writes (`write_slack`/`write_notion` in kernel CAPABILITIES, `feeds: action`), WITH the uniform gate as the safety floor (ambient capability, gated act). Preserve the Reviewer-exclusion (ADR-299 D8 / ADR-304 D6).
3. **The writes** — `platform_slack_send_to_channel` (client `post_message` exists), `platform_notion_create_page` + `platform_notion_append_block` (client methods MISSING — build them), registered in `PLATFORM_TOOLS_BY_CAPABILITY`.

---

## Cross-links

- [ADR-307](../adr/ADR-307-unified-permission-taxonomy.md) — the uniform gate (D1) the platform-write path bypasses; the refactor extends it.
- [ADR-304](../adr/ADR-304-operator-addressing-writes-generalization.md) — D5 (audience-writes via MANIFEST, to be amended to permit kernel-universal) + D6 (Reviewer-exclusion, preserved).
- [ADR-299](../adr/ADR-299-kernel-universal-operator-addressing-capability.md) — operator-addressing vs audience-addressing line; D8 Reviewer-exclusion.
- [derived-trust-tier amendment](../adr/ADR-335-AMENDMENT-derived-trust-tier.md) — `feeds: action` → HIGH tier, the gate that serves the new write capabilities.
- `api/services/primitives/registry.py:681,705` · `permission.py:172,211` · `platform_tools.py:2132,2137` — the receipts.
