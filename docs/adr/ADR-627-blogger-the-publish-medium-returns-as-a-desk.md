# ADR-627: Blogger — the publish medium returns as a desk

**Status**: Ratified 2026-09-01 (operator direction: scaffold the Blogger
app + agent pairing named as "a separate blogger-app arc" when ADR-599 D5
deleted Docs and the `web` medium). Implemented same day.

**Builds on** ADR-599 D5 (the `web` type deleted with its future named) ·
ADR-505 D2 (article + page merged into one band-first outward type) ·
ADR-562 (app-owned config through `register_app`) · ADR-596→601 (an agent is
a being; capability lives at the app; many-to-one is free) · ADR-592 (an app
declares its stage) · ADR-603 (a standing declaration names an APP).

**Out of scope, deliberately**: publishing outward — pushing a post to an
external platform. That is a third disposition of platform reach and gets its
own ADR (ADR-628), ratified beside this one, built later. Blogger v1 composes
posts as workspace artifacts; nothing leaves the workspace without the member
carrying it.

## Context

ADR-505 D2 merged `article` and `page` into one outward type (`web`): "HTML
for someone outside the workspace," band-first, never object-first — the
Medium/Substack/Ghost reference class. ADR-599 D5 then deleted it (2 articles
+ 1 page at the cut, all `test-*`; zero real demand at that time), and named
its future in the deletion commit itself: *"its future is a named separate
blogger-app arc."* The operator has now named that arc.

What exists today:

- **The authoring kernel is parameterized.** Studio serves N apps
  (`StudioSurface app={…}`, `register_layouts`, `blocks_for_app`); only 3 of
  ~20 block kinds are slides-scoped, so the whole shared vocabulary is
  available to a new app for the cost of a registration.
- **The band family is proven, deleted code** — `prose-header` · `prose` ·
  `hero` · `content` · `feature-grid` · `testimonial` · `cta`, with kernel
  rendering that survived the deletion (legacy artifacts still render).
- **The standing machinery is complete.** A declaration names an APP and the
  executor derives (ADR-603 D2); runs are pool-bounded (ADR-618). Blogger has
  been the named "second kind" of standing declaration since ADR-603 shipped
  with strings as its only tenant.
- **A being costs a row.** Capability lives at the app (ADR-601 D1), so the
  question "does Blogger need its own being?" is a voice question, not a
  capability one.

## Decisions

### D1 — The `blogger` app owns the publish medium, as the `post` type

A new app module (`api/services/apps/blogger.py`, the Docs shape) registers
one document type, **`post`**: band-first, `mode: paged`, the ADR-505 D2
outward type resurrected under the app that owns its future. The band
arrangement family returns with it, verbatim in structure — the merge decision
(one type; a blog post opens with `prose-header`, a landing page with `hero`;
the difference is which bands you stack) was ratified in ADR-505 and is not
reopened here.

The slug is **`post`**, not `web`: the member-facing medium is the post, and
`web` was already retired vocabulary when ADR-505 inherited it. The retired
slugs re-alias: `article` / `page` / `web` → `post` in
`RETIRED_LAYOUT_SLUGS`, so the legacy outward artifacts resolve again — they
open in Blogger, render with the band skin, and are never rewritten (the
ADR-481 D5 discipline: legacy renders, never migrates).

### D2 — `blogger` is a being, the desk's voice

A fourth kernel being: identity ⊕ character ⊕ engine, `offered: False` (met
at its desk, never invited — the ADR-600 D2 posture every resident holds).
Its craft is distinct from Editor's, which is why it is not a second desk on
Editor: Editor's contract is *the member's document in the member's voice*
(preserve their words; internal register); Blogger's is *prose written to be
read by someone outside the workspace* — headline, standfirst, a reader who
owes you nothing. Those postures conflict in one character. The operator
named a pairing; the pairing survives contact with the registry's own logic.

No authority, no clock, no mandate — the ADR-460 D3.a cliff holds untouched.
The being's home (`agents/blogger/`, ADR-624) needs no seeding: memory is
written lazily, grants are absent until granted.

### D3 — Stage `beta` **(AMENDED same day by ADR-629: stage `primary` + `badge: "beta"` — full placement, the tag carried as presentation)**

Reachable (launcher tile, auth-gated via the roster-derived
`SURFACE_PREFIXES`), not on the default Dock. `beta` rather than `internal`
because the app is usable at ship (the authoring kernel is the same one
Slides runs daily) and the operator needs to drive it; rather than `primary`
because it has not earned a Dock icon (the ADR-488 lesson: unveil bar is
polish parity, not works-at-all). Being at `beta` also promotes Blogger onto
the /agents pane by derivation (`is_promoted`), which is correct: a member
who can open the desk should be able to read who works there.

No middleware hand-listing needed — that obligation is `internal`-only.

### D4 — The standing leg is assembly, not architecture

A standing declaration naming `app: blogger` works the day this ships:
`resident_for_declaration("blogger")` derives the being through the same
`standing_executor_for_app` door every app uses. Nothing new is built; the
first real blogger declaration is the click-pass, and it discharges the
"second kind of standing declaration" item ADR-603 left owed.

### D5 — Publishing outward is ADR-628's

Blogger v1's output is workspace artifacts. The publish act — a post leaving
the workspace for an external platform — is a **third disposition of platform
reach** (neither INTAKE nor TURN REACH), with its own credential, consent,
and autonomy questions. ADR-628 defines it; nothing in this ADR depends on
it, and nothing in Blogger v1 may reach outward.

## Consequences

- The CLAUDE.md Agents-are-BEINGS row gains Blogger → post; GLOSSARY
  unchanged (no new vocabulary — "post" is a document type, not a concept).
- `test_adr562`'s pinned app set widens to five — the line whose comment says
  a new app is an ADR decision; this is that decision.
- The 11 legacy flow-family (`document`) artifacts are untouched — `document`
  stays unregistered (capture prose belongs to Text, ADR-599). Only the
  3 outward legacy artifacts re-resolve, to `post`.

## Gate

`api/test_adr627_blogger_pairing.py` — the being resolves with the row-key
whitelist; the app registers with a resolvable resident; `post` resolves with
its arrangement family; the retired outward slugs alias to `post`; the
surface row declares `stage: beta`; the standing executor derives.
