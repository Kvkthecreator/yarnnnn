# The lane frame — what a pane's colleague knows, and how it knows it

> **Status**: living canon. Established by ADR-411 (the conventions projection),
> ADR-440 D3 (the binding), ADR-522 (the focus declaration), ADR-495 D3 (the cast),
> ADR-562 (app-owned configuration), ADR-606 (focus at one kernel site; the job
> overlay declared at the app). This document is the composition reference for the
> **Altitude-2** prompt frame — the steward's (Altitude-1) composition canon is
> [agent-composition.md](agent-composition.md) and does not overlap.
>
> **Code home**: `api/services/lane_runner.py::build_lane_conventions` is the ONE
> composition site. `api/services/authoring.py` holds the app registry
> (`register_app` / `posture_for_app`) and `build_focus_line`. The prompt text is
> LLM-facing — changes ride `api/prompts/CHANGELOG.md`.

## 1. What this frame is

Every chat pane in the product — /chat, and the inner panes of Slides, Text,
Images, Strings — runs on the **lane wire** (`POST /api/lanes/{id}/messages`) and
gets its system prompt from **one composition function**, assembled fresh per turn,
derived-never-stored. A lane's colleague knows four kinds of things, from four
different mechanisms with four different lifetimes:

| What it knows | Mechanism | Lifetime | Decided by |
|---|---|---|---|
| **Who it is** (character) | `build_agent_posture` from the ONE register (`agents_registry.AGENTS`) | derived per turn | the app's `resident` declaration (ADR-562/597) |
| **What its job is** (the desk) | the app's **declared posture** — `register_app(posture=…)` | derived per turn | the app's own module (ADR-606 D3) |
| **What object it is working on** | the durable lane↔artifact **binding**; the artifact's current head is read once per turn by the kernel and handed to the posture | binding: durable · content: per-turn | lane creation (ADR-440 D3) |
| **Where the member stands** | the **focus declaration** — typed, transient, app-declared, riding each turn's request | per turn, never persisted | the surface (ADR-522/606) |

Plus the frame-level facts that belong to no app: the commons contract clauses
(kernel data, ADR-533 D1), the mandate head, the connector-reach statement
(ADR-585), and the **cast** — who else is in this conversation (ADR-495 D3).

## 2. The doctrine: object from substrate, place from declaration

"The agent sees what the member sees" decomposes into exactly two channels:

- **The OBJECT comes from the substrate.** The pane's canvas and the colleague's
  posture are both projections of the same workspace files — the bound artifact's
  head, and (for Strings) the desk files beside it. They converge because they
  share a source of truth, not because anyone serialized a screen. This is why the
  Strings pane's setup checklist and `build_strings_desk_posture`'s state block
  agree without any wire between them.
- **The PLACE comes from a typed declaration.** `SurfaceFocus`
  (`web/lib/shell/useSurfaceFocus.tsx`): `{app, path, scope:
  document|page|container|block, id, pageIndex, label, excerpt, viewport}`. An app
  *declares* it (`useDeclareFocus`); the shell never scrapes it; declarations clear
  on unmount; the foregrounded app wins, with a recency fallback so a member
  chatting in /chat beside an open document still carries that document's focus.
  `LanePanel` reads the current declaration and puts it on the wire as `focus` —
  one optional field, dropped by regenerates, never persisted.

**The attention gradient this captures** (and deliberately stops at): open object →
viewport (what's on screen) → selection/caret (a held commitment). Everything above
the selection grain is declared; nothing below it is inferred — see §6.

## 3. The composition order (build_lane_conventions)

1. **Conventions frame** — kernel constants (commons contract, attribution,
   citation, read-before-write, filesystem model, format discipline) + the tool
   line derived from the same reach facts the loop enforces (ADR-585).
2. **Connector-reach section** — stated affirmatively either way.
3. **Mandate head** — first 40 lines, read-only orientation.
4. **Character** — the resident's posture, wearing the app's `name` if declared.
5. **Job overlay** — `posture_for_app(app)`, falling back to the studio posture
   for an unregistered or unstamped binding. Signature:
   `(client, user_id, artifact_path, artifact) -> str`, where `artifact` is the
   head the kernel already read once. Every binding APPENDS to the character.
6. **Focus** — `_compose_focus_section`, the ONE site (ADR-606 D1):
   - *Bound lane*: the ADR-522 grain bullet (`build_focus_line` — operator words,
     1-indexed, viewing≠selected per D3, flow-only heading reading per D4, a
     `selection` label gets its own sentence, a clipped excerpt carries "…") —
     **only when the declaration names the bound artifact or names nothing**
     (ADR-606 D2: the binding is the authority; a foreign focus carried in by the
     recency fallback renders as silence).
   - *Unbound lane*: the default-target line ("The member is looking at: … they
     mean THIS one — edit it in place").
7. **Derive section** (ADR-450 D3) when the lane carries a derive binding.
8. **Cast section** (ADR-495 D3) — a fact about the conversation, composed in the
   frame, species-blind.

## 4. The registry door (what an app declares, and must)

`register_app(slug, resident=…, name=…, standing_executor=…, posture=…)` — an
app's complete AI configuration, declared in the app's own module (ADR-562's
principle finishing its walk in ADR-606 D3). The kernel never imports an app and
never hand-branches per app; `services/apps/__init__.py` is the eager registration
point.

**Obligations, gate-enforced:**
- Every registered app declares a `posture` (`test_adr562_app_owned_config.py`).
- Every surface that mounts `<LanePanel` answers the focus question — a wired
  `useDeclareFocus` or a written FOCUS-SILENCE reason — over a DERIVED roster
  (`test_adr606_pane_sees_the_member.py`). /chat's story is written silence: the
  workbench reads others' declarations; it has no object of its own.

**Why the obligations exist**: ADR-522 shipped this first-class and it decayed to
2-of-4 apps within three weeks, through exactly the two gaps the obligations
close — focus rendered inside one app's builder (so other apps' declarations died
server-side), and declaring being optional (so the Docs→Text transition silently
dropped it). A mechanism whose per-app half is optional decays one surface at a
time; the obligation is what makes "first-class" durable.

## 5. The two rails (do not merge them)

The steward rail (`POST /api/feed`, Altitude 1) carries an `operator_locator` —
an opaque, `[:200]`-truncated, URL-scraped string (ADR-398 D2). The lane rail
carries the typed focus. ADR-522 refused to extend the locator and ADR-606 kept
the refusal: one string serving both altitudes would put two contracts behind one
field. The known inversion — the steward pre-loads governance exhaustively but
knows the member's place only opaquely; the lane knows the place richly — is
named, deferred, and demand-gated.

## 6. Refusals (recorded so they are not re-proposed)

- **No pointer/mouse telemetry.** At the only moment focus is read (send time)
  the pointer is on the composer — degenerate by construction. Hover is transit,
  not commitment, and does not exist on touch. Gestures PROMOTE attention into
  the declared grains (selection today; ADR-579 D7's structured turns next);
  attention below the selection grain is never inferred.
- **No screen/DOM serialization.** The substrate is the shared truth; a serialized
  screen is a second, unattributed, drifting context channel. If a pane shows
  state the colleague lacks, the fix is the posture deriving the same projection
  server-side.
- **Focus is never durable, never authority, never a tool argument.** Per-turn;
  the binding decides what a lane may write; ADR-522 §7 stands.

## 7. Gates

| Gate | Defends |
|---|---|
| `api/test_adr522_focus_declaration.py` | the copy rules, one-kernel-site rendering, the D2 binding guard, the truncation mark |
| `api/test_adr522_focus_is_threaded_not_closed_over.py` | focus threaded as a parameter, never closed over |
| `api/test_adr606_pane_sees_the_member.py` | the pane roster + focus-story obligation, the Text declaration wiring |
| `api/test_adr562_app_owned_config.py` | one registration per app; every app declares resident + posture |
| `api/test_adr571_text_app.py` §2 | the registry dispatch mechanism; text's declared posture IS its builder |
