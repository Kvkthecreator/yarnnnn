# ADR-592 — An app declares how far along it is

**Status**: Accepted
**Date**: 2026-08-21
**Supersedes**: ADR-486 (AI Radar — withdrawn), ADR-574 D2 (the Docs pause — completed)
**Amends**: ADR-488 §5 (the Images unveil bar reads as a stage)

---

## Context

Two apps needed to stop being products: **Radar** (ADR-486) and **Docs**
(ADR-518). The second had already been decided — ADR-574 D2 declared Docs
**paused** on 2026-08-17 — and four days later the operator opened
`yarnnn.com/docs` and found the app fully alive: a working surface, a Dock
icon, six documents listed.

That is the finding this ADR is built on. **The pause was correct and it did
not take effect**, because "hide an app" was not one act. It was six, spelled
by hand in two languages:

| # | Spelling | File |
|---|---|---|
| 1 | `launcher_tier: "search-only"` | `services/kernel_surfaces.py` |
| 2 | `default_pinned: False` | `services/kernel_surfaces.py` |
| 3 | remove from `DEFAULT_KEPT_SURFACES` | `web/lib/shell/surface-preferences.ts` |
| 4 | add a Dock reseed generation | `web/lib/shell/surface-preferences.ts` |
| 5 | the type→app association | `web/lib/file-types/index.ts` |
| 6 | the scheduler lane (apps with a clock) | `api/jobs/unified_scheduler.py` |

ADR-488 (Images) performed 1–4. ADR-574 (Docs) performed 1–4. Neither
performed 5, and neither had a 6 to perform. Both half-worked, and the halves
that were missed were invisible — which is the defining property of this
failure class: **a hand-kept list beside a derived truth drifts, and the drift
reads as success.**

Two specific mechanisms made the Docs pause a no-op on a real desk:

- **The Dock reseed only fires on byte-equality.** `maybeReseedDock` rewrites a
  stored Dock only when it exactly matches the previous default
  (`current.every((s, i) => s === gen.previous[i])`). Any operator who ever
  reordered or unpinned an icon keeps the hidden app's icon **permanently**.
- **`search-only` hides a tile at rest, nothing else.** The route still
  rendered, the launcher's flat search still matched on `summary`, and
  double-clicking any `document` artifact still opened the app.

Radar added a consequence Docs did not have. Its sweeps drained **every
scheduler tick**, and the code says what that costs: *"a sweep's derive is
metered judgment spend."* At the time of this decision three hubs were live
across two workspaces — `ai-frontier`, `desk-e2e`, `fundraising/deck-new-test`
— with a sweep as recent as that morning, 01:28. Two of those three are test
fixtures. **The system was billing production money for an app on behalf of an
end-to-end test.**

## Decision

### D1 — An app declares its exposure as one field, and the rest is derived

Kernel surface rows carry **`stage`**, one of four values, resolved by
`services/app_stage.py`:

| Stage | Roster | Launcher | Dock | Route | Type→app |
|---|---|---|---|---|---|
| `internal` | absent | — | — | redirect stub | falls back |
| `search-only` | served | flat search only | no | live | routes |
| `beta` | served | tile | no | live | routes |
| `primary` | served | tile | yes | live | routes |

`launcher_tier` and `default_pinned` are **derived** from the stage, not
declared beside it. The pair that ADR-297's coherence gate protects
(`default_pinned` == the primary tier, as a set) is now satisfied *by
construction*; that gate stays, guarding the derivation rather than two
hand-kept fields.

A row that declares no stage resolves to the stage its existing fields already
imply (`_implied_stage`), so **every pre-ADR-592 row behaves exactly as it
did**. The seam ships inert — the ADR-375 D4 rule.

### D2 — `internal` leaves the served roster, and that is the whole mechanism

The nav is 100% backend-driven (ADR-297). So dropping a row at
`kernel_surface_entries()` — the same chokepoint ADR-375 §6 #4 already uses for
the steward — removes the Dock icon, the launcher tile, and the flat-search hit
in one act, with **zero frontend change**.

Crucially, it also holds for **an operator whose Dock was curated**: a
persisted slug that names no served surface cannot render an icon. That is the
specific failure the byte-equality reseed could never reach, and the reason
`stage` is enforced at the roster rather than at the defaults.

A `hidden: true` flag was rejected as the spelling. Such a row still ships its
title and summary to every client, is still matched by flat search, and still
occupies a slug the window manager will foreground. Removing the row is the
only spelling under which every consumer agrees without each consumer having to
remember.

**The obligation `internal` carries**: `middleware.ts` derives its protected
route set from the roster, so a slug that leaves the roster **leaves the auth
gate with it**. An internal app's route must become a redirect stub in the same
change, and the stub path must be listed in the middleware's hand-kept set.
Otherwise the route serves 200 to logged-out visitors — the exact defect
repaired on 2026-08-20, when eight surfaces were found ungated for precisely
this reason.

### D3 — Radar is deleted, not staged

Radar is removed entirely: `services/radar.py`, `routes/radar.py`,
`web/components/radar/`, the surface, the registry row, the app registration,
the API namespace, and the scheduler lane.

**Full deletion rather than `stage: internal`, because a standing sweep
spends.** An app nobody can reach must not keep metering judgment against an
operator's balance, and dormant spend machinery is exactly the ambiguity a
future session would have to re-derive. Hiding the door while the meter runs is
the worst of both.

Reopening Radar is a new decision recorded against this ADR, not a tier flip.

### D4 — Docs is hidden in full, and its implementation stays

Docs takes `stage: internal`. Its code is untouched — it is Studio
parameterized (`StudioSurface app={DOCS_APP}`), and the `document` layout, the
`designer` resident and the "Writer" name all still resolve. Only its exposure
is gone. Reopening is a stage flip plus restoring its route and registry row.

`/docs` redirects to **Text**, per ADR-574 D1's prose premise. A `document`
artifact, no longer claimed by `APP_SURFACES.docs`, falls back to Studio.

**ADR-574 D3 recorded a trap here and it does not fire.** D3 warned that
removing `APP_SURFACES.docs` while `document` still resolves to app `docs`
would render a flow document as paged slides. It does not, because
`resolvedMode` is read from the **layout vocabulary**
(`layouts.find(l => l.slug === template)?.mode`), not from the app, and the
`document` layout still declares `mode: "flow"`. The app changed; the mode did
not. D3's requirement — that the surface and the association move *together* —
is honoured: this change moves both.

### D5 — The briefs Radar authored remain

The 21 brief files under `operation/ai-frontier/briefs/`, and their revision
history, stay as ordinary attributed files. Deleting real substrate to tidy an
author census trades the attribution invariant for its appearance — the ruling
already made on 2026-08-20 for the eight free-text `authored_by` rows.

Consequently `system:radar` **keeps its display name** in
`services/principal_display.py` and `web/lib/workspace/attribution.ts`. History
must keep rendering a name, not a raw string. An agent is not an app: the
`scout` / Researcher row stays in `KERNEL_AGENTS`.

Removing the hub declarations (`_radar.yaml`) is the operator's act, handled
separately. Either that or D3 stops the spend; both is belt-and-braces.

## Consequences

- Hiding an app is one field. Developing one internally is the default:
  a new app starts `internal` and climbs.
- `APP_STAGE_{SLUG}` overrides the declared stage per deploy — but it must be
  set on **API + Unified Scheduler** (CLAUDE.md §5). The API alone hides the
  door while the lane keeps spending, which is this ADR's founding defect.
  An unrecognized value is ignored rather than guessed: a typo'd stage silently
  un-hiding an app is the same incorrect-success class.
- `kernel_surface_slugs()` returns the **exposed** set. Callers wanting the
  declared rows read `KERNEL_SURFACES`.
- Gates assert derived counts, never literals — a pinned count reads the next
  hidden app as a violation (the ADR-584 lesson).

## Gate

`api/test_adr592_app_stage.py` — the stage ladder, the derivation's identity on
untouched rows, the roster filter, the stub-and-middleware pairing, and the
absence of every deleted Radar reference.

Pre-existing red at the time of writing (NOT introduced here, measured at
`b0d03a6`): `test_adr297_phase1` 186/1 and
`test_adr338_surface_registry_parity` 12/3, all four failures naming
`autonomy`.
