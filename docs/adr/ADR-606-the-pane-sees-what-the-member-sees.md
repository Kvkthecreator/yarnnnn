# ADR-606: The pane sees what the member sees — focus is the frame's fact, and a pane's job overlay is declared at the app

> **Status**: Accepted + Implemented (2026-08-25, this commit).
> **Date**: 2026-08-25
> **Dimension**: Channel (what the chat surface knows about where the member stands) +
> Orchestration homing (where an app's per-pane prompt contribution is declared).
> **Amends**: ADR-522 (D5's *placement* only — the focus bullet moves from inside
> `build_studio_posture` to one kernel site in `build_lane_conventions`; every other
> ADR-522 decision stands, including the copy rules, the grain vocabulary, D3's
> viewing≠selected distinction, and D4's flow-only heading reading).
> **Extends**: ADR-562 (the app registration gains a `posture` declaration — the same
> "declared where the app lives" motion that re-homed `resident`, `name`, and ADR-604's
> `standing_executor`).
> **Relates to**: ADR-567 D4 / ADR-569 D6 / ADR-571 D4 (the three job-overlay branches
> this ADR re-homes), ADR-495 D3 (the precedent: a fact about the conversation composes
> in the frame, not the posture), ADR-579 D7 (structured turns — the deliberate-gesture
> half, still phased, untouched here), ADR-593 (apps declare semantics, the kernel
> derives emission — the same shape, applied to notifications).

---

## 1. Context — a ratified first-class mechanism decayed into partial adoption

ADR-522 ratified the thesis directly: *what the member is looking at, declared once,
spoken by every app*. Three weeks later the adoption table read:

| App | Declares focus (FE) | Server renders it |
|---|---|---|
| Slides / Images | ✅ full grain | ✅ inside `build_studio_posture` |
| Strings | ⚠️ document grain | ❌ **silently dropped** |
| Text | ❌ never declares | ❌ (its branch could not render it anyway) |

Two structural causes, both homing errors:

**1. Focus rendering lived inside ONE app's posture builder.** The job-overlay dispatch
in `build_lane_conventions` was an `if app == "strings" / elif app == "text" /
elif artifact_path` chain, and only the studio branch's builder took a `focus`
parameter. The strings and text branches, as `elif` siblings, also shadowed the
unbound-focus fallback — so Strings declared focus FE-side and the server dropped it
on the floor. A mechanism whose consumption is optional per call site decays one
branch at a time.

**2. Declaring was optional, so a surface transition silently dropped it.** Docs
declared focus; ADR-574/592/599 retired Docs in favor of Text; Text never picked up
the declaration. ADR-522's own acceptance case ("caret under a heading, ask 'rewrite
this section'") was orphaned by the transition. Nothing forced the question — silence
was indistinguishable from oversight.

## 2. D1 — Focus renders at ONE kernel site, for every lane

The focus bullet composes in `build_lane_conventions` itself, after the app's job
overlay, for bound and unbound lanes alike. `build_studio_posture` loses its `focus`
parameter and its internal focus line; no posture builder sees focus at all.

**Why the placement moves (superseding ADR-522 D5's adjacency clause):** D5 placed the
bullet beside the outline so "the member's PLACE reads next to the artifact's SHAPE."
That adjacency was real but purchasable only inside one app's builder — which is
exactly how two apps ended up dropping the fact entirely. Focus is a fact about the
MEMBER, not about the character or the job wearing the turn — the same reasoning that
put the cast section in the frame rather than the posture (ADR-495 D3). One site that
cannot be forgotten beats per-app adjacency in a frame short enough to read whole.

The copy is unchanged: `build_focus_line`'s register, 1-indexing, D3's
viewing≠selected verb, and D4's flow-only heading rule all stand. One addition: a
`block`-scope declaration labelled `selection` (a raw text range in a prose editor,
which is not a block and must not claim to be one) renders as
`- The member has this text selected — "…"`.

## 3. D2 — On a bound lane, the binding is the authority; a foreign focus is silence

A bound lane renders the grain line only when the declaration's `path` names the bound
artifact (or names nothing). A focus carried in by the shell's recency fallback that
names a DIFFERENT file renders nothing: the lane's binding decides what this desk is
about (the rule `LaneFocus`'s docstring already states for authority), and narrating
another file's selection into this desk's frame would aim the colleague at the wrong
object — the incorrect-success class.

The unbound lane keeps the fundraiser-copy guidance line exactly as shipped
(2026-08-12): `The member is looking at: {app} — {path}. …they mean THIS one`.

## 4. D3 — A pane's job overlay is declared at the app, and the kernel chain is deleted

`register_app` gains `posture` — a callable `(client, user_id, artifact_path,
artifact) -> str` composing the app's job overlay from the artifact head the kernel
already read once per turn. The `if/elif` app chain in `build_lane_conventions` is
DELETED; the kernel resolves `posture_for_app(app)` and falls back to the studio
posture for an unregistered or unstamped binding (the pre-existing default, preserved
byte-for-byte).

Consequences of the unified signature:
- `build_text_posture` becomes pure `(artifact_path, head)` — its private head
  re-read (a second round-trip for bytes the kernel had already fetched, the exact
  defect the studio path fixed in its own comment) is deleted.
- `build_strings_desk_posture` takes the head as `artifact` and keeps its own
  declaration/contract reads (those are desk files, not the bound artifact).
- The design-system section (ADR-449 D4) rides inside the studio wrapper — it is a
  fact about the studio job, not about every job.

This is ADR-562's own principle finishing its walk: resident, name, and
standing-executor were already declared where the app lives; the job overlay was the
last per-app AI configuration still living as kernel branches.

## 5. D4 — Text declares focus: the caret's section, and the selection itself

`TextEditor` declares `useDeclareFocus('text', …)`:
- a non-empty selection → `scope:'block', label:'selection'`, excerpt = the selected
  text (clipped);
- else the caret → the nearest h1/h2 at or above the caret line (ADR-522 D4's rule,
  computed from `parseOutline` — by SOURCE LINE, minting nothing) →
  `scope:'block', label:'heading'`, excerpt = the heading text;
- else `scope:'document'` (renders nothing on the bound lane — the binding already
  says which document — but keeps the declaration alive for the /chat fallback).

`ProseCanvas` reports selection changes to its parent (one callback prop, the
`onSlashRun` shape) — the view owns the caret; the surface owns the declaration.

## 6. D5 — A pane-bearing app owes a focus story

Every surface that mounts `LanePanel` must either declare focus (`useDeclareFocus`)
or carry a written `FOCUS-SILENCE:` reason at the mount — the ADR-533 rendering-story
obligation, applied to the input direction. Gate-enforced with a DERIVED roster (every
`<LanePanel` mount file must be accounted for; a new pane fails the gate until it
answers the question). `/chat`'s story is written silence: it declares nothing and
reads everyone else's declaration — that is its design.

## 7. Refused — recorded so it is not re-proposed

- **Pointer/mouse telemetry.** At the only moment focus is read (send time) the
  pointer is on the composer — the signal is degenerate by construction. Hover is
  sub-second transit, not an attentional commitment; it is also device-broken (no
  hover on touch). The system never infers attention below the selection grain; it
  offers gestures that PROMOTE attention into the declared grains (selection today,
  ADR-579 D7's structured turns next).
- **Screen/DOM serialization.** The substrate is the shared truth; both the pane and
  the posture derive from the same files (the strings desk's checklist and
  `build_strings_desk_posture` are the standing example). A serialized screen would be
  a second, unattributed, drifting context channel.
- **Durable or authoritative focus.** Per-turn, never persisted, never parsed for
  authority, never a tool argument — ADR-522's refusals all stand.

## 8. Implementation

| # | Change | Site |
|---|---|---|
| 1 | `register_app(posture=…)` + `posture_for_app` + `studio_pane_posture` | `api/services/authoring.py` |
| 2 | `build_studio_posture` drops `focus`; focus line composes kernel-side | `api/services/authoring.py`, `api/services/lane_runner.py` |
| 3 | The app chain deleted; registry dispatch + `_compose_focus_section` | `api/services/lane_runner.py` |
| 4 | `build_text_posture` pure; text registers its posture | `api/services/apps/text.py` |
| 5 | Strings registers its posture (lazy wrapper, cycle-free) | `api/services/apps/__init__.py`, `api/services/strings.py` |
| 6 | `selection` label copy in `build_focus_line` | `api/services/authoring.py` |
| 7 | `ProseCanvas` selection callback; `TextEditor` declares focus | `web/components/text/` |
| 8 | Gate: single-site rendering, mismatch guard, pane roster, Text declaration | `api/test_adr606_pane_sees_the_member.py` |
| 9 | ADR-522 gate re-anchored off the old call spelling; 569/571 signature pins re-anchored | `api/test_adr522_focus_declaration.py`, `api/test_adr569_strings.py`, `api/test_adr571_text_app.py` |
| 10 | Prompt CHANGELOG entry (the posture layer is LLM-facing) | `api/prompts/CHANGELOG.md` |
