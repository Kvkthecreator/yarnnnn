# The Docs granularity question — a carry-over brief

> **What this is.** A first-principles brief for a fresh session, written 2026-08-06 at
> `d878242` (plus a concurrent ADR-519 lane at `67f0025`). It carries an operator thesis
> that has **not** been converted into an ADR, the receipts that constrain it, and one
> correction the outgoing session made to its own reasoning. Nothing here is ratified.
>
> **How to use it.** Read §1–§4 before proposing anything. The receipts in §3 killed the
> outgoing session's first proposal; check them yourself rather than trusting the summary
> — several are one grep away.

---

## 1. The operator's thesis, in their words

Over three exchanges, working from live use of the Docs app:

> *"we may need this block composition style approach for docs, because my thesis is also
> that given our attribution and file system native, we may actually be under-weighting
> that capability and derivated data accumulated in the system, and thus, the documents
> itself need not be so granular and closer to google docs"*

> *"whatever google docs like one, single document just may be better. of course how we
> handle the sub shapes i think you can derive by not focusing too much on existing
> applied stack but approach it from first principles given our existing yarnnn core
> architecture"*

> *"we can drop callout and toggle if google docs doesn't accomodate. first focus on
> obtaining singular discipline path"* — and, on scope: *"let's proceed with this in full,
> thus scoping in clean-up and streamlining documentation (can, should delete legacy code
> since post commit we'll have it recorded in legacy)."*

**Read the thesis as two claims, because they have different weights:**

- **(a)** Docs is too granular. A document should behave like one continuous thing, not a
  pile of addressable blocks.
- **(b)** The reason we can afford that is the **substrate**: attribution + parent-pointered
  revisions + a filesystem + citation edges already give us the provenance that block
  granularity was implicitly buying — and we are under-using it.

Claim (b) is the interesting one and is **not yet tested by any receipt below.** The
outgoing session focused on (a) and never probed (b). That is a gap, not a settled point.

---

## 2. Why this came up — the defect that exposed it

The operator selected six blocks in a Docs artifact and the properties pane showed
**"HEADING · Typography: Heading 2 · Turn into"** — describing one block while the member
had a multi-block range. Fixed at `d878242`, but the operator's read of the cause is the
reason this brief exists:

> *"i think the current actual center user select to properties is breaking. i can't tell
> because we're block oriented while approaching via google slides visual and this is
> creating a bigger issue that we initially predicted"*

**The diagnosis that followed** (agreed by both sides, not yet canon): the pane's spine
came from **ADR-519 D3**, which imported Figma's panel grammar. Figma's grammar presumes
**selection = one object**, because that is true in a layout tool. A text range has no
single subject, so the pane had no honest answer and gave the last one it had.

Four Docs ADRs in three days were each paying interest on that mismatch:

| ADR | What it shipped | What it actually was |
|---|---|---|
| 525 | the selection carries a tier | teaching a scope-pane that some selections aren't objects |
| 526 | outline + heading crumb | giving Docs a structure the object grammar couldn't express |
| 527 | the Text section | putting a *range*-following control into a *scope*-based surface |
| `d878242` | multi-block withdrawal | the pane admitting it has no answer |

Four fixes, one unaddressed premise.

---

## 3. The receipts — what an inventory found

A full inventory of `data-block-id` (identity) and `data-block` (vocabulary) consumers was
run at `d878242`. **Verify these; do not trust the summary.**

### 3.1 What is genuinely free of prose identity

- **Citations are self-contained.** `authored_substrate.py:245` `_DATA_REF_RX` lifts paths
  only; `normalizeStructure` skips `data-ref` islands entirely (`artifactOps.ts:368-372`);
  paste keeps `data-ref` and **explicitly drops `data-block-id`** (`projection.ts:2197`).
  The reference edge never needed prose identity.
- **`extract_outline`** (`studio.py:1961`) is a regex over heading text — no ids.
- **`build_focus_line`** (`studio.py:1974-2032`) reads `scope`/`label`/`excerpt` and
  **never the id**. ADR-522's focus is already position-tolerant.
- **`editFlowRegion`** (`artifactOps.ts:406`) is **region-selector addressed, not id
  addressed**. This is the existing proof that prose editing works without ids, and it is
  the Docs (flow) path.
- Page ops (`OpAnchor`/index), git export (zero identity reads), the multi-block range
  (count only), every `div[data-block-id]:not([data-block])` container rule.

### 3.2 What is load-bearing on PROSE identity — and why position can't replace it

The outgoing session proposed stripping ids from prose. **Three receipts refute it**, and
they share one cause: *a position is not stable across an asynchronous boundary.*

1. **Cut-and-paste provenance** — `isInternalPaste` (`projection.ts:2213-2221`, gated
   `adr526_docs_structure.mjs:158-162`) distinguishes "the member cut their own prose"
   from foreign HTML *by finding a `data-block-id` that exists in this document*. There is
   no other signal. Cut/paste is **flow's only reorder mechanism** (`projection.ts:2189`).
   A position cannot survive the OS clipboard. Without prose ids every internal paste
   degrades to the foreign path and drops `data-mark`/`data-highlight`/`data-align`/
   `data-indent` — reintroducing the exact ADR-526 D4 defect.
2. **The patch channel (ADR-524)** — `projectBlock` is *awaited*, then posted to a runtime
   whose DOM may have moved on (`StudioSurface.tsx:903-921`, `projection.ts:1090-1124`,
   `:4409-4425`). The id is the stable handle across that window. The ops its allowlist
   covers are precisely the prose text-edit ops — the patch channel exists **for prose**.
3. **`mergeBlock` needs two prose ids** (`artifactOps.ts:1147`) that must agree across the
   frame/source boundary, and the merge is the op that removes one of them.

Four more that are replaceable but not free: the Docs outline drops entirely
(`StudioDesignTab.tsx:848` `if (!id) continue`); `moveBlock`'s sibling walk goes blind to
prose (`artifactOps.ts:1044-1052` — inverting the exact bug ADR-519 D1 fixed);
`set_artifact_title` is id-anchored (`studio.py:1414`); and the **lane posture explicitly
instructs the model to stamp prose ids** (`studio.py:1713-1719`), so `normalizeStructure`
would have to start *stripping* what the lane writes — it has only ever minted.

### 3.3 The vocabulary is orthogonal to identity

`data-block="kind"` is a separate axis and survives untouched. The partition already
exists and is already gated: `TEXT_BLOCK_KINDS` (`projection.ts:260`) =
`prose, callout, quote, checklist, toggle, heading`; everything else is object-like. This
is ADR-525's tier derivation (`tierOf`, `projection.ts:514-521`) and it is the healthiest
part of the current model.

### 3.4 Gates that encode the current model

If the model changes, these must be re-cut **with their intent preserved**, not deleted:
`test_adr443_studio_model.py:61,85,140` (every kind's markup carries an id),
`test_adr481_flow_chrome.py:75`, `test_studio_split_merge.py:69`,
`test_adr456_studio_wave2.py:100`, `adr482_flow_promote.mjs:138,140`,
`adr526_docs_structure.mjs:158`.

---

## 4. The outgoing session's correction — read this before re-proposing

The session proposed an axiom: **"identity is for what cannot be found by position."** It
then derived that prose should lose its ids. §3.2 refuted the derivation.

The correction it reached, **unratified and worth re-deriving rather than inheriting**:
identity is not about *findability*, it is about **referability across a boundary** — an
async round-trip, a clipboard, a frame edge, a model turn. Prose crosses all four.

If that holds, the thesis's target was never the id itself but **what having an id caused
the chrome to do**: treat prose as an addressable object. `editFlowRegion` (§3.1) proves
identity and object-ness are separable — a prose block can have an id *and* be edited as
part of one continuous region.

**But the operator did not confirm this framing**, and explicitly said the shorthand did
not land:

> *"not really, i dont know what you mean exactly by identity and member facing grain. i
> was just focusing on the infra and tech stack approach"*

So: **re-derive it, in plain terms, and check the derivation against §3.2 before
proposing an implementation.** Do not open with "identity" and "grain" as if they were
settled vocabulary. They are the outgoing session's shorthand, not the operator's.

---

## 5. What was already decided, and is not in question

- **Callout and toggle are dropped.** Operator: *"we can drop callout and toggle if google
  docs doesn't accomodate."* Both are prose in a container (`<aside>`, `<details>`), both
  have a caret, Google Docs has neither. Existing ones survive as **inert names**
  (ADR-511 D8) — they render, nothing gates on them, nothing writes them.
- **Metrics stay with the design system.** ADR-527 §4 + AUTHORING.md rule 13. "Closer to
  Google Docs" means granularity and selection model, **not** point sizes, line spacing or
  a ruler. A yarnnn document wears a *workspace* design system (ADR-449); it is not a
  self-contained artifact. Do not let "Google Docs-like" reopen this.
- **Legacy is deleted, not deprecated.** Operator: *"can, should delete legacy code since
  post commit we'll have it recorded in legacy."* No dual approaches, no shims — ADR-511
  §2 / CLAUDE.md §2.
- **Docs and Studio share machinery.** ADR-518 D2 refuses forked machinery per app. The
  write path, ops registry and runtimes are one implementation. **Chrome composition may
  be the honest fork point** — that would be a real ADR-518 amendment, argued, not a
  footnote.

---

## 6. Open questions the fresh session should answer

1. **Test claim (b).** The operator's substrate argument — that attribution + revisions +
   filesystem + citation edges already provide what granularity was buying — was never
   probed. What *specifically* does block granularity buy today that the revision trail
   does not? That is a receipted question, not a rhetorical one.
2. **Where does the chrome grammar come from?** If not Figma's object spine, then what?
   The tiers already exist (ADR-521 D2: text / structure / object) and the pane does not
   compose by them. A candidate spine — **Selection → Emphasis → Structure → Document** —
   was sketched but never tested against Studio's needs or the shared-component refusal.
3. **Is the pane even the right surface?** Google Docs, Notion and Craft all put emphasis
   on a **bar** and keep the side panel for document-level things. yarnnn has both
   (ADR-527 D4 shipped emphasis into the pane at the operator's instruction). That may be
   one surface too many.
4. **Does `<section>` reopen?** ADR-526 §6 named the two things the heading convention
   cannot carry — collapsible headings and move-a-whole-section. If the model changes,
   re-read that section; the evidence bar it set may now be met.

---

## 7. Disciplines that apply (earned this week, the hard way)

- **Doc-first**: ADR → implementation → canon → click-pass packet. Every ADR this week
  followed it.
- **Guard at the chokepoint, never the call sites.** ADR-484 guarded a rule at two click
  sites; five other routes inherited nothing and its gate stayed green at 14/14 while the
  defect was live. See ADR-525 §1.3 and AUTHORING.md rule 11.
- **A counting gate cannot defend a per-site invariant** — enumerate, assert completeness,
  and **falsify** (inject the defect, confirm the gate trips).
- **Gates must EXECUTE the real extracted body**, never grep a spelling. Six assertions
  broke this week on *formatting* while behaviour was intact; one matched its own
  explanatory comment instead of the code. When a gate fails, first ask whether the
  assertion pinned a spelling or an intent.
- **`next build` from an isolated worktree**, never `tsc` alone, never the main tree (it
  races `next-dev`). It caught a type error every gate passed over.
- **A literal backtick in a comment inside `projection.ts`'s runtime template literals
  breaks the build.** `test_adr521_flow_format_tier.py` guards it; **it fired four times
  this week.**
- **`git commit --only <paths>`**, never `git add -A`. Concurrent lanes are routine here
  and share `projection.ts` / `StudioSurface.tsx` / `artifactOps.ts`.
- **Baseline suspicious gate failures** by stashing your own changes first. `test_adr480`
  has 4 pre-existing failures and `test_studio_name_is_one_fact` is 31/32 — neither is
  yours.
- **Historical ADRs and `docs/analysis/` are dated records.** Do not rewrite their prose to
  match new canon; add a banner instead.

---

## 8. State at handoff

- **HEAD**: `d878242` (this brief's baseline) with a **concurrent ADR-519 lane** at
  `67f0025` touching `artifactOps.ts` and `AUTHORING.md`. Check `git log` before assuming.
- **The interaction contract is `docs/design/AUTHORING.md`** (renamed from `STUDIO.md` at
  `a361052`; the old path is a stub). Rule 11 (tier), rule 12 (heading tree), rule 13
  (metrics/emphasis) are the load-bearing ones for Docs.
- **Three Docs click-passes are OWED and human-only** (the flow runtime is in an
  opaque-origin iframe CDP cannot drive): ADR-525, ADR-526, ADR-527 packets in
  `docs/evaluations/`. **They gate the `web` verification lane** — do not mark it
  validated without them.
- **ADR-528 is free.** ADR-527 was the last one landed by the outgoing session.
