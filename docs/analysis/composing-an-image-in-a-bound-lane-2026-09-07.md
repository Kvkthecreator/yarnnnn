# `composing-an-image` in a bound lane: the last kernel skill, measured

> **Hat B** — evaluation capture, 2026-09-07. Closes the owed item from
> [`what-a-skill-is-for-contract-vs-craft`](what-a-skill-is-for-contract-vs-craft-2026-09-04.md),
> which could not score this skill because the probe ran an **unbound** lane
> (`artifact_path=None`) and the skill defers its token grammar to the pane
> posture, which `authoring.py` composes only for a bound one.
>
> **Method**: real `run_lane_turn` against live production substrate.
> ARM A = the live frame; ARM B = the identical frame with
> `skills_index_section` returning `""`. **Both arms carry the posture** —
> the only difference is whether the index names the skill. One
> **pre-registered** measure, fixed from the skill's own `SKILL.md` before any
> data existed; everything else labelled *exploratory*.

## What the earlier probe was missing, confirmed

`studio_pane_posture` composes for a bound lane and carries
`_tokens_grammar()` — verified directly: **17,475 bytes, `data-x` present,
`data-z` present**. Unbound, none of it composes. So the prior capture's
reading was right: ARM A had been handed craft rules pointing at a grammar the
turn never carried, and its refusal to invent one was correct behaviour, not a
null.

The fixture is built through **production's own creation path** — the registry
skeleton plus `stage_root_attrs(1080, 1080)`, the same shape as
`routes/studio.py:1206` — rather than hand-rolled. A fixture that stamps what
production leaves blank measures the fixture (the ADR-636 trap).

## The pre-registered measure

From `composing-an-image/SKILL.md`, verbatim:

- step 2 — *"Give every layer a `data-z`; unstamped layers fall to the bottom
  and the order stops being yours."*
- step 3 — *"Every layer carries both `data-x` and `data-y` — one without the
  other is not positioned."*

```
positioned_frac = blocks carrying ALL THREE of data-x, data-y, data-z
                  ─────────────────────────────────────────────────────
                                  blocks on the artboard
```

## Result

| trial | ARM A (index) | read the skill | ARM B (no index) | read the skill |
|---|---|---|---|---|
| t1 | **1.00** (5/5 blocks) | ✅ | 0.00 (0/4) | — |
| t2 | **0.00** (0/4) | ✅ | 0.00 (0/4) | — |
| t3 | **0.50** (2/4) | ✅ | 0.00 (0/3) | — |
| mean | **0.500** | 3/3 | **0.000** | 0/3 |

**Exact one-sided permutation: p = 4/20 = 0.200.** All six runs completed;
none excluded.

⭐⭐⭐ **It does NOT reach the n=3 floor of 0.100, and the reason is
instructive: the floor requires PERFECT separation, and trial 2 broke it from
the treated side.** ARM A read the skill and then stamped no `data-z` at all —
output structurally identical to the control's.

**Discovery, by contrast, is total and uncontested**: ARM A reached the skill
3/3, ARM B 0/3, in every trial. The index does its one job perfectly here. What
does not follow reliably is compliance with the rule the skill carries.

## Why ARM A disobeyed a rule it had just read

The three ARM-A artboards say it plainly:

```
t1  background figure + 4 text layers, ALL FIVE stamped     (real overlap)
t2  4 text layers on empty paper, NONE stamped              (no overlap)
t3  4 text layers on empty paper, TWO stamped               (no overlap)
```

⭐⭐⭐ **The agent stamps `data-z` when layers actually overlap and omits it
when they do not.** That is coherent design reasoning — z-order is visually
inert on non-overlapping elements — and it is *not what the skill says*. The
skill's rule is unconditional because the consequence is not visual: ADR-633
sorts unstamped layers by document order, so the Images inspector's
`LayerTree` has nothing to order by and the member's restack gesture has no
authored value to move. **The rule protects the TOOL, not the picture, and the
skill states the rule without stating that.**

This is the silent-failure thesis reappearing one level up. The earlier capture
established that a contract skill's absence is invisible in the artifact. Here
the skill was *present and read*, and the rule still lost — because the agent
could see no reason for it in the artifact, which is exactly the property that
makes it a contract rather than craft.

⭐⭐ **A contract skill has to carry its CONSEQUENCE, not just its rule.** An
unmotivated unconditional rule loses to visible local reasoning about two-thirds
of the time. That is an actionable finding about how to WRITE the skill, and it
generalises past this one file.

## Exploratory (not pre-registered — read as description, not evidence)

| | A t1 | A t2 | A t3 | B t1 | B t2 | B t3 |
|---|---|---|---|---|---|---|
| blocks | 5 | 4 | 4 | 4 | 4 | 3 |
| x+y positioned | 5 | 4 | 4 | 4 | 4 | 3 |
| carrying `data-z` | 5 | 0 | 2 | 0 | 0 | 0 |
| distinct z / tied | 2 / 3 | 0 | 2 / 0 | 0 | 0 | 0 |
| rounds | 3 | 3 | 4 | 3 | 3 | 3 |
| seconds | 91 | 213 | 175 | 74 | 269 | 191 |

**Both arms position with `data-x`/`data-y` in 6/6 runs.** That half of the
grammar comes from the posture and needs no skill — which is the boundary
ADR-601 D1 draws, showing up in the data.

⚠️ ARM A t1's `tied=3` (four text layers at `z=10`) is technically the skill's
own anti-pattern *"Layers stacked at the same `z`"*. ADR-633 §5b already ruled
that **a tie is legitimate, not a defect to normalise** — production's own
artboard carries 5 distinct z across 10 layers. The skill's anti-pattern line
is stricter than the platform's own rule and should not be.

## Rulings

1. **Keep the skill.** Discovery is 3/3 vs 0/3 and the pre-registered gap runs
   entirely in its favour (0.500 vs 0.000, never once reversed). p=0.200 is a
   statement about n=3, not about direction.
2. **Do not claim it separates.** It does not clear the floor, and the capture
   says so. The honest summary is *"directionally strong, discovery total,
   compliance unreliable."*
3. **The skill needs its consequence written in** — the `data-z` rule loses to
   local visual reasoning because nothing in the skill says the rule serves the
   layer rail rather than the picture. Applied below.
4. **Drop the tie anti-pattern** — it contradicts ADR-633 §5b.

## What changed in the code

| file | change |
|---|---|
| `services/skills/composing-an-image/SKILL.md` | step 2 carries the CONSEQUENCE (the rail, the member's restack); the "layers stacked at the same `z`" anti-pattern is removed as contradicting ADR-633 §5b |
| `services/skills/__init__.py` | the docstring's ⚠️ on this skill replaced with the measured result; **the index now admits by EVIDENCE rank** (`_INDEX_RANK`), alphabetical only as a tiebreak |
| `services/skills/assembling-a-composite-document/SKILL.md` | NEW, `text`-scoped, unmeasured (rank 1) — see the postscript |
| `test_adr630_skills.py` | new §3a-rank with an in-process falsification; two census assertions corrected to the invariant they meant |
| `api/prompts/CHANGELOG.md` | `[2026.09.07.1]` |

### The index ordering, and why it is here

Adding a twelfth skill evicted **`writing-a-spec`** — the skill with the
strongest measured evidence in the entire arc (7/7/7 vs 1/0/2, p=0.100) — from
the Text index, because the budget admits alphabetically and truncates the
tail. `UNBOUND_INDEX_CEILING`'s own comments record the ceiling being **raised
twice before** for exactly this ("drops real skills by ALPHABETICAL ACCIDENT";
"withheld the eleventh skill by alphabetical accident").

⭐⭐⭐ **A budget that evicts by alphabet evicts at random with respect to what
the row is worth**, and raising the ceiling buys one skill while leaving the
next eviction just as arbitrary. Admission is now ranked: measured-to-separate
first, unmeasured next, measured-null first to go. Because a withheld row is a
**reach** loss (100% listed vs 58% via ListFiles), this is the same argument
the ceilings themselves were made to carry. **No ceiling was raised.**

Composed sizes, all under their existing ceilings: unbound 3,819/4,000 · text
3,199/3,400 · slides 2,762 · images 1,750 · blogger 2,762.

## Postscript — the composite-document skill, and a premise that was wrong

Part Q's owed item 2 (the nested-document skill) was worked in the same session
and is recorded here because its most useful output was a **correction**.

**The boundary was ruled on the wrong posture.** The ruling — *judgment goes in
the skill, tag vocabulary stays in the posture* — was made after reading
`_blocks_grammar(app)`, which composes all 18 block kinds **with worked
markup** (`table` cited from a CSV, `figure` by `data-ref`, `metrics`,
`comparison`) into a bound lane. On that evidence the skill could name no tag
without becoming a second home for a fact.

That is true of Slides, Images and Blogger. **It is not true of Text.**
`services/apps/text.py` registers `text_pane_posture`, whose docstring says it
outright: *"The lane is bound to ONE prose document… No block grammar, no
Studio machinery (ADR-456 D1's grade constraint)."* Measured: the Text posture
is **1,347 bytes** and contains no `data-block`, no `data-ref`, no `table`, no
citation rule. `all_layouts()` confirms it — the three registered layouts are
`deck`→slides, `post`→blogger, `image`→images. **Text owns no artifact
layout.**

⭐⭐ **A posture read for one app was generalised to a registry of apps.** The
error was invisible because the generalisation ran the right direction for
three of four apps, and the fourth is the one the skill was scoped to.

**What the drive found.** Two bound Text runs on the same fixture (a notes file
plus a 3-row CSV, ask: *"write the Q3 platform review into the bound
document"*):

```
t1  rounds 3   read the skill: NO   figures 1,850 / 2,310 / 3,040 retyped, source uncited
t2  rounds 3   read the skill: NO   same
```

Both produced a genuinely good review. Neither read the skill, though the index
line was verified present in the composed frame (12,094 B). This is the arc's
own established prior, not a new defect: an unaided lane reaches a skill when
the ask names the skill's subject, and *"write the Q3 review"* does not say
*"composite document"*. Part Q measured the same reach problem at 58%.

**What it does establish** is that the gap is real and is about SOURCING, not
markup: with no block grammar and no citation rule anywhere in a Text lane,
nothing tells the agent that a figure lifted from a CSV should say where it
came from. The skill was rewritten for prose against exactly that observed
failure (v1 was written against the block grammar and would have taught a
vocabulary the pane does not have).

⚠️ **The skill ships UNMEASURED and is ranked accordingly** (rank 1, the honest
default in `_INDEX_RANK`). Two drives against one fixture, neither of which
reached it, is not evidence that it works — it is evidence of what goes wrong
without it. Measuring it needs an ask that names its subject, and an arm
comparison; that is a separate probe.

⭐⭐⭐ **A scorer can read the prompt instead of the artifact.** The first pass
reported 21 `data-block` kinds in the output document. They were in the
`document` skeleton's own **stylesheet** — the regex matched CSS selectors, and
21 is the *slides* roster, which should have been the tell. Score against the
artifact's authored content, and sanity-check any count that matches a table
you did not expect.

## Method notes

- **The confirming first trial did not replicate, again.** t1 was a perfect
  1.00-vs-0.00 split — the exact shape that would have been written up as
  `p=0.100` had the probe stopped there. It reached 0.200 by n=3. This is the
  third arc in a row where trial 1 overstated the effect.
- **All six runs completed**, so no exclusion judgment was needed — the first
  time in this probe family. Binding the lane removed the starvation that
  caused three exclusions in probe 8: the treated arm no longer hunts for a
  grammar it was never given.
- The per-run purge covers `/workspace/probe-%` **and** `/workspace/skills/%`,
  kept from probe 8 so the two probes cannot contaminate each other even though
  this skill writes only into its own run folder.
