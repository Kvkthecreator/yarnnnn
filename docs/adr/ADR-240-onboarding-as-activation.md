# ADR-240: Onboarding as Activation — Program Pick + Platform Connect at Signup

> **Status**: **Superseded by ADR-244** (2026-05-01). The OnboardingModal pattern is dissolved into the permanent `Settings → Workspace` surface. Same activation flow + idempotency gate, but the surface now lives forever (operator can switch / deactivate / re-activate any time, not just at first signup). `web/components/onboarding/OnboardingModal.tsx` deleted; `api/test_adr240_onboarding_activation.py` deleted. Auth callback now redirects to `/settings?tab=workspace&first_run=1` instead of mounting a modal. Body preserved verbatim per ADR-236 Rule 2.
> **Original status**: Implemented (2026-04-29, single commit). Round 4 of the ADR-236 frontend cockpit coherence pass — the fourth Tier 1 sub-ADR. Test gate `api/test_adr240_onboarding_activation.py` 8/8 passing (test gate file deleted under ADR-244). TypeScript typecheck clean. Cross-ADR regression check 71/71 across eight gates (231 + 233 P1 + 233 P2 + 234 + 237 + 238 + 239 + 240). CHANGELOG entry `[2026.04.29.N]` recorded. Backend infrastructure was already shipped per ADR-226 Phase 1; this ADR is the FE consumption layer ADR-226 Phase 2 explicitly deferred. Operator manual smoke required at fresh signup.
> **Date**: 2026-04-29
> **Authors**: KVK, Claude
> **Dimensional classification**: **Channel** (Axiom 6) primary — onboarding is a sequenced surface; ADR-240 reshapes it. **Identity** (Axiom 2) secondary — program activation is what gives a workspace its persona-bearing character. **Trigger** (Axiom 4) — the post-signup moment is the activation pulse.
> **Builds on**: ADR-205 (Workspace Primitive Collapse — Implemented), ADR-206 (Operation-First Scaffolding — Implemented), ADR-207 (Primary-Action-Centric Workflow — Implemented; capability gating), ADR-226 (Reference-Workspace Activation Flow — Phase 1 Implemented; this ADR is its Phase 2 FE), ADR-235 (UpdateContext Dissolution — Implemented), ADR-236 (Frontend Cockpit Coherence Pass — Round 3 closed + hygiene), ADR-237 (Chat Role-Based Design System — Implemented), ADR-238 (Autonomy-Mode FE Consumption — Implemented), ADR-239 (Trader Cockpit Coherence Pass — Implemented).
> **Composes with**: ADR-237 (chat-side activation overlay renders through the role grammar), ADR-238 (autonomy chip becomes visible during activation conversation when bundle declares `bounded_autonomous`).
> **Preserves**: FOUNDATIONS axioms 1–9, ADR-141 (execution layers), ADR-156 (single intelligence layer — YARNNN remains sole judgment runtime in chat), ADR-159 (filesystem-as-memory), ADR-194 v2 (Reviewer substrate), ADR-209 (Authored Substrate attribution — bundle fork uses `authored_by="system:bundle-fork"`), ADR-216 (orchestration vs judgment), ADR-225 (compositor surface unchanged), ADR-226 backend (Phase 1 substrate path, fork helper, activation overlay prompt — all unchanged).

---

## Context

ADR-205 + ADR-206 collapsed signup-time scaffolding to the kernel minimum (one YARNNN agent row + skeleton substrate files + Reviewer seat). ADR-226 Phase 1 added an **optional** program-activation path: if a `program_slug` is supplied to `workspace_init.initialize_workspace()`, the helper forks the bundle's `reference-workspace/` into the operator's workspace, with three-tier file categorization (canon / authored / placeholder).

**What's broken today:** the FE has no surface that supplies `program_slug`. `web/app/auth/callback/page.tsx` calls `api.onboarding.getState()` which triggers default scaffolding (no program), then redirects to `/chat`. The only program activation path is `POST /api/programs/activate` — which has no FE caller. Every new operator lands with an empty kernel-default workspace; nobody activates a program at signup.

**ADR-207 sharpens the consequence:** mandates carry `required_capabilities`. A trading-domain mandate requires `write_trading` capability. `write_trading` is gated by an active `platform_connections` row for Alpaca. Without platform connection, the mandate's autonomous execution path is unreachable — the workspace is "knowledge mode" only, advisory at best.

**ADR-236 audit (2026-04-29) Item 4** named this as a real gap: "Promote platform connection from optional refinement to first-class onboarding step. Reframe onboarding around ADR-226 program activation rather than form-shaped data capture."

The verified-state inventory:

| Surface | What exists | What's missing |
|---|---|---|
| `GET /api/programs/activatable` | Returns active + deferred bundles | No FE consumer |
| `POST /api/programs/activate` | Forks bundle reference-workspace | No FE caller |
| YARNNN activation overlay (`prompts/chat/activation.py`) | Engages when `activation_state == "post_fork_pre_author"` | Never engaged because nothing forks from FE |
| `web/app/auth/callback/page.tsx` | Triggers `api.onboarding.getState()` for kernel scaffolding | No program-pick step |
| `/integrations/[provider]/page.tsx` | OAuth callback handler | Discoverable only via Settings — not first-class at signup |
| Platform connection in mandate language | ADR-207 capability gating | No FE surface that says "your mandate needs Alpaca" at signup |

ADR-240 is the FE consumption layer that closes these gaps.

---

## Decision

A **two-step post-signup modal** at the auth callback path. Step 1 picks a program (or skip); Step 2 surfaces the platform connections the active program declares as activation preconditions. Both steps are skippable; defaults are honest about what gets enabled / disabled by skipping.

### D1 — Onboarding Modal at `/auth/callback`

A new client component `web/components/onboarding/OnboardingModal.tsx` mounts after Supabase session is established and `api.onboarding.getState()` triggers kernel scaffolding (preserved). Before redirecting to `HOME_ROUTE`, the callback opens the modal **if** the operator hasn't already activated a program (detected via the existing onboarding-state response — extended by D5 below).

**Two steps, never more:**

- **Step 1 — Program**: cards listing active programs from `GET /api/programs/activatable`, plus a "Start without a program" card. Selecting an active program calls `POST /api/programs/activate` and waits for the response. Deferred programs (`deferred: true`) render with a "Coming soon" disabled card per the registry's intent.

- **Step 2 — Platform connection**: appears **only if** Step 1 activated a program with declared activation preconditions (e.g., alpha-trader requires Alpaca). Renders an affordance focused on the bundle's required platforms. Skip is allowed; the modal closes and the operator lands in `/chat` where YARNNN's activation overlay walks them through the authored-tier files.

If Step 1 activates a program that has no preconditions, Step 2 is skipped automatically. If Step 1 picks "Start without a program," Step 2 is skipped automatically (no preconditions to surface).

### D2 — Step 1 wireframe semantics

The Step 1 cards encode three pieces of information per program:

- Title + tagline (from MANIFEST: `title`, `tagline`)
- Oracle profile blurb (from MANIFEST: `oracle.summary` if present)
- Status badge: **Active** (selectable) / **Coming soon** (disabled)

The "Start without a program" card is its own variant — secondary visual treatment, copy: *"Run the kernel as-is. You can activate a program later from Settings."*

Selection is single-pick. No multi-select. (Multi-program operators are out of scope for this ADR; per CLAUDE.md ADR-222 framing, a workspace runs one program. Multi-program is a future ADR.)

### D3 — Step 2 surfaces only what the bundle declares

When a program activates, the bundle's MANIFEST `activation_preconditions` (or equivalent — read from the bundle reader) declares which platforms must be connected for the mandate's capabilities to bind. Step 2 surfaces **only those**, in the order the manifest declares them.

For alpha-trader specifically: Alpaca (paper or live). Step 2 renders an affordance that explains "your alpha-trader mandate needs Alpaca for write_trading capability — connect now or later."

The implementation re-uses Settings' OAuth flow (link to `/integrations/${provider}/authorize?redirect_to=/auth/callback?next=/chat&onboarding=continue`) so Step 2 cleanly hands off to the existing OAuth callback shape, then re-enters the modal at Step 2 with the connection now visible.

**No duplication of Settings' connection logic.** Step 2 reuses the same `api.integrations.authorize(provider, redirectTo)` call site.

### D4 — Skip semantics are honest

If the operator skips Step 1 (chooses "Start without a program"):
- No fork runs.
- Workspace stays kernel-default.
- Modal closes; redirect to `/chat`.
- The first conversation with YARNNN is the kernel-default onboarding overlay (existing per ADR-190), not the bundle activation overlay.

If the operator skips Step 2 (chose a program but doesn't connect a platform):
- Bundle fork already ran in Step 1.
- The activation overlay engages on first chat (existing per ADR-226).
- YARNNN's first conversation can include "your mandate references trading capability but Alpaca isn't connected — connect via Settings when ready." (Prompt extension is a tiny addition to the existing activation overlay; documented in D6.)

The honesty principle: **skipping doesn't pretend the operator made the optimal choice.** It records the choice and proceeds.

### D5 — Onboarding-state endpoint extension

`api.onboarding.getState()` currently returns `{has_agents: boolean}`. ADR-240 extends this to include the program-activation state so the modal knows whether to mount:

```ts
{
  has_agents: boolean;
  activation_state: 'none' | 'post_fork_pre_author' | 'operational';
  active_program_slug: string | null;
}
```

The two new fields are already computed server-side per ADR-226 Phase 1 (`_classify_activation_state` in `working_memory.py`). The endpoint adapter just surfaces them.

If `activation_state === 'none'` AND `active_program_slug === null` → mount the modal (this is a fresh signup or post-skip state).
If either is set → modal does not mount (operator has already chosen).

This is the **idempotency gate** — the modal does not re-prompt operators who already picked.

### D6 — YARNNN activation overlay extension (small)

When the modal exits with a program active but Step 2 skipped, YARNNN's activation overlay (existing per ADR-226 Phase 1, in `prompts/chat/activation.py`) gains one extra paragraph in its first turn:

> *"I notice your mandate calls for {primary_capability} (e.g., trading) but {required_platform} (e.g., Alpaca) isn't connected yet. You can keep working in knowledge mode, or open Settings to connect when ready. Either is fine — autonomous execution waits on the platform connection per ADR-207."*

The existing activation overlay already walks the operator through authored-tier files; the extension is one paragraph that surfaces the capability gap honestly. Implementation: a small string template extension, not a new prompt module.

---

## What this ADR does NOT do

- **Does not introduce a JS test runner.** Same regression-script pattern as ADR-237 / ADR-238 / ADR-239 per ADR-236 Rule 3.
- **Does not change the activation backend.** ADR-226 Phase 1 helpers (`_fork_reference_workspace`, `_classify_activation_state`, `ACTIVATION_OVERLAY` prompt) are unchanged. ADR-240 adds a tiny D6 paragraph extension; everything else FE-only.
- **Does not move the OAuth callback flow.** `/integrations/[provider]/page.tsx` continues to handle OAuth callback. Step 2's "connect" buttons hand off via the existing `api.integrations.authorize()` call.
- **Does not introduce multi-program operator support.** A workspace runs one program. Multi-program is a future ADR.
- **Does not touch Settings.** ConnectedIntegrationsSection is unchanged. Step 2 reuses authorization via the same API surface; doesn't import the Settings component.
- **Does not change `HOME_ROUTE` or the chat-first landing decision (ADR-205 F1).** Operators who skip both steps still land in `/chat`.
- **Does not delete the existing `api.onboarding.getState()` call** in `auth/callback/page.tsx`. That call still triggers kernel scaffolding side-effects; ADR-240 only extends its return shape per D5.
- **Does not change the activation prompt (`prompts/chat/activation.py`) beyond the small D6 paragraph extension.**
- **Does not introduce a database migration.** `activation_state` and `active_program_slug` are computed server-side from existing substrate (per ADR-226 Phase 1).

---

## Implementation

### Files created (3)

- `web/components/onboarding/OnboardingModal.tsx` (~250 LOC)
  - Two-step modal with the program-pick + optional platform-connect flow.
  - Reads `api.programs.listActivatable()`, calls `api.programs.activate()`, hands off to `api.integrations.authorize()`.
  - Internally tracks `step: 1 | 2`, `selectedProgram`, `activationResult`, `loading`, `error` states.
  - Honest skip semantics per D4.
  - Closes via `onComplete` callback that triggers parent's redirect to `HOME_ROUTE`.

- `api/test_adr240_onboarding_activation.py` — Python regression gate (8 assertions).

- `docs/adr/ADR-240-onboarding-as-activation.md` (this file).

### Files modified (4)

- `web/app/auth/callback/page.tsx`
  - After session establish + kernel scaffolding (preserved), check the extended onboarding-state response.
  - If `activation_state === 'none' && !active_program_slug`, mount `<OnboardingModal>` instead of immediately redirecting.
  - Modal's `onComplete` callback triggers the redirect.

- `web/lib/api/client.ts`
  - Extend `api.onboarding.getState()` return type to include `activation_state` and `active_program_slug`.
  - Add `api.programs` namespace with two methods: `listActivatable()` → calls `GET /api/programs/activatable`; `activate(programSlug)` → calls `POST /api/programs/activate`.

- `api/routes/memory.py` (or wherever the `/api/memory/user/onboarding-state` endpoint lives)
  - Extend the response with `activation_state` (read via existing `_classify_activation_state` helper) and `active_program_slug` (read from the workspace's bundle marker if present; null otherwise).
  - **Backend change is small** — a 5-line addition. ADR-236 scope guard 1 (no backend work beyond Item 6's 500 fix) is **legitimately violated** here, with rationale: ADR-236 Item 4 explicitly anticipates onboarding-flow work that requires the FE to know activation state; the endpoint extension is the smallest possible adapter; the alternative (a separate `/api/programs/activation-state` endpoint) creates a parallel state-query path that violates Singular Implementation.

- `api/agents/prompts/chat/activation.py`
  - Add the D6 paragraph extension as a string append to the existing overlay when `capability_gap` flag is set (computed server-side from mandate's `required_capabilities` minus active `platform_connections`).

### Files NOT modified

- `api/services/workspace_init.py` — fork helper unchanged.
- `api/services/working_memory.py` — `_classify_activation_state` unchanged.
- `api/services/bundle_reader.py` — bundle metadata reading unchanged.
- `api/routes/programs.py` — endpoints unchanged.
- `web/components/settings/ConnectedIntegrationsSection.tsx` — unchanged. Step 2 reuses the authorization API call, not the component.
- `/integrations/[provider]/page.tsx` — OAuth callback unchanged.
- ADR predecessors — Rule 2 historical preservation.

### Test gate

`api/test_adr240_onboarding_activation.py` asserts eight invariants. Mix of FE source-grep and backend response-shape checks.

1. `web/components/onboarding/OnboardingModal.tsx` exists and exports `OnboardingModal`.
2. `web/app/auth/callback/page.tsx` imports `OnboardingModal` from `@/components/onboarding/OnboardingModal`.
3. `web/lib/api/client.ts` exposes `api.programs.listActivatable` and `api.programs.activate` namespaces.
4. `web/lib/api/client.ts` extends the onboarding-state return type with `activation_state` and `active_program_slug` fields (string-grep on the type definition).
5. `api/routes/memory.py` (or current home of `/api/memory/user/onboarding-state`) returns `activation_state` and `active_program_slug` in its response (assertion checks the response model includes the keys).
6. `api/agents/prompts/chat/activation.py` includes the D6 capability-gap paragraph (string assertion).
7. Singular Implementation regression guard: there is exactly one FE call site that activates a program — `OnboardingModal.tsx`. No other FE file references `api.programs.activate`.
8. `OnboardingModal.tsx` does not duplicate `ConnectedIntegrationsSection` logic — assertion is a forbidden-import check that `OnboardingModal` does NOT import from `@/components/settings/ConnectedIntegrationsSection`.

Combined gate target: 8/8 passing.

### Render parity

| Service | Affected | Why |
|---|---|---|
| API (yarnnn-api) | Yes (small) | Onboarding-state endpoint extension; activation prompt one-paragraph extension. |
| Unified Scheduler | No | FE flow only. |
| MCP Server | No | FE flow only. |
| Output Gateway | No | Untouched. |

**No env var changes. No schema changes. No new services.**

### Singular Implementation discipline

- One modal — `OnboardingModal.tsx`. No "skip-modal" / "modal-v2" / shim variants.
- One activation call site — `OnboardingModal.tsx` is the only FE file that calls `api.programs.activate`. Test gate assertion #7 enforces.
- One onboarding-state endpoint — `/api/memory/user/onboarding-state` is extended in shape, not replaced or paralleled. No `/api/programs/activation-state` parallel endpoint.
- One platform-connection authorization path — Settings + Onboarding modal both call `api.integrations.authorize()`. The OAuth callback page (`/integrations/[provider]/`) unchanged.

---

## Risks

**R1 — `auth/callback/page.tsx` is a critical-path file.** Modal mount logic interferes with redirect timing if implemented carelessly. Mitigation: `onComplete` callback is the explicit redirect trigger; the modal does not race with `window.location.href = next`. Skipping the modal preserves the current redirect behavior bit-for-bit.

**R2 — Operator skips Step 1, never activates.** The "Start without a program" card is honest but might lead to underused workspaces. Mitigation: D6's overlay extension surfaces the capability gap on first chat, so operators who skip have a clear path to revisit. Future ADR (out of scope here) could add a "Activate a program" affordance to Settings; today the operator can call `POST /api/programs/activate` via Settings or via chat with YARNNN's mediation.

**R3 — Step 2 modal-after-OAuth-callback re-entry.** When the operator clicks "Connect Alpaca" in Step 2, they're sent to `/integrations/alpaca/authorize` which redirects to OAuth, then back to `/auth/callback?next=/chat&onboarding=continue` (or similar). The modal needs to **re-mount** at Step 2 to show success. Mitigation: query-param `onboarding=continue` triggers Step 2 re-entry; activation state is recomputed from substrate per D5; modal jumps directly to Step 2 if `active_program_slug` is set.

**R4 — Idempotency on re-signup or session reset.** If operator clears cookies and re-signs-in, the modal should not re-prompt. Mitigation: D5's gate uses `activation_state` (substrate-derived) — if substrate has been forked, modal skips. The workspace's filesystem state is the source of truth, not session state.

**R5 — Multi-program operator pressure.** Some operators may want to "try" alpha-trader and later switch to alpha-commerce. Mitigation: out of scope. ADR-240 enforces single-program at signup. If multi-program pressure surfaces, a future ADR introduces program-switch semantics. Scope guard explicit in §"What this ADR does NOT do."

**R6 — Activation-prompt drift.** Adding a D6 paragraph to `prompts/chat/activation.py` is a behavioral change that should be CHANGELOG'd per ADR-236 Rule 4. Mitigation: CHANGELOG entry `[2026.04.29.N]` for ADR-240 includes the prompt addition explicitly.

---

## Phasing

Single commit, sized medium (~400 LOC delta total). The dependency graph is linear:

1. Author `OnboardingModal.tsx` (~250 LOC).
2. Extend `web/lib/api/client.ts` — add `api.programs` namespace + extend onboarding-state type.
3. Extend backend onboarding-state endpoint (5-line addition).
4. Modify `auth/callback/page.tsx` — mount modal when activation_state is none.
5. Add D6 paragraph extension to `prompts/chat/activation.py`.
6. Author `api/test_adr240_onboarding_activation.py` — 8 assertions.
7. Run all gates (231 / 233 P1+P2 / 234 / 237 / 238 / 239 / 240).
8. Manual smoke required: fresh signup → modal renders → pick alpha-trader → fork runs → Step 2 surfaces Alpaca → connect or skip → land in `/chat` → activation overlay engages.
9. Add `[2026.04.29.N]` CHANGELOG entry.
10. Atomic commit + push.

Post-commit: pre-commit `git diff --cached --stat` discipline per ADR-239's recovery note (commit `0a7fee3`) — verify no other-session files swept into the commit.

---

## Closing

ADR-240 is the FE consumption layer ADR-226 Phase 1 explicitly deferred. The backend infrastructure has been waiting; ADR-240 is the surface that finally calls it. With ADR-240 shipped:

- Fresh operators see a program-pick at signup.
- Operators who pick alpha-trader connect Alpaca in the same flow.
- Operators who skip everything still land in a working chat-first workspace.
- YARNNN's activation overlay engages for picked-program operators on first chat.
- Capability gaps surface honestly instead of silently degrading the operator experience.

The umbrella's Item 4 ("promote platform connection from optional refinement to first-class onboarding step") closes. Round 4 lands.
