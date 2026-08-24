# ADR-599: The roster empties, and Studio becomes Slides

**Status**: Ratified + Implemented 2026-08-24 (operator ruling, correcting the ADR-598 direction: *"delete the roster of agents that do not have a dedicated APP linked to them … the agents surface and roster, for the time being, will be potentially empty — this is OK, until we stabilize the roster and agents and apps scaffolding. I want the full evolve of Studio to become Slides."*).

## Context

ADR-596 established the being/grant/declaration/gate frame; ADR-597 dedicated residents per app; ADR-598 split residents from colleagues. The operator's ruling completes the collapse: **for now, the only agents are app residents.** The free-floating colleague roster (Thinker · Researcher · Designer-as-colleague · Critic) and the member-agent machinery (Lisa, "Make one", skills) predate the one-agent-one-app discipline and are deleted — not staged, not hidden — until the scaffolding stabilizes. Articles/blogging is explicitly future scope (a blogger app + agent pairing, its own arc); Studio sheds everything that is not slides.

## D1 — The colleague roster is deleted

`KERNEL_AGENTS` and `KERNEL_POSTURES` empty (the dicts and their gates remain — the registers are structural; their population is zero). The engine-only chat surface (ADR-558) is untouched: a conversation is created with an engine, and now there is simply nobody to invite to the cast. Deleted rows: `sonnet`/Thinker, `scout`/Researcher, `critic`/Critic, and `designer`-as-colleague — **`designer` the row survives by re-homing to `APP_RESIDENTS` as Slides' resident** (the slug is data-compat: ~65 live cast rows and lane stamps carry it; the display name "Designer" is the slides craft name).

Historical transcripts whose turns were answered by deleted slugs render the slug as the fallback label — degraded, accepted, and confined to the operator's own experiments; attribution substrate (`principal_display`) never read the registry and is unaffected.

## D2 — The member-agent machinery is deleted

Creation ("Make one" / `POST /lane-agents`), discovery (`find_member_agents`), skills (ADR-464's `find_agent_skills` + prompt section), the manifest parser, and the hiring cards. Lisa's manifest is archived in the substrate (the file lifecycle act — never a row deletion; ADR-209 history intact). The ADR-598 D3 reasoning ("identity-minting is safe") remains true and is not the point: the operator's ruling is that member agents return, if they return, **as pairings with apps** — rebuilt against the stabilized scaffold, not carried as dormant machinery. Singular-implementation discipline: delete now, reintroduce cleanly.

The `/agents` surface stays in the shell with an honest empty state naming what it is waiting for. `DERIVE_RECIPES` loses its one colleague pin (`design-system`'s `resident: scout`) — absent-resident is already legal for a recipe.

## D3 — What remains is exactly the ADR-597 injectivity, and nothing else

| App | Resident | Register |
|---|---|---|
| **Slides** (né Studio) | Designer (`designer`) | `APP_RESIDENTS` |
| **Text** | Editor (`editor`) | `APP_RESIDENTS` |
| **Strings** | Keeper (`keeper`) | `APP_RESIDENTS` |
| IMAGES | shares `designer` | named exception (metered pipeline; own resident when evidence arrives) |

Residents drop `based_on` — the base operations they pointed at no longer exist, and a resident is self-contained (own posture, own engine). `RESIDENT_ROW_KEYS` = the posture shape minus `based_on`; the D3.a cliff unchanged.

## D4 — Studio becomes Slides, in full (user-facing)

- Kernel surface row: `slug: slides`, title **Slides**, route `/slides`; `icon_key` **unchanged** (`palette` — an icon_key is shared across three registries; a swap is a scope change, not a rename).
- `/studio` becomes an ADR-308 redirect stub → `/slides`, **hand-listed in middleware** (a slug leaving the roster leaves the auth gate — the ADR-592 obligation).
- `register_app("slides", resident="designer")`; the FE surface passes `app: 'slides'` at lane creation. **No lane data move**: measured 2026-08-24, zero live lanes carry `app='studio'` (Studio's bound lanes all predate ADR-567's app stamp; their `agent: designer` stamps keep resolving through the one namespace).
- Member Docks: stored surface preferences naming `studio` are data-moved to `slides`.

## D5 — The non-slides media are deleted

- The **`web` layout** leaves the vocabulary (creation, galleries, type registry). The one live `page` artifact keeps rendering — the kernel CSS that draws existing artifacts is not the type registry that offers new ones.
- The **Docs app is deleted in full** (module, registration, `DOCS_LAYOUTS`) — it was `stage: internal` since ADR-592 with its future explicitly deferred; the operator has now named that future (a blogger app + agent pairing) as out of scope, which makes Docs dormant machinery with no successor claim. The 11 live flow-family artifacts (`document` 8 · `article` 2 · `page` 1) remain as files — substrate is never deleted by an app's retirement — reachable through Files/export; they lose their editing surface. `/docs` continues to redirect (→ `/text`).

## D6 — What is deliberately NOT renamed (kernel internals)

`services/authoring.py` (the authoring kernel wearing the first app's name — ADR-562 §4's documented state), `routes/studio.py`, the `/api/studio/*` namespace, `StudioSurface.tsx` and its component tree, and the `STUDIO_*` kernel tables. These are kernel/internal names with no member exposure; renaming them is mechanical churn across dozens of files and every gate, riding no behavior. They follow in a dedicated rename pass if the spelling starts inviting drift (the pane-housing lesson) — recorded here so the next session knows the split was deliberate, not lazy.

## Consequences

- The agent architecture is now exactly: **app residents + the steward's dissolving stack + (future) declaration-named executors.** Every agent has a desk; nothing free-floats. The ADR-596 dissolution phases proceed against this simpler base.
- ADR-598 D4's craft-naming holds (Designer/Editor/Keeper); D5 is executed by this ADR; ADR-460's roster pedagogy (chooser, hiring, member agents) is **superseded at the surface** while its cliff (D3.a) survives in every register.
- Gate: `test_adr599_roster_empty_slides.py`; major re-anchors in `test_agent_registry` (the roster checks invert), `test_adr592_app_stage`, and the studio-slug gates.
