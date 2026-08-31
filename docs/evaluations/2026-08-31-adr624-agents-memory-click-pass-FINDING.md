# ADR-624 click-pass — the being's memory, driven in production

**Date**: 2026-08-31 · **Build**: `a520cbd` (API deploy `dep-daaiv66q1p3s739a3rn0`, live)
**Principal**: `kvkthecreator@gmail.com` (owner), workspace `d5b9029b…`
**Lane**: surface (`browser`) — read PASS/FAIL per step, both halves per step.

---

## Verdict

**The ADR-624 claim PASSES end to end.** A being's memory is ordinary substrate:
written through the one write path, attributed, versioned, and opened in the
workspace's own editing face from a door on the being's page.

**Two defects found, BOTH PRE-EXISTING and neither caused by ADR-624.** One is
a real discoverability problem that this ADR's feature is the first to expose.

---

## What passed

| # | Step | DOM half | Substrate half |
|---|---|---|---|
| 1 | `memory_path` is served | — | ✅ `/api/lanes` returns `/workspace/agents/{slug}/memory/` for **editor** and **supervisor**; `home_titles` + `desks` also present (the type drift this ADR fixed) |
| 2 | The Memory row renders | ✅ `/agents?agent=editor` shows **Memory → "What Editor has learned"** with the substrate framing beneath | — |
| 3 | The door opens Files at the right place | ✅ click → `/files?…files.path=/workspace/agents/editor/memory/`, breadcrumb `memory`, path line `agents/editor/memory/` | — |
| 4 | A real memory write lands | ✅ appears in Recents as "just now" | ✅ revision `f0ab61cd`, `authored_by=member:2abf…`, `revision_kind=authored`, `parent_version_id=None`, `lifecycle=active` |
| 5 | Memory reads in the ONE editing face | ✅ opens in **Text** — heading, body, `agents/editor/memory/notes.md`, FORMAT ("stays a `.md` file — the same one your connectors read and write"), "Every save is signed and revertible" | ✅ `count_revisions=1`, `list_revisions` returns the row |

Step 5 is the ADR's D4 claim proven: **no private memory renderer.** The file
lands in Text like any other `.md`, which is what "ordinary substrate" has to
mean to be true.

Confinement (D3) was falsified in the gate rather than the browser, and
correctly so: no live caller is `agent`-class-with-a-slug today (a lane is
`member:{id}` → class `operator`), which is the seam the ADR already records.

---

## Defect 1 — a being's home is filed under "System files" (PRE-EXISTING)

**Severity: real.** This is the one worth acting on.

`WORKSPACE_ROOTS["agents"]` declares `group: "system"`
(`api/services/workspace_paths.py:322-329`), and the Files explorer folds every
`system`-group root under one collapsed **"System files"** disclosure. So:

- The Explorer spine shows Documents · Design System · Marketing · Downloads ·
  System files. **No `agents` node** until "System files" is expanded.
- Expanding it reveals Constitution · Governance · Persona · **Agents** · System,
  and `Agents → editor → memory → notes.md` then works perfectly (`1 item` at
  each level).

**Why it is not an ADR-624 regression**: the grouping predates this ADR, and the
row's own description is still ADR-414 language — *"Per-agent homes (the Rung-2
judgment seats, when present)"* — i.e. it was filed as kernel residue for a
model with zero instances. That was defensible when nothing lived there.

**Why it now matters**: ADR-624 D1 makes `agents/{slug}/memory/` a place the
member is invited to *read and correct*, and the surface copy says so ("yours to
read or correct"). A folder the member is told to visit should not be filed
under machine residue. The being's page links straight to it, so the door works
— but a member browsing Files will not find it, and the two halves of the
product disagree.

**Scope decision, deliberately NOT taken here**: moving `agents` out of the
`system` group is a Files-taxonomy change affecting the explorer spine for every
workspace, and it interacts with the grant sidecars in the same folder (which
*are* machine config and arguably belong hidden). The honest options are (a)
regroup `agents` to `work`, (b) keep the root hidden but surface
`agents/{slug}/memory/` specifically, or (c) leave it and rely on the being's
page as the only door. Recorded for a scoped decision rather than changed as a
side effect of this ADR.

---

## Defect 2 — "No revisions yet." on a file that has one (PRE-EXISTING, KNOWN)

The Text properties panel showed **LAST EDITED — No revisions yet.** for the
memory file, while `count_revisions` returned 1 and `list_revisions` returned
the row.

**Not path-specific, and already documented in the code**:
`web/components/text/TextEditor.tsx:298` and `:330` describe this exact symptom
from a prior production measurement (*"Properties reading 'No revisions yet.' on
a file with four revisions"*, and a case on
`/workspace/seulki/babo-song-concept.md`). A control file
(`marketing/strategy/blog-status-…md`, 2 revisions) rendered its author
correctly once fully loaded, so the panel resolves given time — the memory file
was observed mid-load.

**Verified not ADR-624's**: the backend readers return correct data for both
files; nothing in this ADR touches the revision fetch.

---

## Method notes (for the next pass)

- The `/api/lanes` **response body file contains a live JWT** in its request
  headers. Extracted the payload and deleted the file in the same command.
  (The playbook's standing warning; it bit again.)
- **Deep-links to a file race the roots load.** Navigating straight to
  `?files.path=<file>` lands on Recents until `/api/workspace/roots` and the
  per-root `/tree` calls settle, then resolves (URL gains `text.file=`). Two
  early observations here were mid-load states, not defects — re-checked before
  reporting. A single-shot deep-link check would have produced a false finding.
- A **single click selects, double-click enters** in the Files grid.

---

## Live artifact noticed, not acted on

`/workspace/agents/lisa/_agent.yaml` still exists in production substrate — the
member-agent model ADR-599 D2 deleted the machinery for. Substrate is correctly
never deleted by a surface's retirement, so this is not a bug; it is a stale
file worth an operator decision, and it will show up under Agents the moment
Defect 1 is addressed.
