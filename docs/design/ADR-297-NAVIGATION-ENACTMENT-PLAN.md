# ADR-297 Navigation Enactment Plan — Compositor Owns Navigation

> **Status:** Draft (2026-05-30, KVK + Claude)
> **Type:** Enactment plan for the unshipped tail of ADR-297 (D19 / D19.4 / D19.5 / D20 deletions). NOT a new ADR — this fulfills decisions already ratified.
> **Guiding axiom (first-principles, operator-confirmed 2026-05-30):** the window-manager shell is correct (ADR-222 names the compositor *as* the window manager); the browser router is transport, not control. Navigation must flow through the compositor layer, never past it.

---

## The defect in one sentence

The shell machinery of ADR-297 shipped (Desktop, WindowFrame, Dock, multi-mount lifecycle, z-tiers — D11→D18.3 are `Implemented`), but **navigation still happens at the browser-router layer (33 `router.push`/`replace` call sites to authenticated routes) instead of the window-manager layer (`foregroundSurface`, 6 call sites).** Two physics on one desktop. D19/D19.4/D20 documented the fix but were left `Proposed`; the enactment never landed.

This plan is the enactment. It is thesis-mandated cleanup of an unenforced layer boundary, not a re-litigation.

---

## What the audit found (2026-05-30, receipts)

**Two surface-state systems coexist** (the root Singular-Implementation violation):

| System | File | Role | Verdict |
|---|---|---|---|
| **Window manager** | `web/lib/shell/useSurfacePreferences.tsx` | `foregroundSurface` / `closeSurface` / window geometry / z-tiers / cap. Correctly couples open+foreground with URL-as-transport (`doCloseSurface` pushes router only as a *side-effect* of state). | **Canonical** (ADR-297 runtime registry). Keep. |
| **Legacy Supervisor Desk** | `web/contexts/DeskContext.tsx` | ADR-023 surface reducer: `agent-detail` / `document-viewer` / `platform-detail` / `agent-review` / attention queue + its OWN pathname watcher. | **Dead-weight** — duplicates the window manager. Delete after its one live consumer is converted. |

**The one live consumer of the legacy system** (why it can't just be `rm`'d): `NarrativeContext.tsx` (`onSurfaceChange`) is the TP chat-handoff path — when the agent says "I opened Cadence for you," it emits a `DeskSurface` object that `AuthenticatedLayout.handleSurfaceChange` (lines 175–202) maps to `router.push`. That switch contains the wrong mappings (`task-detail → /agents`, should be cadence) and the wrong gesture (push, should be foreground). Convert it; don't orphan it.

**The 33 violations, classified:**

| Class | Count | Examples | Disposition |
|---|---|---|---|
| **1 — Dead routes** | 7 | `ConnectedIntegrationsSection` ×5 → `/work?task=` (dissolved); `FeedFilterBar` ×2 → `/chat` (stub) | **Bug.** Re-point to live surfaces (`/cadence?task=`) or convert to `foregroundSurface`. |
| **2 — Wrong-gesture** | ~4 | `settings/page.tsx` ×2 + `WorkspaceSection` → `/feed` | **Convert** to `foregroundSurface('feed')` per D19.4. |
| **3 — Intra-surface deep-link state** | ~12 | `agents/page.tsx` `router.replace('/agents?agent=…',{scroll:false})`; `context/page.tsx` `?path=`; `cadence/page.tsx` `?task=` | **KEEP.** Window-internal state per D19.4 (= Figma's `?node-id=`). Not cross-surface nav. |
| **4 — Redirect stubs** | ~6 | `system→/settings`, `brand→/identity`, `memory→/context?path=…`, `docs→/context` | **KEEP as transport.** These are cold-boot redirect stubs; the pathname watcher opens the right window. Audit, don't convert. |
| **5 — Orphaned machinery** | 7 | `AuthenticatedLayout.handleSurfaceChange` DeskSurface switch | **DELETE** after converting the NarrativeContext handoff. |

So the real conversion surface is **Class 1 + Class 2 (~11 sites) + the handoff path** — not 33. Class 3 + 4 are correct already. This is the discipline payoff of classifying before sweeping.

---

## The hardening principle: make the wrong gesture impossible

The fix is not "convert 11 call sites." Call-site conversion regresses the moment the next component reaches for `useRouter().push` (the React-default thing in the room). The durable fix is a **layer boundary enforced by one primitive + one guard:**

1. **One navigation primitive** — `navigateToSurface(slug, params?)` on the window-manager layer. Internally: `foregroundSurface(slug)` + sync URL as transport. This is the syscall-for-navigation. It is the *only* sanctioned way to move between surfaces in-app.
2. **Router demoted to transport** — `useRouter().push` to an authenticated surface route becomes architecturally illegal (like an app drawing to the framebuffer). Inbound transport (cold-load pathname → window) stays; outbound router-as-navigation goes.
3. **A guard that finds violations mechanically** — a test gate (and/or lint rule) that bans `router.push('/{kernel-surface-slug}')` outside the primitive. Regression-proof.

---

## Phased plan (Singular Implementation — each phase lands green)

### Phase 0 — Reconcile the doc-code honesty gap (doc-only, no code)

The most dangerous current state: D19/D19.4/D20 read as ratified but the code is at ~D18. Future sessions build on claimed coherence that isn't there.

- Flip D19 / D19.4 / D19.5 / D20 status lines from `Proposed` to `Enacting (see ADR-297-NAVIGATION-ENACTMENT-PLAN.md)` until this plan completes, then `Implemented`.
- This file (`docs/design/`) is the working tracker; ADR-297 stays the canon.

**Gate:** none (doc). **Risk:** zero.

### Phase 1 — The navigation primitive (additive, no deletions)

- Add `navigateToSurface(slug, params?)` to `SurfacePreferences` interface + provider in `useSurfacePreferences.tsx`. Body: validate slug is a kernel surface → `foregroundSurface(slug)` → if params, sync URL via the existing transport mechanism (mirror `doCloseSurface`'s router-as-side-effect pattern).
- Re-point the 6 existing `foregroundSurface` callers? No — they're already correct; leave them. The primitive *wraps* the verb for the param case + future-proofs the URL-sync contract.
- Export a thin `useNavigate()` convenience if ergonomics demand (decide at impl; lean toward not adding indirection).

**Gate:** `tsc` + `next build` clean. Primitive unused yet → no behavior change. **Risk:** low (additive).

### Phase 2b — Chat surface meta-awareness (rides on the unification)

**Operator requirement (2026-05-30):** the chat surface must *display* which surface the operator is currently viewing — so operator ↔ agent ↔ surface share meta-awareness through the chat channel. The chat is the room they talk in; the room should announce what's on the table.

**Why this belongs in the unification, not as a bolt-on:** the signal that tells the *agent* "the operator is asking about Cadence" and the signal that tells the *operator* "you're talking about Cadence" must be **the same signal**, sourced from the **same window manager**. Today `ChatDrawer` reads `surfaceOverride` from `useDesk()` (the legacy DeskContext this plan deletes). Migrating that read to `foregrounded` (from `useSurfacePreferences`) is forced by Phase 3's deletion — and once migrated, both the visible label and the agent's `sendMessage({ surface })` payload derive from one source. Shared meta-awareness by construction.

Current state (receipts): `ChatDrawer.tsx:55` reads `useDesk().surface` → passes `surfaceOverride={surface}` into `ConversationPanel` → `sendMessage(message, { surface })` (`ConversationPanel.tsx:176`). The agent **already receives** surface context (drives ADR-186 profile resolution). The gaps: (a) the source is the legacy context, (b) the drawer header shows static "Conversation" — the operator sees nothing.

**Two deliverables:**
1. **Source migration:** `surfaceOverride` flows from `{ type: 'atomic', slug: foregrounded }` (window manager) instead of `useDesk()`. One source feeds both label + agent payload.
2. **Visible label:** drawer header subtitle "Conversation" → `Viewing: {surface title}` (e.g. "Viewing: Cadence"), where title is the compositor's `surface.title` for the foregrounded slug (already in `useComposition()`). When no surface is foregrounded (Desktop), subtitle reads "Desktop" or reverts to "Conversation".

**Gate:** `tsc` + `next build`; operator smoke — open Cadence, summon chat, confirm header says "Viewing: Cadence" AND the agent's response reflects cadence context. **Risk:** low (additive label + one-line source swap; rides Phase 3's required migration). Lands with Phase 3 (it depends on the `useDesk` removal) — or just before it as the bridge.

### Phase 2 — Convert Class 1 + Class 2 + the handoff (the real surface)

- **Class 1 dead routes:** `ConnectedIntegrationsSection` ×5 `/work?task=X` → `navigateToSurface('cadence', {task: 'X'})` (confirm cadence is the task home post-`/work`-dissolution). `FeedFilterBar` ×2 `/chat` → the feed surface (confirm whether these are filter-clears that should stay `router.replace` for URL-only param work — Class 3 candidate; verify before converting).
- **Class 2 wrong-gesture:** `settings/page.tsx` ×2 + `WorkspaceSection` `/feed` → `navigateToSurface('feed')`.
- **The handoff:** rewrite `AuthenticatedLayout.handleSurfaceChange` — map the surviving `DeskSurface` kinds to `navigateToSurface` with *correct* slugs (`task-detail → 'cadence'`, `agent-detail → 'agents'` w/ param, `document-viewer → 'files'`/`/docs`, etc.). Delete the `router.push` arm.

**Gate:** extend `api/test_adr297_phase1.py` (or new `_phase2`) — assert zero `router.push('/work'|'/chat')` in the tree; assert handoff maps to live slugs. `tsc` + `next build`. Operator browser smoke. **Risk:** medium (touches live handoff).

### Phase 3 — Delete the legacy Supervisor Desk system (Singular Implementation)

Once nothing produces `DeskSurface` for navigation:

- Strip the legacy surface kinds + attention-queue + dual pathname-watcher from `DeskContext.tsx`. Decide: does DeskContext survive at all, or fold its last real responsibility into the window manager? (Audit `NarrativeContext`, `ConversationPanel`, `Launcher`, `AtomicSurfaceMount` consumers — several may only need `foregroundSurface`.)
- Delete `handleSurfaceChange`'s now-dead arms.
- Delete `ThreePanelLayout` residue import in `ConversationPanel.tsx`.
- Audit + remove `setBreadcrumb` writes from atomic surfaces (D19 §3 — keep `BreadcrumbContext` for legacy non-atomic routes only).

**Gate:** `tsc` + `next build`; grep gate confirms zero `DeskSurface`-as-navigation; phase test green. **Risk:** medium-high (largest deletion; do last, isolated).

### Phase 4 — The regression guard (hardening)

- Test gate: ban `router.push('/{slug}')` / `router.replace('/{slug}')` for any kernel-surface slug, outside `useSurfacePreferences.tsx` + redirect-stub files (allowlist). Python test walking the tree, same shape as the existing `api/test_adr209_no_filename_versioning.py` banned-pattern guard.
- Optional: ESLint `no-restricted-syntax` rule (web has no eslintrc yet — adding one is its own small decision; the Python gate is sufficient for v1).

**Gate:** the guard itself is the gate. **Risk:** low.

### Phase 5 — Stale-route cleanup (independent, can land anytime)

- The ~8 legacy redirect stubs (`chat`, `workfloor`, `orchestrator`, `overview`, `operation`, `team`, `system`, `memory`) — confirm each still has an inbound need (bookmark safety) or delete. Several may be deletable now.

**Gate:** grep for inbound links to each stub before deleting. **Risk:** low.

---

## Sequencing + commit shape

- **Phase 0** lands first, alone (doc honesty before code).
- **Phase 1** lands alone (additive primitive, green, no behavior change).
- **Phase 2** lands as one commit (conversions + handoff rewrite + phase-2 test) — this is where operator-visible routing becomes coherent.
- **Phase 3** lands alone (the big deletion, isolated for blast-radius clarity).
- **Phase 4** lands with or right after Phase 3 (guard locks in the win).
- **Phase 5** opportunistic.

Each phase: `tsc` clean + `next build` clean + the phase's test gate + (Phase 2/3) operator browser smoke. No dual-render, no flag-gating — Singular Implementation per D8.

---

## The decoupled question (NOT in scope here)

ADR-297 grew 18 same-session amendments adding macOS-fidelity window richness (drag / resize / z-stack / 8-window cap / cascade / minimize / zoom). **First principles endorse the window-manager *shell*; they do not mandate macOS-fidelity as a goal.** Window-chrome richness is *layout policy* (ADR-297 itself flags it as 2nd-order, operator-configurable) and is **orthogonal to this navigation fix.** Whether the alpha-1 operator needs the full window-manager richness vs. a simpler "atomic surfaces, one foregrounded, Dock to switch" is a separate product decision — to be taken on operator need, not metaphor-fidelity. This plan fixes the *navigation gesture*; it touches none of the window-richness machinery.

---

## Definition of done

1. One navigation primitive owns all in-app surface movement.
2. Zero `router.push`/`replace` to a kernel-surface route outside the primitive + allowlisted stubs.
3. Legacy Supervisor Desk navigation machinery deleted (Singular Implementation).
4. A regression guard prevents the boundary from leaking again.
5. ADR-297 D19/D19.4/D19.5/D20 flipped to `Implemented` with this plan referenced.
6. Operator browser smoke: clicking around the desktop produces one consistent physics (window-open/foreground), no viewport-replace surprises.
