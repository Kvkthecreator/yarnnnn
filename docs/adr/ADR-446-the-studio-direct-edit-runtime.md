# ADR-446 — The Studio direct-edit runtime: editing the projection, writing the source

> **Status**: **Accepted** (2026-07-12, operator-commissioned as a full re-approach of the
> selection→chat-seed model). The operator's verdict: the seed-the-chat model is "only partially
> right… we need to think closer to a webpage editor like Wix — select and edit ON SCREEN, IN
> REAL TIME." This ADR makes the Studio canvas a **sanctioned editor mount**: the member edits
> block text in place; the edit maps back to the artifact's SOURCE (never the projected DOM) and
> lands through ADR-444's mechanical write door as a debounced, operator-attributed, CAS-guarded
> revision. It also kills the selection→composer auto-seed spam. Derivation:
> `docs/analysis/the-studio-direct-edit-projection-to-source-2026-07-12.md`. Living design doc:
> `docs/design/STUDIO.md`.

**Date**: 2026-07-12
**Dimension**: Mechanism (the member's keys drive a mechanical transform) + Channel (the canvas
becomes an editor, not only a viewer) + Substrate (every edit is one attributed revision).

**Amends**: ADR-236 (the mount contract's "apps render, never edit" letter) · ADR-443 D2
(TRANSFORM's mechanical half gains direct text editing) · ADR-444 D1 (the mechanical write path
gains a keys-fed input) · ADR-440 §7 (records the operator's widening of the reference-app scope;
narrows the "keystroke-realtime" non-goal to CRDT co-editing only).
**Preserves**: single-writer-per-path (ADR-286) · the CAS door / no-merge (ADR-406) · one
attributed write door (ADR-236's *point*) · reference-render-never-embed (ADR-440 D5) · the block
model / grammar-not-schema (ADR-443) · free-because-no-LLM mechanical class (ADR-396).

---

## D1 — Direct text editing is a mechanical TRANSFORM fed by keys

The Studio has two write paths (ADR-444 D1): the **judgment path** (the bound lane — content,
rewrites, restructures, cites; metered) and the **mechanical path** (deterministic FE DOM ops →
`POST /studio/artifacts/write`; free). This ADR adds an input to the mechanical path: **the
member types in a block, and the keystroke-burst becomes one deterministic transform** on the
artifact's source, landed through the same door as an operator-attributed, CAS-guarded revision.

This is not a second write path — it is the ADR-444 path with keys instead of buttons. ADR-236's
letter ("apps render, never edit") is amended; its point — *no silent second write path;
everything lands attributed through one door* — is upheld exactly.

## D2 — Editing the projection, writing the source (the load-bearing rule)

The canvas renders a **projection**, not the artifact source: `resolveArtifactHtml(html, path,
{pointer:true})` resolves `data-ref` citations into displayable content (blob URLs, tables,
`<pre>`), strips executables, and injects the pointer runtime
(`web/components/workspace/viewers/projection.ts`). **A direct edit must NEVER serialize the
projected document back to the file** — that would bake resolved citations into copies (destroying
the living-reference thesis, ADR-440 D5), lose stripped content, and serialize the injected
runtime.

Instead, an edit is a **source-mapped transform**:

1. The runtime emits `{data-block-id, new inner content}` from the edited block in the projection.
2. The FE applies that to the artifact's **SOURCE** html — a pure `artifactOps`-style transform
   (`editBlockText(sourceHtml, blockId, newInner)`) that finds the same `data-block-id` in the
   file content and swaps its inner.
3. The transform **sanitizes** `newInner` (strips `script`/`on*`/`javascript:`) — the member's
   keys cannot inject an executable.
4. It lands through `POST /studio/artifacts/write` with CAS (`expected_parent_version_id`).

The **`data-block-id` is the join key** between projection and source (ADR-443 R1: the DOM is the
model; the projection preserves block annotations, resolving only citation *contents*). This is
why blocks landed before tweaks (ADR-443): a keystroke, like a gesture, wants a block to aim at.

## D3 — The citation-island rule

A block may contain a citation (ADR-443 R3). Inside an editable block the projected citation is a
**resolved copy**; typing must not be able to alter or bake it. Therefore:

- every `[data-ref]` inside an editable block is `contentEditable="false"` (the caret cannot
  enter it);
- at projection-in-edit-mode time, each citation element is stamped with its **source outerHTML**
  (`data-src-html`) — because by render time its content is resolved and its source form is not
  otherwise recoverable from the projected DOM;
- on commit, the runtime **restores each island to its source form** before reading the block's
  inner, so the emitted `newInner` carries the citation in its living-reference markup, never its
  resolved bytes.

A text edit therefore never touches a cited source or bakes a reference — it edits only the prose
around the islands. The 80% case (a figure block with an editable caption) works: caption
editable, figure inviolate.

## D4 — The commit atom (debounce): the revision, never the keystroke

The revision is the atom; there is no CRDT, ever (ADR-406/286). A keystroke-burst becomes one
revision on **`blur` (member leaves the block) OR idle-2s within a block, whichever first**. A
byte-identical (no-op) edit commits nothing. "Real time" means the manipulation *feels immediate*
(you type in place, you see it) — NOT keystroke-level co-editing. One editing session on one block
→ one revision → one legible History entry ("Studio: edit prose block b7").

Interleaving is the unchanged CAS contract: if the lane or a toolbar op wrote while the member
typed, the commit's `expected_parent_version_id` is stale → 409 → the canvas reloads; the in-flight
edit is lost (correct under single-writer-per-path — no merge). The 2s idle cap bounds the loss to
at most one idle window. Text editing inherits the exact contract the toolbar already lives under.

## D5 — Selection is for editing + toolbar ops; the lane hears it only on explicit ask

The pointer runtime (click → select the nearest `[data-block]`) stays — selection anchors the
toolbar's mechanical ops and now gates edit mode (select a block, then edit it). The
**auto-seed of the selection into the chat composer is removed** (it produced the operator's
observed seed-append spam: `"Selected the h2…: Selected the p…: "` piling up). The lane hears about
the selection **only on an explicit "Ask about this" affordance** on the selection chip — one seed,
on purpose. A click now *selects*; it does not narrate to chat.

## D6 — Scope: text now, geometry later

- **Ships**: in-place text editing of block content (headings, paragraphs, list items,
  callout/quote/checklist text, figure captions) — one block → one `editBlockText` → one revision;
  the citation-island rule; the debounce; the seed-spam kill + explicit-ask.
- **Deferred, unchanged from ADR-444/440**: style/geometry tweaks (the tweak-inspector /
  gesture-composer, now properly block-grained) · publish/pins · desktop tile · the engineer-agent
  hire. Layout flow containers (a slide, `<main>`, `<article>`) are structure, not blocks — you
  edit the blocks inside them, which falls out for free (only `[data-block]` becomes editable).

## Consequences

- **Positive**: the Studio's WYSIWYG becomes real without a second write path, a shadow model, a
  merge layer, or new attribution/meter/schema; direct edits are the finest-grained,
  best-attributed revisions in the benchmark class; the moat becomes *more* visible (every
  keystroke-burst settles into the system of record with a legible History message); the seed spam
  is gone and the click's meaning is unambiguous.
- **Cost**: an edit runtime in `projection.ts` (contentEditable toggle + island stamp/restore),
  one pure `editBlockText` transform, `StudioCanvas`/`StudioSurface` wiring, a posture line, a
  CHANGELOG entry, a gate extension. No backend change (the mechanical door already accepts full
  HTML with CAS).
- **Risk**: low — the transform is pure and reversible (revisions); CAS prevents lost updates;
  the island rule + `newInner` sanitize keep citations and executables safe; a projection/edit
  failure falls back to the lane (chat) which is untouched.

## The one-line statement

**The member edits block text on the canvas and it feels immediate, but the edit maps back through
the block's id to the artifact's SOURCE — citations restored to their living-reference form,
executables stripped, the burst debounced into one operator-attributed CAS-guarded revision — so
the Studio gains a real WYSIWYG that is still, keystroke for keystroke, the only editor whose every
change settles into the system of record.**
