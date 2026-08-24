# ADR-602: Editor takes the authoring desks — and a being follows its app's exposure

**Status**: Ratified + Implemented 2026-08-24 (operator ruling on the ADR-601 many-to-one capability: *"i still want to push for editor to handle both slides and text apps … wouldn't that mean we no longer need Designer?"* — answered with the IMAGES carve-out the operator then confirmed).

**Builds on**: ADR-601 D1 (many-to-one), ADR-601 D2 (provenance), ADR-600 (one register). **Amends** ADR-599 D4's `slides → designer` pairing.

## Context

ADR-601 established that capability lives at the APP (measured: the job overlay is 86.7% of a Slides frame against the character's 2.4%), so a being's prompt weight is constant in the number of desks it serves. Many-to-one became free, and the operator's standing question — one voice for document work — became answerable at zero cost.

The remaining question was whether Designer survives at all. It does, and the reason is a real distinction rather than a legacy accommodation.

## D1 — Editor takes Slides and Text

`register_app("slides", resident="editor")`. Editor now speaks for both authoring desks; its blurb and posture widen to name both crafts (decks and documents) without claiming either app's grammar — that stays in the job overlay, selected by `app`, untouched.

**No data move, and the reason is structural**: ADR-597 D1 made the resident DERIVED at read time from the app registration. Re-registering `slides` re-points every Slides lane — live and historical — at serve and at turn, in the same commit. This is precisely the property that ADR-597 was written to establish, collecting its first real dividend.

**Cast rows are the exception, and they are NOT touched here.** `conversation_cast.agent_slug` persists the slug (a membership event, ADR-597 D3's reasoning), and ~65 rows carry `designer`. Those rows keep resolving because `designer` remains a live being (D2) — so there is no orphaning, and no migration is required by this ADR. A future retirement of the slug would need one; that is named, not performed.

## D2 — Designer keeps IMAGES

Designer is **not** retired. IMAGES is a metered generation pipeline, not an authoring desk: folding it under Editor would put a prose voice in front of image generation and re-merge the distinction ADR-597 D2 drew for a reason.

The carve-out is therefore substantive, not residual:

| being | desks | craft |
|---|---|---|
| **Editor** | slides · text | authoring — decks and documents |
| **Designer** | images | generation — the metered pipeline |
| **Keeper** | strings | maintenance — a designated file kept true |

The two planner lookups (`decompose.py`, `studio_arrangement_plan.py`) both resolve `designer` and are correct **for different reasons after this ADR**: IMAGES' layer planner is Designer's own desk; Slides' arrangement planner is machinery that happens to plan layout. Both are gate-asserted so a later retirement of `designer` cannot silently break either.

## D3 — A being follows its app's promotion

IMAGES is `launcher_tier: search-only` (ADR-488 — off the default Dock, reachable by search but not in the product's front door). Designer's only desk is therefore not promoted, so **Designer is withheld from the /agents pane** until IMAGES is.

**The predicate is `launcher_tier_for(...) == "primary"`, deliberately NOT `is_exposed`.** Those answer different questions and the difference is load-bearing here: `is_exposed` asks *does this surface reach the served roster* — true even for `search-only`, which is reachable-but-unpromoted — while the pane asks *would a member meet this being in the normal course of using the product*. Using the exposure predicate would have listed Designer, which is the outcome this decision exists to prevent.

`is_promoted(slug)` is **derived, never a column on the being**: the surface registry already declares the stage (ADR-592), and a second copy on the row is the ADR-562 second-home failure — it would drift the moment IMAGES is promoted and nobody remembered to flip the being. Deriving it means **promoting the app promotes its voice, in one edit** with no gate to remember.

Filtered server-side, in `_beings_payload`: the pane asks "who works here", and a being the member cannot reach is not an answer to that question.

The cliff is untouched: promotion is presentation, in the same family as `offered`. It answers *is this being's work in front of a member today*, never *what may this being do*.

## D4 — Icons follow the craft

- **Editor** takes `pen-tool` — the operator's choice, and the glyph that reads as authoring.
- **Designer** takes `palette` — generation and composition, distinct from authoring at a glance.
- The **/agents surface** leaves `users-round` for `bot`.

The `users-round` note in `surface-icons.tsx` records why it was chosen in 2026-07-20: *"a pair of ROUNDED people = the colleagues you've hired and named"*, deliberately distinct from `users` (humans). **That reasoning expired with ADR-596**: agents are BEINGS, the roster is residents rather than hires, and a people-glyph now names the wrong noun — the same fault the note itself records `users` being replaced for. `bot` is object-like and sits in the concrete family (Chat bubble · Files folder · Slides deck).

The key is changed in BOTH registries in one commit (`kernel_surfaces.py` declares, `surface-icons.tsx` maps) — the recorded lesson that an `icon_key` is shared across registries and a one-sided edit renders a blank.

## Consequences

- One voice for document work: a member asking "who is responsible for my writing?" gets one answer across decks and documents.
- Designer survives with a coherent remit rather than as a legacy row, and disappears from the pane until IMAGES is unveiled — at which point it returns without an edit.
- The `designer` slug stays live, so ~65 cast rows and both planners keep resolving. Retiring the slug outright would need a measured migration; **named here, deliberately not performed** (the live count is unverified from this environment).
- Gates: `test_agent_registry.py` extended (exposure derived not declared; the roster withholds an unexposed being; icons distinct); `test_adr597` re-anchored to `slides → editor`. Every new check falsified.
