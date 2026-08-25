# ADR-607: The steward hears the typed focus — the operator locator is superseded, not extended

> **Status**: Accepted + Implemented (2026-08-25, this commit).
> **Date**: 2026-08-25
> **Dimension**: Channel (what the steward rail knows about where the operator stands).
> **Supersedes**: ADR-398 D2 (the operator locator — the URL-scraped, `[:200]`-truncated
> opaque string). D2's *goal* ("this file" resolves; placement asks act on where the
> operator actually is) is preserved and strengthened; its *mechanism* is deleted.
> **Resolves**: the two-rails inversion named in [lane-frame.md](../architecture/lane-frame.md) §5
> and deferred by ADR-522 ("the locator is not extended") and ADR-606 §"the two rails".
> **Relates to**: ADR-522 (the focus declaration — the type this ADR adopts), ADR-606
> (one kernel rendering site per rail; the binding-authority precedent), ADR-441 D1
> (the two-renderer wire split — NOT merged by this ADR).

## 1. Context — the inversion, now resolvable on evidence

After ADR-606 the two chat rails knew the member's place asymmetrically:

- **The lane rail** carries a typed `SurfaceFocus` — app-declared, grain-scoped
  (document/page/container/block), selection-aware, rendered by one kernel site.
- **The steward rail** carries `operator_locator` — a string composed by **scraping
  URL params** for the foregrounded slug's prefix (`ChatDrawer.tsx`), truncated to
  200 chars, opaque at every hop by design.

ADR-522 §1 already diagnosed the locator's defects (apps contribute by accident;
cannot carry a grain; a mechanism that works for apps that never adopted it is a
coincidence, not a contract) but deliberately left it alone — the typed channel was
new and the steward had no observed need. Two things changed:

1. **The declaration infrastructure is now first-class and obligated** (ADR-606 D5:
   every pane-bearing app declares focus or a written silence). The steward rail
   scraping URLs beside a shell that already holds a richer, truthful declaration is
   a **dual approach** — the exact shape Singular Implementation exists to delete.
2. **ADR-522's own refusal was scoped to *extending* the locator** ("making one
   string serve both altitudes would put two contracts behind one field"). Adopting
   the TYPE is not that: the rails keep their wires and their renderers; they share
   a *vocabulary*, exactly as they already share the workspace path grammar.

## 2. D1 — The feed wire gains `focus`; the locator is deleted everywhere

`ChatRequest` (`routes/feed.py`) gains an optional typed `focus` (the ADR-522 D2
wire shape, one model shared in spirit — the steward rail declares its own Pydantic
model to keep the wires independent per ADR-441). The shell composes it from
`useCurrentFocus()` — the same declaration the lane mount reads, including the
recency fallback, so the drawer and a pane beside it tell the same story.

`operator_locator` is DELETED — the ChatDrawer URL-scrape, the `[:200]` truncation,
every pass-through hop (`feed.py` → `wake.py` → `wake_sources/addressed.py`), and
the ask-block line in `freddie_agent.py`. No compatibility shim: an old client that
still sends `locator` is ignored by Pydantic's normal unknown-field handling on the
request model, and the frame simply carries no place line — the pre-ADR-398 state,
honest and temporary for the duration of a deploy skew.

## 3. D2 — One renderer, parameterized by actor; rendered at one steward site

`build_focus_line` (the ADR-522/606 renderer) gains an `actor` parameter
(default `"The member"`; the steward passes `"The operator"`). The steward renders
the place as one block in the **addressed ask** (`_ask_for_trigger`), replacing the
locator line:

```
_The operator is writing from: {app} — {path}._
{grain line, when finer than document: viewing/selected/writing-under…}
```

- **One site per rail** (the ADR-606 D1 rule): lanes render in
  `_compose_focus_section`; the steward renders in the addressed-ask composer.
  Neither imports the other's composition machinery beyond the shared pure
  renderer.
- **Non-authoritative, transient, never persisted** — all ADR-522 refusals carry
  over verbatim. The steward's substrate reach is unchanged; focus steers
  attention, never permission.
- Addressed wakes only: reactive/scheduled wakes have no operator standing
  anywhere, and render nothing — same as today.

## 4. What this deliberately does not do

- **Does not merge the rails** — two wires, two request models, two rendering
  sites. ADR-441 D1 stands.
- **Does not give the steward the lane's binding guard** — the steward is not
  bound to an artifact; every declaration renders (there is no binding to be the
  authority). If the steward ever gains a bound mode, the ADR-606 D2 guard is the
  precedent to import.
- **Does not touch the lane rail** — byte-identical frames there.

## 5. Implementation

| # | Change | Site |
|---|---|---|
| 1 | `build_focus_line(actor=…)` | `api/services/authoring.py` |
| 2 | `ChatRequest.focus` (typed model) + locator field deleted | `api/routes/feed.py` |
| 3 | Threading: `focus` through the addressed wake context; `operator_locator` hops deleted | `api/services/wake.py`, `api/services/wake_sources/addressed.py` |
| 4 | The ask-block place lines; locator line deleted | `api/agents/freddie_agent.py` (prompt-layer: CHANGELOG + ratchets) |
| 5 | ChatDrawer composes `focusToWire(useCurrentFocus())`; the URL-scrape deleted | `web/components/shell/chrome/ChatDrawer.tsx` |
| 6 | Gate: wire→ask threading, locator absence with presence controls, actor word per rail | `api/test_adr607_steward_hears_focus.py` |
| 7 | Canon sync: lane-frame.md §5 (inversion resolved), GLOSSARY focus row (steward sibling), ADR-LEDGER | `docs/` |
