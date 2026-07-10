# ADR-435 — Delete the Home surface

> **Status**: **Accepted** (2026-07-10, operator-directed). The `home` surface — the composed front page (ADR-312/367/369) — is **deleted in full**. Its six kernel slots are not re-homed into a new surface; their content remains reachable through the mirror surfaces that already own each concept (queue, activity, files). The dock anchor + `default_pinned` + legacy-slug normalization sink move to **`chat`**. **Supersedes** ADR-312 (Home as composition), ADR-367 (Home as operating cockpit), ADR-369 (Home split), and the Home clauses of ADR-340/349 (launcher IA primary tier).
>
> **Why**: Home was the single **composition surface** in a registry of **substrate mirrors** — and it wore the same `register: "application"` label as the flat mirror `files`, so the taxonomy could not distinguish them. It read as an *exception* to the "one surface ↔ one substrate concern" discipline (ADR-297/340 DP29) that the codebase is otherwise hardening. Two operator reasons: (1) the composition is, in practice, a **glorified redirect** — its program tab echoes surfaces that already exist, and its front-page slots each deep-link to a mirror that owns the concept; (2) its exceptional status **breaks the conceptual integrity** we are trying to harden. The resolution chosen is **subtraction, not naming**: rather than promote `composition` to a validated register (keeping Home as a legitimately-distinct kind), the surface is removed, so the registry becomes uniformly mirror-shaped. The accepted product cost: **there is no composed glance-dashboard**; the operator reaches each concern through its own surface.

**Date**: 2026-07-10
**Dimension**: Channel (Axiom 6 — the surface registry) + Substrate (Axiom 1 — the mirror discipline the deletion restores)

**Extends / supersedes**:
- **Supersedes ADR-312** (Home as composition), **ADR-367** (operating cockpit), **ADR-369** (Home split front-page/program-cockpit). The composition thesis is retired; the surface it produced is deleted.
- **Amends ADR-340 D5 / ADR-349** (launcher IA): the primary tier drops from `{home, chat, files}` to `{chat, files}`; `chat` becomes the anchor.
- **Amends ADR-415** (Channels dissolved): the `context/feed/channels → home` legacy-slug normalization re-points to `chat`; `DEFAULT_KEPT_SURFACES` moves `['home'] → ['chat']`.
- **Amends ADR-412 D3** (chat as a surface): `chat` gains `default_pinned: True` and the dock-anchor role.

**Preserves**:
- **`HOME_ROUTE = "/desktop"` is UNCHANGED.** The Desktop shell is the authenticated landing; the `home` *surface* (route `/home`) is a tile within it. Deleting the surface does **not** touch the boot path. Post-auth still lands on `/desktop`; first-run still diverts to `/setup`.
- **The composition registry survives.** `LIBRARY_COMPONENTS` / `dispatchComponent` (`web/components/library/registry.tsx`) is **shared with WorkDetail** (`MiddleResolver`, `ChromeRenderer`) and does not die with Home. Only the Home-exclusive `kind` rows are pruned. *(This corrects an earlier analysis that named Home the sole consumer.)*
- **`RecentsView` survives.** `HomeRecents` was a `limit`-wrapper over the shared `RecentsView`, which the **Files** surface also mounts. Only the wrapper is deleted.
- The three-way surface parity gate (ADR-338) stays green by removing `home` from backend registry + FE union + FE registry **in lockstep**.

---

## 1. The problem — one composition in a registry of mirrors

The surface registry is, by its own docstring, a set of **substrate mirrors**: "surfaces mirror substrate … 1:1 to a substrate concept" (`kernel_surfaces.py`). DP29 ("mirror once, compose few", ADR-340) makes the mirror the escape hatch and the composition the rare, deliberate exception. In practice there was **exactly one** composition surface — `home` — and the `register` field could not even express its distinctness: `register` is an unvalidated string with three de-facto values (`application | intent | os-config`), and `home` and `files` **both** carry `register: "application"` despite Home being a two-layer composition and Files a flat mirror.

So Home was an exception the taxonomy could not name. The audit (`docs/analysis/the-viewer-app-scope-audit-fe-2026-07-10.md` §1 Finding 3) established this precisely. Two ways to resolve an unnameable exception: **name it** (promote `composition` to a validated register) or **remove it** (delete the surface). The operator directed removal — the hardening thesis of the current arc is subtraction, and a convenience dashboard is not worth a permanent taxonomy exception.

## 2. The decision — delete, do not re-home

`home` is deleted as a surface. Its six front-page slots (constitution band, decision queue, workspace timeline, recents, recent artifacts, judgment trail) are **not** relocated into a replacement surface. Each concept already has a mirror that owns it:

| Home slot | Where the concept already lives |
|---|---|
| constitution band (MANDATE/autonomy) | `workspace-settings` (intent panes) + `system-agent` |
| decision queue | `queue` surface (the ADR-307 gate's own mirror) |
| workspace timeline | `activity` surface (the ADR-410 timeline) |
| recents | `files` surface (mounts the same `RecentsView`) |
| recent artifacts | `files` surface |
| judgment trail | `activity` / `notifications` |

The glance-composition is the thing lost. That is the accepted cost. An operator who wants "everything at once" now visits the surfaces; the OS no longer composes them into one page.

## 3. The replacement anchor — `chat`

Home was the sole `default_pinned` surface, the `DEFAULT_KEPT_SURFACES` dock anchor, the sink for three dead legacy slugs (`context/feed/channels`), and the Desktop first-time-detection anchor. All of that moves to **`chat`**, for a recorded reason: chat is the steward's voice (ADR-412) and the active operating surface an empty workspace should land on — "what do you want to do," not a passive browser. `files` was the alternative; `chat` wins because the anchor should be the surface you *act from*, not the one you *read*.

## 4. The teardown map (the ordered change set)

**A. Anchor repoint (lockstep — the app breaks otherwise):**
1. `web/lib/shell/surface-preferences.ts` — `DEFAULT_KEPT_SURFACES: ['home'] → ['chat']`; `LEGACY_SLUG_ALIASES` `context/feed/channels: 'home' → 'chat'`.
2. `web/components/shell/Desktop.tsx` — first-time anchor check `kept[0] !== 'home' → !== 'chat'`.
3. `web/app/(authenticated)/settings/page.tsx` (account purge + reset) + `web/components/library/SetupSequence.tsx` ("Go to Home" button) — `navigateToSurface('home') → 'chat'`.
4. Redirect stubs targeting `/home`: `sources/page.tsx`, `invite/[token]/page.tsx`, `UserMenu.tsx`, `next.config.js` (`/channels` + `/context`) → repoint to `/chat` (or keep a `/home → /chat` redirect stub for bookmark safety).

**B. Remove the surface (three-way parity lockstep — ADR-338):**
5. Backend `api/services/kernel_surfaces.py` — delete the `home` row; move `default_pinned: True` to the `chat` row.
6. FE `web/types/desk.ts` — remove `'home'` from the `KernelSurfaceSlug` union + `KERNEL_SURFACE_SLUGS`.
7. FE `web/components/shell/SurfaceRegistry.tsx` — remove the `home` import + registry entry.

**C. Delete Home-only components:** `home/page.tsx`, `HomeRenderer.tsx`, `HomeContext.tsx`, `HomeHeader.tsx`, and `kernel-home/{HomeFrontPage, ProgramCockpit, HomeRecents, WorkspaceTimeline, KernelDecisionQueue, KernelRecentArtifacts, KernelJudgmentTrail}.tsx`.

**D. Prune now-dead registry + program code:** `LIBRARY_COMPONENTS` entries for the 3 `Kernel*` slots + the 9 program-section components (Trader×7, Author×2); the `programs/alpha-trader/*` + `programs/alpha-author/*` Home-cockpit component files; the `home.program_sections` blocks in `alpha-trader/SURFACES.yaml` + `alpha-author/SURFACES.yaml`; `getProgramSections` (`resolver.ts`) + the `composition_resolver.py` `home` branch; the backend `GET /workspace/home-bundle` endpoint + its FE client method.

**E. PRESERVE (shared — do NOT delete):** `RecentsView.tsx` (Files reuses it), the `LIBRARY_COMPONENTS`/`dispatchComponent` core + `KernelDeliverable*` entries (MiddleResolver/ChromeRenderer reuse them), `ProgramLifecycleDrawer.tsx` (SetupSequence uses it), `lib/workspace/timeline-rows.tsx` (verify no non-Home consumer before removing WorkspaceTimeline).

**F. Test gates to update (~18):** `test_adr338_surface_registry_parity`, `test_adr297_phase1` (default_pinned uniqueness → `chat`), `test_adr312_home_as_composition` (delete — thesis retired), `test_adr369_home_split` (delete), `test_adr367_home_cockpit` (delete), `test_adr340_p3_launcher` + `test_adr349_launcher_ia` (primary tier → `{chat, files}`), `test_adr415_channels_dissolved` (normalization → `chat`, `DEFAULT_KEPT_SURFACES → ['chat']`), `test_adr408_d51_timeline`, `test_adr410_attention`, `test_adr331_setup_rendering`, `test_adr375_agent_gating`, `test_adr225_compositor`, `test_adr297_navigation_enactment`, `test_adr412_chat_surface`, `test_adr340_p4_legibility`, `test_adr317_daily_pnl_dispatcher`, `test_recents_view_unified`, `test_nav_no_cross_surface_router_push`.

## 5. What this ADR does NOT do

- **Does not change the boot path.** `/desktop` is untouched (Preserves §).
- **Does not delete the composition registry.** `dispatchComponent`/`LIBRARY_COMPONENTS` stay for WorkDetail (Preserves §).
- **Does not re-home the six slots.** Their content lives on the mirror surfaces that already own each concept (§2). The glance-composition is intentionally lost.
- **Does not promote `composition` to a validated register.** The alternative resolution (keep Home, name the class) is explicitly rejected in favor of subtraction (§1).
- **Does not touch the alpha-trader/alpha-author program *substrate*.** Only their Home-cockpit *rendering* components + `home.program_sections` declarations are pruned; the programs' recurrences, mandate, and judgment substrate are untouched.

## 6. The one-line statement

**Home was the one composition in a registry of mirrors and the taxonomy could not name the exception, so — choosing subtraction over naming — the surface is deleted, its six slots left to the mirror surfaces that already own each concept, the dock anchor moved to `chat`, the boot path (`/desktop`) untouched, and the composition registry preserved because WorkDetail still needs it.**
