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

**Amended 2026-08-24 (audit)**: a being serving NO desk is promoted only if it is `offered`. The original clause promoted every unhoused being, which failed *open* — deleting an app's `register_app` line would have leaked its orphaned resident onto the pane while deleting the surface row correctly withheld it. A colleague (`offered`) legitimately has no desk; a non-offered being with no desk is unreachable everywhere and is withheld.

The cliff is untouched: promotion is presentation, in the same family as `offered`. It answers *is this being's work in front of a member today*, never *what may this being do*.

## D4 — Icons follow the craft

- **Editor** takes `pen-tool` — the operator's choice, and the glyph that reads as authoring.
- **Designer** takes `palette` — generation and composition, distinct from authoring at a glance.
- The **/agents surface** leaves `users-round` for `bot`.

The `users-round` note in `surface-icons.tsx` records why it was chosen in 2026-07-20: *"a pair of ROUNDED people = the colleagues you've hired and named"*, deliberately distinct from `users` (humans). **That reasoning expired with ADR-596**: agents are BEINGS, the roster is residents rather than hires, and a people-glyph now names the wrong noun — the same fault the note itself records `users` being replaced for. `bot` is object-like and sits in the concrete family (Chat bubble · Files folder · Slides deck).

The key is changed in BOTH registries in one commit (`kernel_surfaces.py` declares, `surface-icons.tsx` maps) — the recorded lesson that an `icon_key` is shared across registries and a one-sided edit renders a blank.

## D5 — A bound lane names its resident, and speaks plainly

**The defect this closes was operator-observed on the deployed surface**: a Slides lane's composer read *"Message Claude Sonnet 4.6…"* while Editor was answering. Both authoring surfaces resolved the speaker through two lookups that are structurally empty — `apps[].name` (the ADR-562 D6 RENAME override, `''` for slides and text because neither renames its resident) and `agents` (the HIRE roster, `[]` since ADR-599 because nobody is `offered`). Both missed, and the chain fell through to the engine label.

**A resident was never going to be on the hire roster** — that is ADR-598's whole ruling — so this was not a wiring slip but the two rosters answering different questions. Both surfaces now consult `beings` (served from the same registry the prompt reads) before falling back, and the fallback stays: an engine label is the honest answer for a lane with no resident.

**Copy is plain language.** Blurbs are one short line in a member's own words (*"Writes with you — decks and documents."*), the pane's sections read "In an app" / "To work with", and **the ADR number is gone from the empty state** — an ADR is an internal address, and a member reading "ADR-599" learns nothing they can act on. Gate-asserted: no `ADR-` may appear in rendered surface copy, and a blurb is capped at 60 characters.

## D6 — The per-being page

`?agents.agent={slug}` opens one being: who they are, where they work, what runs them, and whether they can be changed. Both halves of the plumbing were already sanctioned and needed no new decision — `SURFACE_PARAM_KEYS.agents = ['agent']` declares the depth, and `SURFACE_EPHEMERAL_PARAM_KEYS` already marks it not-remembered, because (in the compositor's own words) *"a roster's POINT is the list; a profile is a momentary look"*. Depth moves via `setSurfaceParams`, never a pathname flip — the shell's foreground effects branch on the `/desktop` baseline.

**A kernel being's page is read-only and says so.** Enforcement stays server-side at `assert_editable` (ADR-601 D3); this surface *states* the fact and must never be the only thing that does. A member-authored being's page will read "Yours — you can change this one" from the same field, with no new branch.

The engine is served on the payload (`model`) so the page can say what runs a being rather than implying it — no new disclosure, since `model_names` is already public on the lane envelope.

## D7 — A bound lane belongs to an app, stamped or not

**Operator-observed after D5 shipped**: a live Slides deck still read *"Claude Sonnet 4.6 is working…"*. D5 fixed the lookup; this is the layer beneath it.

`_lane_agent` derived the app from `lane_meta["app"]` — the ADR-567 D4 stamp. Every lane created **before** ADR-567 has no such stamp (~35 of them, which ADR-597 D3 deliberately left alone rather than back-inferring), so the precedence skipped to the legacy `agent` stamp and, absent that, returned `None`. The FE then correctly rendered the engine label. Correct by the letter of the precedence, wrong in the room.

**A bound lane belongs to an app whether or not anyone stamped it.** `app_for_lane(lane_meta)` reads the stamp when present and otherwise asks the artifact: `.html` is Slides' currency, `.md` is Text's. Path-shaped rather than content-shaped, deliberately — reading artifact CONTENT here would make a hot pure function do IO for every lane in a list, and the two apps that have residents are unambiguous by extension. Anything else returns `""` and the precedence continues exactly as before, so an unrecognised artifact stays honest rather than guessed.

Fixed at **both** layers, because they fail independently:

- **API** — `app_for_lane` closes the gap for every consumer (the turn, attribution, the lane list).
- **FE** — each authoring surface resolves the resident from **its own app registration** first, falling back to the lane's derived agent. A surface cannot be wrong about which app it is; that is a stronger fact than any stamp on a row.

The precedence is otherwise untouched and gate-asserted: an explicit stamp still outranks the artifact.

## Consequences

- One voice for document work: a member asking "who is responsible for my writing?" gets one answer across decks and documents.
- Designer survives with a coherent remit rather than as a legacy row, and disappears from the pane until IMAGES is unveiled — at which point it returns without an edit.
- The `designer` slug stays live, so ~65 cast rows and both planners keep resolving. Retiring the slug outright would need a measured migration; **named here, deliberately not performed** (the live count is unverified from this environment).
- Gates: `test_agent_registry.py` extended (exposure derived not declared; the roster withholds an unexposed being; icons distinct); `test_adr597` re-anchored to `slides → editor`. Every new check falsified.
