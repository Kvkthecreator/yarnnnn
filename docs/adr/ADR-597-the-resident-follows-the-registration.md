# ADR-597: The resident follows the registration — and a desk seats its own colleague

**Status**: Ratified + Implemented 2026-08-24 (the first ADR-596 follow-through; operator-directed: *"ensure we have dedicated one agent to one APP — Designer to Studio, Editor to Text, an agent to strings"*).

## Context

Two defects with one root, both operator-observed on the deployed surface:

- A Studio desk read **"Claude Sonnet"** where the member should read a colleague.
- A Strings desk read **"Designer"** where the resident is Keeper.

The root: a bound lane's resident was **persisted at creation** (`lane_meta["agent"]`) while being, by ADR-562's own words, *"a fact about the APP, not the lane."* A now-fact was stored — the exact anti-pattern ADR-460 D4 names for postures — so every registration change strands every live desk on yesterday's declaration. The app's *rename* was already derived at turn time for exactly this reason; the *slug* wasn't. Production census (2026-08-24): 71 active bound lanes across four stamp shapes, including 3 lanes bound to the deleted radar app and 2 pre-567 lanes with no stamps at all.

## D1 — The resident is derived at read time; the stamp is retired as a write

For a lane with a binding app, **both consumption points derive the resident from the app's registration**: the serve path (`GET /lanes` → the FE label chains) and the turn path (responder fallback + the engine-follows-resident comparison). Precedence: `resident_for_app(lane_meta["app"])` → `resident_for_recipe(lane_meta["derive_recipe"])` → the stored stamp (legacy rows, deleted registrations) → none.

`create_lane` **stops writing `lane_meta["agent"]`**. What creation legitimately records stays recorded: the **model** (a historical fact — what the lane ran on; ADR-460 spec §6 unchanged) and the **cast row** (a membership event — who was invited). Existing stamps become dead keys read only as last-resort fallback; a lane whose app leaves the roster degrades to the engine label — honest, exactly what those lanes are.

## D2 — One app, one dedicated colleague (injectivity, for user-facing desk apps)

ADR-467 D1 already held one direction: an app pins one colleague. This ADR adds the converse for user-facing desk apps: **a colleague serves one desk**. Identity does the work character was made for — the member's mental model stops needing "Designer, but called Editor here":

| App | Resident | Change |
|---|---|---|
| Studio | **Designer** | unchanged — the maker keeps its original desk |
| Text | **Editor** — NEW `KERNEL_POSTURES` row, `based_on: designer` | replaces `resident="designer", name="Editor"`; the rename mechanism (ADR-562 D6) stays for member nicknames, but Text no longer needs it — the character IS Editor |
| Strings | **Keeper** | unchanged (ADR-569 D6 already dedicated it) |

Editor is a **posture, not a fourth base row**, by the ADR-460 growth rule: working prose in the member's own document is PRODUCE pointed at the page — a stance, exactly the Critic/Keeper precedent.

**Named exceptions, deliberately open** (so they are not re-discovered): **IMAGES** still pins designer — its resident drives a metered generation pipeline, and re-posturing it deserves its own evidence, not a rename rider. **Docs** (`stage: internal`, ADR-592) keeps `designer`-as-"Writer" until the ADR-581 D5 app split decides its shape. Both violate injectivity today, knowingly.

## D3 — The data moves (one-time, measured first)

- **Text desks re-seat**: 30 active text-bound lanes' cast rows (`conversation_members.agent_slug`) update `designer` → `editor` — the cast drives responder selection, so without this the flip would leave existing desks answered by yesterday's colleague.
- **Radar's desk lanes archive**: 3 active lanes bound to an app deleted by ADR-592. A desk for a dead app is not a conversation anyone can continue coherently.
- The 35 pre-567 Studio lanes (no `app` stamp, `agent: designer`) are **left alone**: their stamp is correct, their labels render Designer, and back-inferring `app` buys nothing while risking a wrong guess.

## Consequences

- A registration change now propagates to every live desk at the next read — label and posture together, no cleanup SQL ever again.
- The Studio "Claude Sonnet" class of defect is structural history: only a lane with *no* derivable and *no* stored resident shows the engine, and that display is true.
- Gate: `api/test_adr597_resident_derivation.py`. The ADR-558 arc's owed "lane-cleanup SQL" is discharged by D3 and closed.
