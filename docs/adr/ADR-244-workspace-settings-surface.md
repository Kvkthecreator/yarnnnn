# ADR-244 — Workspace Settings Surface: Program Lifecycle as a First-Class Cockpit Concern

**Status:** Proposed (2026-05-01)

**Supersedes:** ADR-240 (Onboarding-as-Activation — modal pattern dissolves into the surface).

**Amends:** ADR-226 (closes the deactivation + post-signup-activation gaps explicitly punted at v3).

**Preserves:** ADR-205 F1 (chat-first landing), ADR-206 D6 (CRUD split: create-via-modal, update-via-chat), ADR-209 (Authored Substrate + revision attribution), ADR-214 (four-tab cockpit nav), ADR-222 (kernel/program boundary), ADR-225 (compositor), ADR-235 D1 (substrate writes route through inference primitives + WriteFile, not forms).

---

## Context

Two parallel observations forced this ADR:

1. **Workspace init audit (2026-05-01).** A "purge then re-init without program" lands the operator in a chat-functional but under-scaffolded state — MANDATE / IDENTITY / BRAND are visible skeletons, but no surface walks the operator through authoring them. The activation overlay (`prompts/chat/activation.py`) only engages when a bundle is active for the workspace via `bundles_active_for_workspace` (capability-implicit per ADR-224 §3). For the no-program path it never fires. The standard workspace prompt has "confirm before mandate write" guidance but no first-turn cue to start authorship. The empty workspace feels under-scaffolded because it *is* under-scaffolded — there's no surface.

2. **`OnboardingModal` is a modal that pretended to be a permanent surface.** ADR-240 shipped a two-step modal at signup (program-pick + platform-connect). Once the operator picks "Start without a program" or completes Step 2, the modal cannot be re-opened. There is **no way for an operator to switch programs, deactivate, re-pick after a purge, or even inspect "what program am I running" without parsing MANDATE.md by eye**. ADR-226 v3 acknowledged the gap explicitly: *"operator who skips at signup and connects platform later doesn't get fork (gap is honest; future ADR addresses if pressure surfaces)"*. The pressure has surfaced.

A third observation falls out of the first two: **the L2 purge silently drops program activation**. `clear_workspace()` at `routes/account.py:585` calls `initialize_workspace(client, user_id)` with no `program_slug`, so an operator who had alpha-trader activated and clicks "Clear workspace" lands in generic state with bundle templates gone. Without a settings surface to re-activate, this is a one-way door.

The right shape is: **one permanent settings surface for program lifecycle, replacing the modal entirely**. Not a parallel surface — the modal is deleted, the auth callback's first-run redirect lands on the surface, and every subsequent program operation (switch, deactivate, re-activate, inspect substrate status, see capability gaps) happens on the same page.

---

## Decisions

### D1. Surface location: `Settings → Workspace` tab

Add a sixth tab to the existing settings shell at `web/app/(authenticated)/settings/page.tsx`: `Workspace`. Order: `Billing | Usage | System | Workspace | Connectors | Account`. (Workspace lands before Connectors so the natural reading order matches operator intent — "what program am I running" precedes "which platforms am I connected to".)

The surface is read-mostly. The only mutation affordances are:

- **Activate** (when no program is currently active) — POST `/api/programs/activate`.
- **Switch** (when a different program is active) — same POST endpoint; the bundle's idempotent re-fork rules (ADR-226 §4) handle it. Operator-authored content is preserved per ADR-209; canon files re-applied; authored files re-applied only if still skeleton.
- **Deactivate** (when a program is active) — new POST `/api/programs/deactivate`. **Drops the bundle-template marker only**; operator-authored content stays. See D5.
- **Connect missing platform** — deep-link to existing `/settings?tab=connectors`. Same OAuth flow the rest of the app already uses. No duplication of `ConnectedIntegrationsSection` logic.
- **Open a substrate file in chat** — deep-link to chat with an authoring intent (out-of-scope for this ADR; the surface exposes the file path + state, not an intent param).

The surface does **not** edit MANDATE / IDENTITY / BRAND / AUTONOMY / principles content. Per ADR-206 D6 + ADR-235 D1, those are judgment-shaped writes routed through chat (`InferContext`, `InferWorkspace`, `WriteFile`).

### D2. Endpoint rename: `/api/memory/user/onboarding-state` → `/api/workspace/state`

The "onboarding" framing dies with the modal. Singular implementation discipline: one canonical workspace-state endpoint, one canonical name, one caller-facing URL. The new endpoint:

- **Path:** `GET /api/workspace/state`
- **Side effect preserved:** lazy roster scaffolding (calls `initialize_workspace` if no agents) — this is the load-bearing first-login behavior auth/callback depends on. Idempotent — only fires when no agents exist.
- **Shape extended (additive):**
  ```python
  class WorkspaceStateResponse(BaseModel):
      has_agents: bool                        # legacy, kept for callback gate
      activation_state: str                   # 'none' | 'post_fork_pre_author' | 'operational'
      active_program_slug: Optional[str]      # parsed from MANDATE.md template marker
      # New fields per ADR-244:
      available_programs: List[ProgramItem]   # mirrors /api/programs/activatable
      substrate_status: SubstrateStatus       # per-file skeleton/authored classification
      capability_gaps: List[CapabilityGap]    # required-but-not-connected platforms for active bundle
  ```

The OLD endpoint is **deleted**, not aliased. All call sites — `auth/callback`, `settings/page.tsx` (post-purge safety-net calls), `api.onboarding.getState()` — migrate in the same commit. Settings-side cosmetic comments referring to "onboarding modal" are rewritten to reference the Workspace tab.

The endpoint moves out of `routes/memory.py` into a new `routes/workspace.py` so the URL prefix is honest (it's not a memory endpoint anymore). Keep `OnboardingStateResponse` Pydantic model name as `WorkspaceStateResponse`. Same renames in API client (`api.onboarding.getState` → `api.workspace.getState`).

### D3. New endpoint: `POST /api/programs/deactivate`

Closes ADR-226's deferred deactivation gap. Behavior:

- Reads the active program slug from MANDATE.md heading marker (same logic as `routes/memory.py:255-274`).
- If no active program: returns `{deactivated: false, reason: "no_active_program"}` — idempotent no-op.
- If active program exists: rewrites the MANDATE.md heading line from `# Mandate — alpha-trader (template)` to plain `# Mandate`. **Body content untouched** — operator's authored mandate stays. `authored_by="system:program-deactivate"` per ADR-209.
- Returns `{deactivated: true, prior_program_slug: "alpha-trader"}`.

The deactivation is **soft by design**: operator's authored content is theirs (ADR-209 preserves it; ADR-235 D1 routes substrate writes through operator/inference attribution; the purpose of deactivation is to sever the bundle's idempotent re-fork relationship, not to wipe authored content). If the operator wants to wipe content, that's a Files-side delete or an L2 purge — not "deactivate".

**Out of scope for this ADR:** auto-archive recurrences scaffolded by the bundle on deactivation, auto-disconnect bundle-required platforms. Both can be added if pressure surfaces; the conservative default is "deactivation drops the marker, leaves substrate alone".

### D4. L2 / L4 purge: preserve `active_program_slug` and re-fork

`clear_workspace()` and `reset_account()` both call `initialize_workspace()` with no `program_slug`. This silently strips program activation. ADR-244 fixes both call sites:

1. **Before** the purge SQL, read the current `active_program_slug` from MANDATE.md heading marker (use the same parser as the workspace-state endpoint).
2. Run the purge as before.
3. **Re-init** with the captured slug: `initialize_workspace(client, user_id, program_slug=prior_slug, browser_tz=...)`. The init function already supports this parameter (per ADR-226 Phase 1).
4. Operator lands in `post_fork_pre_author` state with bundle templates back in place — they get to re-author MANDATE/IDENTITY against the same program. Same-program purge is no longer a one-way door.

If the operator wants to drop their program too, they explicitly click Deactivate first, then purge.

L1 (`clear_work_history`) is unaffected — it doesn't touch substrate.

L3 (`disconnect_platforms`) is unaffected at the substrate level. Disconnecting Alpaca makes the bundle no longer "active" via `bundles_active_for_workspace` (capability-implicit per ADR-224 §3), but the MANDATE.md heading marker is unchanged. This is the pre-existing inconsistency between the two activation signals (`active_program_slug` from substrate vs. `bundles_active_for_workspace` from connections); the surface exposes both honestly via `capability_gaps` so the operator sees: *"alpha-trader template is in your MANDATE, but Alpaca is not connected — autonomous execution is paused."*

### D5. Auth callback: redirect first-run to the Workspace tab, not modal

`/auth/callback/page.tsx` currently mounts `OnboardingModal` when `activation_state === 'none' && !active_program_slug`. ADR-244 changes the behavior:

- The callback still calls `api.workspace.getState()` (renamed) to trigger lazy roster scaffolding.
- If `activation_state === 'none' && !active_program_slug`: redirect to `/settings?tab=workspace&first_run=1` instead of `next` (typically `/chat`).
- The Workspace tab reads `?first_run=1` and renders the same content layout, but tightens the call-to-action: a "Continue to chat" link is prominent at the top, and the operator can pick a program OR explicitly continue without one.
- Once the operator picks a program OR clicks "Continue to chat", the surface navigates them to `/chat` with `?first_run` cleared. From that point on, the Workspace tab is just the Workspace tab — no special first-run treatment.

`first_run=1` is a render hint, not a different surface. Same code path, one extra prop. Singular implementation.

### D6. `OnboardingModal` deletion

Delete `web/components/onboarding/OnboardingModal.tsx`. Delete `api/test_adr240_onboarding_activation.py`. Delete the `BUNDLE_PLATFORM_REQUIREMENTS` map from the modal — its single use case (Step 2's Connect Alpaca affordance) becomes a deep-link to `/settings?tab=connectors` from the Workspace tab. The mapping itself is no longer needed FE-side; the bundle reader's MANIFEST already declares `requires_connection` per capability, surfaced through `capability_gaps`.

The `web/components/onboarding/` directory is empty after deletion; remove it.

### D7. Hard boundary: zero edit affordances for substrate content

The surface displays:

- Mandate: `skeleton` ✗ or `authored` ✓ — file path link to Files; "Open in chat to author" deep-link.
- Identity: same.
- Brand: same.
- Autonomy: same. (Note: AUTONOMY.md is canon-tier in alpha-trader; for a no-program workspace it's the kernel default. The surface labels it "kernel-default" vs "operator-customized" rather than "skeleton" vs "authored", because operator-customization is rare and the kernel default is a working state.)
- Reviewer principles: same. (Reviewer's seat is at `/agents?agent=thinking-partner&tab=principles` per ADR-241; the Workspace tab links there.)
- Bundle-shipped recurrence YAMLs (per `/workspace/reports/*/`): listed by program but not editable.

The surface NEVER renders an `<input>` or `<textarea>` for substrate content. Every "edit" routes elsewhere — chat for authoring, Files for direct markdown editing, the Reviewer detail for principles. This boundary is the discipline that prevents the surface from devolving into a settings panel three ADRs from now.

### D8. Doc radius scope (in this commit)

In addition to the ADR file itself:

- **Mark ADR-240 Superseded** in its status header; preserve body verbatim per ADR-236 Rule 2.
- **Update ADR-226** status header — note that v3's deferred "deactivation gap" + "post-signup activation gap" close in ADR-244 D3 + D5 respectively.
- **Update CLAUDE.md** ADR list — add ADR-244 entry; mark ADR-240 superseded in its entry.
- **Update `docs/design/SURFACE-CONTRACTS.md`** — add Workspace settings surface contract with the read-only-status discipline locked in.
- **Update `docs/architecture/os-framing-implementation-roadmap.md`** — note that ADR-226 §6 (operator activation flow) gains a permanent surface beyond signup, plus the deactivation flow now exists.
- **Test gate** — `api/test_adr244_workspace_settings_surface.py` covers: (1) endpoint rename + shape, (2) deactivate idempotency + soft-by-design preservation, (3) L2/L4 program preservation, (4) OnboardingModal deletion, (5) callback redirect target, (6) singular activate-callsite (the surface is the only FE caller of `api.programs.activate`).

No prompt changes. The TP meta-awareness discussion is deferred to a follow-on ADR per the operator's instruction; once this surface lands, TP's prompt will gain a deterministic reference target ("you're in `post_fork_pre_author` — visit Settings → Workspace to switch programs"), but that's not in this commit.

---

## What this ADR does NOT do

- Does not change `_classify_activation_state` heuristics. Same skeleton detection, same three states.
- Does not change the activation overlay (`prompts/chat/activation.py`). Same prompt, same engagement criteria. The TP meta-awareness pass is a separate ADR.
- Does not introduce a "no-program activation overlay" for the kernel-default path. That's the TP discussion.
- Does not change bundle activation semantics (`bundles_active_for_workspace`). The pre-existing inconsistency between substrate marker and capability-implicit signal is exposed honestly via `capability_gaps`, not resolved.
- Does not introduce a new DB column or migration. Every signal (active_program_slug, activation_state, substrate_status, capability_gaps) is derived server-side from existing substrate.
- Does not auto-archive recurrences on Deactivate. Deactivation drops the marker only.
- Does not add edit affordances for any substrate file. Operator authoring stays in chat per ADR-206 D6.

---

## Implementation seam (two commits, atomic)

**Commit 1 — Backend.**
- New file `api/routes/workspace.py` with `GET /workspace/state` (extended shape) + `POST /programs/deactivate` registered under `/api/programs` prefix.
- Delete `routes/memory.py::get_onboarding_state` + `OnboardingStateResponse`.
- L2 (`clear_workspace`) + L4 (`reset_account`) capture `active_program_slug` pre-purge, pass to `initialize_workspace`.
- `services/programs.py` (new) — small module with `parse_active_program_slug(mandate_content)` so the parser is shared (currently duplicated inline in `routes/memory.py`).
- Test gate `api/test_adr244_workspace_settings_surface.py` (Python regression script, no JS test runner per ADR-236 Rule 3).

**Commit 2 — Frontend.**
- New `web/components/settings/WorkspaceSection.tsx` (the surface body).
- Add `Workspace` tab to `settings/page.tsx`.
- Auth callback: redirect to `/settings?tab=workspace&first_run=1` instead of mounting `OnboardingModal`.
- API client: rename `api.onboarding` → `api.workspace`; add `api.programs.deactivate`; extend `api.workspace.getState()` return type.
- Delete `OnboardingModal.tsx` + `web/components/onboarding/` directory + `api/test_adr240_onboarding_activation.py`.
- Doc updates per D8.

Both commits land green: backend tests pass, FE production build clean, Python regression gate 100%.

---

## Acceptance

- Operator who signs up + skips program at first run can later activate alpha-trader from `Settings → Workspace`.
- Operator who activated alpha-trader can deactivate without losing their authored mandate.
- L2 purge of an alpha-trader workspace lands in `post_fork_pre_author` state with bundle templates re-applied — same program, fresh slate.
- L3 disconnect of Alpaca surfaces a `capability_gaps` entry on the Workspace tab; operator sees "Connect Alpaca" deep-link.
- `OnboardingModal.tsx` does not exist in the tree. `web/components/onboarding/` does not exist.
- `api.onboarding` does not exist on the API client. `api.workspace.getState()` is the canonical state read.
- `api/test_adr244_workspace_settings_surface.py` regression gate passes.
- Existing ADR-225 / ADR-226 / ADR-228 tests still pass (no regression).

---

## Cross-references

- ADR-205 — chat-first landing preserved; surface does not change HOME_ROUTE.
- ADR-206 D6 — CRUD split honored: substrate authoring stays in chat.
- ADR-209 — every substrate write through this surface (deactivation marker rewrite, L2/L4 re-fork) attributed via `authored_by`.
- ADR-214 — cockpit nav unchanged (4 tabs). The surface lives in Settings, not in nav.
- ADR-222 — kernel/program boundary respected: surface reads bundles via `bundle_reader`, never imports kernel-internal state.
- ADR-225 — surface is independent of compositor; reads bundle metadata (title, tagline, current_phase) directly from `bundle_reader._all_slugs() + _load_manifest()`.
- ADR-226 — v3's "future ADR addresses if pressure surfaces" → ADR-244.
- ADR-235 D1 — substrate writes (deactivation marker rewrite) route through `WriteFile(scope='workspace')`, not a new primitive.
- ADR-240 — Superseded by ADR-244.
- ADR-241 — Reviewer principles deep-link respects `?agent=thinking-partner&tab=principles`.
