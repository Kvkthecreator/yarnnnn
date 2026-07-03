# ADR-400 — The Two-Principal Files Surface: a GitHub-repo browser, not a Finder

> **Status**: **ACCEPTED** (ratified by KVK 2026-07-02). Implementation in progress — all four tiers in one pass. §7 open questions resolved: **Q1 rename = YES** (operator verb, root-scoped); **Q2 = menu-first** (right-click "Move to…"; drag-and-drop a fast-follow); **Q3 = NO empty-trash** (ADR-209 retain-everything — Trash is a view, archived is permanent-but-hidden); **Q4 = full attribution** (reuse the ADR-388 attribution module — a file ChatGPT wrote shows as such).
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6 — how a human perceives + acts on the substrate) primary; **Mechanism** (Axiom 5 — the operator-verb permission carve) + **Substrate** (Axiom 1 — Layer 1 made operable, not just legible) secondary.
> **Discourse base**: the operator's Phase-1 reframe — *"now that we've shifted from a fused agent+filesystem model to Phase 1 being the filesystem + shared memory, the Files surface needs to be even closer to a macOS/Windows Explorer: not just list (read), but relocate (move), delete (to a trash can, not erase), for non-text too. I don't think we modify in-app yet — that's what Freddie is for. We're more like GitHub + Copilot."*
> **Amends**: [ADR-329](ADR-329-files-as-first-class-work-legibility-surface.md) — extends the five-verb operator law with **`move`** (operator-relocate, topology-scoped) and ratifies the **Trash surface** as the visible, reversible home of the delete verb ADR-329 already made `archive-not-erase`. The ADR-329 "one-line UX law" is widened, not overturned: *the operator adds, moves, and deletes their **own** material; the system authors, edits, and indexes; everyone reads — and reading includes seeing who owns and authored what.*
> **Builds on**: [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) (the multi-principal commons — this ADR is that commons made concrete at the file surface: two actor-classes, human + agents, visibly distinct) · [ADR-320](ADR-320-constitution-region-topological-cut.md) (the caller×root permission topology — the operator's move/delete authority is the operator-owned prefix, nothing more) · [ADR-337](ADR-337-file-layer-verb-completion.md) / [ADR-339](ADR-339-file-verbs-recursive-list-and-exact-search.md) (the `MoveFile`/`DeleteFile`/`EditFile` primitives — **already shipped**; this ADR *surfaces* them, it does not build them) · [ADR-307](ADR-307-unified-permission-taxonomy.md) (the one gate every operator verb still flows through).
> **Preserves**: ADR-236/ADR-329 **no-inline-edit** (the operator never edits file *content* in-app — edit intent routes through the chat/Freddie surface; this is the GitHub+Copilot boundary, ratified, not touched) · ADR-209 authored-substrate (every move/delete is an attributed revision; delete is a tombstone, reversible).

---

## Amendment 2 (2026-07-03) — the interaction layer: universal action-feedback + native Move (Q2 fast-follow landed)

**The gap.** Amendment 1 got the *reach* right, but the verbs shipped with browser-native interaction: `window.alert` / `window.confirm` / `window.prompt`. The operator flagged five things on the live surface: (1) the right-click menu rendered **transparent**; (2) event handling was **blind** — no toast, no loading state, no success feedback; (3) "Move to…" was a **raw `/workspace/…` path text input** ("users will find that discussing"); (4) Trash worked but needed the same polish; (5) the machine-config carve warning was **too technical**. The operator's directive: fix it **universally, not Files-only, so it expands elsewhere.**

**The correction:**

1. **The transparent menu was a design-token bug, not a Files bug.** The theme defined only 7 color tokens; `FileContextMenu` used `bg-popover` / `hover:bg-accent` / `text-destructive` — all undefined → transparent. Fixed by adding the shadcn-standard overlay/interactive token set (`popover`, `card`, `accent`, `destructive`, `success` + foregrounds, light+dark) to `globals.css` + `tailwind.config.ts`. This is an app-wide fix — any overlay/menu/danger UI now has real tokens.

2. **A universal action-feedback layer replaces the browser dialogs** — `web/contexts/FeedbackContext.tsx` (`useFeedback()` → `toast` / `confirm` / `runAction`), mounted once at the authenticated-shell root. `runAction` is the "not blind" primitive: a pending→success/error toast around any async op. Canon: **`docs/design/ACTION-FEEDBACK.md`** — the singular design doc, so future dev doesn't hand-roll a second toast system or reach for `window.confirm`. **This is the reusable payoff** — connectors, settings, agent grants adopt the same layer next.

3. **Move + Rename become modals, not prompts (Q2 RESOLVED — menu-first AND drag-and-drop shipped together).** "Move to…" opens a **folder-picker modal** (`MoveToFolderModal` — a destination tree, folders only, disabled where the operator can't organize) — the operator never types a path. Rename opens a **single-field modal** (`RenameModal`). And the ratified Q2 fast-follow — **drag-and-drop** — landed in the same pass: a file dragged onto a folder in the left tree moves it (`WorkspaceTree` `onMoveByDrag`, drop-highlight, ownership-gated on both ends). Drag is the fast gesture; the folder-picker is the deliberate/accessible path. **Grid drag-drop remains a later fast-follow** (tree is the primary folder-structure target).

4. **The carve message is macOS-plain** — `organizeBlockedReason` returns `{ title, body }` object-focused, no mechanism jargon ("It's used by the system to keep your workspace running" / "It's a settings file the system needs in this exact place" — not "read by name / would break the reader").

5. **Trash + the ContentViewer inline delete route through the same layer** — Restore and delete now use `runAction` + the styled `confirm` (danger treatment), not `window.confirm` / `window.alert`.

**What Amendment 2 does NOT change:** the operator-reach policy (Amendment 1's `operator_can_organize` is untouched — backend-authoritative), the no-inline-content-edit boundary (edit is still agents-through-chat), trash-not-erase, full attribution. This is purely the **interaction layer** — how the already-correct verbs feel.

**Canon touched:** new `docs/design/ACTION-FEEDBACK.md` (the singular feedback-layer doc). Amendment 2's law: *the operator's file verbs feel native — a styled menu, a folder-picker (or a drag), a pending/outcome toast, a plain-language block — all through ONE app-wide action-feedback layer, never a browser dialog.*

---

## Amendment 1 (2026-07-02) — operator reach is the BACKEND policy, not `uploads/`-only. D3 corrected.

**The error.** The original D3 scoped the operator's move/delete/rename to operator-*authored* material only (`uploads/` + `inbound/uploads/`), showing every other file as "Managed by Freddie — edit through chat" with disabled/greyed verbs. That was **wrong on first principles**, and the operator caught it: *"why can't the user move and delete — these should be possible. Back to first principles and service philosophy."*

**Why it was wrong.** It conflated two different locks. ADR-320's topology lock protects the workspace from **foreign principals** (an MCP caller, an agent) writing where they shouldn't. The original D3 mis-applied that same lock to **the human operator in their own workspace** — inverting who serves whom. It's the operator's filesystem; Freddie is labor acting *for* them. `PRECEDENT.md` / `IDENTITY.md` are the operator's *own* constitution + persona, not OS files protecting the system from the user. And because delete is trash-not-erase (reversible tombstone) and move is an attributed revision, letting the operator organize their own substrate is **safe** — nothing is destroyed.

**The receipt.** The backend was already correct. `workspace_paths.CALLER_WRITE_POLICY['operator'] = ('system/',)` — the human is locked from *only* `system/` (runtime orchestration state); the canon comment says verbatim *"operator — the human. Writes everything except system/... including governance/."* And the runtime gate gives the operator a blanket free-pass (`resolve_permission → APPLY "non_freddie_caller"`), so the enforced reality is even more permissive. **The `uploads/`-only restriction lived ONLY in the ADR-400 FE + the new move/delete/restore routes I added** — a surface over-restriction contradicting the backend's own policy.

**The correction (D3 reversed):**

1. **One source of truth = the backend operator policy** (`CALLER_WRITE_POLICY['operator']`, locking `system/`). The FE + the move/delete/restore routes **mirror it** — no separate FE scope list, no invented `_OPERATOR_ARCHIVABLE_PREFIXES` narrowing. The operator can move/rename/trash **any file except `system/`** (runtime state that is not hand-edited).
2. **`_*.yaml` / `_*.json` machine-config carve** — these are read by code at an **exact path** (the scheduler reads `_budget.yaml`, the gate reads `_principles.yaml`); renaming or moving one breaks the reader. So they stay non-movable/non-renamable — **not** as a permission hierarchy, but as a **filesystem-integrity rule** (don't rename a file another program finds by path). Delete-to-trash of a `_*.yaml` is likewise disallowed for the same reason. This is the ONE carve on top of the backend policy.
3. **Optimistic FE + honest error (the Windows-Explorer model)** — the FE does **not** defensively grey/hide the verbs. It lets the operator *try*, and if the backend restricts it, surfaces a clean modal/alert ("This file is managed by the system and can't be moved/renamed") — exactly like Explorer telling you a file is in use or protected. No greyed-lock clutter; optimistic UI, backend-authoritative, honest failure.
4. **The context menu belongs on the MAIN PANEL, not just the left tree** — the operator right-clicks files where the file thumbnails are (the RecentsView icon grid + the ContentViewer folder listing), matching the macOS/Explorer reference. The current implementation wired the full menu only to the left tree; the main panel had Properties-only (or nothing). The verb menu is extracted to a shared component and mounted on every file surface (Singular Implementation).

**What still holds from the original ADR-400:** the GitHub+Copilot two-principal *framing* (§2), no-inline-content-edit (edit is authoring, stays agents-through-chat), trash-not-erase + Restore (D4/D8), full attribution in Properties (D6), Rename as an operator verb (Q1). Only the *scope* of the operator's organize-verbs (D3) is corrected — from "own material only" to "everything except `system/` + machine-config, backend-authoritative."

**The corrected one-line law:** *the operator organizes (move/rename/trash) their whole workspace except the runtime state and the machine-config code reads by path; the agents author + edit content; the surface lets the operator try and reports honestly when the backend restricts — it does not pre-judge.*

*(Sections 2–7 below are the ORIGINAL ratified text, preserved as history. Where they say "operator-owned roots / topology-scoped to `uploads/`", read the Amendment-1 correction above: operator reach = backend `CALLER_WRITE_POLICY['operator']` + the `_*.yaml` integrity carve.)*

---

## 1. Why this ADR — the metaphor was wrong, and the gap is a *surface* gap

**The metaphor correction.** ADR-329 reached for "Finder." But a Finder is **single-actor**: the human is the only one who touches the files, so move/delete/rename are all human and all direct. YARNNN's filesystem is **two-principal** (ADR-373): the human *and* the agents (Freddie, program agents) both act on the substrate. A pure Finder would have to *hide* that second actor — and the second actor (attributed authorship + a judgment agent editing on your behalf) **is the entire differentiation**. Hiding it to feel like Finder throws away the moat at exactly the surface where it should be most visible.

The right metaphor is **GitHub + Copilot**:

- **You (the human)** browse the repo, read every file **with full provenance** (blame / revision history — the moat made visible), and organize *your own* material: add files, move them, send them to trash.
- **The agents (Copilot / Freddie)** are the ones who *author and edit* content. You don't hand-edit files in the browser; you route intent through the agent.
- **The surface shows the division** — who owns what, who last touched it, and *why a given verb is or isn't available here* (GitHub's "you don't have write access to this path" made friendly).

This is Explorer-**familiar** in chrome (a tree, an icon grid, right-click menus, a trash) but GitHub-**souled** in semantics (two principals, provenance-first, agent-authored). It is the honest surface for the Phase-1 "the filesystem *is* the product, operated by humans AND agents" thesis.

**The gap is a surface gap, not an engine gap.** The verbs already exist:

- `MoveFile`, `DeleteFile`, `EditFile` are shipped primitives (ADR-337/339), each flowing through the ADR-307 gate and the ADR-320 topology lock.
- `DeleteFile` → `authored_substrate.delete_live_file` is **already trash-not-erase**: it writes a tombstone revision (who deleted, when, why, and the file's current blob), so the file is recoverable. The upload-delete route already sets `lifecycle=archived`, ADR-209-retained, reversible.

So "move to trash rather than erase, keeping the readable + actual file" is **already the substrate behavior**. What's missing is the **human surface** that (a) exposes move, (b) shows the trash + offers restore, (c) offers the right-click affordances a file explorer has, and (d) makes the two-principal ownership legible. This ADR ratifies that surface.

---

## 2. The two-principal verb model (the ratifiable law)

Extends the ADR-329 verb table. **New/changed rows in bold.**

| Verb | Who acts | How (human surface) | Substrate effect |
|---|---|---|---|
| **read** | human + agents | human browses; agents call `ReadFile` | none — reading **includes provenance** (authored-by + revision chain; ownership badge) |
| **add** | **human** | upload affordance on Files | `write_revision` to the operator-owned lane (`inbound/uploads/`), attributed `operator` |
| **move** *(NEW)* | **human** *(own material)* + agents | **"Move to…" (right-click / menu / drag) on operator-owned files** → the existing `MoveFile` primitive; agents move as part of placement/derive | attributed revision (removal at old path + write at new); **topology-scoped** — see §3 |
| **delete → trash** *(surfaced)* | **human** *(own material)* + agents | **"Move to Trash" on operator-owned files**; a **Trash view** lists archived files + **Restore** | `lifecycle=archived` tombstone revision — **reversible**, blob retained (ADR-209) |
| **edit** | **agents only** | human routes intent through chat → Freddie/`WriteFile` (`EditInChatButton`, never a text field) | attributed revision — **the human never edits file content in-app** (ADR-236/329 preserved) |
| **index** (embed) | **agents only** | `Embed` primitive, autonomy-gated | derived Layer-2 index; never a human button |

**The widened one-line law:** *the human adds, moves, and deletes their **own** material and reads everything with provenance; the agents author, edit, and index; the surface shows who owns what and why a verb is or isn't available here.*

The delta from ADR-329 is exactly **`move` added as a human verb** (topology-scoped) and **the trash + restore made a first-class surface**. Everything else is ADR-329 verbatim.

---

## 3. Topology is the guardrail — the human moves/deletes only what the human owns

The GitHub analogy is also the *safety* model. On GitHub you can't `rm` a file you don't have write access to; here the human can't trash a file the *system* authored. This is not a limitation to apologize for — it is the **permission topology made legible** (ADR-320), and it is the second half of the moat's frontend payoff (ADR-329: "attribution *and* permission topology, made legible").

- **Operator-owned roots** (movable + trashable by the human): `/workspace/uploads/` (legacy) + `/workspace/inbound/uploads/` — the exact `_OPERATOR_ARCHIVABLE_PREFIXES` already enforced by the delete route + the FE `OPERATOR_DELETABLE_PREFIXES` constant. Move destinations for the human are likewise restricted to operator-owned roots (you can reorganize *your* uploads; you can't move a file *into* `governance/`).
- **System-owned files** (constitution, governance, persona, operation, agent context): the human's Move/Trash affordances render **disabled with a reason** — "Managed by Freddie · edit through chat" — not hidden. Legibility over concealment: the human *sees* that the agent owns it, which teaches the two-principal model rather than faking a flat filesystem. (An agent, acting through the gate, can still move/edit these — that's its job.)
- **No new write authority.** Every human move/delete flows through the *existing* ADR-307 gate + `_is_path_locked` topology. This ADR grants the human **zero** power they didn't already have at the primitive layer — it only *exposes* the operator-scoped slice of it. A locked root stays locked; the gate is unchanged.

---

## 4. Decisions (proposed — for operator ratification)

| # | Decision | Proposed |
|---|---|---|
| **D1** | Metaphor | **GitHub-repo browser (two-principal), not Finder (single-actor).** Explorer-familiar chrome, provenance-first + agent-authored semantics. |
| **D2** | Operator verb set | Add **`move`** (operator-relocate) to the ADR-329 operator verbs; keep add + delete; **preserve no-inline-edit** (edit is agents-only, through chat). |
| **D3** | Move/delete scope | **Topology-scoped to operator-owned roots** (`uploads/` + `inbound/uploads/`). System files show disabled affordances **with a reason**, never hidden. No new write authority — reuse the ADR-307 gate + ADR-320 lock. |
| **D4** | Trash | A first-class **Trash view** (lists `lifecycle=archived`) + **Restore** (un-archive = a new `active` revision; the substrate already supports it). Delete is trash-not-erase (already true); this makes it *visible + reversible in the UI*. |
| **D5** | Right-click context menu | The Explorer/Finder muscle-memory affordance: right-click a file → Open · Get Info · Move to… · Move to Trash (each enabled per D3 topology). Reduces button-hunting; the primary interaction verb. |
| **D6** | Two-principal legibility | Files visibly distinguish **operator-owned vs agent-owned** (a quiet ownership badge / who-last-touched), and disabled verbs explain *why*. This realizes ADR-329's stated-but-unbuilt payoff. |
| **D7** | Non-text parity | Move/trash/restore work for **all file types** (the verbs are format-blind — they operate on the revision, not the content). Viewing non-text uses the ADR-395 blob path already shipped. |
| **D8** | Restore mechanism | New: an **un-archive** path (`lifecycle=archived → active` via `write_revision`, attributed `operator`, message "restored from trash"). Small, additive; the archive was always designed reversible. |

---

## 5. What this is NOT (the discipline check)

- **NOT in-app content editing.** The human never edits a file's *content* in the browser (ADR-236/329). "Edit" remains an agent verb through chat/Freddie — the Copilot boundary. Move/rename/trash are *organization* verbs (metadata/placement), not *authoring* verbs; that's why they're the human's and edit isn't.
- **NOT a topology break.** The human gains no ability to write/move/delete outside operator-owned roots. The gate + lock are untouched; this ADR is a *surface* over the existing permission model.
- **NOT a Finder.** We deliberately keep the two-principal reality *visible*. A file explorer that hid who-authored-what would discard the moat.
- **NOT new primitives.** `MoveFile`/`DeleteFile` exist. The only new backend surface is the **Restore** (un-archive) path (D8) + a **Trash list** read endpoint (`lifecycle=archived`) — both thin, both additive.

---

## 6. Implementation shape (post-ratification — informational, not ratified here)

Four tiers, one pass (per operator direction):

1. **Trash surface (D4/D8)** — a Trash view listing archived files + Restore; the un-archive route.
2. **Operator move (D2/D3)** — "Move to…" on owned files → `MoveFile`, destination-scoped to operator roots.
3. **Right-click context menu (D5)** — Open / Get Info / Move to… / Move to Trash, enabled per topology.
4. **Two-principal legibility (D6)** — ownership badge + disabled-with-reason on system files.

No schema change. Backend: one Restore route + one Trash-list read (both over existing `workspace_files` + `write_revision`). Frontend: `WorkspaceTree` + Files page gain the context menu, move dialog, trash view, ownership legibility. Everything flows through the existing ADR-307 gate.

---

## 7. Open questions for ratification

1. **Rename** — is in-place rename (a filename change) an operator verb too, or does it stay an agent/Freddie concern? (Rename is a `MoveFile` with the same parent — cheap to include, but it edges toward "the human reorganizes freely." Lean: include it, still operator-root-scoped.)
2. **Drag-to-move vs menu-only** — ship the right-click "Move to…" dialog first, add drag-and-drop later? (Drag-and-drop in a tree is more FE work; the menu is the honest MVP.) Lean: menu first, drag as a fast-follow.
3. **Trash retention** — archived files live forever (ADR-209 retention), or is there an eventual "empty trash" hard-delete? (Hard-delete would violate ADR-209's retain-everything; lean: no empty-trash — Trash is a *view*, archived is permanent-but-hidden, matching the substrate's actual semantics. If storage ever demands it, that's a separate ADR.)
4. **Ownership badge granularity** — binary (you / agent) or full attribution (You / Freddie / ChatGPT-via-MCP / …, reusing the ADR-388 attribution module)? Lean: full attribution — the module exists and the interop story (a file ChatGPT wrote, visible as such) is the moat.
