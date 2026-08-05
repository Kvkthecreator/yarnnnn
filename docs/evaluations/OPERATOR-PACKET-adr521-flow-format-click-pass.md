# OPERATOR PACKET — ADR-521 flow format-tier click-pass

**For**: a **human** driving a real browser. Not Claude Code, not a CDP browser
principal — see §0 for why this lane is human-only.
**Subject**: ADR-521 (the flow benchmark) as shipped in `5abb52a`, plus the D6
verb-tier fix landed 2026-08-05.
**Written**: 2026-08-05. **Target**: production (`https://yarnnn.com`), Docs app,
a **disposable** document (see §2).

---

## 0. Why a human drives this one

The flow edit runtime (`EDIT_SCRIPT`) is injected into the Studio canvas iframe,
which is `sandbox="allow-scripts"` with **no** `allow-same-origin`
([StudioCanvas.tsx:632](../../web/components/studio/StudioCanvas.tsx#L632)). That is an
**opaque origin**, and the playbook's §2 ceiling applies in full:

- the parent cannot read live DOM inside it (`contentDocument` is `null`), so
  the DOM half of a step has no query to make from outside; and
- **CDP-synthesized keystrokes do not drive an in-frame runtime.** The runtime
  listens with `document.addEventListener('keydown', …)` *inside* the frame and
  postMessages verbs out — a synthetic keyboard is not the instrument.

Every ADR-521 affordance is a keyboard or selection gesture. So a CDP pass here
could produce failures indistinguishable from harness limitation, and the
playbook is explicit: **never record a synthesized-input failure as a product
defect.** Relaxing the sandbox for a test build would change the thing under
test. Hence: a human, a real keyboard.

**What a gate already covers, so you don't have to.**
`api/test_adr521_flow_format_tier.py` (34/34, every assertion falsified) pins the
*source* — that the deterministic toggle exists, that `wrapSelection` is gone,
that the paste allowlist drops media, that the D6 gate is called before any verb
gets a subject. **What a grep cannot see is the caret.** That is this packet:
does the formatting actually apply, and does it *survive the write door*.

---

## 1. The one defect this pass is really hunting

Before ADR-521, bold across a heterogeneous range (h1 + prose + list) rode a bare
`execCommand`. Because an h1 is already bold, the toggle tried to *un*-bold it
with style spans — which `sanitizeInner` strips at commit. The formatting looked
applied and then **silently reverted on reload**. That is the operator report
that opened the ADR ("selecting across different blocks is possible, but then the
actual formatting isn't").

**So the reload is not a formality — it is the assertion.** Any step that says
"reload" fails if the formatting is there before and gone after.

---

## 2. Setup — use a disposable document

**Do not run this on a document you care about.** A format pass mutates content,
and step 6 deliberately exercises delete-adjacent keys. The revision chain is
append-only, but the *head* is live.

1. Sign in at `https://yarnnn.com` as yourself.
2. Open **Docs** → create a **new** document, name it `adr521-clickpass-<date>`.
3. Paste or type this starting content so every tier has a subject:

```
Heading One                     ← make this an H1 (slash → Heading 1)
This is an ordinary paragraph of prose that runs long enough to select across.
• first bullet                  ← a bullet list (slash → Bulleted list)
• second bullet
```

4. Let it save (the revision indicator settles).

---

## 3. Steps — text tier (the selection law)

Record **PASS / FAIL / INCONCLUSIVE** per row, plus what you actually saw.

| # | Gesture | Expected |
|---|---|---|
| **1** | Drag-select from **inside the H1**, through the paragraph, **into the second bullet**. Click **B** in the format bar. | Bold applies to the prose and the list text. The **H1 does not change** (it is already bold — bolding it is a no-op, never an un-bold). Nothing flickers back. |
| **2** | **Reload the page.** | ⭐ **The bold is still there.** This is the silent-revert assertion — if the bold vanishes, the write door is still stripping it and the pass FAILS here. |
| **3** | Select the same cross-block range again. Click **B** again. | Bold is **removed** everywhere it was applied (every eligible part was formatted → the op removes). |
| **4** | Select a range where **part** is bold and part is not. Click **B**. | Bold applies **everywhere** — the deterministic rule: any unformatted eligible part means "apply", never a per-part flip that leaves a mosaic. |
| **5** | Select across the paragraph **and** a bullet. Click **I** (italic). | Italic applies across both, including into the heading if your range covers it (italic, unlike bold, is **not** heading-exempt). |
| **6** | Select a cross-block range. Apply **code**. | Code wraps per block — you get code formatting in each block the range touches. **No block structure is mangled**; the paragraph and bullets remain separate blocks. Old behavior threw or merged blocks together. |
| **7** | Select a cross-block range, press **⌘B** on the keyboard. Then **⌘I**. | Identical to clicking the bar — one implementation, two doors. |
| **8** | Place a **collapsed caret** (just click, no selection) and press **⌘B**, then type. | Browser-native type-ahead bold. Whatever the browser does here is correct — this is deliberately *not* claimed by yarnnn. |

## 4. Steps — structure tier

| # | Gesture | Expected |
|---|---|---|
| **9** | Caret inside the **second bullet**, press **Tab**. | The bullet **nests** one level (it becomes a sub-item). |
| **10** | Press **⇧Tab**. | It **unnests** back. |
| **11** | Caret inside the **paragraph** (not a list), press **Tab**. | A **literal tab** is inserted. ⭐ **The writing session does not end** — the caret stays, focus is not lost, no block is exited. (Tab escaping the editor was the historical failure this guards.) |

## 5. Steps — paste (two gates)

| # | Gesture | Expected |
|---|---|---|
| **12** | Copy a few paragraphs **with headings and a list** from a Word doc / Notion page / any web article. Paste into the document. | **Structure survives** — headings are headings, lists are lists. |
| **13** | Inspect what landed. | ⭐ **Junk is stripped**: no colors, fonts, background shading, class names, or inline styles carried over. Pasted **images do not appear** (media enters as cited figures, never as pasted bytes — a dropped image is CORRECT, not a bug). |
| **14** | Copy text containing a **hyperlink**, paste. | The link **survives** as a link (`href` is the one attribute kept). |
| **15** | Paste **plain text** (e.g. from a terminal or a .txt file). | Lands clean as before — the plain-text path is unregressed. |
| **16** | **Reload.** | Everything pasted is still exactly as it looked after paste. |

## 6. Steps — the D6 verb tier (the fix landed 2026-08-05)

This is the newest change and the one with real data-loss history. Test it
carefully **on the disposable document**.

| # | Gesture | Expected |
|---|---|---|
| **17** | Select **all the text inside one paragraph** and press **Backspace** (the paragraph is now empty). Press **Backspace** once more. | The empty paragraph **merges up** into the previous block — normal editor behavior. ⭐ **It must NOT delete the whole paragraph block as a unit.** (Before the fix, it did.) |
| **18** | Drag-select a **cross-block range** (H1 → prose → bullet) and press **Backspace**. | **Only the selected range** is deleted. ⭐ **A whole block must NOT disappear.** (Before the fix, it did.) |
| **19** | Click a **figure / table / image block** (an object, not prose) to select it, press **Backspace**. | The object **is** deleted as a unit — objects legitimately keep the unit verb, because there is no caret to speak for them. This step passing is as important as 17/18: the fix must not have disabled the tier wholesale. |
| **20** | Press **⌘Z** after each of 17–19. | The previous state comes back. |

---

## 7. Record your results here

For each step: verdict + what you saw. Be specific about *anything* that
flickered, reverted, or felt wrong even if the end state looked right.

```
STEP  VERDICT       NOTES
1     [ ]
2     [ ]           ← the reload assertion; be exact
3     [ ]
4     [ ]
5     [ ]
6     [ ]
7     [ ]
8     [ ]
9     [ ]
10    [ ]
11    [ ]           ← did the session survive Tab?
12    [ ]
13    [ ]           ← what junk, if any, came through?
14    [ ]
15    [ ]
16    [ ]
17    [ ]           ← D6: merge, not block-delete
18    [ ]           ← D6: range, not block-delete
19    [ ]           ← D6: objects still deletable
20    [ ]
```

**Browser + OS**: ______________  **Date**: ______________
**Document path**: ______________

---

## 8. What this pass does NOT cover

Name the gaps so a later summary cannot silently upgrade them:

- **Deck / web media** — every step above is the `document` (flow) grain. The
  paged grain's format bar is capped by the editing block and is unchanged by
  ADR-521; it is not exercised here.
- **The substrate half.** This packet's steps 2 and 16 use *reload* as a proxy
  for "the write door kept it". A true substrate receipt (the stored revision
  HTML actually containing `<strong>` across the blocks) needs a repo session
  with DB access. Hand results back and it can be closed properly.
- **Multi-principal** — one principal only; no member/owner split is tested.
- **Mobile / touch selection** — desktop pointer + keyboard only.

Method-strength rule (playbook §7): what you observe here is **Probed** for DOM
behavior and **inferred** for storage until the substrate query runs. Do not let
a later summary call it more than that.
