# ADR-571: The Text app — a dedicated surface for the prose currency

> **Status**: **Accepted** (2026-08-14, operator-corrected re-cut of ADR-570's
> housing, directed in-session: *"my understanding was that it is a dedicated app.
> just like docs. that's why i asked to mimic docs app in full"* — names chosen by
> the operator: app **Text**, colleague **Editor**).
> **Date**: 2026-08-14
> **Dimension**: **Channel** (a new kernel surface + bound lane) primary;
> **Identity** (an app-named colleague over an existing resident) secondary.
> **Relates to**: ADR-570 (the doors, CAS spine, and chat seam all CARRY — only the
> housing is re-cut), ADR-456 D1 (still honored: the *Docs canvas* never absorbs md;
> a separate app owning the type is exactly "an app decision"), ADR-518 (Docs — the
> shape being mirrored), ADR-562 (resident declared in the app's own module; engine
> follows the resident), ADR-567 D4 (lane_meta.app selects the job overlay),
> ADR-486 D7 + ADR-297 (surface registration + parity), ADR-514 D2 (Open With —
> Preview stays one click away), ADR-550→551 (the precedent this follows: an
> operator-corrected reversal recorded as its own ADR, same week).
> **Amends**: ADR-570 D1/D2 (housing): the editor is no longer an inline app in
> Files — the `markdown.editor` registry row and its selection plumbing are DELETED
> (singular implementation). ADR-570 D3's re-cut of "never edits" survives in
> spirit: mutation lives in chat and in app SURFACES (Docs · Studio · Text), never
> in a viewer.

---

## 1. Context — the correction

ADR-570 shipped the markdown editor as an inline app inside Files (Open With ▸
Editor). The operator's instruction — *"mimic and cross reference the existing docs
APP … even the chat agent should also be the same naming"* — had been read as
conventions-parity; it meant **shape-parity**: a dedicated app in the switcher,
like Docs, with a landing, its own param, and a resident colleague beside the
canvas. The ADR-550→551 lesson applies verbatim: the mechanism was live and the
housing was wrong, and those come apart cleanly. Everything below the housing —
the widened member write door, the CAS/409 spine, the chat linkification — carries
unchanged.

## 2. Decisions

### D1 — The Text app: a kernel surface, Docs-shaped, unveiled at birth

Slug `text`, title **Text**, route `/text`, archetype `document`. The surface has
two states, mirroring Docs: a **landing** (recent prose documents from the
workspace revision feed, deduped by path and filtered to the prose class, plus a
New gesture that creates `Documents/{slug}.md` through the ADR-570 member door)
and an **open state** — the markdown editor as the canvas, with the bound lane
rail beside it. The `text.file` param follows the Docs pattern (owned, restored on
launch, written back on open/close). Unlike Strings' search-only start, Text ships
`launcher_tier: primary` with a Dock row and a new dock-reseed generation — the
operator's correction *was* the unveil decision.

### D2 — The type claim: Files hands `.md` to Text the way it hands `.html` to Docs

`resolveSurfaceApplication` claims the prose class (`.md`/`.markdown`/`.txt`,
excluding arrivals under `inbound/` and `_`-prefixed leaves) for the Text surface.
Opening a prose file anywhere in Files launches Text on it; **Preview stays one
Open With away**, and the ADR-514 per-file override can re-pin it. The ADR-570
inline `markdown.editor` app is **deleted** — registry row, FileBody selection
plumbing, ContentViewer threading — because the editor now has exactly one home.
The full-list `inlineHandlers` generalization stays (it is correct independent of
this app). This answers ADR-456 D1's motivating question literally: MANDATE.md
opens in a nice editor — the Text app, under the same principal-gated door.

### D3 — The colleague: Editor, an app name over the designer resident

`register_app("text", resident="designer", name="Editor")` — the exact Docs/Writer
shape (ADR-562: name over an existing resident, no new agent row; the engine
follows the resident, server-side). "Writer lives in Docs; Editor lives in Text."
The Keeper path (a new KERNEL_POSTURES row) is consciously NOT taken: Editor's
character IS the writing character; only the name differs. The bound lane is the
same two-field call every app uses (`{name, app: 'text', artifact_path}`); the
roster needs no edit — residency IS the roster (ADR-562).

### D4 — The lane posture: a Text branch, because the studio fallback would lie

A bound lane with no app branch falls through to `build_studio_posture`, which
lifts `data-template` from the artifact — an `.md` has none, silently resolves to
`document`, and the colleague would be handed an HTML-block contract for a
markdown file (the exact hazard ADR-570's scoping flagged; the reason radar and
strings each have a branch). `lane_meta.app == "text"` selects
`build_text_posture` (in `services/apps/text.py`, beside the registration): the
job is THIS document — read it fresh, refine it conversationally, whole-file
honest writes through the substrate primitives, `derived_from` when authoring from
sources. No block grammar, no Studio machinery.

### D5 — What carries from ADR-570, untouched

The member write door (prose class ∧ carve law ∧ principal gate) and its
`head_version_id` return; the studio door's principal-gate repair; CAS + the
409-names-who-moved conflict surface (now inside the Text canvas); the chat-seam
linkification (a chat link lands in Files, whose open funnel now routes prose to
Text — the round-trip ends in the app).

### D6 — Falsifiers / click-pass

(1) Text appears in the launcher and Dock; `/text` renders landing → recents →
open. (2) Opening an `.md` from Files lands in Text with the Editor lane bound;
the speaker label reads **Editor** (served from the app registration, never
asserted client-side). (3) A save lands attributed with a new head; a concurrent
MCP edit makes the next save 409 with the connector's attribution. (4) New creates
`Documents/{name}.md` and opens it. (5) Preview via Open With still renders inline
in Files. (6) The ADR-297 three-way slug parity and ADR-562 config gates stay
green.

## 3. Not done / not changed

- **Docs stays HTML-native** — no md in the Docs canvas, no conversion (ADR-456 W4
  still deferred).
- **No block model, ever, in Text** (ADR-456 D1's grade constraint holds).
- **No csv/json claim** — the table viewer keeps csv inline; machine formats keep
  their doors.
- **No new agent row** (D3 — name over resident).
