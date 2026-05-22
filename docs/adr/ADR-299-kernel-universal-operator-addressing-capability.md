# ADR-299: Kernel-Universal Operator-Addressing Capability — `send_operator_email`

**Status**: Proposed 2026-05-22
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

**Proposed.** Implementation deferred to follow-up commits per the phased roadmap. Phase 1 is the load-bearing commit (kernel module + tool wrap + regression test); Phases 2-4 follow naturally.

The 2026-05-22 discourse round validates the architectural claim; the implementation work is normal-engineering-shaped. The ADR is committable as Proposed before Phase 1 ships.

## Cross-references

- 2026-05-22 L6 validation observation: [`docs/observations/2026-05-22-052244-l6-variant-f-clause-validation/`](../observations/2026-05-22-052244-l6-variant-f-clause-validation/)
- alpha-author bundle ADR: [ADR-283](ADR-283-alpha-author-bundle.md) (D7 + Discovery Note 2)
- Resend integration: ADR-192 Phase 4 (`api/integrations/core/resend_client.py`)
- Existing platform tools: `api/services/platform_tools.py` (EMAIL_TOOLS at line 809)
- Capability flow: ADR-269 (`get_platform_tools_for_agent`)
- AUTONOMY gating: ADR-217 + ADR-249
- FOUNDATIONS DP21 (Variant F): the canonical Reviewer formalization this ADR completes for the substrate-continuity archetype
