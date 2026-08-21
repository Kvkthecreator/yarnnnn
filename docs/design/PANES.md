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
PANE_MIN_PX     180        below this a slot is a sliver — hiding it is the honest gesture
PANE_MAX_PX     rail 560   an absolute backstop, per slot
                side 900
PANE_MAX_SHARE  rail 1/3   the share of the measured container, per slot
                side 1/2
```

**The ceiling is per slot, because the two slots are not the same kind of thing.**
A `rail` is an **index** — a list of names and timestamps. Past about a third of the
surface it shows the same rows with more whitespace while the canvas pays for it, so a
third is a real ceiling rather than a guess. A `side` pane is a **working surface** —
Properties, and a conversation the member reads and types into. There the canvas and the
pane are closer to peers and the member is entitled to say so: **half**.

> Both halves of the ceiling have to move together. `PANE_MAX_PX` was 560 for every slot,
> so on any monitor wider than ~1680px the **px backstop**, not the share, was what
> actually bound — raising the share alone would have changed nothing visible. (Reported
> symptom: a 1600px workbench capped its side pane at 533px and the drag read as "hitting
> something". Now asserted as behaviour at that exact width.)

**Why the stored width is px, and the share is only a ceiling.** A percentage *as the
stored value* stays proportional through a window resize, which sounds right and is wrong
at the small end: a rail stored as 30% is a comfortable 420px on a 1400px monitor and a
270px sliver beside a 630px canvas in a 900px window — the crush the ladder exists to
prevent, arriving through the member's own setting. Storing px and clamping it cannot do
that: the member's choice is honoured wherever it fits, bounded by the share where it does
not, and never *shrinks itself* on a surface that got smaller. The share is a **ceiling on
the canvas's behalf**, not the unit the width is kept in.

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

## 7. The composer names a SPEAKER, never a subject

A pane's composer placeholder addresses **who answers**, resolved in this order: the
Agent holding the floor (when two or more could answer) → `speakerLabel` (ADR-562 D5 —
the app's name for its resident, else the colleague's own name, else the engine label) →
the generic **"Write a message…"**.

**Never the lane's name.** A lane is named for its **subject**, and on every bound app
that subject is a **file** — so the composer read *"Message Learn:
embed-application-2026-08-10.md…"*, addressing a document as if it could reply. Every
caller already passed `speakerLabel`; the placeholder was simply reaching past it.

**The fallback is generic on purpose.** A sentence true of every surface beats a name
true of none. `LanePanel` is the single composer behind Chat, Studio, Text and every
desk, so one wrong guess there is wrong four times over.

## 8. The canvas has a MEASURE, and the gutter does not grow

A pane's **width** is settled by §4; what is set *inside* it is a separate question. A
transcript is prose, and prose has a comfortable line length **regardless of how much room
the window has**. Edge-to-edge, a maximised chat set a line of assistant text at ~1800px —
roughly three times the measure typography has converged on, and the eye loses its place
returning to the next line.

`TRANSCRIPT_MEASURE_PX = 820`, centred, shared by the transcript **and the composer** (a
full-width input under a centred conversation reads as two different documents, and the
reply lands where the eye was not). Deliberately wider than the document measure
(`FACE.measure`, 46rem ≈ 736px): a document is serif at a reading size, a transcript is
sans at UI size with bubbles, a gutter and an avatar rail, so the same character count
needs more room.

**It is a MAX, not a width — which is the entire small-screen story.** Below 820px the
column *is* the pane and the layout is byte-identical to before. Measured across the real
mounts:

| mount | width | column |
|---|---|---|
| Text rail · Studio side pane | 320–380 | unchanged |
| phone chat · chat drawer | 390–400 | unchanged |
| tablet chat | 768 | unchanged |
| side pane at its new 50% ceiling (1600px surface) | 800 | unchanged |
| laptop → maximised chat | 1100–1800 | **capped at 820, centred** |

**The gutter stays a flat `px-3` and does NOT grow at a breakpoint.** `LanePanel` is ONE
component mounted at four independently-sized widths, so a `sm:px-6` there asks the
**window** a question only the **container** can answer — it would spend 24px of gutter
inside a 380px side pane on a large monitor. That is §9's refusal, and it shipped in the
first cut of this change before being caught. The centred measure supplies the breathing
room on a wide pane; the flat gutter keeps a narrow one honest.

## 9. Chrome centres on the canvas column, not on the pane

§8 gives the canvas a measure. The rows *above* it — an app's identity row and its
verb row — then have a choice: sit flush against the pane's edge, or centre on the
column the canvas actually occupies. **They centre on the column.**

Flush-left, Text's file name **drifted every time the right pane opened or closed** —
the surface had no stable spine, and the toggle we had just added made that visible. The
reference behaviour is Google Docs: the title and the toolbar are centred over the page,
and the page does not move when a side panel appears.

The column is **derived**, not pinned: `FACE.column = FACE.measure + 2 × FACE.gutter`
(46rem + 2×1.5rem = 49rem). The canvas composes its padding from the same `FACE.gutter`,
so a measure change moves the page and its chrome together. A pinned `'49rem'` in the
chrome would silently stop tracking.

**Three zones, and the flanks must be equal.** Left acts · centre identity · right acts,
with both flanks `flex-1`. A centre zone between *unequal* siblings is not centred — it
merely sits between them and slides as either side grows.

**The centre zone takes `flexBasis` + `maxWidth`, never a fixed `width`.** It should *be*
the column where the pane can afford it and shrink below that where it cannot; a fixed
width claims 784px inside a 500px pane and squeezes the flanking acts before it yields.

**A verb row scrolls; it never wraps.** A wrapping toolbar changes the canvas's vertical
origin as the pane narrows, so the document visibly jumps. Docs scrolls for the same
reason. The scrollbar is hidden — chrome on chrome, on a row one line tall.

## 10. Standing refusals

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

## 11. Owed

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
