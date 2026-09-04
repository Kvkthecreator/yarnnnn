# What a skill is for: contract, not craft

> **Hat B** — evaluation capture, 2026-09-04. Sequel to
> [`skills-discovery-and-the-agents-page`](skills-discovery-and-the-agents-page-2026-09-04.md),
> which found the skills index had **no measurable effect on output quality**
> across three skills. That result was real and it was incomplete: it tested
> three skills whose craft a strong model already has. This capture tests the
> other eight, and the null splits cleanly in two.
>
> **Method**: real `run_lane_turn` against live production substrate, ARM A =
> the live frame, ARM B = the identical frame with `skills_index_section`
> returning `""`. One **pre-registered** measure per skill, taken from that
> skill's own `SKILL.md` before any data existed; every other measure is
> reported labelled *exploratory*, so a post-hoc pick is visible as post-hoc.
> Exact permutation tests (at n=3/arm the p-value floor is 0.100; at n=2 it is
> 0.333).

## The finding

**A skill pays when it encodes a right answer the model has no prior for.**

Sonnet 5 knows how to review a draft, summarize sources, and cite evidence. It
cannot guess that this workspace's design-system manifest is called
`_design.yaml`, that an artboard layer needs `data-z`, or that a deck's numbers
belong in a sibling CSV. The first is craft; the second is **contract**.

Every skill in the kernel is one or the other, and the A/B separates them:

| skill | kind | pre-registered measure | with index | without | p |
|---|---|---|---|---|---|
| `writing-a-spec` | **contract** | prescribed sections (of 7) | **7, 7, 7** | 1, 0, 2 | **0.100** |
| `deriving-a-design-system` | **contract** | kernel CSS variables (of 18) | **15, 18, 17** | 7, 0 | **0.100** |
| `presenting-from-sources` | **contract** | CSV beside the deck | 1, 1, 0 | 0, 0, 0 | 0.400 |
| `composing-an-image` | **contract** | layers with `data-x`+`data-y` | *not measurable — see below* | | |
| `creating-skills` | contract | valid `SKILL.md` frontmatter | 1, 1 | **1, 1** | 1.000 |
| `comparing-options` | craft | assumptions stated | 1, 0, 1 | 0, 0, 0 | 0.400 |
| `reviewing-drafts` | craft | did **not** edit the draft | 0, 0, 0 | 0, 0, 0 | 1.000 |
| `writing-updates` | craft | facts marked "(unconfirmed)" | 0, 0, 0 | 0, 0, 0 | 1.000 |

**0.100 is the exact-permutation floor at n=3/arm** — two skills reach it with
perfect separation. Both are contract skills. No craft skill separates at all,
which replicates the first capture's null on its own three.

**`creating-skills` is the instructive exception.** It is a contract skill and
shows *no* gap — because ARM B read it anyway: with no index, it ran
`ListFiles system/skills/`, found the skill about making skills, and followed
it. The ask ("make that a reusable thing the workspace knows how to do")
points straight at the folder. The mirror sufficed *for that one ask*. §Step 2
tests whether that generalises. It does not.

### `composing-an-image` is not measurable by this probe, and the reason is structural

First reading: ARM A scored 9 layers all carrying `data-x`/`data-y`/`data-z`
against ARM B's 10 layers with **zero** — the sharpest gap in the set. Then ARM
A produced *nothing* on two later trials, and the traces said why: it read the
skill and went hunting for a design system, then for an existing artboard to
learn the markup from. Neither existed — the probe purges every prior folder
between runs.

Seeding the brand fixed the first cause and not the second, because the second
is not a seeding problem. `composing-an-image` says so itself in its opening
line: *"The pane posture owns the token grammar (`data-x`/`data-y`/`data-z`,
opacity, blend); these are the CRAFT constraints."* That grammar is composed by
`services/authoring.py` for an **artifact-bound** lane, and this probe runs
unbound (`artifact_path=None`). So ARM A received craft rules that defer to a
grammar the turn never carried, and correctly went looking for it.

⭐⭐ **A skill that explicitly defers to the posture cannot be A/B'd without the
posture.** The three runs are excluded — a non-completion caused by the harness
is not a score of zero — and the one clean pair is reported without a claim.
Measuring this skill needs a bound Images lane, which is a different probe.

⭐ Worth noting what the failure was: the agent **refused to invent a
coordinate grammar** rather than guess. That is the contract skill behaving
correctly under a starved harness, which is the opposite of the reading the
raw zero would have supported.

## Why the contract half matters more than the numbers suggest

In every contract case the unaided output **looks fine**. This is the part that
does not show up in a quality score:

- A design system with no `_design.yaml` is a plausible folder of CSS — and
  `services/design_systems.py` discovers systems by querying
  `.like("path", f"%/{DESIGN_MANIFEST_BASENAME}")` (`:298`), i.e. *by the
  presence of that manifest*. The folder is invisible to the platform.
  Nothing errors.
- An artboard whose layers carry no `data-z` is valid HTML — and ADR-633's
  stack-order rule is explicit: *"A layer with no `data-z` sorts by document
  order beneath those that have one."* With NO layer stamped, the stack is
  document order entire: it stops being authored, and the Images inspector
  (`LayerTree.tsx`) has nothing to order by.
- A deck with its numbers typed into prose renders identically to one with a
  CSV beside it — until the number changes in one place and not the other,
  which is the drift the rule exists to prevent.

⭐⭐⭐ **The contract skills fail silently and functionally.** That is the
opposite of the craft skills, where an unaided output is merely *a bit worse*
and a reader can see it. It is also why the first capture's null was not the
whole story: it measured prose quality, and the thing at risk here is not
prose.

---

## Step 2 — the thin index: does a pointer buy what the roster buys?

The first capture found ARM B locating skills unaided via `ListFiles system/`,
and `creating-skills` above shows the same thing. That suggested the ~3.3 KB
per-skill roster might be replaceable by a pointer, reclaiming the bytes.

**ARM T** replaces the roster with the index HEAD plus one sentence — *"before
doing work one names, LIST system/skills/ and read the one that matches"* —
**360 bytes, naming no skill**. Four skills × three arms × three trials.

| arm | index | reached the skill | first tool call at | files |
|---|---|---|---|---|
| **A** full roster | 3,312 B | **100 %** | call 2.08 | 1.50 |
| **T** thin pointer | 360 B | **58 %** | call 43.2* | 1.50 |
| **B** nothing | 0 B | 42 % | call 60.4* | 1.83 |

*\* 99 substituted where the skill was never reached, so the mean is a rank
statistic, not a round count.*

Monte-Carlo permutation, 20k resamples:

```
A vs T   reached: p = 0.038      A vs B   reached: p = 0.005
A vs T   1st-call: p = 0.004     A vs B   1st-call: p = 0.000
T vs B   reached: p = 0.682      T vs B   1st-call: p = 0.238
```

⭐⭐⭐ **The pointer is statistically indistinguishable from nothing at all**
(T vs B, p = 0.68). And the output shows why the difference is not cosmetic —
`writing-a-spec`, the contract measured section by section:

```
ARM A (roster) : 7/7   7/7   7/7        read the skill 3/3
ARM T (pointer): 1/7   0/7   7/7        read the skill 1/3
ARM B (nothing): 0/7   0/7   0/7        read the skill 0/3
```

**ARM T produces the contract exactly when it happens to read the skill.** The
roster's 3,000 bytes do not buy convenience or latency — they buy the
*reliability* of the read. A pointer makes the craft findable; the roster makes
it found.

⭐⭐ **This inverts the hypothesis the earlier evidence suggested.** ARM B
locating a skill by listing a folder was real, and it was not generalisable: it
happens when the ask names the skill's own subject (*"make that a reusable
thing"* → `creating-skills`) and not otherwise. Reasoning from that one case to
"the mirror is sufficient" would have cut 3,000 bytes and taken contract
compliance from 100 % to 58 %.

## The ruling

1. **Keep the roster.** It is the only arm that reaches the skill every time,
   and on contract skills the read *is* the outcome.
2. **Do not prune skills on a quality score.** The craft skills score null
   because a strong model already has that craft — which is an argument about
   the model, not about the skill's worth to a weaker one. The contract skills
   are the ones carrying weight, and they carry it silently.
3. **Argue the ceilings on reach-rate.** `INDEX_CEILING` (3,400) /
   `UNBOUND_INDEX_CEILING` (4,000) now have an outcome receipt: 100 % vs 58 %
   reach. A future cut must be tested against that, not against byte count.
4. **The next skill should be a contract skill.** The four that separate all
   encode shapes the model cannot guess. A skill teaching craft a frontier
   model already has is prose we pay for every turn and cannot measure.

---

## What changed in the code

Nothing composed changes. Every index is byte-identical (unbound 3,947/4,000 ·
text 3,101 · slides 2,762 · images 1,750 · blogger 2,762) because the edits
touch bodies and comments, never a `description`.

| file | change |
|---|---|
| `services/skills/__init__.py` | the module docstring carries the split and its consequence (*a skill cannot be pruned on a quality score*); `INDEX_CEILING` carries the three-arm receipt, so a future cut is argued against reach-rate |
| `services/skills/creating-skills/SKILL.md` | new §"What makes a skill worth writing" — the actionable half, for whoever writes the next one |
| `api/prompts/CHANGELOG.md` | `[2026.09.04.3]`, per the prompt-change protocol |

**Deliberately NOT done: no skill was deleted.** The null skills score null
because a frontier model already holds that craft — an argument about *this
model*, not about the file. Deleting them buys ~1.5 KB and loses the floor
under a weaker or cheaper engine, which `LANE_MODELS` makes a live
possibility. The finding changes what we *write next*, not what we remove.

## Method notes

Four harness defects, all found by reading traces rather than trusting scores.
Three of them would have recorded a probe bug as a finding.

1. **A shared parent folder is a shared example shelf.** The first launch
   nested every run under `probe8/`; ARM A immediately read the smoke test's
   output as an example. Fixed with an opaque top-level folder per run *plus*
   a purge of every prior probe folder before each run — an opaque name hides a
   run from a sibling listing, not from the root listing the agents actually do.
2. **The round cap measured itself.** At `_LANE_MAX_ROUNDS = 8`, ARM A read
   `comparing-options`, obeyed its "evidence per option per criterion" rule,
   spent every round searching, and scored **zero files** against an arm that
   simply wrote. Raised to 16 for the probe so the comparison is craft vs
   craft. ⭐ **A cost ceiling becomes a behaviour rule the moment the treatment
   spends rounds.**
3. **A skill writes outside the run folder.** `creating-skills` lands in
   `skills/{name}/` — so ARM A's work was neither captured (scored 0 files for
   real output) nor purged (ARM B then read it as an example). That pair is
   excluded; the harness now purges and captures both prefixes.
4. **A non-completion is not a zero.** Three runs produced nothing and would
   have scored as failures of the skill. Two were `composing-an-image` ARM A
   hunting a design system the purge had deleted — *the treatment created the
   starvation*, since only the skill-reading arm was told to use one. The rule
   is now in the scorer.

And one discipline that paid for itself: **one pre-registered measure per
skill**, taken from that skill's own `SKILL.md` before any data existed, with
every other column printed as *exploratory*. The predecessor capture found a
22-vs-5 citation gap in trial 1 that reached p = 0.500 by n = 6; scoring many
columns and reporting the best one is how that happens.

⭐⭐⭐ **The strongest single lesson is #4 generalised: three of the four defects
made the TREATED arm look worse, because a skill makes an agent do more —
search for evidence, look for the design system, refuse to invent a grammar.
An A/B that scores completion naively will systematically penalise the arm
that is behaving correctly.**
