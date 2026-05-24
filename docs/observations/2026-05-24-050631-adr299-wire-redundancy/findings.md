# ADR-299 wire redundancy — Hat-B finding (second-order)

**Hat**: External Developer of the System (Hat B per CLAUDE.md §"The Two Hats").

**Captured**: 2026-05-24 by operator-prompted re-review during pre-flight for ADR-299 Phase 4 testing.

**Trigger**: operator-prompted question — *"isn't resend a systematic feature and thus its set-up is built-in, not something for an individual user to do?"* The pre-flight had named "operator must connect Resend" as a setup step; the question prompted a survey of existing email infrastructure that surfaced the redundancy.

**Predecessor**: [`docs/observations/2026-05-24-042952-adr299-class-naming-redundancy/`](../2026-05-24-042952-adr299-class-naming-redundancy/) — yesterday's earlier ADR-299 correction (registry redundancy). This is the second-order redundancy that earlier correction missed.

## Finding

**ADR-299 Phase 1 wired `platform_email_send_to_operator` to the wrong Resend wire.** YARNNN has TWO Resend integrations today, with different purposes; Phase 1 wrapped the audience-addressing wire (per-user OAuth) when it should have wrapped the operator-addressing wire (system-keyed). The yesterday's class-naming correction (`50df8b4`) correctly renamed the class to "operator-addressing" but pointed it at audience-addressing infrastructure.

### The two existing Resend wires

| Wire | Path | Operator setup | Purpose | Used by |
|---|---|---|---|---|
| **System-keyed** (ADR-040 + ADR-202) | `api/jobs/email.py::send_email` reads `RESEND_API_KEY` env var on Render | **None** — built-in, deployed | **Operator-addressing**: notifications + daily-update pointer emails | `services/notifications.py` (agent-ready / agent-failed / suggestion-created — ADR-040); `services/daily_update_email.py` (ADR-202 daily-update pointer template); `services/delivery.py` for daily-update task delivery |
| **Per-user OAuth/API-key** (ADR-192 Phase 4) | `api/integrations/core/resend_client.py` reads `platform_connections.platform='email'.credentials_encrypted` via Fernet decrypt | Operator connects via Settings → Integrations → Email | **Audience-addressing**: commerce-archetype customer / newsletter sends | `platform_email_send` + `platform_email_send_bulk` tools (ADR-192 Phase 4 framed for e-commerce autonomous customer communication) |

### What ADR-299 Phase 1 did

`platform_email_send_to_operator` was added to `EMAIL_TOOLS` in `services/platform_tools.py` (per-user OAuth wire) with a `send_to_operator` branch in `_handle_email_tool` that:
1. Fetches `platform_connections` row where `platform='email'` (per-user OAuth check)
2. Decrypts the operator's stored Resend API key
3. Calls `get_resend_client().send(api_key, ...)` — same per-user wire as `platform_email_send`

Yesterday's class-naming correction (`50df8b4`) added a `CAPABILITIES` dict entry with `platform_connection_requirement: {platform: 'email', status: 'active'}` — preserving the per-user wire-gate.

**This is structurally wrong.** The operator-addressing wire was never per-user OAuth. ADR-040 ("Notifications") and ADR-202 ("Daily-Update Email Pointer Template") both used `api/jobs/email.py::send_email` with the system-keyed env var. ADR-192 Phase 4 explicitly framed its per-user wire as audience-addressing for commerce operators sending to customers — a different concern.

### Why the redundancy escaped both ADR-299 drafting AND yesterday's correction

ADR-299 D2 said *"Wraps existing `platform_email_send` infrastructure from ADR-192 Phase 4."* This was incorrect — ADR-192 Phase 4's infrastructure is the audience-addressing wire. The operator-addressing wire (ADR-040 + ADR-202) was never surveyed during ADR-299 drafting.

Yesterday's correction (`50df8b4`) caught the **architectural-class-naming redundancy** (parallel `KERNEL_UNIVERSAL_CAPABILITIES` registry vs existing `CAPABILITIES` dict) but did not catch the **wire redundancy** because the wire correctness was assumed-not-verified. The class was renamed correctly to "operator-addressing"; the wire underneath remained pointed at audience-addressing infrastructure.

**Discipline lesson** (recursing one level deeper than yesterday's): when correcting an architectural-class redundancy, also verify the wire each class member points at. Renaming the class without re-verifying the implementation collapses to a relabel-only correction that leaves the structural bug intact.

### Evidence collected during pre-flight

| Check | Result |
|---|---|
| `RESEND_API_KEY` referenced in `api/jobs/email.py:51` (system-keyed, env var) | ✅ Present |
| `RESEND_FROM_EMAIL` referenced in `api/jobs/email.py:56` (system sender) | ✅ Present (defaults to `yarnnn <noreply@yarnnn.com>`) |
| `notifications` table exists with `channel='email'` schema | ✅ Present |
| Notifications fired in last 7 days | 0 (live wire exists, dormant traffic — separate observation worth noting; not a bug per se since notifications fire on agent-ready/failed events that haven't triggered recently) |
| `daily_update_email.py` wired into `services/delivery.py:1018` for daily-update task | ✅ Present |
| `services/daily_update_email.py` file size | 9854 bytes — substantive implementation, not a stub |
| Per-user OAuth wire (`platform_connections.platform='email'`) on test workspaces | ❌ Zero rows — no operator has connected, by design |

The system wire is **provably present in code, wired into ADR-040 + ADR-202 use cases, and operationally dormant on the test workspaces**. The per-user wire is structurally what ADR-192 Phase 4 designed for commerce; nothing in alpha-author or kvk/alpha-trader-2 workspaces uses it today.

### What this means for ADR-299

ADR-299's architectural class is correct ("operator-addressing capability"). What's wrong is its implementation pointed at audience-addressing wire. The correction is a wire rewrap, not an architectural rethink. Specifically:

- **`platform_email_send_to_operator` handler** needs to call `api.jobs.email.send_email(to=operator_email, subject=..., html=...)` instead of fetching per-user encrypted Resend key + calling `resend_client.send(api_key, ...)`
- **`CAPABILITIES` dict entry** for `send_operator_email` needs `platform_connection_requirement: None` (no wire-gate; system Resend is environment-deployed, always present in any live deploy)
- **`CAPABILITY_PROVIDER_MAP` + `PLATFORM_TOOLS_BY_CAPABILITY`** wiring for `send_operator_email` needs reworking — the existing resolution path is `platform_connections`-gated by design, but `send_operator_email` has no per-user wire-gate. Two options: (a) kernel-side branch in `get_platform_tools_for_capabilities` that surfaces kernel-universal-no-connection-gated capabilities unconditionally, OR (b) treat 'email' as a permanently-connected provider (less honest because per-user 'email' connections are a separate concept)
- **Phase 3 persona-frame "wire-gate handling" prose** (3d8211a commit) becomes obsolete — there is no wire-gate. The clause should be deleted or reframed to explain that send_operator_email is always available; substrate-vs-wire drift detection no longer applies
- **Regression test** needs updates to reflect no wire-gate + new resolution path
- **ADR-299 Discovery note 2** explaining the wire redundancy + the correction shape + the recursive-discipline-lesson

## Recommendation (Hat-A correction — Path X)

Three-commit cross-hat shape, same as yesterday:
- **Commit 1** (this file): Hat-B observation
- **Commit 2**: Hat-A correction — wire rewrap + CAPABILITIES dict simplification + Phase 3 prose update + regression test update + ADR-299 Discovery note 2
- **Commit 3**: Hat-B resolution

### Files affected by the correction

- AMEND `api/services/platform_tools.py::_handle_email_tool::send_to_operator` branch — replace `get_resend_client().send(api_key, ...)` with `api.jobs.email.send_email(to=operator_email, subject=..., html=...)`. Drop `platform_connections` lookup + Fernet decrypt at branch entry (those are for audience-wire only; operator-wire skips them).
- AMEND `api/services/orchestration.py::CAPABILITIES["send_operator_email"]` — drop `platform_connection_requirement`; runtime stays `kernel` (was `external:email`, but with no wire-gate, kernel-runtime is correct).
- AMEND `api/services/platform_tools.py::CAPABILITY_PROVIDER_MAP` — `send_operator_email` no longer routes through `email` provider (since the provider gate is per-user OAuth which doesn't apply). Need kernel-side branch in `get_platform_tools_for_capabilities` to surface the tool unconditionally.
- AMEND `api/services/platform_tools.py::PLATFORM_TOOLS_BY_CAPABILITY["send_operator_email"]` — entry stays (tool name is correct) but resolution path changes per above.
- AMEND `api/agents/reviewer_agent.py::_PERSONA_FRAME` — drop the "wire-gate handling" clause that the Phase 3 commit added. The clause was correct for the wrong wire; for the right wire there is no wire-gate.
- AMEND `api/test_adr299_kernel_universal_capability.py` — update assertions to reflect no wire-gate + new resolution path. `test_wire_gate_degrades_silently_when_email_not_connected`-style assertions become obsolete.
- AMEND `docs/adr/ADR-299-...md` — Discovery note 2 explaining the wire redundancy + the correction; update D2 + D5 prose to reflect the system-Resend wire.
- AMEND `api/prompts/CHANGELOG.md` — entry [2026.05.24.3] documenting the Phase 3 prose update (deletion of wire-gate clause).

### Render parity check

`RESEND_API_KEY` + `RESEND_FROM_EMAIL` need to be set on **both** API service (`srv-d5sqotcr85hc73dpkqdg`) AND Unified Scheduler (`crn-d604uqili9vc73ankvag`) — the Scheduler runs the wake path that fires the Reviewer's email-send. Per `api/.env.example:23`, `RESEND_API_KEY` is named; not directly readable via Render MCP read-env, but the existing `daily_update_email.py` wiring (which runs through the Scheduler's delivery path) implies it's been set. Worth verifying with operator before Phase 4 testing.

### Net impact on Phase 4 validation

**Phase 4 becomes immediate-testable**:
- No operator Resend connect ceremony required
- Operator opts in to one notification via chat (flip `active: false → true`) — that's the only operator-side action
- Next natural Reviewer wake (or substrate-event canary) fires `send_operator_email` via system wire → email lands in operator's inbox from `yarnnn <noreply@yarnnn.com>`
- Validates the full L6 capital-execution branch on alpha-author per ADR-299's original Phase 4 framing

## Severity

Medium. Phase 1 + Phase 2 + Phase 3 functionality is structurally working in code but pointed at infrastructure that requires operator ceremony to activate — when the right infrastructure is already system-deployed and requires zero operator action. Caught within ~24h of yesterday's earlier correction (which itself was caught within 48h of Phase 1 shipping). Discipline is holding — corrections land before the wrong shape produces operator confusion or wasted setup.

## Status

**OPEN** — Hat-A correction commit follows next; Hat-B resolution commit confirms after correction lands.

## Cross-references

- Predecessor (yesterday's class-naming redundancy): [`2026-05-24-042952-adr299-class-naming-redundancy/`](../2026-05-24-042952-adr299-class-naming-redundancy/)
- ADR-299 (current state): [`docs/adr/ADR-299-kernel-universal-operator-addressing-capability.md`](../../adr/ADR-299-kernel-universal-operator-addressing-capability.md)
- ADR-040 (Notifications, original operator-addressing wire): naming conventions only; the operative code is `api/services/notifications.py`
- ADR-202 (Daily-Update Email Pointer Template, operator-addressing wire usage): [`docs/adr/ADR-202-...`](../../adr/) — see specifically §1 framing
- ADR-192 Phase 4 (per-user audience-addressing Resend wire): [`docs/adr/ADR-192-...md`](../../adr/) — §"Phase 4 — Email send capability"
- System Resend wire: `api/jobs/email.py::send_email` (~90 LOC, reads `RESEND_API_KEY` + `RESEND_FROM_EMAIL` env vars)
- Per-user Resend wire: `api/integrations/core/resend_client.py` (used by `platform_email_send` + `platform_email_send_bulk`)
- Phase 1 commit that introduced the wire error: `3f0cabb`
- Yesterday's class-naming correction (that left the wire error intact): `50df8b4`
- Phase 2 (bundle preferences schema): `50d37a8` — unaffected; schema is wire-agnostic
- Phase 3 (persona-frame nudge): `0248b56` — the "wire-gate handling" prose becomes obsolete with the correction
- MANDATE nudge: `3d8211a` — unaffected
