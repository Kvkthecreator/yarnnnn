# Studio editing click-pass — run 1: BLOCKED by the harness, not by the product

> **Suite**: `docs/evaluations/eval-suites/studio-editing-click-pass.yaml` (16 steps, `suite_kind: browser`)
> **Principal**: `owner:kvkthecreator@gmail.com` on `d5b9029b` (LIVE, read-mostly)
> **Instrument**: Claude in Chrome (chrome-devtools MCP), one isolated context `owner-kvk`
> **Date**: 2026-07-31 · **SHA under test**: `0af797d` (covers `4318904`, `817eecd`, `f5a9515`, `9c79a57`)

## Scope of this record — read first

**2 of 16 steps produced a verdict. 14 did not run.** This is not a sign-off.
The blocker is a property of the *harness*, not of the Studio. No defect in the
four commits under test is claimed or cleared here.

## The blocker, stated precisely

The Studio canvas is an iframe with `sandbox="allow-scripts"` and **no
`allow-same-origin`** (`StudioCanvas.tsx:599`) — an opaque origin by
construction. Two consequences, both fatal to this manifest's method:

1. **The parent cannot read live canvas DOM.** `contentDocument` is `null`;
   `contentWindow.__yarnnnCaretLive` throws `SecurityError`. The playbook's
   §1 DOM half cannot be observed by query. The a11y snapshot *can* see inside
   the frame, but §2 forbids treating a snapshot as a DOM state check — that
   rule exists because it produced a wrong finding in the settings pass.
2. **Synthesized keystrokes do not drive the in-frame runtime.** The
   architecture is explicit at `StudioCanvas.tsx:134`: *"The canvas is a
   sandboxed iframe — keys land in its document or nowhere — so the runtime
   hears them and posts an existing verb out."* Keys must be heard by the
   runtime **inside** the frame, which then `postMessage`s verbs to the parent.

Observed, and the reason (2) is stated as fact rather than suspicion:

| Input | Result |
|---|---|
| `type_text "/"` on a document | Literal `/` inserted **and the palette opened** (13 kinds) |
| `press_key ArrowDown` ×8 with palette open | Highlight stayed on index 0. Never moved. |
| `type_text "cal"` with palette open | Did **not** filter (13 rows still). Characters landed in the document body as a text node. |

The characters reach the contenteditable; the runtime's key handlers do not
fire as they would for a human. **A real member's keyboard is not what this
harness delivers**, so every keyboard step is unobservable here.

## Per-step verdicts

| # | Step | Verdict | Method strength |
|---|---|---|---|
| 2 | `document-still-has-slash` | **PASS** | Probed (DOM) |
| — | (write-path, side 4 of thesis) | **PASS** | Probed (substrate) |
| 1 | `deck-has-no-slash` | NOT RUN | — |
| 3 | `deck-toolbar-insert-is-a-real-menu` | **INCONCLUSIVE** | see below |
| 4–5 | right-click insert (located / bare canvas) | NOT RUN | — |
| 6–10 | undo · caret-guard · Tab · palette-Enter · Escape | NOT RUN | keyboard — unobservable |
| 11–13 | clamp · scroll-close · highlight-visible | NOT RUN | 13 needs arrows |
| 14 | `legacy-slugs-resolve-and-are-never-offered` | NOT RUN | — |
| 15 | `colour-swatches-render-resolved-values` | **PARTIAL** | Probed (a11y, parent DOM) |

### Step 2 — PASS (probed)

Caret placed in a paragraph, `/` typed. Palette opened as
`div.absolute.z-30.w-72`, listing **all 13 kinds** (Heading, Text, Callout,
Quote, Checklist, Divider, Toggle, Button, Table, Metrics, Chart, Image,
Gallery), box `top 414 / bottom 712` inside an 850px viewport — within
viewport. The document is correctly stamped `data-yarnnn-mode="flow"`.

> **Correction, in place (playbook §7).** My first query for the palette
> filtered on `position: fixed` and returned nothing; I was one step from
> recording "no palette on a document" as a defect. The palette is
> `position: absolute`. **The bad query was mine, the product was correct.**
> This is the §2 failure mode (a state check that measures the wrong thing)
> reproduced exactly, and it is why the negative was re-checked before being
> written down.

### Step 3 — INCONCLUSIVE, and deliberately not reported as a defect

Toolbar **Insert** opens the same 13-kind menu, anchored, within viewport
(DOM half: PASS). But **no Divider ever landed in substrate** across three
routes — a11y-uid click on the palette row, a full synthesized pointer
sequence (`pointerover→pointerdown→mousedown→pointerup→mouseup→click`) at the
row's real coordinates, and a CDP-native click on the row's uid.

`has_hr = false` after all three. On its face that is the ADR-482 shape the
suite hunts (a route that opens and is pickable but whose act never
completes). **It is not reported as such**, because the same harness is
independently proven unable to deliver input the runtime hears (table above),
and a block insert needs the caret position that lives inside the frame. A
"defect" indistinguishable from a known harness limitation is not a finding.

**This step must be re-run by a human or a same-origin instrument before any
conclusion is drawn.** It is the single highest-value item owed.

### Step 15 — PARTIAL (probed, parent DOM only)

The Properties panel renders `TONE` **directly under `TYPOGRAPHY`** as a
swatch row — `Auto` (pressed) · `Accent` · `Muted` · `Inverse` — with the role
named beside it, and the applied-system cue ("YARNNN Design System … supplies
these values") still present. Consistent with `f5a9515` and ADR-487 D9: no
`--paper` / `--ink-06` / `--deck-stage` offered.

Not full PASS: observed on the **document** subject, not the deck the step
names, and swatch *resolved colour values* were not sampled — only role labels.

## The write path — PASS (probed, substrate)

Side 4 of the thesis is the one side fully exercised, incidentally:

- 8 revisions appended to `hello/document.html` (21 → 29).
- Every row `authored_by = operator`, message `Studio: edit document`.
- **No history rewritten, no revision deleted, no block id lost.** The restore
  was itself a forward revision through `POST /studio/artifacts/write`
  (`head_version_id: eb64628e-a772-496b-9f0a-0c7bf70dc429`).

ADR-209 held under an adversarial, sloppy, multi-route editing session.

> Note for the manifest: step 3's receipt expects a message naming the block
> ("Studio: add Callout block"). The mechanical door's actual default is
> `"Studio: structural edit"` (`routes/studio.py:575`) and text edits arrive as
> `"Studio: edit document"`. **The receipt as written would fail on message
> match even for a correct insert.** Fix the expectation, not the code.

## Damage and restore — full accounting (playbook §6.5/§6.6)

I dirtied the live flow subject with harness noise and **restored it to
byte-identical baseline**.

| | |
|---|---|
| Dirtied | `daddfadfadsf` → `daddfadfadsf////`; stray `cal` text node in block `bwpr5` |
| Over-correction | 4 backspaces removed the slashes, then the emptied block collapsed — the whole `daddfadfadsf` block was lost (22106 → 22038 bytes) |
| Restored from | pre-session blob `a8a7218…` (2026-07-28, revision `dcf7e450`), extracted losslessly via psycopg2 |
| Final state | **22 077 bytes — byte-identical to baseline.** `block_restored=t`, `still_dirty=f`, `stray_cal=f` |

**Guardrails re-asserted, all held:** `prd-for-yarnnn` 106 (untouched) ·
`test-deck-2` 27 (untouched) · `test-article` 1 · `test-page` 2 ·
`untitled-image` 11 · `untitled-canvas` 16. Only `hello` moved.

> **Lesson for the manifest.** `hello` is described as safe to mutate because
> the substrate is append-only. True for *history* — but the head content is
> live, and a harness that types into a real document damages it in ways
> "append-only" does not undo. A **disposable rig artifact** should be the flow
> subject, per playbook §3's own preference for rigs over live principals. The
> only reason this run is clean is that a pre-session blob happened to exist.

## Preconditions that DID hold (worth not re-deriving)

- **Deploy verified live, behaviorally.** The served `srcdoc` (117 843 bytes)
  contains both `__yarnnnCaretLive` and `FLOW_MODE` — markers introduced by
  `9c79a57` and `817eecd`. The bundle under test is the new one, not stale.
- **Baseline receipts all executed and matched the manifest exactly** (hello 21,
  test-deck-2 27, prd 106, test-article 1, test-page 2). No drift since
  `0af797d`. The manifest's §4 discipline paid off — zero dead receipts.
- **Login instrument works** for the live-workspace principal; identity
  re-asserted on-page (`uid=1_14 → kvkthecreator@gmail.com`) and via JWT
  (`sub 2abf3f96…`).
- **API base** is `https://yarnnn-api.onrender.com` (not same-origin with
  `www.yarnnn.com`) — relevant to any future in-browser receipt.

## What must change before run 2

1. **A same-origin or human instrument.** The keyboard/canvas steps (1, 4–13)
   cannot be driven by CDP synthesis across `sandbox="allow-scripts"`. Either a
   human drives the manifest (the operator-packet lane, which already exists
   for settings), or a test-only build relaxes the sandbox — the latter changes
   the thing under test and is probably wrong.
2. **Re-cut the flow subject onto a disposable rig artifact.** Do not type into
   a real document with a synthetic keyboard.
3. **Fix step 3's receipt message expectation** to the door's real default.
4. **Step 3 is the priority.** Whether the toolbar insert completes is
   genuinely unknown after this run, and it is exactly the ADR-482 class the
   suite exists to catch.

## Verdict

**The suite is not yet runnable by this instrument.** Two steps passed, one is
inconclusive and needs a human, thirteen did not run. The Studio's write path
is receipted sound; nothing else about the four commits is confirmed or denied
by this pass.

A receipted negative is a real result (playbook §7): *the browser-principal
lane, as currently tooled, cannot verify the Studio canvas.* That is the
finding, and it applies to every future canvas manifest — not just this one.
