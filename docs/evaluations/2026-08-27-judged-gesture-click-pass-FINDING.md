# Judged-gesture click-pass — ADR-609 / 612 / 613, driven (2026-08-27)

**Lane**: surface (browser) + gate falsification. **Target**: the judged-act arc
at `3ec933a` — ADR-609 (the anchor), ADR-612 (the Text gesture), ADR-613 (the
Slides half). **Principal**: rig owner `kvkthecreator@yarnnn.com`, own Chrome
profile on an isolated `--user-data-dir`, raw CDP (the shared
chrome-devtools-mcp profile was left alone — a concurrent session holds it).
**Owed item discharged**: the browser click-pass ADR-612 §5 and ADR-613 §5 both
name. The Slides half had never been driven at all.

## Verdict

| Claim | Result |
|---|---|
| **609 D1** the anchor CONFINES the edit | **PASS** — driven end to end in production |
| **612 D4** the door claims no turn until Send | **PASS** — stayed "Rewrite", flipped on the real turn |
| **612 D5** the write lands on the selection | **PASS** — only the selected span changed |
| **613 D4** the chip's noun follows the grain | **PASS** — block vs range named differently |
| **613 D1/D2** the deletions landed | **PASS** — no Ask row, no AI badge in the block menu |
| **612 D1** the door hangs in the MARGIN | **FAIL in BOTH apps** — covered the prose it acts on |
| **613** Slides has a pending state | **FAIL** — never built; the door claimed nothing, ever |
| **613** the door needs a subject | **FAIL** — rendered on the rect alone; clicking did nothing |
| (incidental) every gated steward write | **FAIL** — `execution_error`, unrelated to this arc |
| **612 D6** one gesture at a time | **FAIL** — a second click appended; operator-reported (§5) |
| **612 D6** the chip is the target, not the prefill | **FAIL** — restated in the composer; operator-reported (§5) |

Six defects. Four found by DRIVING, two by the operator reading a screenshot the
pass had already taken and not interrogated (§5). The gates were green over
every one of them.

---

## 1. The door covered the prose it was about to rewrite (612 D1)

ADR-612 D1's revised text is explicit: *"It now hangs in the MARGIN beside the
selection… The selection is already highlighted; the door does not need to point
at it, it needs to not cover it."*

Driven, it does not. Measured in production:

| App | selection right | door left | content edge | verdict |
|---|---|---|---|---|
| Text | 431 | **434** | 952 | on "italic and code." |
| Slides | 556 | **564** | 1215 | on the word "thesis" |

**Root cause — a margin measured against the wrong thing.** The placement test
was

```js
if (anchor.right + GAP + DOOR_W < vw) return { left: anchor.right + GAP, top };
```

`vw` is the VIEWPORT. A viewport is far wider than a reading column, so the test
is true almost always — including when the space to the selection's right is the
rest of the member's own sentence. For a short MID-LINE selection ("rewrite
these three words", the commonest case there is) the door was therefore placed
*inside* the content, every time.

This is the same defect the ADR already records once, rotated 90°. Commit
`70cc903` fixed the selection's **box** (a multi-line selection's caret-union is
not its visual extent). This one is about what the box is **compared against**.
The multi-line case passed both times because a full-column selection's `right`
already reaches the column edge — so the two bugs' passing cases overlap, which
is why the first fix read as complete.

**The fix.** The margin is the space outside the CONTENT, so the caller declares
it: `SelectionAnchor` gains `contentLeft` / `contentRight`, supplied by
`ProseCanvas` (the CodeMirror `contentDOM` box) and by `StudioCanvas` (the
iframe's own box, same offset mapping, still no zoom multiply per ADR-613 D3).
Absent bounds the door claims **no** margin and falls below the selection —
guessing is how it landed on the prose in the first place.

Driven against the two measured geometries after the fix: Text `434 → 960`
(past the column at 952), Slides `564 → 1223` (past the artifact at 1215). Both
previously-correct cases are unchanged.

## 2. Slides shipped the gesture without ADR-612 D4 (the pending state)

The Text half was driven into D4 precisely because a door that says nothing at
the click makes the act feel like it went nowhere. `StudioSurface` mounted
`SelectionGesture` with **no `pending` prop at all** — so a member who clicked
Rewrite and pressed Send watched the door read "Rewrite" through the whole turn.

Now wired the same way as Text, and for the same reason: the click only ARMS
(a seed is not a turn — the member may still edit the intent, dismiss the chip,
or never send), and the lane's `onSeededTurn` promotes armed → pending. Same
guarded stuck-state release, same generous ceiling.

## 3. A Slides door that opened onto nothing

The mount was keyed on `selRect` alone, while `gestureTarget` needs the rect
**and** the selection, and `rewriteSelection` early-returns without it. A rect
arriving without a selection therefore rendered a door wearing the fallback
label `'the selection'` that did nothing when clicked — the ADR-373 D6
incorrect-success shape at the affordance layer. The mount now requires
`gestureTarget`, and the fallback noun is deleted (it was the tell).

## 4. Incidental, and NOT this arc: every gated steward write is failing

Driving the Rewrite surfaced a production break in a neighbouring system. The
steward rail showed `EditFile ×3` and `WriteFile` all returning
`execution_error`, and the steward diagnosed itself correctly:

> `Could not find the 'agent_slug' column of 'action_proposals' in the schema cache`

Migration 248 dropped `action_proposals.agent_slug` with the rest of the
pre-ADR-596 agent model. `enqueue_gated_action` still put the key in its insert
dict, and PostgREST refuses the **whole statement** on an unknown column — so
every gated substrate write funnelling through that one path died.

This is the second production break from migration 248 that green gates missed
(the first was `/api/feed/history`), and the same lesson: **a column measured at
0 non-null rows says nothing about whether a WRITER still names it.** Fixed here
because it was in the way of the click-pass; the `agent_slug` thread is deleted
end to end (schema, arg, insert key, and the dead `auth.agent_slug` field with
0 readers), not nulled out.

---

## Gate falsification — 3 real holes, all the known classes

25 breaks applied to the code the two gates guard. 22 went red. The three that
stayed green:

**(a) A source-grep over dead code (609 D3).** The anchor-handover checks
searched `lane_runner.py` for the f-string SOURCE. Placing `return line` above
the entire D3 clause left both greps matching their own comments while no seed
line ever carried an anchor. Now DRIVEN: `_seed_line` is exec'd and the rendered
sentence is read — the thing the ADR claimed the gate already did.

**(b) A literal that is a PREFIX of its own defeat (612 D4).** The stuck-state
release was asserted as `"setPendingRewrite(null), 180_000" in editor`. That
passes when the guard is inverted (the timer never arms), when the effect is
deleted into a dead helper, and when the ceiling is widened to `180_000_000` —
50 hours, i.e. no release — because `180_000` is a prefix of it. Now the effect
is matched as a construct, bounded by its dep array, with the ceiling matched to
its closing paren.

**(c) An unscoped search that found a different thing (612 D2).** `label:
'selection'` appears in Text's SEED and, a few hundred lines up, in its FOCUS
declaration (ADR-522 — ambient, a genuinely different thing that shares the
string). So changing the seed's own label to `'block'` passed: exactly the
noun/anchor divergence D2 exists to prevent. Now scoped to the seed block.

Also worth recording: two "holes" in the first sweep were **harness artifacts**,
not gate defects — my break text landed outside the region the assertion slices,
so the assertion never saw it. Re-run properly, the zoom-divide and `meter`
checks are sound. A falsifier that fails to reach the code is not evidence of a
hole, and reporting it as one would have sent a future session to fix a
correct gate.

The margin assertion was **amended, not loosened**: it now pins the stricter
rule (measured against content, both callers must supply bounds) and would fail
on the shipped code. New Slides D4 assertions added. Falsified 15×: 14 red, and
the one that stayed green (deleting the interface fields) is caught by `tsc`,
which was confirmed rather than assumed.

## 5. Operator-reported after the pass: one gesture, one target, one turn

Reviewing the shipped Text half, the operator caught two things the pass had
looked straight past — both visible in one screenshot where the composer read
**"Rewrite the selection: Rewrite the selection:"**:

> *"when a rewrite is selected on the chat pane, shouldn't we prevent a second
> rewrite? … and separately, if the yellow chat rewrite is highlighted,
> shouldn't we NOT need the text 'Rewrite the selection'? i feel like it takes
> up un-needed real estate."*

Both are right, and they share a root. The seed effect APPENDS when the
composer is non-empty, so a second click did not re-arm the target — it
concatenated, which is the doubled text. And the prefill was a second, weaker
spelling of what the chip and the typed seed already carry.

Worth recording that **the click-pass produced the evidence and missed the
reading**: I drove exactly one Rewrite per document, so the append path never
ran twice in front of me, and I photographed the doubled prefill's single-click
form (`Rewrite the selection:`) without asking what it was FOR. A screenshot is
not an observation until someone interrogates it.

Fixed per ADR-612 D6: the door withdraws while a gesture is held (reported off
the lane's state as `onSeedHeld`, distinct from `onSeededTurn`), and the prefill
is deleted in both apps in favour of a placeholder that asks for the intent.
Send still requires typed text — one send path, not two.

## Not covered

- **The landing scroll (612 D5) was not visually confirmed.** The rewrite landed
  correctly and the document was short enough to fit on screen, so there was no
  scroll to observe. The algorithm is gate-driven over 10 cases; a long-document
  landing is still owed.
- **ADR-609's multi-block selection** still carries one primary, as §4 says.
- `test_adr462_context_menu.py` is **50/54 before and after** — the same 4
  pre-existing failures (arrangement carry + frame labels), measured both sides.
