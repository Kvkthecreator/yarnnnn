# Carry-over prompt — is composition-by-reference substrate-native, or an artifact-app feature?

> Paste the block below as the next session's opening prompt. Staged
> deliberately: **Stage 1 is a narrow, falsifiable wedge with a measured
> failure behind it. Stage 2 is the general thesis.** Do Stage 1 first and let
> its answer constrain Stage 2 — the last three arcs all went wrong by letting
> the broad question swallow the narrow one.
>
> Written 2026-09-07, after the skills arc closed at `ce59554`.

---

## The prompt

Continue the composition thread. **Do not take this prompt's summary as fact —
front-load your own context first**, in this order:

1. `docs/SESSION-HANDOFF.md` Part R (most recent), then Q and P.
2. `docs/adr/ADR-448-the-reference-edge-derived-from-on-the-ledger.md` and
   `docs/adr/ADR-357-citation-binds-to-source-not-internal-path.md` — the two
   ADRs that already ratify most of the thesis below.
3. `api/services/apps/text.py` (`build_text_posture` — read the docstring's
   ADR-456 D1 "grade constraint" claim) beside
   `api/services/authoring.py::_blocks_grammar` and `_POSTURE_FRAME`'s
   §"Citing workspace objects".
4. `git log --oneline -8` — a PARALLEL SESSION also commits here; check
   authorship before assuming a change is yours to build on.

### What is already true (verify, don't trust)

Composition-by-reference is **not** missing. It exists at three layers, none
app-specific in principle:

- **Ledger** — `derived_from` is a real column (ADR-448), walkable by `trace`,
  and warns before a source is deleted.
- **Artifact** — `data-ref` (living path) + `data-ref-rev` (pin), resolved at
  render by `web/components/workspace/viewers/projection.ts`, which flags a
  dangling ref `data-ref-broken` rather than failing silently.
- **Doctrine** — ADR-357 / DP31: a citation binds to the **Source**, never the
  internal path; *"a claim with no resolvable Source does not ship."*

So "make an image, save it, cite it from a deck" is already the design. The
question is not whether composition should be first-class. It is **where the
mechanism lives, and why one app is outside it**.

---

## STAGE 1 — the wedge. Why does the document app carry no reference grammar?

Measured 2026-09-07 (recorded in
`docs/analysis/composing-an-image-in-a-bound-lane-2026-09-07.md`, postscript):

```
slides   _blocks_grammar carries data-ref   ✅
images   _blocks_grammar carries data-ref   ✅
blogger  _blocks_grammar carries data-ref   ✅
text     posture is 1,344 B, NO data-ref, NO citation rule, NO block grammar
         text also owns NO artifact layout at all (all_layouts(): deck→slides,
         post→blogger, image→images)
```

And the consequence, observed in two bound Text drives on the same fixture (a
notes file + a 3-row CSV, ask: *"write the Q3 platform review into the bound
document"*):

> **Both runs retyped the CSV's figures (1,850 / 2,310 / 3,040) into a markdown
> table and cited the source file nowhere.** Neither reached the
> `assembling-a-composite-document` skill from its index line.

**⭐⭐⭐ PARTLY PRE-ANSWERED — verify this, it is the crux.** Read on
2026-09-07:

- **ADR-456 D1 is a FORMAT ruling, not a reference ruling.** It says HTML is
  the sole canonical source for Studio artifacts and markdown is an interchange
  projection. It says **nothing about citation or `data-ref`**. So
  `text_pane_posture`'s *"no Studio machinery (ADR-456 D1's grade constraint)"*
  cites a constraint about **block-grade editing machinery** — annotation-on-DOM,
  block ids, arrangements — which is **orthogonal to whether a document cites
  its sources**. If that holds, the exclusion is **inherited, not principled**,
  and that is the finding.
- **ADR-574's amendment banner on ADR-456 points the same way, harder**: it
  records that any future HTML-native surface must ship a **server-side
  `data-ref` projection** or inherit invisibility, because an exporter over
  unresolved `data-ref` elements returns empty containers. Reference resolution
  is treated there as a *platform* obligation, not an app's choice.

**⚠️ AND THE SHARPEST FACT — the Text lane IS already told to cite.** Measured
on the composed frame:

```
bound TEXT frame (12,048 B):  derived_from  ✅ present     data-ref  ❌ absent
unbound lane frame:            derived_from  ✅ present     data-ref  ❌ absent
PARTICIPANT_FILESYSTEM_MODEL:  mentions cite / data-ref / derived_from — NO
```

So the ledger-level citation rule (`derived_from`) reaches Text from the kernel
commons contract **and the agent retyped the CSV anyway, twice.** That kills
the simplest hypothesis ("it was never told") and makes the real question much
better:

> **Is `derived_from` the wrong grain for this failure?** `derived_from` cites
> the file the DOCUMENT was made from. It cannot say *this number came from that
> file* — it has no claim-level grain. `data-ref` does, because it is resolved
> at render. A document that cites a CSV in `derived_from` and then retypes its
> figures is **fully compliant with the rule it was given** and still drifts.

⚠️ **Rule this before proposing anything.** Three distinct claims are in play
and only one is obviously defensible:
1. "A prose document has no arrangement/block grammar" — defensible (ADR-456).
2. "A prose document may not cite its sources" — already FALSE (`derived_from`
   is in the frame).
3. "A prose document has no CLAIM-GRAIN citation" — TRUE today, and this is the
   actual gap. Decide whether it should be.

**Possible outcomes, all legitimate:**
- a claim-grain citation available to Text (NOT the 18-kind block roster — that
  would re-import the machinery ADR-456 excluded on purpose);
- a deliberate "no", written down with its reason so it stops being re-litigated;
- the finding is about the SKILL, not the frame: `assembling-a-composite-document`
  already carries "name the source of every figure, inline" and neither drive
  reached it. Reach, not doctrine, may be the whole defect.

⭐⭐⭐ **ESTABLISH THIS BEFORE DESIGNING ANYTHING.** `projection.ts` is what
makes `data-ref` live. **Find out which render pass a Text artifact goes
through.** If Text documents are not projected, a `data-ref` in one is inert
markup and a body-level rule is worse than useless — it would author a citation
nothing resolves, which is exactly the "empty containers" failure ADR-574's
banner describes. The answer to this one question decides whether Stage 1 is a
frame change, a skill change, or nothing.

---

## STAGE 2 — the thesis, constrained by whatever Stage 1 returns

**Should composition-by-reference be substrate-native — a kernel fact every
engine composes against — rather than a per-app authoring grammar?**

"Every engine" means all of these, and they do not share a composition site
today:

| engine | how it composes | `derived_from` | `data-ref` |
|---|---|---|---|
| bound lane (slides/images/blogger) | `lane_runner` + `_blocks_grammar` | ✅ | ✅ |
| bound lane (**text**) | `lane_runner` + `text_pane_posture` | ✅ | ❌ |
| open/unbound lane | `lane_runner`, no posture | ✅ | ❌ |
| a standing run | `build_standing_frame` (toolless) | (verify) | (verify) |
| an MCP connector | `mcp_composition.compose_*` | (verify — `trace` walks the edge) | (verify) |
| an external LLM via MCP | the tool contracts only | (verify) | (verify) |

*(The first three rows were measured 2026-09-07; the last three were not — check
them rather than inheriting the pattern.)* Note `PARTICIPANT_FILESYSTEM_MODEL`
mentions **none** of `cite` / `data-ref` / `derived_from` — the commons contract
carries the citation rule elsewhere in the kernel tail, so find where before
proposing to add to it.

**The specific sub-questions worth answering, in order:**

1. **Is the participant contract the right home?** `PARTICIPANT_FILESYSTEM_MODEL`
   and `PARTICIPANT_REGISTER` (ADR-533/638, `services/workspace_paths.py`) are
   already kernel constants composed for every lane regardless of app. "Cite,
   don't copy" is the same *kind* of fact as "this is your filesystem" — a
   property of the commons, not of an app. **If it belongs anywhere kernel-level,
   it is probably here.** Test that against ADR-533 D1's own boundary.
2. **What does it cost?** The kernel tail composes into EVERY turn. DP22/ADR-306
   says the prompt layer is ablated, not accreted, and adding is the last resort.
   A clause here needs the same evidence as any prompt instruction: **a repeated,
   observed failure** (the two Text drives are exactly one such observation —
   n=2, same fixture, so treat it as a lead, not a proof).
3. **Is the failure silent?** This is the arc's own test for whether a rule pays
   (`api/services/skills/__init__.py` docstring). A retyped figure **looks
   perfect** and drifts the moment the source moves — silent and functional,
   which is the profile that argues for a contract rather than craft prose.
4. **Does an external caller need it too?** ADR-623 established *"external must
   never be better than internal"*. Check whether the inverse now holds: an MCP
   connector writing a file gets the commons contract; does it get the citation
   rule? If not, is that a gap or correct?

### What would FALSIFY the thesis

State these before running anything, and mean them:

- **A Text artifact is not rendered through `projection.ts`** → a body-level
  `data-ref` is inert; the edge belongs on the ledger only, and Stage 1's answer
  is "the current state is correct". ⭐ Check this FIRST — it is the cheapest
  falsifier and it invalidates the most work.
- **The skill already says it and simply was not reached** (`assembling-a-
  composite-document` step 3: *"Name the source of every figure, inline"*) →
  the defect is REACH, which the skills arc already measured, and no doctrine
  changes.
- A Text document is never rendered through `projection.ts` → a body-level
  citation grammar is inert; the edge belongs on the ledger only.
- An A/B shows a lane cites its sources at the same rate with and without the
  clause → it is prose we pay for in every turn (the exact null the skills arc
  measured for craft skills).
- The kernel tail is already at its ceiling → the clause has to displace
  something, and what it displaces is the real decision.

### Method (this is where the last four arcs actually went wrong)

- **Pre-register ONE measure per arm before running**; print everything else as
  exploratory. A confirming first trial is the one to distrust — Part P's
  22-vs-5 gap reached p=0.500 by n=6, and Part R's perfect 1.00-vs-0.00 trial 1
  became p=0.200 by n=3.
- **A rule makes an agent do MORE** (look for the source, refuse to assert). An
  A/B that scores completion naively penalises the arm behaving correctly.
  Score completion first; read the trace behind every zero.
- **Score the artifact, not the prompt.** A scorer counting `data-block` in a
  produced document found 21 kinds — they were in the skeleton's own stylesheet,
  and 21 was the *slides* roster. Strip `<head>`/`<style>` before scoring, and
  treat any count matching a roster you did not expect as a bug.
- **Evaluate a per-app registry FOR THE APP IN QUESTION.** Last session ruled a
  boundary from `_blocks_grammar` — correct for 3 apps, wrong for the 4th, which
  was the one being scoped. Compose the posture for that app and grep it; it is
  three lines.
- **Isolate per run AND purge between runs.** The substrate leaks craft between
  arms — anywhere the agent can write, another arm can read (including
  `skills/`, which is outside any run folder).
- **Scope verification to what the change can reach.** A full sweep on a
  posture/docs change proves nothing and its reds are environmental. Check for
  stray CHILD processes before trusting any sweep against the live workspace.
- ⚠️ **macOS caches bytecode outside the repo** —
  `~/Library/Caches/com.apple.python/<abs path>/`. `find -name __pycache__`
  does not clear it, and a stale `.pyc` will make a correct source file import
  as a falsified value. Falsify **in-process** (mutate + `try/finally`) rather
  than by editing source.

### Also still open (unrelated to this thread; don't let them bundle)

The composite-document skill is unmeasured and ranked 1 accordingly · the
`agent-composition.md` §3.2.1 re-cut (df797d2 left a working decision table, so
this is tidiness, not a hazard) · the standing run's reach receipt · the GitHub
aperture · the `ADR-411 D4` phantom citation (33 sites / 26 files → ADR-408/460)
· ADR-640 D2's two derived rows.

**Pick up with Stage 1 and drive it rather than reading about it.**
