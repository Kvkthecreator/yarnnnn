# OPERATOR PACKET — ADR-522 focus-declaration click-pass

**For**: a **human** driving a real browser. Not Claude Code, not a CDP browser
principal — see §0.
**Subject**: ADR-522 (the focus declaration) as shipped in `7eeb39d`.
**Written**: 2026-08-06. **Target**: production (`https://yarnnn.com`), Studio +
Docs, a **disposable** deck and document (see §2).

---

## 0. Why a human drives this one

Same ceiling as ADR-521's packet, for the same reason. The signals ADR-522
declares are produced *inside* the Studio canvas iframe, which is
`sandbox="allow-scripts"` with **no** `allow-same-origin` — an opaque origin.

- The parent cannot read live DOM inside it (`contentDocument` is `null`).
- **CDP-synthesized keystrokes do not drive the in-frame runtime.** PgUp/PgDn
  on the stage are handled by `ensureStageNav`'s listener *inside* the frame.

Every step below turns on a caret position or a paging gesture. A CDP pass
would produce failures indistinguishable from harness limitation, and the
playbook is explicit: **never record a synthesized-input failure as a product
defect.**

**What the gate already covers, so you don't have to.**
`api/test_adr522_focus_declaration.py` (falsified 4×) pins the *rendering*: that
1-indexing holds, that viewing and selected stay distinguishable, that the
heading-as-section rule is flow-only, and that an undeclared focus renders
nothing. It also pins the wire end-to-end and that focus is read off the
request rather than the durable lane binding.

**What a gate cannot see is whether the declaration matches where you actually
are.** That is this packet.

---

## 1. The one-line claim under test

> The agent knows the *place*, not just the document — so a deictic ask ("this
> slide", "this section") resolves without a clarifying question.

The originating failure: a deck open, a slide on the stage, nothing selected,
"tidy up this slide" → *"which slide?"*

---

## 2. Setup

- A **disposable** deck (Studio, ≥5 slides with distinguishable content) and a
  **disposable** document (Docs, ≥3 `##` headings with prose under each).
  Disposable because step 3 and step 6 let the agent *write*.
- One browser, logged in as yourself. No second principal needed — focus is
  per-viewer, and nothing here crosses a grant boundary.

---

## 3. Steps

Each step: **do**, then **observe**, then **record**. A step passes only if the
agent's *first* reply acts on the right thing — a clarifying question is a
FAIL, not a retry.

### Step 1 — the originating case (deck, stage view, nothing selected)
1. Open the deck in Studio. Confirm the stage view (one slide fills the canvas).
2. Page to **slide 4** with PgDn or the ‹ › chrome. **Click nothing.**
3. In the lane, send: `tidy up this slide`

**PASS**: the agent acts on **slide 4** — its reply names slide 4's actual
content, and the write lands on slide 4.
**FAIL**: it asks which slide, or edits slide 1 / the whole deck.

> This is the exact session that produced the ADR. If only one step gets run,
> run this one.

### Step 2 — viewing vs selected must not blur
1. Still on the deck. Page the stage to **slide 2**.
2. Now click a block on **slide 5** (use the navigator if the stage hides it).
3. Send: `what am I looking at?`

**PASS**: the agent names the **block on slide 5** — the selection is the finer
grain and wins over the viewport.
**FAIL**: it names slide 2, or names both and hedges.

### Step 3 — the block grain
1. Click a single text block on any slide.
2. Send: `rewrite this in fewer words`

**PASS**: only that block changes. **FAIL**: it rewrites the slide or the deck.

### Step 4 — Docs, the heading-as-section reading
1. Open the disposable document in Docs.
2. Put the caret in a **prose paragraph** under the **second** `##` heading.
   Type a character and delete it, so the caret is unambiguously live. Click
   nothing else.
3. Send: `rewrite this section`

**PASS**: the agent rewrites from that heading down to the next one, and its
reply names the heading. **FAIL**: it rewrites the whole document, only the one
paragraph, or asks which section.

> §5 of the ADR is honest that "section" here means *from this heading to the
> next* — Docs has no section element. Judge against that, not against a
> hypothetical wrapper.

### Step 5 — the untitled-heading edge
1. In Docs, add an empty `##` heading, put the caret in prose beneath it.
2. Send: `what section am I in?`

**PASS**: the agent says the heading is untitled (or equivalent) rather than
claiming a wrong title or erroring.

### Step 6 — silence costs nothing (the negative)
1. Open **Radar** and foreground it. (Radar has no lane; this checks the
   declaration doesn't leak or break anything.)
2. Return to the deck **without** selecting or paging — a freshly opened
   artifact, untouched.
3. Send: `what can you see?`

**PASS**: the agent describes the artifact, and does **not** claim a slide or
block you haven't touched. A confident-but-wrong "you're on slide 1" is a FAIL
— it means a stale or fabricated declaration.

---

## 4. What to record

Per the playbook, each step needs **both**:

- a **DOM/UI observation** (what you saw on screen — which slide was staged,
  which block was ringed), and
- a **substrate receipt** where the click writes (steps 1, 3, 4, 6): the
  revision the write produced, via the file's revision history — path +
  revision id + which blocks changed.

A run record goes in `docs/evaluations/` beside this packet. Record **negatives
too**: a receipted "the agent asked which slide" is a real finding, and it is
the outcome that would reopen ADR-522 D3.

---

## 5. If a step fails

Do not fix it in the browser. Note which step, what you sent, what came back,
and which of the two halves (DOM / receipt) disagreed. The likely culprits, in
order:

1. **Step 1 fails** → the viewport never reached the surface. `onScrollPos` is
   wired at [StudioCanvas.tsx](../../web/components/studio/StudioCanvas.tsx)
   → [StudioSurface.tsx](../../web/components/studio/StudioSurface.tsx); the
   runtime side is `reportScroll` in
   [projection.ts](../../web/components/workspace/viewers/projection.ts).
2. **Step 4 fails** → the heading walk. `headingAboveOf` in `projection.ts`,
   and the flow-only branch in `build_focus_line`
   ([studio.py](../../api/services/studio.py)).
3. **Any step gets a clarifying question** → check the turn actually carried
   focus: the `focus` field on `POST /api/lanes/{id}/messages`.
