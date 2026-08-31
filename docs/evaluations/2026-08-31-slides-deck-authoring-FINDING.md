# Finding — the Studio deck lane cannot author a deck: the token budget is spent on thinking

**Date**: 2026-08-31 · **Hat**: B (external developer of the system)
**Trigger**: operator asked for (a) an audit of the live deck at
`/workspace/operation/yarrnnnn-decl/deck.html` and (b) a check that a NEW deck
scaffolds correctly through the LLM after the recent refactors.

---

## 1. The headline

**The prompt envelope is correct. The token budget was not.** (FIXED — §5.)

A bound Studio deck lane on `anthropic/claude-sonnet-5` **cannot complete a
"make me a deck" turn**. It reads the artifact and the design system, then
issues `WriteFile` with an EMPTY `content` key six times in a row until the
8-round budget dies. The member sees:

```
[lane turn exhausted its round budget without a final reply]
```

Reproduced deterministically, twice, plus isolated at the API layer.

### Root cause

`STUDIO_LANE_MAX_TOKENS = 8192` (`api/services/authoring.py:35`).

Sonnet 5 **thinks by default**. Measured on the real posture + the real prompt:

| max_tokens | thinking_tokens | deck bytes written | outcome |
|---|---|---|---|
| 8192 (shipped) | **6102** (75% of budget) | **102** (truncated stub) | FAIL |
| 32000 | 794 | **14,425** / 10,163 | complete 6-slide deck |

At 8192 the response is cut mid-JSON. Per the guard's own comment
(`services/primitives/workspace.py:966-972`), truncation "drops `content`,
keeps `path`" — so the write arrives empty. `empty_content_blocked` correctly
refuses it; the model retries; the loop burns out.

**The guard is working. The budget is what is wrong.** The 8192 figure is
documented against Sonnet 4.6 (`lane_runner.py:138-149`), whose thinking was
not on by default. The engine moved; the budget did not.

**Blast radius**: `_studio_max_tokens()` applies to EVERY bound lane
(`lane_runner.py:1345-1346`, `:1569-1570`) — slides, text, images, and every
derive recipe. Deck authoring is simply the longest single document, so it
fails first and most reliably.

### Why no gate caught it

`test_adr440_studio.py:74` asserts only `STUDIO_LANE_MAX_TOKENS > 2048`. A
ceiling that must track a MODEL PROPERTY cannot be defended by a constant
lower bound.

### One observed side effect

`'test'` (4 bytes) was written over a 35KB skeleton during a probe run — a
model retry after truncation. The empty-guard blocks 0 bytes but not 4.

---

## 2. The live deck audit — `operation/yarrnnnn-decl/deck.html`

10 slides, 48,031 bytes. **Structurally sound and on CURRENT vocabulary**:

- `data-area` / `data-area-role`: **46 occurrences, `data-slot`: 0** — the
  ADR-619 migration is fully landed in this artifact.
- 61 `data-block-id`s, **all unique**, no duplicates.
- **Containment law holds** — zero blocks authored as direct children of a
  slide (verified by an HTML-parser nesting walk, not a regex).
- Every `data-arrange` is a registry slug.

### Content defects that ARE due for cleanup

| # | Slide | Defect | Origin |
|---|---|---|---|
| 1 | 10 | Pure scaffold placeholder: `"Slide title"` + a `42%` / `label` metric, `data-area="main"` **completely empty** | never composed |
| 2 | 1 | A `prose` block reading `Heading` / `…` sits in the TITLE slide, after the real thesis | palette insert |
| 3 | 1 | Logo `<figure>` has `alt="…"` and a `<figcaption>…</figcaption>` — literal ellipsis as alt text | palette default |
| 4 | 3 vs 4 | **Duplicated content** — "The proof is in the history." and its body appear on BOTH slides verbatim | authoring residue |
| 5 | 4 | `data-block-id="btest1"/"btest5"/"btest6"` — test ids in a live deck; also carries "Replace with your image." | test residue |
| 6 | 3 | `data-ref-kind="background"` with `data-ref-rev=""` — **unpinned** citation (posture says always stamp the rev) | |
| 7 | 8, 9 | `data-ref-rev=""` on both the CSV table and the chart | |

Defects 1–3 are **not the LLM's fault** — they are scaffold/palette defaults
the member inserted and never composed. Which is exactly what ADR-620's
`compose` gesture exists to fix, and it is correctly wired (below).

### A design gap worth noting

The `title` arrangement declares **only a heading area**
(`authoring.py:689`). So a member who inserts a prose block on a title slide
has nowhere legal for it to go — it lands in the heading area, which is what
produced defect #2. The containment law is satisfied and the result still
looks wrong. Either `title` gains a body area, or the palette should refuse
a body block on a heading-only arrangement.

---

## 3. What is CORRECT (verified, do not re-audit)

- **`_POSTURE_FRAME` is fully migrated to ADR-619 vocabulary.** Zero
  `data-slot` in any prompt text. Remaining `data-slot` reads are FE
  read-side legacy fallbacks only.
- **A fresh deck scaffolds cleanly** — `build_skeleton('deck')` emits 2 slides
  with correct `data-area`/`data-area-role`, stable ids, containment respected.
- **Deck creation involves no LLM** — `POST /studio/artifacts` writes a
  deterministic skeleton (`routes/studio.py:1186-1190`).
- **The ADR-620 compose seed is correct end-to-end.** `compose_replace`
  travels FE → route → `_seed_line`; the page-grain noun renders "slide 10"
  (not "the slide block"); both permission directions are stated explicitly.
  Gate `test_adr620_compose_at_slide_grain.py` PASSES.
- **Given adequate budget the model obeys every law it is taught**: 6 slides,
  all-registry arrangements, all-known block kinds, containment clean, zero
  inline styles on blocks, **zero raw hex colours** (ADR-583 D1 colour law),
  no fabricated citations.

---

## 4. `probe_studio_deck_quality.py` had two harness defects (BOTH FIXED)

1. **It certified its own fixture.** When every `WriteFile` is refused the
   file still holds the probe's own skeleton — and `verdict()` scored THAT,
   reporting `PARTIAL (operable, wrong skin)` on a run where the lane wrote
   nothing. An ADR-373 D6 incorrect success: the harness answered a question
   the lane never reached.

   *Correction to an earlier draft of this finding:* I first attributed this
   to a write-ORDER race (skeleton landing after the turn). That was wrong —
   the code writes the skeleton before `run_lane_turn`, and the revision row
   that looked late belonged to the NEXT invocation. The incorrect success is
   real; the mechanism is the verdict not noticing an unchanged artifact.
   **Fix**: compare against the skeleton and return `NO WRITE` before scoring.

2. **Its id check failed correct decks.** `n_ids == n_blocks` counted ids
   GLOBALLY, but since ADR-519 a SLIDE carries a `data-block-id` with no
   `data-block`. A well-formed 6-slide deck scored `25/19` and FAILED.
   Criterion 2 is per-block ("every content unit carries `data-block` AND
   `data-block-id`"), so the count now reads ids off the block-bearing
   elements themselves. **Falsified both ways**: the same deck that scored
   `25/19 → FAIL` now scores `19/19 → PASS`, and the skeleton self-test is
   unchanged.

## 5. What was DONE (all landed + verified)

1. **`STUDIO_LANE_MAX_TOKENS` 8192 → 32000** (`services/authoring.py`), with
   the measurement table inline. Thinking ranged **1,783–14,580 tokens on
   identical prompts**, so a ceiling derived from a mean is unsafe;
   worst-observed thinking + the largest document ≈ 19.5K. 24576 passed 5/5,
   16384 failed ~1 in 3, 8192 failed outright. A cap, not a spend.
2. **`_LANE_TIMEOUT_S` 120.0 → 420.0** (`services/lane_runner.py`). Raising
   the budget made the timeout the NEXT wall — the first real drive at 32000
   died on a socket read timeout, not on the model. Measured 19,272 tokens in
   172.6s (~112 tok/s), so a full-budget turn needs ~287s.
3. **The exhaustion fallback is a member-legible sentence** at both the
   streaming and non-streaming sites, and it says the document is UNCHANGED —
   the fact that matters most, and the one the old bracketed note omitted.
4. **`test_adr440_studio.py` re-anchored** from `> 2048` to `>= 24576`. The old
   assertion passed at the very value where the lane could not author at all.
5. **FOUR probe defects fixed** (§4 above plus two found while verifying):
   the `aspect-ratio` check read only the FIRST unmarked `<style>`, but the
   16:9 stage rule lives in the MARKED `data-kernel` block — so it reported
   "the lane invented slide CSS" on `build_skeleton`'s own output; and
   `\bvh\b` could never match `92vh` (no word boundary between a digit and a
   letter), so that check was dead from the day it was written.
6. **Deck test residue removed** (`operation/yarrnnnn-decl/deck.html`,
   revision `e7e5007f`): the `btest*` "duplicate test with image" slide, the
   stray `Heading`/`…` prose block on the title slide, and the literal-ellipsis
   `alt`/`figcaption`. 10 slides → 9, 48,031 → 46,563 bytes. Verified: the 7
   untouched slides are byte-identical, containment holds, 52/52 unique ids,
   all three `<style>` blocks intact. Prior revision retained for revert.

### The proof

A real bound deck lane, driven end-to-end at the new settings:

```
VERDICT: PASS
bytes: 39585 · slides: 6 · coverage: 100% of slides annotated
blocks: heading 8, prose 3, callout 1, checklist 1, metrics 1, quote 1,
        timeline 1, button 1  (17/17 with ids)
skin: aspect-ratio=True  invented-vh=False
```

Before the fix, the same drive wrote **nothing** and reported
`[lane turn exhausted its round budget without a final reply]`.

### Deliberately NOT done

- **The three empty `data-ref-rev=""` citations stay unpinned** (slide 3
  background, slide 8 CSV, slide 9 chart). Stamping them is a content decision
  about which revision the deck means to cite; the operator scoped this run to
  test residue only.
- **Slide 10's scaffold is left for the Compose gesture.** Filling it invents
  words in the deck's voice — the operator's call, and ADR-620's `compose`
  door is exactly the right instrument.
- **Thinking is not explicitly bounded.** The better long-term fix is for the
  router to pass a `thinking` budget so document bytes are reserved rather than
  merely likely. That is a cross-provider change to a provider-blind transport
  (LiteLLM), out of scope here — and named in the constant's comment so the
  ceiling can come back down when it lands.
