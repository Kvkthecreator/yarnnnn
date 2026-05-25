# ADR-299: Operator-Addressing Capability — `send_operator_email`

**Status**: Phase 1 Implemented 2026-05-22; corrected FOUR times in-place across 2026-05-24 and 2026-05-25 (Discovery notes 1-4 below). Phase 2 + 3 Implemented 2026-05-24. After Discovery note 4 (the final correction): resolution path always-surfaces kernel-universal-no-wire-gate capabilities AND `EMAIL_SEND_TO_OPERATOR_TOOL` is explicitly registered in `REVIEWER_PRIMITIVES` (the Reviewer's tool surface registry is separate from the agent-path resolution that was corrected by Discovery notes 2 + 3). Regression gate 10/10 PASS post-correction; sibling reviewer-formalization gate 10/10 PASS. Phase 4 (L6 validation observation) ready for canary v4 — the structural bug chain that caused canary v1-v3 to fail end-to-end is now fully corrected.
**Date**: 2026-05-22
**Authors**: KVK, Claude
**Companion**: [`docs/observations/2026-05-22-052244-l6-variant-f-clause-validation/ADDENDUM.md`](../observations/2026-05-22-052244-l6-variant-f-clause-validation/ADDENDUM.md) — surfaced the L6 capital-execution gap on alpha-author that triggered this discourse
**Depends on**: ADR-118 (Skills as Capability Layer), ADR-176 (Work-First Agent Model), ADR-192 (Resend integration), ADR-217 (AUTONOMY gating), ADR-222 (OS framing), ADR-224 (Kernel/Program Boundary), ADR-227 (Task Capability Tool Augmentation), ADR-269 (Capability Flow Wiring), ADR-283 (alpha-author bundle)
**Amends**: ADR-283 D7 (alpha-author capability menu) — clarifies that the bundle-rejection of audience-bearing platform writes does NOT preclude kernel-universal operator-addressing writes
**Preserves**: Singular Implementation discipline, kernel/program boundary, ADR-283's archetype shape

## Context

ADR-283 D7 + Discovery Note 2 (2026-05-17, operator-authored) established that alpha-author's bundle does NOT ship audience-bearing platform writes — *"alpha-author's loop is 'audit a body of work that compounds' → zero external writes are bundle-required."* Discovery Note 2 explicitly listed *"LinkedIn / X / newsletter publishing-platform writes, commerce reads/writes, and email writes"* as out-of-archetype.

The 2026-05-22 L6 Variant-F clause validation observation ([`docs/observations/2026-05-22-052244-l6-variant-f-clause-validation/`](../observations/2026-05-22-052244-l6-variant-f-clause-validation/)) surfaced a follow-on question: how does alpha-author exercise FOUNDATIONS DP21 clause 5's "physical-platform-write" sub-branch if the bundle has no external writes? The natural answer per ADR-283 was "it doesn't — alpha-trader is the only surface for that branch, by design." That's true for *audience-bearing* writes (LinkedIn, newsletter publishing, X posts).

But the discourse round on 2026-05-22 surfaced an architectural distinction Discovery Note 2 collapsed: **email-to-operator-own-inbox and email-to-audience-list use the same wire protocol (SMTP via Resend) but are structurally different surfaces**. The first is observability — the Reviewer telling the operator about workspace state. The second is publication — the Reviewer addressing the operator's audience. Discovery Note 2 was correct to reject the second; it accidentally also rejected the first by collapsing them under one "email writes" line.

Cross-archetype stress-test (10 scenarios across alpha-author/yarnnn-author, alpha-author/netflix-script-author, alpha-trader/kvk, hypothetical alpha-commerce, edge cases) confirms that operator-addressing email writes generalize cleanly across every alpha workspace and don't require bundle-level capability declarations because they're not archetype-specific — they're OS-level observability.

This ADR proposes the first **kernel-universal capability** as an architectural class distinct from bundle-specific capabilities: capabilities that apply to every program bundle regardless of archetype, gated by AUTONOMY and operator preferences rather than by `platform_connections`.

## Decision

### D1. Architectural class: kernel-universal capability

Capabilities split into two structural classes:

**Bundle-specific capabilities** (existing, unchanged):
- Declared in `docs/programs/{slug}/MANIFEST.yaml::capabilities[]`
- Gated by `requires_connection: <platform>` against active `platform_connections`
- Archetype-specific — `write_trading` only makes sense for trading-bearing operations
- Examples: `read_trading`, `write_trading`, `write_slack`, `read_notion`, `read_commerce`
- Resolved by `services/bundle_reader.py::bundles_active_for_workspace`

**Kernel-universal capabilities** (NEW, this ADR):
- Declared in kernel code (no MANIFEST entry required)
- Not gated by `platform_connections` (no `requires_connection`)
- Available to every program bundle regardless of archetype
- Gated instead by AUTONOMY posture (ADR-217) + operator preferences (`_preferences.yaml`)
- The first instance: `send_operator_email` (this ADR)
- Future instances expected: cross-workspace operator status digests, calendar-event reminders, anything where the load-bearing addressee is *the operator's own identity*

The distinguishing test: **does this capability address operator-identity (kernel-universal) or does it address a third party / audience / external counterparty (bundle-specific)?** If the addressee is `auth.users.email` for the workspace's owner, it's kernel-universal. If the addressee is anyone else, it's bundle-specific.

### D2. First instance: `send_operator_email` capability

**Capability key**: `send_operator_email`

**Shape** (parallels existing MANIFEST capability shape from `alpha-trader/MANIFEST.yaml`, but lives in kernel code not in any bundle):

```python
# api/services/capabilities.py (or similar kernel location — see D5)
KERNEL_UNIVERSAL_CAPABILITIES = {
    "send_operator_email": {
        "category": "tool",
        "runtime": "kernel",            # not external:provider — kernel-mediated
        "requires_connection": None,    # NOT platform-gated
        "tools": ["platform_email_send_to_operator"],
        "addressee_resolution": "auth.users.email",  # at send-time, never cached
        "autonomy_posture": "observability",  # see D4
    }
}
```

**Tool**: `platform_email_send_to_operator(subject: str, html: str, cc_list?: list[str])`
- Tool resolves operator's email at send-time from `auth.users.email` for the workspace owner
- Never accepts a free-form `to:` parameter — the addressee is structurally fixed to the operator
- `cc_list` allows operator-declared carbon-copies (e.g., operator's secondary email) but those addresses are sourced from operator-authored substrate (`_preferences.yaml` field), not LLM-supplied
- Wraps existing `platform_email_send` infrastructure from ADR-192 Phase 4 (`api/integrations/core/resend_client.py`); does NOT introduce a new email provider
- The wrap is the load-bearing thing: the existing `platform_email_send` accepts any addressee and is bundle-capability-gated. `platform_email_send_to_operator` is kernel-universal, structurally cannot address third parties, and uses the same Resend wire underneath

**Why a new tool rather than re-using `platform_email_send`**: the addressee constraint is structural, not policy. `platform_email_send` (per ADR-192 Phase 4) is shaped for audience-bearing use cases — the LLM supplies the `to:` field. A kernel-universal "send to operator" tool that took a `to:` parameter would re-introduce the audience-bearing surface this ADR explicitly does NOT ship. By wrapping with addressee-resolution baked in (operator-identity from `auth.users`), we get the "operator inbox" semantic without LLM-controlled audience targeting.

### D3. Bundle-vs-kernel boundary clarification (amends ADR-283 D7)

ADR-283 D7 Discovery Note 2's rejection list (*"LinkedIn / X / newsletter publishing-platform writes, commerce reads/writes, and email writes"*) stands, with a clarification: **the rejection is of *audience-bearing* writes**, not of operator-addressing writes via the same wire.

The corrected framing:

| Capability | Class | ADR-283 D7 verdict |
|---|---|---|
| `write_linkedin` (LinkedIn API post) | Audience-bearing, bundle-specific | ❌ Out of alpha-author archetype (correct) |
| `write_x` (X API post) | Audience-bearing, bundle-specific | ❌ Out of alpha-author archetype (correct) |
| `platform_email_send` to newsletter list | Audience-bearing, bundle-specific | ❌ Out of alpha-author archetype (correct) |
| `send_operator_email` (operator's own inbox) | Operator-addressing, kernel-universal | ✅ NOT covered by D7 rejection; available to all bundles per this ADR |

This is not a supersession of ADR-283 D7 — it's a clarification that D7's collapsed framing of "email writes" obscured a structural distinction that the 2026-05-22 stress-test made explicit. The audience-bearing-vs-operator-addressing class boundary becomes canonical going forward.

### D4. AUTONOMY routing: operator-addressing writes are observability, not consequential action

Per ADR-217, the AUTONOMY ceiling gates **consequential actions** — writes that move capital, change external-counterparty state, bind publication to an audience. The Reviewer's verdicts on capital actions route through `should_auto_apply` → `handle_execute_proposal` (manual queues; bounded queues above ceiling; autonomous binds within ceiling).

**Operator-addressing writes do NOT route through this flow.** They are observability — the Reviewer telling the operator about workspace state via the operator's preferred out-of-band channel. The architectural commitment:

- A `send_operator_email` call from any Reviewer cycle fires directly when the workspace's `_preferences.yaml` declares operator-update emails as active
- The `_preferences.yaml` declaration is the operator's standing approval (authored once, applies continuously) — analogous to how operator-authored cadence preferences are honored via Schedule reconciliation per ADR-275
- AUTONOMY `delegation: manual` does NOT block operator-addressing writes — the operator already approved them by declaring the preference. AUTONOMY scoping is for *third-party-affecting* writes, not for *operator-self-addressing* writes.
- If `_preferences.yaml` has no entry for operator-update emails, the capability is available but unused — Reviewer doesn't fire emails the operator hasn't asked for

**Discipline rule**: operator-addressing writes inherit operator authorization from `_preferences.yaml` declarations, not from per-action AUTONOMY gating. This keeps the AUTONOMY surface focused on the consequential-action class it was designed for (ADR-217 + ADR-249) and prevents observability noise from clogging the operator's Queue.

### D5. Capability registration location

**Decision**: register kernel-universal capabilities in a new module `api/services/kernel_capabilities.py` (parallel to `api/services/orchestration.py::PRODUCTION_ROLES` for production roles, but specific to capabilities — not roles).

**Why a new module**:
- `services/orchestration.py` is dense with role definitions, registry helpers, and runtime resolution; adding a new top-level dict would obscure the new architectural class
- Putting the kernel-universal capabilities in their own file makes the "kernel-universal vs bundle-specific" distinction visible at file-organization level
- Naming the file `kernel_capabilities.py` makes its scope explicit
- Future kernel-universal capabilities land in this file by convention; bundle-specific capabilities continue to live in MANIFESTs

**Resolution path** (parallels bundle capability resolution per ADR-269):
- `get_platform_tools_for_agent(agent, task_required_capabilities)` is extended to also merge kernel-universal capabilities into the agent's tool surface
- When a recurrence declares `required_capabilities: [send_operator_email]` in its YAML, the dispatcher:
  - Checks `KERNEL_UNIVERSAL_CAPABILITIES` first (no `requires_connection` gate)
  - Falls through to bundle MANIFEST capabilities (with `platform_connections` gate)
  - Merges resolved tool list and exposes to the agent's prompt
- Singular Implementation: the dispatcher uses one resolution path; the kernel-vs-bundle distinction is a lookup-table source, not a parallel runtime code path

### D6. Why operator-addressing capability is kernel-universal not per-bundle

The case for kernel-universal placement (over re-declaring `send_operator_email` in every bundle's MANIFEST):

1. **It generalizes across every alpha workspace by construction** — every workspace has an operator with an email address; that's true for alpha-trader, alpha-author, alpha-commerce, every hypothetical future bundle
2. **Per-bundle re-declaration would re-leak the archetype-conflation D7 corrected** — saying "alpha-author has email capability" risks operators interpreting it as the audience-bearing variant. Saying "kernel provides operator-addressing observability to every workspace" is structurally cleaner
3. **It's the structurally OS-level surface** — operator-self-addressing notifications are the canonical "OS sends a notification to the user" pattern; not a vertical-specific capability
4. **It avoids capability-menu drift** — without kernel-universal placement, alpha-trader would need to add `send_operator_email` to its MANIFEST too (for daily trade summary emails), and alpha-commerce would too, and so on. Each addition risks subtle variation; the kernel-universal version is one definition forever

### D7. What this ADR explicitly does NOT do

- **Does not add audience-bearing email** — `send_operator_email` is structurally constrained to the workspace owner's inbox. Operator's-audience-list emails (newsletter sends to subscribers) remain off-archetype for alpha-author per ADR-283 D7 and would require their own bundle (per Singular Implementation)
- **Does not generalize to SMS/push channels** — those are deferred; their authorization shape (phone-number verification ceremony, push-token management) is different enough to warrant separate ADR discourse. Future channels come back through additional ADR amendments, not silent extension under this capability
- **Does not introduce a new email provider** — wraps existing Resend integration from ADR-192 Phase 4. No new env vars on Render services
- **Does not modify the AUTONOMY routing for consequential actions** — operator-addressing writes follow `_preferences.yaml` opt-in; capital actions still flow through `should_auto_apply` unchanged
- **Does not modify alpha-trader bundle** — alpha-trader inherits the new capability without MANIFEST changes; existing alpha-trader workspaces gain operator-update emails by declaring the preference in `_preferences.yaml`
- **Does not modify ADR-283 D7 strictly** — clarifies the audience-bearing-vs-operator-addressing distinction D7's collapsed list obscured; D7's rejection of audience-bearing writes stands

## Implementation roadmap (phased)

Each phase lands as its own commit with its own validation gate.

### Phase 1 — Kernel capability registration + tool wrap (~2 hours)
- New module `api/services/kernel_capabilities.py` declaring `KERNEL_UNIVERSAL_CAPABILITIES` dict with `send_operator_email` entry
- New tool `platform_email_send_to_operator` registered in `api/services/platform_tools.py` — wraps existing Resend client with structural addressee resolution from `auth.users.email`
- Capability resolution in `get_platform_tools_for_agent` extended to check kernel-universal capabilities before bundle MANIFEST
- Regression test `api/test_adr299_kernel_universal_capability.py` validates: (a) `send_operator_email` resolvable on workspace with no MANIFEST capabilities, (b) tool refuses LLM-supplied `to:` field (structurally pinned to operator), (c) bundle capability gate still works for bundle-specific capabilities (no regression)

### Phase 2 — `_preferences.yaml` schema extension (~1 hour)
- Bundle reference-workspaces (`alpha-author`, `alpha-trader`) extend their `_preferences.yaml` template with a new `operator_notifications:` block declaring opt-in / opt-out per notification type
- Reviewer reads this section on every wake (part of the existing `_preferences.yaml` envelope per ADR-275 D5)
- Empty/absent block = no operator-update emails fire (default-off)

### Phase 3 — Reviewer prompt nudge for operator-update awareness (~30 min)
- `_PERSONA_FRAME` cadence section extended: when operator has declared operator-update preferences AND the cycle has substrate-worth-reporting, the Reviewer should compose and send via `platform_email_send_to_operator`
- CHANGELOG entry per Prompt Change Protocol

### Phase 4 — L6 capital-execution branch validation on alpha-author (~observation; cost: ~$0.30 LLM tokens)
- Operator declares `operator_notifications: {daily_corpus_state_update: true}` in yarnnn-author's `_preferences.yaml`
- Wait for next natural Reviewer wake (substrate-event or cron_tick)
- Observe Reviewer emit `platform_email_send_to_operator` call → operator receives email
- Capture artifacts: `execution_events` row with funnel decision + the email itself + Reviewer reasoning in `judgment_log.md`
- Update [`docs/observations/2026-05-22-052244-l6-variant-f-clause-validation/`](../observations/2026-05-22-052244-l6-variant-f-clause-validation/) ADDENDUM with the consequential-action gate-fire evidence on alpha-author (closing clause 5 active-branch on alpha-author without requiring audience-bearing capabilities)

## Stress-test scenarios validated against the proposed shape

The 2026-05-22 discourse round stress-tested this against 10 scenarios across alpha-author, alpha-trader, and hypothetical alpha-commerce workspaces. Headline:

- **Symmetric fit across both alpha-author workspaces** (yarnnn-author founder-content + netflix-script-author screenplay): operator-addressing emails work for both without bundle changes
- **Natural fit for alpha-trader** (daily after-hours P&L summaries): bonus capability that no existing bundle MANIFEST declares, gained for free under kernel-universal placement
- **Future alpha-commerce inherits without authoring work** — confirms the kernel-universal placement payoff
- **Surfaced the audience-vs-operator distinction** that D7's collapsed framing obscured (Scenario 5: newsletter sends to subscribers ≠ daily update to operator's own inbox)
- **Surfaced the channel-agnostic question** (Scenario 6: SMS/push) and resolved in favor of email-specific naming for v1 to keep the architectural commitment narrow
- **Surfaced the AUTONOMY-routing question** (Scenario 8: should operator-update emails require manual click under `delegation: manual`?) and resolved in favor of `_preferences.yaml` opt-in as the standing authorization
- **Surfaced the identity-resolution discipline** (Scenario 10: operator changes email mid-workspace) — addressee resolved at send-time, never substrate-cached
- **Surfaced spam-pattern risk** (Scenario 9: operator with N workspaces gets N daily emails) but bounded as downstream product-design problem, not a capability-shape problem

Full stress-test reasoning trace lives in the 2026-05-22 session log; the load-bearing decisions are crystallized in D2-D4 above.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Operator-update emails become noise, get marked-as-read, loop breaks | Default-off via `_preferences.yaml`. Operator opts in per workspace. No platform-default subscriptions. |
| Tool gets re-used as audience-bearing surface (someone passes operator's friend's email as `cc_list`) | `cc_list` only accepts addresses sourced from operator-authored substrate (`_preferences.yaml` field), not LLM-supplied. Structural pin. |
| Per-workspace operator-email duplication when operator runs multiple workspaces | Downstream product-design problem (digest roll-up, subject-line prefixing); capability ships unchanged; UX iteration handles spam-fatigue |
| Kernel-universal class accidentally becomes a dumping ground | Discipline rule (D1): kernel-universal class is for *operator-identity-addressing* capabilities only. Anything addressing third parties / audiences / external counterparties is bundle-specific. ADR amendments enforce this filter. |
| Capability resolution becomes ambiguous when both kernel-universal and bundle declarations name overlapping capabilities | Kernel-universal wins by precedence in `get_platform_tools_for_agent` resolution order. Documented in code + this ADR. Bundle authors cannot redeclare kernel-universal capabilities (the resolution is one-way). |

## What this changes about the L6 validation envelope

Once Phase 4 lands, alpha-author exercises the consequential-action gate-fire branch (clause 5 of FOUNDATIONS DP21) on its own substrate — no longer architecturally-deferred-to-alpha-trader-only.

The conglomerate-alpha thesis (per ALPHA-1-PLAYBOOK + ADR-191) keeps its archetype separation: alpha-trader still validates **capital-execution** (Alpaca paper orders → real fills → reconciliation), alpha-author validates **substrate-continuity** (corpus state → operator-update emails → operator-read-back). Both archetypes now exercise consequential-action gate-fire on substrate that matches their archetype's value-creating loop.

## Status

**Phase 1 Implemented 2026-05-22.** The kernel module (`api/services/kernel_capabilities.py`), tool wrap (`platform_email_send_to_operator` in `EMAIL_TOOLS` + `send_to_operator` branch in `_handle_email_tool`), and resolution wiring (kernel-universal pre-check in `get_platform_tools_for_capabilities`) all shipped. Regression gate `api/test_adr299_kernel_universal_capability.py` 8/8 PASS; sibling reviewer-formalization gate (`test_reviewer_formalization.py`) 8/8 PASS confirming no regression in adjacent canon. Singular Implementation discipline honored — one resolution path, one tool definition, structural addressee pin enforced at three layers (schema absence + handler runtime rejection + source-level test guard).

**Phases 2-4 deferred to follow-up commits**:
- Phase 2: `_preferences.yaml` schema extension for `operator_notifications:` opt-in block (alpha-author + alpha-trader bundle reference workspaces)
- Phase 3: `_PERSONA_FRAME` cadence-section nudge for Reviewer awareness of operator-update preferences (with CHANGELOG entry per Prompt Change Protocol)
- Phase 4: L6 validation observation on alpha-author (operator declares preference, observe natural cycle emit `platform_email_send_to_operator`, capture artifacts → updates `docs/observations/2026-05-22-052244-l6-variant-f-clause-validation/` ADDENDUM with explicit consequential-action gate-fire evidence on alpha-author without audience-bearing capabilities)

## Cross-references

- 2026-05-22 L6 validation observation: [`docs/observations/2026-05-22-052244-l6-variant-f-clause-validation/`](../observations/2026-05-22-052244-l6-variant-f-clause-validation/)
- 2026-05-24 architectural-class-naming redundancy finding (motivated the Discovery note below): [`docs/observations/2026-05-24-042952-adr299-class-naming-redundancy/`](../observations/2026-05-24-042952-adr299-class-naming-redundancy/)
- alpha-author bundle ADR: [ADR-283](ADR-283-alpha-author-bundle.md) (D7 + Discovery Note 2)
- Resend integration: ADR-192 Phase 4 (`api/integrations/core/resend_client.py`)
- Existing platform tools: `api/services/platform_tools.py` (EMAIL_TOOLS at line 809)
- Capability flow: ADR-269 (`get_platform_tools_for_agent`)
- AUTONOMY gating: ADR-217 + ADR-249
- Existing CAPABILITIES dict (where send_operator_email now lives post-correction): `api/services/orchestration.py:1129`
- FOUNDATIONS DP21 (Variant F): the canonical Reviewer formalization this ADR completes for the substrate-continuity archetype

## Discovery note — architectural-class-naming redundancy correction (2026-05-24)

This ADR was patched in place on 2026-05-24 after operator-prompted re-review surfaced a redundancy in D1 + D5: the introduced "kernel-universal capability" class was a renaming of an existing pattern, and D5's parallel registry duplicated existing infrastructure.

**The redundancy**: `api/services/orchestration.py:1129` already shipped a `CAPABILITIES` dict (pre-ADR-299) with 15 entries carrying `platform_connection_requirement: None` — the structural property D1 named as the distinguishing test for "kernel-universal." The `_resolve_capability` fallthrough (ADR-224) already handled the kernel-vs-bundle distinction. D5's parallel `KERNEL_UNIVERSAL_CAPABILITIES` registry in new module `api/services/kernel_capabilities.py` introduced a second registry doing what the existing single registry already did.

**The genuine novelty** in `send_operator_email` is NOT "kernel-universal" (existing class) but **operator-addressing** — a capability whose addressee resolves from `auth.users.email` for the workspace owner, regardless of wire-gate presence. Three patterns sit in the existing CAPABILITIES dict, not two:

1. **No-wire-gate kernel** (15 existing entries): `summarize`, `web_search`, `chart`, etc. No external API; addressee is N/A.
2. **Wire-gated audience-addressing bundle** (existing): `write_slack`, `write_notion`. External API + LLM-supplied addressee → third-party / audience surface.
3. **Wire-gated operator-addressing** (NEW, the actual novelty): `send_operator_email`. External API + addressee structurally pinned to operator identity → operator surface.

D1 collapsed (1) and (3) under one banner, but (1) already existed. The actual novel axis is the **addressee-class distinction** — operator-identity vs third-party — not the kernel-vs-bundle housing.

**Why the redundancy escaped initial drafting**: pre-ADR-299 research delegated to a general-purpose agent reported *"no explicit `CAPABILITIES = {} dict currently visible (capabilities are embedded in role definitions + bundle MANIFESTs)."* This was incorrect — the dict was at line 1129, ~110 lines below where the agent looked. Discipline lesson: delegate research to subagents, but verify load-bearing facts before designing on top of them.

**The corrections in this patch**:

- **D1 reframed**: category renamed from "kernel-universal capability" (existing pattern) to **operator-addressing capability** (the genuine novelty). The distinguishing test is now sharpened to: *does this capability address operator-identity (operator-addressing) or a third party / audience / external counterparty (audience-addressing or third-party-addressing)?* The addressee class is the load-bearing axis, not the kernel-vs-bundle housing.
- **D5 reframed**: parallel registry decision retracted. `send_operator_email` lives in the existing `CAPABILITIES` dict at `services/orchestration.py:1129` with a new `addressee_class: "operator"` field. The existing `_resolve_capability` + `CAPABILITY_PROVIDER_MAP` + `PLATFORM_TOOLS_BY_CAPABILITY` resolution path handles surface assembly — no parallel pre-check in `get_platform_tools_for_capabilities`. Singular Implementation honored.
- **D2 stands unchanged**: the tool wrap (`platform_email_send_to_operator` + `send_to_operator` branch in `_handle_email_tool` + structural addressee pin) is genuinely new and correct.
- **D3 stands unchanged**: the ADR-283 D7 clarification is still load-bearing — audience-addressing rejection holds; operator-addressing was the conflated-away exception.
- **D4 stands unchanged**: operator-addressing writes are observability, not consequential action; gated by `_preferences.yaml` opt-in not per-action AUTONOMY click.
- **D6 reframed**: kernel-universal placement justification (over per-bundle re-declaration) survives in spirit — operator-addressing capabilities sit in the kernel `CAPABILITIES` dict, available to all bundles via the existing fallthrough path. The reasoning was right; the implementation housing (parallel registry vs existing dict) was wrong.
- **D7 stands unchanged**: scope limits (no audience-bearing email, no SMS/push, no new email provider, etc.) all hold.

**Files affected by the correction** (single Hat-A commit, three-commit cross-hat shape per CLAUDE.md §"The Two Hats"):
- DELETED: `api/services/kernel_capabilities.py` (parallel registry)
- AMENDED: `api/services/orchestration.py` — `send_operator_email` entry added to `CAPABILITIES` dict with `addressee_class: "operator"` + `autonomy_posture: "observability"` fields
- AMENDED: `api/services/platform_tools.py` — `send_operator_email` wired into `CAPABILITY_PROVIDER_MAP` + `PLATFORM_TOOLS_BY_CAPABILITY`; parallel kernel-universal pre-check in `get_platform_tools_for_capabilities` deleted
- AMENDED: `api/test_adr299_kernel_universal_capability.py` — rewritten to test corrected shape (8/8 PASS post-correction)
- AMENDED: this ADR (in-place per Singular Implementation; no v1/v2)

**Architectural takeaway**: the kernel/bundle boundary (ADR-224) was already correctly designed for capabilities that operate across all archetypes. The error was introducing a new architectural class when a new field on the existing class would have sufficed. The lesson generalizes: when proposing a new architectural class, the first check is whether the existing class has space for a new field that captures the genuine novelty. If yes, prefer the new field over the new class. New classes are expensive (parallel registries, parallel resolution paths, doc churn); new fields are cheap (additive metadata on existing entries).

This patch supersedes the affected sections in place per Singular Implementation. No v1/v2; the corrected text is the ADR.

## Discovery note 2 — wire redundancy correction (2026-05-24)

This ADR was patched again in place on 2026-05-24 after operator-prompted re-review during pre-flight for Phase 4 testing surfaced a second-order redundancy Discovery note 1 missed.

**The redundancy**: YARNNN has two existing Resend wires today, and Phase 1 (commit `3f0cabb`) wired `platform_email_send_to_operator` on the wrong one. Yesterday's class-naming correction (commit `50df8b4`) correctly renamed the class to "operator-addressing" but did not re-verify the wire underneath — leaving the operator-addressing capability built on audience-addressing infrastructure.

**The two existing wires:**

| Wire | Path | Operator setup | Purpose |
|---|---|---|---|
| **System-keyed** (ADR-040 + ADR-202) | `api/jobs/email.py::send_email` reads `RESEND_API_KEY` env var | None — built-in, deployed | Operator-addressing — `services/notifications.py` (agent-ready / agent-failed alerts) + `services/daily_update_email.py` (ADR-202 daily-update pointer emails) |
| **Per-user OAuth** (ADR-192 Phase 4) | `api/integrations/core/resend_client.py` reads `platform_connections.platform='email'.credentials_encrypted` (Fernet-encrypted) | Operator connects via Settings → Integrations → Email | Audience-addressing — `platform_email_send` + `platform_email_send_bulk` for commerce-archetype customer/newsletter sends |

ADR-299 Phase 1 attached `platform_email_send_to_operator` to the per-user OAuth wire — meaning the operator-addressing capability required operator Resend OAuth ceremony to activate, when the correct operator-addressing wire (system Resend) was already deployed and required zero operator action.

**Recursive discipline lesson**: when correcting an architectural-class redundancy, also verify the wire each class member points at. Renaming the class without re-verifying the implementation collapses to a relabel-only correction that leaves the structural bug intact. Same shape as Discovery note 1's lesson, recursing one level deeper.

**The corrections in this second patch**:

- **D2 reframed (wire)**: the tool implementation rewires to system Resend via `api/jobs/email.py::send_email`. Handler refactored to early-return at top of `_handle_email_tool` before the per-user `platform_connections` fetch (which is for the audience-addressing wire only). The `send_to_operator` branch:
  - Resolves operator email via `get_user_email(auth.client, auth.user_id)` from `auth.users.email` at send-time (unchanged from prior shape — addressee resolution discipline preserved)
  - Rejects LLM-supplied addressee fields (`to`, `cc`, `bcc`, `from_email`, `from_name`) with clear errors (structural pin preserved at three layers: schema absence + runtime rejection + source-level test guard)
  - Calls `system_send_email(to=operator_email, subject=..., html=..., reply_to=...)` instead of `resend.send(api_key, ...)` — system wire, no per-user API key
- **D2 reframed (runtime + wire-gate)**: kernel `CAPABILITIES` dict entry for `send_operator_email`:
  - `runtime` changed from `"external:email"` → `"kernel"` (system wire is environment-deployed kernel infrastructure, not external provider)
  - `platform_connection_requirement` changed from `{platform: "email", status: "active"}` → `None` (no per-user OAuth gate)
- **D5 reframed (resolution path)**: `get_platform_tools_for_capabilities` extended to consult kernel `CAPABILITIES` dict for no-wire-gate capabilities (`platform_connection_requirement is None`) BEFORE the `CAPABILITY_PROVIDER_MAP` per-user gate check. When such a capability is requested, its tools surface unconditionally — no `connected_providers` check, since the wire is environment-deployed. Singular Implementation honored: one resolution function, two source layers (kernel CAPABILITIES dict for no-wire-gate + CAPABILITY_PROVIDER_MAP for wire-gated), one return list. `send_operator_email` removed from `CAPABILITY_PROVIDER_MAP` (was pointing at `"email"` provider, which is the audience-addressing surface).
- **Phase 3 persona-frame wire-gate clause deleted**: the prose teaching the Reviewer to note substrate-vs-wire drift in `standing_intent.md` when `platform_email_send_to_operator` is absent from the tool surface — that clause was correct for the wrong wire. The corrected wire has no wire-gate; the tool is always available. Replaced with a single-paragraph note that `platform_email_send_to_operator` uses the system-deployed Resend wire, no operator-side setup required, and sends from `yarnnn <noreply@yarnnn.com>` by default with Reply-To routing replies to operator's inbox.
- **D3 stands unchanged**: ADR-283 D7 clarification still holds — audience-addressing rejection stands; operator-addressing was the conflated-away exception.
- **D4 stands unchanged**: operator-addressing writes are observability, not consequential action; gated by `_preferences.yaml` opt-in.
- **D6 reframed**: kernel-universal placement justification stands; the specific implementation housing changes from "wrapping per-user OAuth wire in EMAIL_TOOLS" to "early-return on system wire before per-user OAuth fetch path."
- **D7 stands unchanged**: scope limits all hold.

**Files affected by this second correction**:
- AMENDED: `api/services/platform_tools.py::_handle_email_tool` — `send_to_operator` branch moved to top of function as early return; calls `system_send_email` (alias for `api/jobs/email.py::send_email`) instead of `resend.send(api_key, ...)`; removed reliance on per-user `platform_connections` fetch.
- AMENDED: `api/services/orchestration.py::CAPABILITIES["send_operator_email"]` — `runtime: "kernel"`; `platform_connection_requirement: None`.
- AMENDED: `api/services/platform_tools.py::CAPABILITY_PROVIDER_MAP` — `send_operator_email` entry removed (no longer provider-gated).
- AMENDED: `api/services/platform_tools.py::get_platform_tools_for_capabilities` — extended with kernel `CAPABILITIES` dict no-wire-gate branch that surfaces tools unconditionally when `platform_connection_requirement is None`. Singular Implementation per the lesson from Discovery note 1: one function, lookup-source distinction (kernel-dict vs provider-map) is internal, not a parallel runtime code path.
- AMENDED: `api/agents/reviewer_agent.py::_PERSONA_FRAME` — Phase 3 wire-gate clause deleted; replaced with one-paragraph system-wire note.
- AMENDED: `api/test_adr299_kernel_universal_capability.py` — runtime assertion, `platform_connection_requirement` assertion, handler-shape assertions, resolution-path assertions all updated. New test `test_resolution_surfaces_send_operator_email_unconditionally` validates the kernel-dict branch in resolution. 9/9 PASS.
- AMENDED: `api/prompts/CHANGELOG.md` — entry `[2026.05.24.3]` documenting the Phase 3 prose update.
- AMENDED: this ADR (in-place per Singular Implementation; no v1/v2/v3).

**Net impact on Phase 4 validation**: Phase 4 becomes immediate-testable. No operator Resend connect ceremony required. Operator opts in to one notification (flip `active: false → true` in `_preferences.yaml`) via chat or direct edit; next natural Reviewer wake or substrate-event canary fires the email via system wire; operator receives email from `noreply@yarnnn.com` with Reply-To set to their own inbox. The L6 capital-execution branch on alpha-author can now close on its own substrate without requiring audience-bearing capabilities.

**Architectural takeaway (recursive)**: yesterday's Discovery note 1 named the lesson "prefer new field on existing class over new class when novelty fits, and verify load-bearing facts before designing on top of delegated research." Today's Discovery note 2 adds: **when correcting a class-naming redundancy, verify the wire each class member points at**. The class-vs-wire distinction is structurally orthogonal — naming the class correctly doesn't guarantee the implementation reaches the right wire. Both checks are now codified in the corrected regression gate (runtime + wire-gate + handler-shape assertions).

This patch supersedes the affected sections in place per Singular Implementation. No v1/v2/v3; the corrected text is the ADR.

## Discovery note 3 — resolution-path always-surface correction (2026-05-25)

ADR-299 Phase 4 canary attempt revealed a third-order redundancy: after Discovery notes 1 + 2 corrected the class + wire, the runtime resolution path still required explicit recurrence/hook `required_capabilities` opt-in to surface kernel-universal capabilities. Operator-addressing capabilities were described in canon as "always available" (D1 + D4) but treated by the runtime as opt-in-per-recurrence (same as bundle-specific wire-gated capabilities).

**Root cause**: `api/services/platform_tools.py::get_platform_tools_for_capabilities` looped ONLY over the caller-supplied `capabilities` list. When the substrate-event wake path called with `capabilities=[]` (hardcoded at `api/services/wake.py:1464`), no capabilities resolved — including kernel-universal ones. The capability was correctly registered + correctly wired + correctly the right shape, but the runtime resolution never reached it from substrate-event wakes.

**Correction**: extended `get_platform_tools_for_capabilities` with an always-surface pass that loops over the kernel `CAPABILITIES` dict and surfaces every entry with `platform_connection_requirement is None` — regardless of whether it appears in the caller-supplied `capabilities` list. The explicitly-requested-capabilities pass survives for wire-gated capabilities (which DO need per-recurrence opt-in, because they affect third parties / audiences).

**Files corrected by Discovery note 3**:
- `api/services/platform_tools.py::get_platform_tools_for_capabilities` — added the always-surface pass before the explicitly-requested-capabilities loop; removed the early-exit on empty `capabilities` (since kernel-universal still surfaces).
- `api/test_adr299_kernel_universal_capability.py` — `test_resolution_surfaces_send_operator_email_unconditionally` extended to assert the always-surface branch exists.

**This patch supersedes Discovery note 2's D5 reframe in place per Singular Implementation. No v3/v4; the corrected text is the ADR.**

## Discovery note 4 — REVIEWER_PRIMITIVES inclusion correction (2026-05-25)

While implementing Discovery note 3's always-surface fix, a fourth-order redundancy surfaced: **the Reviewer's tool surface is NOT built via `get_platform_tools_for_capabilities` at all.** `api/agents/reviewer_agent.py:1373` reads:

```python
tools = list(REVIEWER_PRIMITIVES) + [RETURN_VERDICT_TOOL]
```

The Reviewer gets exactly `REVIEWER_PRIMITIVES` from `api/services/primitives/registry.py:394`. Platform tools (including `platform_email_send_to_operator`) were not in that list and never were. ADR-299 Phase 1's wire-up was structurally incomplete from day one:

- ✅ Tool added to `EMAIL_TOOLS` (the agent-path platform tools list)
- ✅ Capability registered in kernel `CAPABILITIES` dict
- ✅ Handler branch added to `_handle_email_tool`
- ✅ Resolution path extended (Discovery note 2 + 3)
- ❌ **Tool NEVER added to `REVIEWER_PRIMITIVES`** — the registry the Reviewer's surface is actually built from

The Reviewer never had access to `platform_email_send_to_operator` at all, regardless of operator opt-in, regardless of wire correctness, regardless of resolution-path correction. Four cascading corrections all addressing the wrong layer.

**Correction**: lift the tool definition out of the `EMAIL_TOOLS` list literal as a named module-level constant `EMAIL_SEND_TO_OPERATOR_TOOL` in `platform_tools.py`, and add it to `REVIEWER_PRIMITIVES` in `registry.py`. Tool count goes 21 → 22.

**Files corrected by Discovery note 4**:
- `api/services/platform_tools.py` — `EMAIL_SEND_TO_OPERATOR_TOOL` lifted as named module-level constant before `EMAIL_TOOLS`; `EMAIL_TOOLS` now references the constant. Tool description updated to reflect system Resend wire (was still describing per-user OAuth — Discovery note 2 prose).
- `api/services/primitives/registry.py` — imports `EMAIL_SEND_TO_OPERATOR_TOOL` from `services.platform_tools`; added to `REVIEWER_PRIMITIVES` list.
- `api/test_adr299_kernel_universal_capability.py` — new assertion `test_reviewer_primitives_includes_send_operator_email`.

### The fourth-recursion lesson (named precisely)

Different actors in the system have different tool-surface assembly paths:

- **Agent's tool surface**: `get_platform_tools_for_agent` → `get_platform_tools_for_capabilities` (kernel CAPABILITIES dict + bundle MANIFEST + platform_connections)
- **Reviewer's tool surface**: `REVIEWER_PRIMITIVES` (curated subset)
- **ChatAgent's tool surface**: `CHAT_PRIMITIVES` (similar shape to REVIEWER_PRIMITIVES)
- **Sub-LLM specialist (DispatchSpecialist)**: `HEADLESS_PRIMITIVES` or role-specific subset

**Adding a kernel-universal capability requires explicit inclusion in EACH actor's surface registry — they don't auto-flow from kernel `CAPABILITIES` dict to actor surfaces.** The kernel `CAPABILITIES` dict is the registry of "what exists"; per-actor surface registries (`REVIEWER_PRIMITIVES`, `CHAT_PRIMITIVES`, `HEADLESS_PRIMITIVES`, role bundles) are the registries of "what each actor can call." A capability registered in the former without inclusion in the relevant latter is structurally unreachable from that actor.

### Updated recursion-lesson table (final form for this session)

| Depth | Lesson |
|---|---|
| 1 | Class-naming redundancy: prefer new field on existing class over new class |
| 2 | Wire-pointing: verify the wire each class member points at, not just the class |
| 3 | Resolution-path always-surface: verify the resolution path actually surfaces the capability to callers that should have it |
| 4 | **Per-actor surface registries**: verify each actor-specific tool registry (REVIEWER_PRIMITIVES / CHAT_PRIMITIVES / HEADLESS_PRIMITIVES / role bundles) includes the capability separately — kernel CAPABILITIES is "what exists," per-actor surfaces are "what each actor can call" |

### Why this finally closes the chain

After Discovery note 4:
- Tool definition: ✅ (`EMAIL_SEND_TO_OPERATOR_TOOL` named constant, system-wire description)
- Capability registered in kernel: ✅ (`CAPABILITIES["send_operator_email"]`, no-wire-gate, addressee_class=operator)
- Wire correct: ✅ (system Resend via `api/jobs/email.py`)
- Resolution path always-surfaces: ✅ (Discovery note 3 fix)
- Reviewer's tool surface includes: ✅ (Discovery note 4 fix — added to `REVIEWER_PRIMITIVES`)
- Agent's tool surface includes: ✅ (Discovery note 3 fix — always-surface in `get_platform_tools_for_capabilities`)
- Dispatch chain: ✅ (`is_platform_tool` → `handle_platform_tool` → `_handle_email_tool::send_to_operator` early-return → `system_send_email`)
- Operator opt-in: ✅ (`_preferences.yaml::operator_notifications.{slug}.active: true` is standing approval per D4)
- Persona-frame teaches it: ✅ (Phase 3 prose update)
- AUTONOMY routing as observability: ✅ (D4 commitment honored by handler — no `should_auto_apply` call)

Canary v4 should produce the full chain green: REJECT verdict + email landed in operator inbox.

This patch supersedes the affected sections in place per Singular Implementation. No v1/v2/v3/v4; the corrected text is the ADR.
