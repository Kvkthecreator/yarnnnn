# ADR-451: Open-by-Format — the Surface-Owning App

**Status**: Accepted (2026-07-13, operator-ratified — "fully aligned"). The completion of the
ADR-436/438 open model the operator's pure-OS reading demanded: Files is the Finder; opening a
file whose default app **owns a surface** routes to that app, instead of rendering it flat inside
Files.
**Date**: 2026-07-13
**Dimension**: Channel (which chrome a file opens in) — one branch on the existing open contract.

**Amends**: ADR-438 (the one file-open contract gains its third arm: *surface-owning app →
navigate; has-inline-detail → on-surface; else → FileOpenModal*) · ADR-436 (the app registry gains
the "owns a surface" binding class beside in-frame renderers).
**Preserves**: ADR-436 (resolver returns an ordered list; the **"Open with" picker stays
deferred** until a second installed app claims the same format — exactly the future the operator
named) · ADR-441 (chat's artifact cards/mounts unchanged — the in-conversation preview is not the
Finder's open verb) · the inline viewers (they remain the **Quick Look analog** for passive
formats — preview-in-place is a feature, not the bug; the bug was preview standing in for open).

> **Amended (2026-07-15, the seam-contract spine):** the "chat's artifact cards/mounts
> unchanged" line above is refined. An in-conversation card is still a citation preview and
> never the open verb — but the card now consults THIS registry for its **depth and primary
> affordance**: a surface-owned format renders Quick-Look-grade with "Open in ‹app›" as the
> primary action; an unclaimed format keeps its full inline render. The Quick Look analog
> extends from Files' inline viewers into conversation previews — one registry, one gesture
> vocabulary. Mechanics on ADR-443 (amendment); rationale in
> `docs/analysis/chat-think-three-axes-discourse-2026-07-15.md` §11.

---

## D1 — A registry layer above the viewer table: the surface-owning app

`web/lib/file-types` gains `resolveSurfaceApplication(path, contentType)` — a small registry
sitting ABOVE `resolveViewerApplication` (the in-frame renderer table). A row claims a format for
an app that owns a whole surface. v1 ships one row:

- **Studio** claims `.html`/`.htm` (its artifact format) → `{surface: 'studio', param: 'file'}` —
  **except arrivals** (paths under `inbound/`): a retained observation is a record to preview, not
  an authoring canvas; arrivals keep the inline html viewer.

No claimant → `null` → the existing behavior, byte-identical.

## D2 — The open contract's branch (Files only)

The Files surface's single open path (`handleExplorerSelect_byPath` — tree click, tile click,
menu Open, recents) consults the resolver first: a surface-owning claim →
`navigateToSurface(surface, {param: path})`; otherwise the master-detail inline viewer as today.
This is the macOS gesture: double-clicking a `.pptx` opens PowerPoint; Finder never renders it
in-pane. Chat mounts and the FileOpenModal are NOT branched — an in-conversation card is a
citation preview, not an open verb (ADR-441's ruling stands).

## D3 — What is deliberately not built

The "Open with" picker (deferred until >1 claimant — ADR-436's resolver already returns an
ordered list); per-file default overrides; any DB/registry table (one FE code-seeded row, the
`STUDIO_LAYOUTS` discipline). When the next installed app claims a format, the picker decision
re-opens with a real forcing case.
