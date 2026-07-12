# The Studio direct-edit re-approach: editing the projection, writing the source (2026-07-12)

> Derivation for ADR-446. The operator's verdict on the selection→chat-seed model: it is
> "only partially right… we need to think closer to a webpage editor like Wix — select and edit
> ON SCREEN, IN REAL TIME." This doc works out *how* direct editing lands over a canvas that
> renders a **projection**, not the source — the one hard problem — and what canon it amends.
> Receipts under every load-bearing claim.

---

## 1. The verdict, and what it overturns

The Studio's mutation model to date has been **single-path through the lane** (chat): the canvas
renders and points; every write flows through the bound lane or the mechanical toolbar. Direct
manipulation was named a **deferred / drift-guarded** thing:

- STUDIO.md §"What Studio is NOT" line 68: *"no keystroke-realtime co-editing… no WYSIWYG second
  write path"* (`docs/design/STUDIO.md:68`).
- ADR-440 D7: *"Keystroke-level realtime co-editing is a permanent non-goal: the revision is the
  atom, and there is no merge/CRDT layer, ever (ADR-406/286)"* — but also, in the same breath,
  *"Direct manipulation, when it comes, is a gesture-composer — never a second write path…
  applied as attributed revisions"* (`ADR-440…:72`).

The operator's verdict **widens the reference-app scope** (ADR-440 §7 standing intent): direct
**text editing on the canvas** is now in scope. The critical distinction the operator drew is
**modality, not architecture**: the member should *type in the document*, not describe the change
to a chat that types for them. Chat stays — for judgment work (rewrite, restructure, cite, argue).
Direct manipulation becomes the default for *direct* changes (fix a word, correct a heading).

**What must NOT change** (the invariants that make this a widening, not a reversal):

- **The revision is the atom. No CRDT, ever.** "Real time" means *the manipulation feels
  immediate* (you type in place, you see it), NOT keystroke-level co-editing with operational
  transform. The commit unit is a revision landed through the CAS door — ADR-406/286 stand
  (`api/services/authored_substrate.py` `StaleWriteError`; `docs/adr/ADR-406…`).
- **One attributed write door.** ADR-236's point — *no silent second write path* — is preserved
  by routing every direct edit through the SAME `POST /studio/artifacts/write` that ADR-444's
  mechanical toolbar already uses (`api/routes/studio.py:121-158`). Typing is a mechanical
  TRANSFORM fed by keys instead of buttons; attribution (`authored_by="operator"`) + CAS +
  revisions make it legible. ADR-236's *letter* ("apps render, never edit") is amended; its
  *spirit* (everything lands attributed through one door) is upheld.

---

## 2. The hard problem: the canvas renders a projection, not the source

This is the whole design. The Studio canvas does not render the artifact's source HTML — it
renders a **projection** computed by `resolveArtifactHtml(html, path, {pointer:true})`
(`web/components/workspace/viewers/projection.ts:233-254`). The projection pass, in place, on a
parsed `Document`:

1. **Resolves every `data-ref` citation** into displayable content — a signed blob URL for a
   binary image, an inline `data:` URL for an SVG, a rendered `<table>` for a CSV, an escaped
   `<pre>` for other text (`projection.ts:83-142`). The citation's *living reference* becomes a
   *resolved copy* in the projected DOM.
2. **Strips every artifact-authored executable** — `script`/`iframe`/`object`/`embed`, inline
   `on*` handlers, `javascript:` URLs (`projection.ts:213-227`).
3. **Injects the kernel pointer runtime** — the only script that runs in the `allow-scripts`
   frame (`projection.ts:167-208, 243-251`).

**The trap** (the operator named it): if direct editing serialized *the projected document* back
to the file, it would:

- **bake resolved citations into copies** — a `<img data-ref="operation/brand/logo.png">`
  projected to `<img src="blob:…">` would be written back as the blob, destroying the
  living-reference thesis (Part 3 of the probe: *"the reference IS the point"*,
  `services/studio.py:363-365`);
- **lose stripped content** — anything the projection removed (there should be none in a
  well-formed artifact, but the pass is defense-in-depth) would vanish;
- **lose the injected runtime's neutrality** — the pointer `<script>` and `<style>` would be
  serialized into the source.

**Therefore the editing model is a source-mapped transform, never a projection serialize:**

> An edit event carries `{data-block-id, new inner content}`. The FE applies that change to the
> **SOURCE** html (an `artifactOps`-style pure DOM transform on the *original file content*, not
> the projected DOM), re-sanitizes (strips executables again — the member cannot inject a script
> by typing), and lands it through the mechanical door with CAS.

This is **exactly the ADR-444 shape** already proven: `applySlideLayout`/`insertBlock` in
`artifactOps.ts` parse `file.content` (the source), transform, `serialize()`, and land through
`api.studio.writeArtifact(path, html, file.head_version_id, message)`
(`web/components/studio/StudioSurface.tsx:292-316`). A text edit is one more pure transform:
`editBlockText(sourceHtml, blockId, newInnerHtml)`. **No new endpoint, no new attribution, no new
meter, no schema** — the mechanical door and the block model already carry it.

### 2.1 Why the block model makes this tractable

The DOM is the model (ADR-443 R1): top-level content units carry `data-block` +
`data-block-id` (`ADR-443…:30-35`). The projected DOM preserves those ids — the projection pass
never touches block annotations, only citation *contents*. So the edit runtime can:

- toggle `contentEditable` **per block** (`[data-block]` elements) inside the projected iframe;
- on commit, read the edited block's **id** (`data-block-id`) and its **new inner HTML** from the
  projection;
- hand `{blockId, newInner}` to the parent, which finds the SAME `data-block-id` in the SOURCE
  and swaps its inner content.

The block id is the join key between projection and source. This is why ADR-443's "blocks before
tweaks" sequencing was correct: *a gesture wants a block to aim at* (`ADR-443…:58`), and so does a
keystroke.

### 2.2 The citation island rule (the sub-trap)

A `data-block` element may *contain* a `data-ref` citation (ADR-443 R3: "a block may contain
citations", `ADR-443…:18`). Inside an editable block, the projected citation is a **resolved
copy** — a `<img src="blob:…">` or a `<table>` built from CSV. If the member's edit swept that
resolved form into `newInner`, writing it back to source would bake the citation.

**Rule: citations inside an editable block are `contentEditable="false"` islands.** The runtime
marks every `[data-ref]` (and its subtree) non-editable so the caret cannot enter it and the
member cannot delete/alter its *resolved* form by typing. On commit, the runtime **restores each
island's SOURCE form** before emitting `newInner` — it re-reads the island's original
`data-ref`/`data-ref-rev`/`data-ref-kind` attributes (which the projection preserves on the
element) and emits the element as its *unresolved* citation markup, not its resolved content.

Concretely: the projection, when in edit mode, must **stamp each citation element with its own
source outerHTML** (a `data-src-html` attribute, base64 or escaped) at projection time — because
by render time the element's *content* is resolved and its source form is otherwise unrecoverable
from the projected DOM alone. On edit-commit the runtime substitutes each island back to its
`data-src-html` before serializing the block's inner. The parent's source transform then sees the
citation in its living-reference form, identical to what was in the file. **The source file's
citations are never touched by a text edit** — only the prose around them.

(Simpler alternative considered and rejected: "forbid editing blocks that contain citations."
Rejected because the 80% case — a figure block with an editable caption — is exactly a block with
a citation *and* editable prose. The island rule keeps the caption editable and the figure
inviolate.)

---

## 3. The commit atom (debounce policy)

Keystroke-level writes would flood the revision chain — each character a revision is absurd and
violates "small patches keep the revision history legible" (`services/studio.py:334`). The
revision is the atom (§1); the question is *when* a burst of keystrokes becomes one revision.

**Decision: commit on `blur` (the member leaves the block) OR idle-2s within a block, whichever
first; never per-keystroke.** Rationale:

- **blur** is the natural "I'm done with this block" boundary — the same instinct as tabbing out
  of a form field. It maps one editing session on one block → one revision → one History entry
  ("Studio: edit prose block b7").
- **idle-2s** is the safety net for a member who edits one long block for minutes without
  leaving — it lands progress so a crash/navigation doesn't lose work, and keeps each revision a
  bounded diff. 2s is the felt-instant threshold; shorter floods, longer risks loss.
- **A no-op edit commits nothing** — if the block's inner is byte-identical to source, skip the
  write (the mechanical door would otherwise mint a byte-identical revision;
  `authored_substrate` dedupes blobs but a revision row is still noise).

**Interleaving with the lane and the toolbar** is handled by the CAS door, unchanged: if the lane
(or a toolbar op) wrote while the member was typing, the member's commit carries a stale
`expected_parent_version_id` → 409 → the canvas reloads (`StudioSurface.tsx:308-313`,
`routes/studio.py:153-157`). The member's in-flight edit to that block is lost — which is correct
under single-writer-per-path (ADR-286): there is no merge. The 2s idle cap bounds how much can be
lost to at most one idle window. This is the same contract the toolbar already lives under; text
editing inherits it without new machinery.

---

## 4. What of the pointer runtime + the seed spam

The pointer runtime (selection via click → `postMessage {tag,text,dataRef,blockId,blockKind,
slideIndex}`) **stays** — selection still anchors the toolbar's mechanical ops (`StudioSurface.tsx:
231-252, 318-353`) and now also gates edit mode (you select a block, then edit it). What **dies**
is the **auto-seed into the chat composer** on every selection:

`StudioSurface.tsx:239-249` unconditionally calls `seedComposer("Selected the … block…: ")` on
every `onPoint`. That is what produces the operator's observed **seed-append spam** — LanePanel's
`composerSeed` effect *appends* to the composer (`LanePanel.tsx:174-177`), so clicking three
elements yields `"Selected the h2…: Selected the p…: Selected the …: "` piling up in the input
(the operator's screenshot).

**Fix**: selection no longer touches the composer. The lane hears about the selection **only on an
explicit affordance** — an "Ask about this" action on the selection chip (the toolbar already
renders the chip, `StudioInsertMenu.tsx:152-165`). Clicking it seeds the composer *once*, on
purpose. The default reading of a click becomes: *select the block* (for editing + toolbar ops),
not *narrate to the chat*.

This also resolves the modality confusion the operator named: a click was doing double duty
(anchor a toolbar op AND narrate to chat). After the pivot, a click *selects*; a double-click (or
an "Edit" toggle) *enters text edit*; the chat hears the selection only when the member explicitly
asks.

---

## 5. Scope: text first, geometry later

- **Text edits are the 80% case and ship now**: editable prose inside `[data-block]` elements
  (headings, paragraphs, list items, callout/quote/checklist text, figure captions). One block →
  one `editBlockText` transform → one revision.
- **Style / geometry tweaks stay deferred** to the ADR-444 tweak-inspector direction (v1.2's
  gesture-composer, now properly block-grained). Dragging, resizing, color-picking a block is
  *property* editing — a different transform class (`EditFile`-style attribute patches), and the
  benchmark itself keeps those behind an "apply on exit" model (`ADR-440…:72`). Text is the honest
  first cut: it is the manipulation members reach for first and the one that maps cleanly to
  block-inner transforms.
- **Layout containers stay non-text-editable regions** — a deck slide's `<section class="slide">`
  or a document's `<main>` is structure, not a block (ADR-443 D4). You edit the *blocks inside*,
  not the container. This falls out for free: the runtime only makes `[data-block]` editable.

---

## 6. The canon this amends (doc-first)

| Canon | Current letter | Amendment |
|---|---|---|
| **ADR-236** (mount contract; "apps render, never edit") | Mutation flows through chat only | The Studio canvas becomes the sanctioned **editor mount**. Typing in place is a mechanical TRANSFORM (ADR-444 D1's member path) fed by keys. The *letter* is amended; the *point* (no silent second write path — everything lands attributed through one door) is upheld: direct edits route through `POST /studio/artifacts/write`, CAS-guarded, `authored_by="operator"`. |
| **ADR-443 D2** (seven operations) | TRANSFORM's mechanical half = insert/slide/slide-master | TRANSFORM's mechanical half now includes **direct text editing**. The operator word is just **"Edit"** — on the page, like every editor since 1984. No eighth operation (D2's closure holds — this is TRANSFORM). |
| **ADR-444 D1** (two write paths) | Mechanical = structural ops (blocks/slides) via buttons | Mechanical now also = **text edits via keys**. Same door, same CAS, same free-because-no-LLM class. The judgment path (lane) is unchanged. |
| **ADR-440 §7** (drift guard + direct-manipulation clarification) | "any further direct manipulation (drift test)"; "keystroke-level realtime co-editing a permanent non-goal" | Record the operator's **widening of the reference-app scope** to include direct text editing. The permanent non-goal narrows precisely: *keystroke-level CRDT co-editing* stays refused (the revision is the atom); *direct text manipulation committed as revisions* is now in scope. The drift guard reflects standing intent. |
| **STUDIO.md** §"What Studio is NOT" | "no keystroke-realtime co-editing · no WYSIWYG second write path" | Reworded: *no keystroke-realtime CO-EDITING (CRDT)* stands; the WYSIWYG line is replaced by *in-place editing lands as debounced attributed revisions through the one write door — not a second write path*. |

**Nothing about the invariants changes**: single-writer-per-path (ADR-286), the CAS door
(ADR-406), no merge/CRDT, the reference-render-never-embed guard (ADR-440 D5), attribution +
metering (unchanged — mechanical edits are free per ADR-396). The pivot is a **modality** added
over an **architecture** that already carried it.

---

## 7. The build (all Studio-owned)

1. **`projection.ts`** — an edit runtime, injected in `{pointer, edit}` mode:
   - toggle `contentEditable` on the selected `[data-block]` (the parent commands it via
     `postMessage`; the runtime enters/exits edit mode);
   - mark every `[data-ref]` inside an editable block `contentEditable=false` and stamp each with
     its **source outerHTML** (`data-src-html`) at projection time (the island rule, §2.2);
   - on `blur`/idle-2s, restore islands to their source form, read `{blockId, newInner}`, and
     `postMessage {type:'yarnnn-edit', blockId, newInner}` to the parent;
   - re-strip executables is unnecessary inside the runtime (the parent re-sanitizes on the source
     transform), but the runtime forbids paste-of-HTML by using `contentEditable="plaintext-only"`
     where supported, falling back to a paste sanitizer.
2. **`artifactOps.ts`** — `editBlockText(sourceHtml, blockId, newInner): OpResult | null`: parse
   source, find `[data-block-id="…"]`, replace its inner, serialize. Pure, id-preserving, in the
   exact shape of the existing ops (`artifactOps.ts:93-154`). Sanitize `newInner` (strip
   `script`/`on*`/`javascript:`) before insertion — the member's keys cannot inject executables.
3. **`StudioCanvas.tsx`** — accept an `editing` command + an `onEdit` callback; forward the edit
   `postMessage`; a small "Edit / Done" affordance (or double-click a block to edit).
4. **`StudioSurface.tsx`** — kill the auto-seed on `onPoint` (§4); add the explicit "Ask about
   this" on the chip; wire `onEdit` → `applyOp((html)=>editBlockText(html, blockId, newInner),
   "Studio: edit …")` — reusing the existing `applyOp` executor verbatim.
5. **posture** (`services/studio.py:335-338`) — widen the concurrent-writer clause: the member
   now also **edits text** directly between the lane's turns; re-read before editing, treat
   current content as truth, never renumber ids. **Prompt CHANGELOG** entry.
6. **gate** — extend `test_adr443_studio_model.py` (or a new `test_adr446`): assert
   `editBlockText` exists + is id-preserving + sanitizes; assert the edit runtime toggles
   `contentEditable` and restores citation islands; assert the seed-spam is gone (no unconditional
   `seedComposer` in `onPoint`); assert the explicit-ask affordance exists. Keep 58/58 + 43/43
   green. `tsc --noEmit` is the FE gate.

**The macro thesis holds and gets louder**: every edit — typed, clicked, or asked — lands as an
**attributed, versioned, traceable revision over living workspace references**. Direct editing
makes the moat MORE visible: History stays legible (debounced, well-messaged revisions), citations
stay references (the island rule guarantees it), the floor never moves (CAS + single-writer). The
bet vs Wix/Claude Design is not feature parity — it is that the Studio's WYSIWYG is the only one
whose every keystroke-burst settles into the system of record.
