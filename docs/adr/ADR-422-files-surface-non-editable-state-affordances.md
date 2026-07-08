# ADR-422: Files-Surface Non-Editable-State Affordances — One Grey Becomes Three Honest States

**Status**: Proposed (2026-07-08). FE-only, zero backend, zero schema. A Channel-dimension coherence pass on the Files surface: the single grey/`SYS` treatment for "you can't freely touch this" splits into three distinct, plain-language, macOS-Finder-native affordances, each derived from data already on every tree node. A concrete down-payment on the re-founding direction (ADR-384) — it makes the *current* six-root substrate legible to a layman without waiting on the meaning-folder re-homing.
**Date**: 2026-07-08
**Dimension**: Channel (Axiom 6 — what the operator sees and how, over the substrate the other axioms own)
**Relates to**: ADR-388 (the derived tree + shared file-row + attribution module this extends), ADR-400 (the two-principal Files surface + `operator_can_organize` reach + the "edit via chat, not in-app" boundary), ADR-376 (the `inbound/` raw lane whose immutability this finally surfaces), ADR-209 (the `authored_by` attribution chain the affordances read), ADR-384 (the re-founding — this is forward-compatible with it by construction, §6), ADR-410 D4 (the operator-facing-vocabulary discipline `SYS` violates)
**Amends**: ADR-388 (D3 attribution made legible → extended to three legibility *states*, not one author label), ADR-400 (the `operator_can_organize` carve gains a UI vocabulary — the carve was backend-authoritative but rendered as one flat grey)

---

## 1. Context — one grey for three different things

The Files surface today collapses every "the operator can't freely edit this"
case into a single visual treatment: a lowercase `sys` tag + a dimmed row.
The operator flagged this in a live walk (screenshot, 2026-07-08) against
Finder/Explorer: a layman cannot tell *why* a file is not-freely-editable, and
the one tag that does exist (`sys`) is developer vocabulary leaking onto an
operator surface.

The recon (2026-07-08) confirmed the surface conflates **three genuinely
distinct states** into that one grey:

| State | Example | What it actually is | What the operator should feel |
|---|---|---|---|
| **Machine-config** | `governance/_autonomy.yaml` | A settings file the system reads at an exact path; renaming/moving it breaks the reader (a filesystem-integrity fact, not a permission hierarchy) | "The system needs this here — tune it in Settings, don't hand-move it" |
| **Agent-authored** | a file `freddie:` / a hired agent / `yarnnn:mcp:*` wrote | Your file — you own and can reorganize it — but content is authored by an agent, edited through chat, not typed into in-app (the ADR-400 GitHub+Copilot boundary) | "This is agent work; you own it; edit it through chat" |
| **Raw intake** | `inbound/mcp/claude/inbox.md` | An immutable attributed observation of what arrived from the outside — retained forever, never rewritten (ADR-376 DP32) | "This is a record of what came in; it doesn't change" |

Three current gaps, all FE-only (recon receipts):

1. **The `sys`/dim heuristic is too coarse.** It triggers on *any*
   leading-underscore filename ([`WorkspaceTree.tsx:145`](../../web/components/workspace/WorkspaceTree.tsx#L145),
   `isSystemFile` = `_`-prefix alone), so a prose `_notes.md` gets the same
   "system" grey as `_autonomy.yaml`. The real carve is
   `operatorCanOrganize(path) === false` (`system/` OR `_*.{yaml,yml,json}`,
   [`ownership.ts:37`](../../web/lib/workspace/ownership.ts#L37)) — the coarser
   heuristic mis-labels prose.
2. **`inbound/` immutability is not modeled.** `operatorCanOrganize` has no
   `inbound/` carve, so the FE currently believes the operator can move/trash
   raw intake (the backend may 403). No "immutable/raw" indicator exists
   anywhere in the FE.
3. **The backend root glyphs are fetched then dropped.** `GET /workspace/roots`
   returns `icon` (a lucide name) + `semantic_class` per root (ADR-388 D1,
   `WORKSPACE_ROOTS` in [`workspace_paths.py`](../../api/services/workspace_paths.py#L167)),
   but `buildRootNodes` discards both ([`page.tsx:153`](../../web/app/(authenticated)/files/page.tsx#L153))
   — so `constitution`/`governance`/`contract`/`inbound` all fall back to a
   generic folder glyph, and the semantic class never reaches a row.

## 2. The decision in one sentence

**A file's not-editable state is a first-class, plain-language affordance
derived from `path` + `authored_by` (both already on every tree node) —
machine-config reads as system-managed, agent-authored reads as owned-but-agent-written,
raw-intake reads as immutable-record — replacing the single `sys`/grey
treatment; and the Files tree renders the backend-supplied meaning glyph +
semantic class it currently drops.**

No new backend data. No schema. No write-path or gate change. The three states
are already fully determined by fields the FE holds; it simply doesn't
distinguish them yet.

## 3. Decisions

### D1 — Three affordance classes, derived not stored

A shared helper (extending the ADR-388 attribution module) classifies every
file node into exactly one **legibility state**:

```
fileLegibilityState(node) →
  'machine-config'   if operatorCanOrganize(node.path) === false
                        (system/ OR _*.{yaml,yml,json})   ← the true carve
  'raw-intake'       else if node.path is under inbound/  ← immutable record
  'agent-authored'   else if authorClass(node.authored_by) ∈ {reviewer, agent, mcp, member, specialist}
  'operator'         else (authored_by = operator, or absent)
```

Precedence is deliberate: machine-config wins over raw-intake wins over
agent-authored (a machine-config file under `inbound/` — none exist today, but
the ordering is defined — reads as machine-config; an inbound file wins over
its `mcp:` authorship because immutability is the stronger operator fact).

Each state renders a **distinct, plain-language affordance** — glyph + optional
one-line "why" — replacing the single grey/`sys`:

| State | Glyph | Row treatment | "You can" (Get-Info) |
|---|---|---|---|
| machine-config | lock (muted) | dim, no `sys` word | "managed by the system" (existing `organizeBlockedReason` copy) |
| raw-intake | archive/down-arrow (muted) | dim | "a record of what came in — it doesn't change" |
| agent-authored | author badge (attribution module) | normal weight | "authored by {label} — edit via chat" |
| operator | none | normal | "move · rename · trash · edit via chat" |

The `sys` word is **deleted** (ADR-410 D4 — no developer vocabulary on an
operator surface); the glyph + Get-Info copy carry the meaning.

### D2 — `inbound/` immutability enters the organize model

`operatorCanOrganize` (the SINGULAR carve source, ADR-400 Amendment 1 —
[`workspace_paths.py:453`](../../api/services/workspace_paths.py#L453) backend +
[`ownership.ts:37`](../../web/lib/workspace/ownership.ts#L37) FE mirror) gains a
third carve: **paths under `inbound/` are not operator-organizable** (they are
immutable attributed observations — moving/renaming/trashing a record of what
arrived is a category error; the raw lane is reasoned-against-never-rewritten,
ADR-376). This is the FE catching up to a backend truth, and it must land on
**both** sides of the singular carve (the FE mirror AND the backend
`operator_can_organize`) so the surface and the gate agree. `organizeBlockedReason`
gains the raw-intake message.

*(Note: this is the one decision here that touches a backend file —
`workspace_paths.py::operator_can_organize` — but it is a carve-list addition,
not a gate/write-path/schema change. The recon flagged that the FE currently
*believes* it can organize intake; closing that on one side only would leave the
surface and gate disagreeing.)*

### D3 — The Files tree renders the backend meaning glyph + semantic class

`buildRootNodes` stops dropping `root.icon` and `root.semantic_class`. A small
icon resolver maps the backend lucide names (`scroll-text`, `shield`,
`file-signature`, `brain`, `folder-cog`, `arrow-down-to-line`, …) to rendered
glyphs. The existing `resolveSurfaceIcon` registry
([`surface-icons.tsx`](../../web/lib/shell/surface-icons.tsx)) is the wrong
namespace (kernel *surface* icons) and lacks these names — so this extends that
registry (or adds a sibling file-root resolver) with the `WORKSPACE_ROOTS`
glyph set. The path-string `if`-ladder in `WorkspaceTree.getFileIcon` for root
glyphs is retired in favor of the backend-supplied `icon` (the kernel names the
glyph, the FE maps it — ADR-388 D1's stated contract, finally honored).

This makes the current six-root substrate legible-by-glyph *today*, and is
forward-compatible with the re-founding: when roots are renamed to
meaning-folders (ADR-384), an un-mapped root still renders with its raw name
(ADR-388 §6) and its meaning glyph if the backend supplies one.

### D4 — Get-Info states the "why", macOS-plain

The Get-Info modal (ADR-388 D5, `NodeDetailsPanel`) already shows a "You can"
row and the `organizeBlockedReason` body. It gains a one-line **state
descriptor** at the top of the file properties — the plain-language sentence for
the file's legibility state (D1 table, right column) — so the *reason* a file is
not-freely-editable is stated where the operator looks for it, in object
language ("It's a settings file the system needs in this exact place"), never
mechanism jargon ("read by exact path"). This reuses the Amendment-2 macOS-plain
copy discipline (ADR-400 Amendment 2 §4).

## 4. What this does NOT do

- **No new backend data, no schema, no primitive.** The three states derive
  from `path` + `authored_by` already on the node + `semantic_class`/`icon`
  already in the roots response (currently discarded).
- **No gate/write-path change.** D2 adds one carve entry to the *organize*
  reach (which files the operator may move/rename/trash) — it does not touch the
  ADR-307 permission gate or `write_revision`.
- **No inline content editing.** The ADR-236/329/400 boundary stands: the
  operator never edits file *content* in-app; edit routes through chat. This ADR
  only makes *why a file is not-freely-editable* legible.
- **Does not pre-empt the re-founding.** It surfaces the *current* substrate
  honestly; when ADR-384 re-homes roots to meaning-folders, the derived tree +
  un-mapped-root fallback (ADR-388 D1/§6) carry it with no re-edit. The
  affordance classes (D1) key on `operatorCanOrganize` + `inbound/` + author
  class — all of which survive the re-homing (permission-as-metadata keeps the
  organize carve; `authored_by` is unchanged).

## 5. Cascade / blast radius

- **Frontend**: a `fileLegibilityState` helper (extends
  [`web/lib/workspace/attribution.ts`](../../web/lib/workspace/attribution.ts));
  `WorkspaceTree.tsx` (replace `isSystemFile` `_`-heuristic with the state
  helper; delete the `sys` word; render state glyph); `ownership.ts` (D2 carve +
  message); `buildRootNodes` in `files/page.tsx` (stop dropping `icon`/`semantic_class`);
  the root-icon resolver (extend `surface-icons.tsx` or a sibling);
  `NodeDetailsPanel.tsx` (D4 state descriptor).
- **Backend (one file, carve-list only)**: `workspace_paths.py::operator_can_organize`
  (+ `inbound/` carve, D2) so the FE mirror and backend agree.
- **Canon**: this ADR; GLOSSARY only if it names the `sys` tag.
- **Gate**: `api/test_adr422_files_legibility.py` — assert `operator_can_organize`
  returns False for an `inbound/` path (D2); the FE gate (extend
  `test_adr388`/`test_adr400` or a new FE assertion) that the `sys` word is gone
  and the three states resolve distinctly. `tsc --noEmit`.

## 6. Why this is the right down-payment now

The full re-founding (ADR-384 meaning-folders) is the deep fix for the
architecture-shaped tree the operator saw — but it is doc-first, unbuilt, and
gated behind an unscriptable per-workspace judgment step (ADR-384 §7 step 6).
This ADR ships the *legibility* half of the operator's complaint with zero
substrate risk, using data that already exists, and by construction survives the
re-founding rather than racing it. It is the Files-surface analog of ADR-388's
own reasoning (§6): make the surface correct-by-construction across the
re-founding instead of after it.
