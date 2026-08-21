# PANES — the housing contract

> **The one-line statement:** a multi-pane surface is a **canvas** flanked by **chrome**;
> the canvas is the subject and never yields, each chrome slot is independently hideable
> and resizable, and there is exactly **one** spelling of the ladder, the toggle and the
> width for every surface in the product.

**Status:** live. Implemented at [`web/lib/shell/pane-layout.ts`](../../web/lib/shell/pane-layout.ts),
gated by [`web/scripts/gates/pane_layout.mjs`](../../web/scripts/gates/pane_layout.mjs).
Written 2026-08-21.

**Why this is a design doc and not an ADR.** It ratifies no new decision. The ladder was
already ratified (AUTHORING.md rule 15, 2026-08-12), the "never ship an inescapable
state" rule was already ratified (ADR-519), and the measured-container principle was
already ratified. What was missing was a **home one rung above any single app**, so that
the rules applied to *every* surface instead of to whichever ones happened to import a
module named `authoring/`. This doc is that home; the code change is the same widening.

---

## 1. The model

```
┌────────┬──────────────────────────────┬────────┐
│  rail  │           canvas             │  side  │
└────────┴──────────────────────────────┴────────┘
   chrome            SUBJECT              chrome
```

**`canvas` is the subject.** The artifact, the conversation, the document — the thing
the member came for. It has no toggle and no width of its own: it takes what the chrome
leaves. **The canvas never yields** (rule 15's ordering principle, unchanged).

**`rail` and `side` are chrome.** Each is independently hideable and resizable, and each
folds in a declared order as room runs out.

**A slot a surface does not compose is ABSENT, not broken.** Text composes no rail —
markdown has no navigator. Chat composes no side — the conversation *is* the canvas, and
the participants drill-in deliberately takes the whole pane rather than splitting it.

> **Absence is legitimate; a second spelling never is.** This is the pane-spine rule's
> asymmetry ([AUTHORING.md §The pane](AUTHORING.md)) applied one rung out. Absence is a
> property of the surface's grain. A surface declaring its own threshold, its own drag,
> or its own storage key is a property of nothing — it is drift.

## 2. The ladder (four rungs, one home)

| rung | layout | what folds |
|---|---|---|
| `full` | three columns, full labels | nothing |
| `condensed` | three columns, glyph verbs | labels; Share/Export → ⋯ |
| `two-pane` | canvas + side as an OVERLAY | the side column |
| `single-pane` | one pane + a bottom tab bar | everything but the active pane |

Thresholds live in `lib/shell/surface-preferences.ts` (`PANE_SINGLE_PX` 768 ·
`PANE_THREE_COLUMN_PX` 1024 · `PANE_FULL_LABELS_PX` 1280), beside the shell's own
`MOBILE_BREAKPOINT_PX` (640), so "how wide is wide" has one declared home. Read through
`usePaneLadder()`. **Never re-spelled as `md:`/`lg:` in a class string.**

**A surface measures its own CONTAINER, never the viewport.** A surface can be narrow
inside a roomy window (a 320px window on a 1440px monitor); the viewport says "desktop"
for a 768px tablet and for a 320px window alike, and both leave the canvas a sliver.

**The hook returns a CALLBACK ref, and that is load-bearing.** The first spelling took a
`RefObject` observed in a `useEffect([ref])`. It shipped green — tsc, build, and 33 gate
assertions — and never measured once, because a surface returns its start state before it
returns the workbench: at the effect's only run the node was null, it bailed, and a stable
ref identity meant it never re-ran. The rung sat at its roomy default forever.

## 3. The toggle

**Every slot that can be hidden has a door, at every rung where it is a column.**

The shipped code had this **inverted**, in both directions, and the inversion is the
reason this contract exists:

- Studio and Text gated their `PanelRight` door on `sideIsOverlay` — the 768–1024px band
  only. But an overlay **already** dismisses on backdrop-click and Escape. The rung with
  no way out was the **column** rung: the ordinary desktop, permanently spending 380px
  with no affordance to reclaim it. The state existed (`sideOpen`) and was **inert** —
  force-reset to `false` whenever the rung was not overlay.
- Chat had no door at all. Its 288px rail was `shrink-0`, always present, never hideable,
  never resizable.

**The rule:** the door is hidden only at `single-pane`, where the bottom tab bar *is* the
switcher and a second control would be a second answer to one question.

**A hidden slot must have a reachable door.** ADR-519's lesson — never ship an inescapable
state. Where the door lives *inside* the slot it hides (Chat's rail), a second door is
required outside it; where the door is outside (Studio, Text), one control whose label
flips is enough. **The number of controls is not the property**; reachability is.

> **Corollary — an empty state must not name an absent affordance.** Chat's empty state
> read "Pick a chat on the left." With the rail hidden that sentence points at nothing,
> which reads as a broken product rather than a hidden panel. It now names what is
> actually there.

## 4. The width

**px, clamped to a band, and clamped again against the measured container.**

```
PANE_MIN_PX     180   below this a slot is a sliver — hiding it is the honest gesture
PANE_MAX_PX     560   a backstop; the share ceiling is the real limit
PANE_MAX_SHARE  1/3   a slot may never take more than a third of its container
```

**Why not %.** A percentage stays proportional through a window resize, which sounds right
and is wrong at the small end: 30% of a 1400px monitor is a comfortable 420px rail; 30% of
a 900px window is a 270px rail beside a 630px canvas — the crush the ladder exists to
prevent, arriving through the member's own setting. A px width clamped to `container / 3`
cannot do that: the choice is honoured wherever it fits and quietly bounded where it does
not.

**The clamp runs on every render, not only on drag.** The container changes width under a
persisted value (a window resize, the chat drawer opening), and the stored number must
never win over the room actually available.

## 5. Persistence

Per **(surface, slot, workspace, user)**, in localStorage, keyed through
`shellStateSuffix` — the one key-forming helper the dock and window state already use, so
pane state scopes identically and never leaks across a workspace switch.

**Why not `useSurfacePreferences`.** That store answers *which surfaces are open and where
the windows are* — the OS's business, synced to the server so a fresh device inherits a
desktop. Pane widths are a property of one surface **on one screen**: a 520px rail chosen
on a 27" monitor is actively wrong on the laptop the member opens next. Local by nature.

**A moving default.** A surface whose resting visibility depends on what it opened — a
deck wants its slide strip, a document does not — hands the slot a `defaultShown` that may
change once the artifact loads. The slot follows it **until the member chooses**, and never
fights them afterwards. This replaces Studio's `navUserSet` latch, which held the member's
choice for the **session** only; their next visit forgot it.

## 6. What each surface composes

| surface | rail | canvas | side |
|---|---|---|---|
| **Studio** / Docs / IMAGES | slide strip (paged only) | the artifact | Properties · Chat |
| **Text** | — (markdown has no navigator) | the document | Properties · Chat |
| **Chat** | lane list | the conversation | — (the drill-in owns the pane) |
| **Strings** (via `DeskHousing`) | roster of subjects | the lifecycle pane | the bound lane |
| **Files** (via `SettingsPaneShell`) | explorer tree | the viewer | — |

## 7. Standing refusals

- **No second threshold.** A surface declaring its own "how wide is wide" is the drift
  this contract ends. Chat's hand-rolled 600px was the fourth spelling; it is deleted.
- **No hand-rolled drag.** Resize belongs to `usePaneSlot`. Three independent pointer-drag
  handlers with three key schemes and two different pointer APIs existed; two are deleted
  and one is exempted below.
- **No door gated on the overlay rung.** The overlay dismisses itself; the column is what
  needs the door.
- **No `md:`/`lg:` in a pane's class strings.** A second spelling of a threshold is how the
  shell and a surface came to disagree about what a tablet is.

### The one exemption, named

**The chat drawer** (`components/shell/chrome/ChatDrawer.tsx`) keeps its own width store,
its own 320–720 band, and its own drag. It is **shell chrome, not a slot inside a
surface**: it is sized against the viewport, it carries a postural default keyed on the
foregrounded surface (`AUTHOR_WIDTH` / `SUPERVISE_WIDTH`, ADR-316 §5), and in Desktop
layout mode it is a `position: fixed` overlay consuming zero flex space. Folding it into a
surface-slot contract would be a false unity. Recorded here so the exemption is a decision
rather than an oversight.

## 8. Owed

- **`SettingsPaneShell` still derives NARROW from `useViewport().isMobile`** — the window,
  not its own box. That is the fifth spelling of "how wide is wide" and the one place the
  ladder has not reached. Converting it changes the drill-in contract every Settings pane
  depends on, so it is left standing and named rather than folded in silently. The width
  contract is shared today; the threshold is owed.
- **Files lost its collapse toggle** in the 2026-06-30 unification onto `SettingsPaneShell`
  (the in-code epitaph at `files/page.tsx` still names "icon-rail-collapse" among the
  deleted plumbing). The resize came across; the collapse did not. `usePaneSlot` now
  supplies both — wiring the door is a small follow-on.
- **Browser click-pass** of all four surfaces at each rung.
