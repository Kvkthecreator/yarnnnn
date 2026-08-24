# ADR-598: A resident is not a colleague — the roster answers "who do you want to work with?"

**Status**: Ratified + Implemented 2026-08-24 (operator-observed on the deployed /agents surface within hours of ADR-597: Editor and Keeper appeared under "Who you can hire" — an app's furniture offered as colleagues).

## Context

ADR-597 minted Editor and Keeper as `KERNEL_POSTURES` rows, and the roster — which serves every kernel character — immediately listed them for hire. The operator's read was correct and precise: *"have clear separation between APP-mapped agents [and colleagues] … apps like text, studio [are] more human substrate-processing oriented, and their agents just [the app's own voice]."*

The blur is conceptual, not cosmetic. Two different questions were being answered by one dict:

- **"Who do you want to work with?"** — the roster's question. A colleague: hireable, nameable, cross-app, a character a member builds their own agent on.
- **"Who speaks for this desk?"** — an app's question. A resident: app-owned identity, named for the desk's craft, reached only through the app's bound lanes, existing because its app exists.

ADR-596's frame decides it: both are *beings* (no species), but a resident is an **app-declared binding fact wearing a face**, not a member-facing relationship. Putting it on the hiring path was a category error in the ADR-597 build — this ADR is the correction, same-day.

## D1 — Three registers, one namespace

`agents_registry` now holds `KERNEL_AGENTS` (base operations) + `KERNEL_POSTURES` (colleague stances — Critic) + **`APP_RESIDENTS`** (desk voices — Editor, Keeper). Resolution stays ONE namespace (`_kernel_character`): a lane pinning `editor` resolves exactly like one pinning `critic`, so no live lane, cast row, or attribution changes. Keyspaces disjoint, gate-asserted. The D3.a cliff holds on the third register identically (same row shape, same banned-vocabulary checks, same "no key outside the whitelist").

Slugs are data-compat: `editor`/`keeper` are on live cast rows; display names may move, slugs must not.

## D2 — The roster serves colleagues only; a manifest bases on colleagues only

`list_agents` never serves a resident. `parse_agent_manifest` refuses `based_on: <resident>` — the desk's voice is not a character to wear, and allowing it would put the furniture back on the hiring path through the side door. ADR-460 D1 ("no un-hireable rows rendered on the roster") is not violated but *honored*: a resident is never ON the roster because it was never a colleague.

## D3 — Member creation STAYS (the "Make one" question, answered)

The operator asked what creating a new agent *means*, and whether to prevent or phase it out. Answered from ADR-596: creating a member agent is **minting identity over a kernel capability** — a name, a tone, a color, an avatar, optionally an engine, over a colleague's character. It grants nothing, gates nothing, routes nothing (strict-key manifest, refused-not-ignored). That is exactly the layer ADR-596 says members own, so it stays. What the register split prevents is the thing worth preventing: identity minting can never reach capability, and now can't wear an app's voice either. (Production today: one member agent, `lisa`, strict-parse clean.)

## D4 — The naming register for residents (recommendation recorded)

The operator floated mechanical names ("Text-Bot", "Slides-Bot") to make the non-colleague nature legible. **Recommendation: keep craft names (Editor, Keeper) and let the register carry the semantics.** The resident *converses* in the desk's lane — "I'm Editor, what do you want to do with the doc?" is better conversation than "I'm Text-Bot" — and the separation is now structural (off the roster, un-basable), so the name no longer has to do taxonomy work. If the operator rules for the mechanical register anyway, it is a one-line `name:` change per row; slugs stay.

## D5 — PROPOSED, not executed: Studio → Slides, and the flow type → Article

The operator's directional ask, converging with ADR-581 D5's contemplated Deck/Articles split. **Measured before proposing** (live artifacts, 2026-08-24): `deck` 8 · `document` 8 · `article` 2 · `page` 1 · `image` 2 — the flow-medium family has 11 live artifacts, so **retraction would strand real work; renaming the type to Article is the honest move** (two artifacts already carry that template name).

Executing "Slides, in full" is its own arc, not a rider: the rename touches the `/studio` URL + redirect stub + middleware hand-listing (the ADR-592 obligation), `register_app("studio")` + `lane_meta.app='studio'` on live rows, `routes/studio.py`, `StudioSurface`, curated Docks, and the `services/authoring.py` naming (which ADR-562 §4 already flags as "the authoring kernel wearing the name of the app that arrived first" — the rename makes that file's name MORE wrong, and the pane-housing arc's lesson applies: a module named for one app invites a second spelling). Needs: an ADR of its own, a data move for lane stamps, and the operator's go on the outward-facing URL change.

## Consequences

- /agents reads: Lisa (yours) + Thinker · Researcher · Designer · Critic. Editor and Keeper are met where they live — their desks.
- The purity discipline gains its third structural guard: capability uniform (ADR-467), authority unrepresentable (ADR-460 D3.a), and now **hireability = colleagues only**.
- Gates: extended `test_agent_registry.py` (cliff + disjointness + roster exclusion + manifest refusal, falsified both ways); re-anchored `test_adr569` / `test_adr571` / `test_adr562` / `test_adr597` to the register move.
