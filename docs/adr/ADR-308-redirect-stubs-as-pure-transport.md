# ADR-308 — Redirect Stubs as Pure Transport: Closing the OS-Shell Bimodality Seam

> **Status:** Implemented (2026-06-01) — 12 interior stubs converted to server `redirect()`; `/docs` stale copy purged; regression gate `api/test_adr308_redirect_stubs_transport.py` 13/13; sibling gates green (phase1 137/137, nav-enactment 21/21, pace 12/12); FE `tsc --noEmit` clean. `ALLOWLIST_REDIRECT_STUBS` in the ADR-297 nav guard emptied (the client-stub pattern no longer exists in any stub). Landed alongside the `brand`-slug deletion (ADR-309 re-classification) in the same commit.
> **Authors:** KVK, Claude
> **Amends:** [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) D19.4 (finishes the invariant D19.4 declared but did not fully enact — `isLegacyNonAtomicRoute` survives only at the authentication boundary, *not* inside the authenticated workspace) · the redirect-stub policy in [`web/lib/routes.ts`](../../web/lib/routes.ts) (stubs move from client-render to transport)
> **Preserves:** [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) axiom (surface = viewport panel, not URL destination) · D17 (Desktop as load-bearing layer) · D19.5 (compositor owns navigation) · [ADR-222](ADR-222-agent-native-operating-system-framing.md) (kernel/userspace boundary) · [FOUNDATIONS](../architecture/FOUNDATIONS.md) Axioms 1–9 · Singular Implementation
> **Dimensional classification:** **Channel** (Axiom 6 — where the operator sees the system)

---

## Context

[ADR-297](ADR-297-surfaces-as-substrate-mirror.md) canonized the OS-shell axiom: **a surface is a viewport panel bound to substrate; the URL is optional addressing transport, not the surface's identity.** D17 made the Desktop layer always-rendered. D19.5 + the navigation-enactment work (commits `fbfcb02` → `91786e3`) converted call sites from `router.push` to `navigateToSurface` and deleted the legacy `DeskContext`, so the window manager (`useSurfacePreferences`) is the single source of surface-state truth.

D19.4 went further and named the structural delimiter directly. After the operator observed that clicking Settings *erased the workspace* (the Desktop + all open windows vanished from the DOM), D19.4 ratified:

> *"Inside the authenticated workspace, every surface is a window mounted on the Desktop. Pages survive only at the **authentication boundary** … The `isLegacyNonAtomicRoute` branch survives at the authentication boundary, **not inside it**."* — ADR-297 D19.4, decisions 1 + 6

D19.4 enacted that for Settings + Connectors (promoted to kernel surfaces). **But it never accounted for the redirect stubs**, and they are the unhealed remainder of the same seam.

### The symptom (operator-observed, 2026-06-01)

Navigating to `/context?path=…` (a redirect stub, mid-flight) produced a view that *looked* like the OS — the dock/TopBar painted — but the dock didn't work, window controls were dead, and the surface was never registered as foregrounded. The operator framed it as: *"when for whatever reason we don't stay on /desktop … the docker doesn't work, existing features on desktop intended agent-OS-like implementation essentially break but only look fine."*

This is the **same observation D19.4 acted on**, ten days later, surfacing through a different door. The `/context → /files` rename ([commit `3270d5a`](https://example)) closed *one* stub's blast radius by making the redirect target a recognized kernel slug, but the seam is structural, not per-route.

### The bimodality, in receipts

`SurfaceViewport` decides whether the OS shell engages by string-matching the URL's first segment against the kernel-slug list:

```ts
const firstSegment = pathname.split('/').filter(Boolean)[0];
const pathnameSlug = isKernelSurfaceSlug(firstSegment) ? firstSegment : null;
const isLegacyNonAtomicRoute =
  !isDesktopRoute && pathnameSlug === null && firstSegment !== undefined;
if (isLegacyNonAtomicRoute && mountSlugs.length === 0) return <>{children}</>;  // ← drops out of OS-mode
```

This makes **URL the load-bearing decider of whether the operator gets OS-mode or orphaned-browser-page-mode** — precisely the role ADR-297's axiom forbids the URL from playing. Of the authenticated-interior routes that hit this fallback today, almost all are **redirect stubs**:

| Route | Kind | Falls to `isLegacyNonAtomicRoute`? |
|---|---|---|
| `/chat` `/context` `/delegation` `/memory` `/operation` `/orchestrator` `/overview` `/system` `/team` `/workfloor` `/backend` `/integrations` | redirect stub (`'use client'`, renders `null`, `router.replace` in `useEffect`) | **YES — violates D19.4 invariant** |
| `/docs` (interior) | redirect stub → `/files` (stale "Redirecting to Context…" copy) | **YES — violates D19.4 invariant** |
| `/auth/*`, marketing, `/docs/[id]` public viewer | authentication-boundary / operator-external | YES — *correct* per D19.4 |

Every redirect stub is a client component that **mounts inside the authenticated layout → ShellCompositor → SurfaceViewport, paints one orphaned frame, then redirects.** Worse: when the operator already has windows open (`mountSlugs.length > 0`), the `&& mountSlugs.length === 0` guard is false, so the stub does *not* even take the clean fallback — it falls through to the windowed render path with `pathnameSlug === null`, so `visibleSlug` resolves to "last open window" and `foregroundSurface` never fires for the stub's true target. That is the exact half-broken state the screenshot caught: windows present, dock painted, window manager pointing at a stale surface.

The chrome is always-mounted (TopBar paints unconditionally), but window-manager engagement is gated on URL-slug recognition. **"Looks fine, breaks."**

---

## Foundational principle

> **A redirect stub is transport, not a surface. It must never render inside the OS shell.**

This is the direct corollary of ADR-297's axiom (URL is transport, not identity) and D19.4's invariant (the fallback branch lives at the authentication boundary, not inside it). A redirect stub's entire job is to forward one URL to another. It carries no substrate, mounts no panel, and has no operator-facing render. Letting it paint a client-component frame inside `(authenticated)/` is the only reason it touches `SurfaceViewport` at all — and that single frame is the bimodality seam.

---

## Decisions

### D1 — Redirect stubs move from client-render to server transport

Every authenticated-interior redirect stub converts from a `'use client'` component (`useEffect` + `router.replace`, returns `null`) to a **Next.js server-component `redirect()`**. A server `redirect()` is issued *before any layout renders* — it never enters `AuthenticatedLayout`, never reaches `ShellCompositor`, never paints an orphaned frame in `SurfaceViewport`. The operator's browser receives the redirect and re-requests the canonical route, which mounts as a window normally.

Concretely, each stub page becomes:

```ts
// web/app/(authenticated)/chat/page.tsx
import { redirect } from 'next/navigation';

// Legacy /chat → /feed (ADR-259). Pure transport per ADR-308 D1 —
// server redirect, never renders inside the OS shell.
export default function ChatRedirect({ searchParams }: { searchParams: Record<string, string | string[]> }) {
  const qs = new URLSearchParams(searchParams as Record<string, string>).toString();
  redirect(qs ? `/feed?${qs}` : '/feed');
}
```

Query-param preservation is retained (the stubs that forward `?path=` / `?tab=` / OAuth callback params keep doing so — server `redirect()` accepts the full target string). The redirect-stub *policy* in `routes.ts` is preserved; only the *mechanism* changes (client `useEffect` → server `redirect()`).

**Stubs converted** (all 12 authenticated-interior stubs): `/chat`, `/context`, `/delegation`, `/memory`, `/operation`, `/orchestrator`, `/overview`, `/system`, `/team`, `/workfloor`, `/backend`, `/docs` (the interior `→ /files` stub; the public `/docs/[id]` viewer is unaffected). `/integrations` is audited: if it's a redirect stub it converts; if it carries real content it's reclassified per D3.

### D2 — `isLegacyNonAtomicRoute` becomes genuinely auth-boundary-only

After D1, no authenticated-interior route reaches `SurfaceViewport` via the fallback branch. The branch then catches *only* what D19.4 said it should: `/auth/*`, the public `/docs/[id]` viewer, and marketing/static routes — all of which render *outside* the `(authenticated)` route group anyway and therefore outside `AuthenticatedLayout`.

This makes D19.4's stated invariant **true in code**, not just in prose. The branch is retained (it is the honest auth-boundary delimiter), but a regression guard (D4) asserts no kernel-slug-adjacent authenticated route can hit it.

### D3 — Operator-external interior content (if any) is reclassified, not fallback-rendered

If the `/integrations` audit (or any future route) surfaces a genuine authenticated-interior page that is *not* a redirect stub and *not* a kernel surface, it is resolved one of two ways — never left on the fallback branch:

- **(a)** it carries substrate → it becomes a kernel or program surface (the ADR-297 path), or
- **(b)** it is operator-external → it moves *out* of `(authenticated)/` into the public route group (the `/docs/[id]` precedent).

There is no third category. "Authenticated-interior page that renders outside the Desktop" is the bimodality D19.4 abolished; D1+D3 remove its last instances.

### D4 — Regression guard against re-introducing the seam

A test guard (modeled on `api/test_adr297_navigation_enactment.py` and `api/test_adr209_no_filename_versioning.py`) asserts:

1. **No `'use client'` + `useEffect` + `router.replace`/`router.push` redirect pattern in any `web/app/(authenticated)/*/page.tsx`** (the banned client-stub shape). Allowlist: none — every interior stub must be a server `redirect()`.
2. Every server-`redirect()` stub's target resolves to a recognized kernel slug route OR another stub that terminates at one (no redirect cycles, no dead targets — this also catches the `/docs` "Redirecting to Context…" stale-target class).
3. Optionally: every route directory under `(authenticated)/` is either (a) a kernel slug in `KERNEL_SURFACE_SLUGS`, or (b) a server-redirect stub, or (c) explicitly allowlisted as operator-external (`docs/[id]`). Anything else fails the gate — this is the structural assertion that makes D2's invariant enforceable, generalizing the slug-sync guard from commit `77d4497` and the slug/route guard the `/context` incident motivated.

### D5 — Stale stub copy purged

`/docs/page.tsx` ("Redirecting to Context…") and any other stub carrying pre-rename copy is corrected in the same commit. Server `redirect()` stubs render nothing, so the copy disappears structurally — but the docblock is updated to name ADR-308 + the live target.

---

## What this ADR does NOT do

- **Does not delete `isLegacyNonAtomicRoute`.** It is the honest auth-boundary delimiter (D19.4 decision 6). D2 narrows what reaches it to zero authenticated-interior routes; the branch stays for `/auth/*` + public content.
- **Does not change the redirect-stub *policy*** (when a stub is added, when it's removed — `routes.ts` policy preserved). Only the *mechanism* (client → server).
- **Does not promote any stub target to a new surface.** Targets already exist as kernel surfaces.
- **Does not touch the window manager, Desktop, WindowFrame, or composition resolver.** The fix is entirely in the stub-render mechanism + a guard.
- **Does not change middleware auth-gating.** Stubs stay in `PROTECTED_PREFIXES` (a server `redirect()` from an authenticated route still wants the auth check first; an unauthenticated hit to `/chat` should still bounce to login, then forward).
- **Does not address the broader "could `SurfaceViewport` stop consulting the URL entirely"** question (the maximal enactment of the axiom). That is a larger horizon; D1–D4 close the operator-felt seam with the minimal structural change. If pressure remains after this, a successor ADR can evaluate dissolving the URL-slug gate altogether.

---

## Implementation order (single commit, locked scope)

1. Convert the 12 interior stubs to server `redirect()` (D1) — delete `'use client'`, `useEffect`, `useRouter`; add `redirect()` from `next/navigation`; preserve query params.
2. Audit `/integrations`; convert or reclassify per D3.
3. Correct `/docs/page.tsx` stale copy + target (D5).
4. Add the regression guard (D4): `api/test_adr308_redirect_stubs_transport.py` (banned client-stub pattern + target-resolves-to-slug + interior-route-classification).
5. Doc cascade: ADR-297 D19.4 gains an "ADR-308 finishes this invariant" note; `routes.ts` redirect-stub policy docblock updated (mechanism is now server `redirect()`); CLAUDE.md OS-framing paragraph notes "redirect stubs are transport, never rendered in the shell."

---

## Consequences

- **The "looks fine, breaks" class is structurally eliminated.** No authenticated-interior URL can drop the operator into orphaned-mode, because no interior route renders inside the shell except real surfaces. The seam D19.4 declared closed is closed in code.
- **One rendering mode inside the authenticated app** (Desktop + windows), exactly one delimiter (the auth boundary), enforced by a guard. Singular Implementation honored at the navigation layer.
- **Faster + flicker-free redirects.** Server `redirect()` has no orphaned-frame paint, no `useEffect` round-trip — the operator never sees a stub render.
- **Cheap to extend.** Future renames add a one-line server-redirect stub that the guard validates; the bimodality door cannot be reopened by a client-stub by construction.
