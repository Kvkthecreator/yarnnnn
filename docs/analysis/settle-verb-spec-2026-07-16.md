# The Settle Verb — Spec

**Status**: Spec, ready to build. Implements the **ratified direction** of [ADR-457](../adr/ADR-457-think-and-make-the-service-model.md) **D3** (the verb) onto **D4** (the think-home convention). Sequenced as step 2 by [ADR-460](../adr/ADR-460-agents-one-concept-independent-facts-one-gate.md) §8 — after W0, before the Agent registry.
**Date**: 2026-07-16
**Relates to**: ADR-457 D3/D4/D8 · ADR-450 (DERIVE_RECIPES — the precedent this reuses and the seam it does **not** cross) · ADR-448 (`derived_from` — the reference edge) · ADR-423 (`revision_kind='derivation'`) · ADR-401 (the derive organ that never fired) · ADR-325 (embed as a gated primitive) · ADR-411 D4 (`member:` attribution) · ADR-307 (the one gate) · DP32 (retain + attribute + cite).

---

## 1. What settle is, in one line

> **"Keep this" — the act that turns a conversation into record.** It reads a lane transcript, distills the insight into one markdown note, lands it at the D4 think-home, cites the conversation on the ledger (`derived_from` → the lane), and **embeds it** so the next question can find it.

Three birds, one verb (ADR-457 D3, verbatim): the **felt moment of the moat** (episodic → cumulative, on screen) · the **missing derive organ** (ADR-401's chain has been broken at *derive* since the audit — autonomous derive never fired; settle is that organ, human-staged) · the **retrieval fix** (settled products embed, so grounding reads an indexed corpus).

## 2. The design question, and the fact that decides it

**Is settle a new `DERIVE_RECIPES` row, or its own path?**

The registry is the obvious home — ADR-450 ratified *"recipes are data, not sub-processes,"* and a settle-as-recipe would be one dict entry. **The code says no**, and precisely why:

```
$ grep -n '"accepts"' api/services/derive_recipes.py
35:  "accepts": ["file"],     # context-brief
61:  "accepts": ["file"],     # design-system
101: "accepts": ["file"],     # deck
128: "accepts": ["file"],     # prd
```

**Every recipe accepts a *file*.** The whole registry is built on a source that is a path in the commons — `build_derive_section(recipe_slug, source_path, ...)` normalizes it to `/workspace/...` and hands the model "read the projection for binary raws." **Settle's source is a transcript** — `session_messages` rows, not substrate, with no path, no revision, no projection.

That is a **difference in kind, not degree**. Forcing a conversation into a `source_path` would either (a) invent a fake path for a session, or (b) widen `accepts` to `["file", "conversation"]` and fork every recipe's mechanics on the source type — the dilution ADR-460 just spent an ADR removing.

**Ruling: settle is a sibling of the recipe path, not a row in it.** It reuses the same *spine* — a posture overlay + the file verbs + `derived_from` + `revision_kind='derivation'` — with a conversation-shaped source. When a recipe's source is a file, use a derive lane; when it is the thinking itself, use settle. Two paths, one discipline. (If a third conversation-sourced distillation ever appears, *then* the shared abstraction has two instances and earns itself. Not before.)

## 3. D1 — Settle is one route, not a primitive

**`POST /api/lanes/{id}/settle`** — the member's act on their own lane.

Not a primitive, and the reason is the ADR-460 discipline applied one level down: a primitive is a capability an *LLM* may invoke. Settle is a **member's gesture** — it fires only on a human act (the never-ambient invariant), and the model it runs is the *transport*, not the actor. Adding `Settle` to `CHAT_PRIMITIVES` would let a model settle its own conversation unasked, which is the ambient behavior the whole discourse refuses.

The route:
1. Loads the lane + its transcript (the member's own; grant-scoped like every lane read).
2. Runs **one bounded LLM turn** with the settle posture (§4) — no tool loop; the model returns the note's **content**, not a tool call. *(Rationale: giving the model `WriteFile` here would let it choose the path, and D4's convention is the kernel's to enforce, not the model's to interpret. The model distills; the kernel places.)*
3. **Places** the note per D4 (§5) — server-side, deterministic.
4. **Writes it** through `write_revision` with `derived_from=[lane_ref]`, `revision_kind="derivation"`, `authored_by="member:{user_id} via {model}"`.
5. **Embeds** it (`_embed_workspace_file`) — the retrieval fix; the bird that dies if skipped.
6. Meters it: `record_execution_event(slug="settle", session_id=lane_id, ...)` — **the falsifier-2 instrument W0 built** (`staged` flips True at the first settle).
7. Returns `{path, title, revision_id}` so the FE can render the moment.

## 4. D2 — The settle posture (kernel constant, one screen)

Composed at turn time, never stored (the ADR-411 D6 / ADR-414 D2 pattern). It carries only what the model needs to distill:

- **The job**: distill this conversation into ONE note a colleague could act on **without reading the transcript**. The transcript is the raw and is retained; the note is the *understanding*.
- **The shape**: a title line · what was decided or understood · the reasoning that matters (not the transcript's path to it) · open questions. Under ~120 lines. Selective beats complete.
- **The bar**: every load-bearing claim must be traceable to something actually said. **Never invent specifics.** If the conversation reached no conclusion, say so plainly — a settle that manufactures a decision is worse than no settle.
- **The output contract**: return the note's markdown **and nothing else** — a `# Title` first line (the kernel slugs it) and the body. No preamble, no "here's your note."

**Explicitly NOT in the posture**: where to write (kernel places), how to cite (kernel writes the edge), whether to embed (kernel does). Every mechanic the kernel can do deterministically, the kernel does — the model's only job is judgment about *content*. This is the ADR-460 D3.a instinct applied to a posture: don't give the model a lever the kernel should hold.

## 5. D3 — Placement: kernel-deterministic, D4-conformant

Target: **`operation/{topic}/{yyyy-mm-dd}-{slug}.md`** (ADR-457 D4), Documents root as fallback.

- **`{slug}`** — from the model's `# Title` line, kebab-cased, truncated. Deterministic.
- **`{yyyy-mm-dd}`** — UTC, server-side.
- **`{topic}`** — the one judgment call in placement, resolved by a **deterministic ladder** (no LLM):
  1. **A bound lane** (`artifact_path`) → the artifact's own meaning-folder. The thinking about a thing lands beside the thing.
  2. **A derive lane** (`derive_source`) → the source's folder. Same logic.
  3. **An existing peer folder** whose name matches the title's leading noun — an **exact, case-insensitive match against existing `operation/*` folders only.** No fuzzy matching, no LLM guess. *(A near-match that lands thinking in the wrong topic folder is worse than the fallback: the fallback is visibly un-filed, a mis-file is invisibly wrong.)*
  4. **Fallback** → the Documents root (D4's stated fallback).
- **Collision** — if the path exists, suffix `-2`, `-3`. Never overwrite: two settles from one conversation are two acts, and the ledger's job is to keep both.

**No new namespace, no kernel noun, no scaffolding** (D4's constraint, honored). `operation/memory/` and `operation/decisions/` stay un-canonized (D4 named them demo residue).

## 6. D4 — The citation: what `derived_from` points at

The edge must name **the conversation**, and here is the honest problem: **`derived_from` is a list of workspace paths** (ADR-448 — "the absolute workspace paths this revision was made from"), and **a lane is not a file**. It has no path.

Three options were weighed:

1. **Materialize the transcript as a file**, then cite its path. Rejected: it doubles every conversation into substrate nobody asked for, and DP32 already treats the transcript as the retained raw *in its own table*. The raw is retained; retention does not require a second copy.
2. **Widen `derived_from` to accept non-path refs.** Rejected for now: it changes the ADR-448 column's meaning for every reader (`list_dependents`, `trace`, the Files delete-warning) to serve one caller.
3. **Cite the lane by a stable reference in the revision's `message` + `metadata`, and leave `derived_from` for paths.** **Chosen.**

**The chosen shape:** `derived_from` carries the lane's *bindings* when it has them (a bound lane's `artifact_path`, a derive lane's `derive_source`) — real paths, a real edge, already meaningful to `trace` and `list_dependents`. The **conversation itself** is cited in the revision's **`message`**: `"settled from the lane '{name}' (session {lane_id})"`.

> **Corrected at build (2026-07-16, caught by the live probe).** This section originally specified the lane id riding `write_revision(metadata={"settled_from_session": lane_id})`. **That was wrong**, and the probe proved it: `write_revision`'s `metadata` writes to **`workspace_files.metadata`** — the *file* row — which **the next revision overwrites**. This settle's provenance would have been silently lost the first time the note was edited. `workspace_file_versions` has **no metadata column** (`\d` receipt: `id · user_id · path · blob_sha · parent_version_id · authored_by · author_identity_uuid · message · created_at · workspace_id · revision_kind · derived_from`). Its **`message` is the permanent per-revision record** — immutable, greppable, and already surfaced by `trace`. The lane id lives there. *Lesson worth keeping: "metadata" on a write path is not automatically per-revision; check which row it lands on.*

**This is a named, honest gap, not a fudge.** `trace` on a settled note will show *"derived from the artifact"* but not *"…via this conversation"* until conversations are addressable in the reference graph. That is the **conversation-as-substrate question**, which is exactly ruling **(c)** in the chat(think) capture (the comments inversion — "make the Conversation binding-capable from birth"). **Settle does not pre-empt (c); it records the dependency.** When (c) rules, the edge upgrades in one place. An unbound chat lane's settle will have an empty `derived_from` and carry its provenance in metadata only — honest, and visibly incomplete, which is the point.

## 7. D5 — What settle is NOT

- **Not ambient.** Fires only on a member's click. No auto-settle, no "should I keep this?" nudge. The never-ambient invariant (capture §3.3) is not negotiable.
- **Not a summary.** A summary compresses what was said; a settle distills what was *understood* and drops the rest. The posture says so explicitly.
- **Not the autonomous derive.** ADR-401 D5's wake-routed derive stays deferred. Settle is the *human-staged* organ — same act, a hand on it.
- **Not a Studio artifact.** It produces prose substrate (`.md`), which is Think's grammar (the seam-contract split axis: prose-substrate vs composition-grammar). Graduating a note → an artifact is `learn-from` (ADR-452), a separate act.
- **Not multi-note.** One settle → one note. A conversation with three insights settles three times, or once badly. (Revisit against felt need, never speculation.)

## 8. Build order

1. `api/services/settle.py` — the posture constant + `build_settle_posture()` + `place_settle_note()` (the §5 ladder, pure) + `settle_lane()` (the orchestration).
2. `POST /api/lanes/{id}/settle` in `routes/lanes.py`.
3. FE: a "Keep this" affordance on the lane + the landed-note moment (the felt beat — it must *show* the note landing, not toast-and-vanish).
4. Gate `api/test_settle_verb.py`: the placement ladder (all four rungs + collision); the posture carries no placement/citation mechanics; `revision_kind='derivation'`; the settle meters with `slug="settle"` + `session_id` (falsifier 2's staging); **settle is not in any primitive registry** (the not-a-primitive ratchet); embed is called.
5. Prod probe: settle a real lane → receipt the path, the revision, the embed, and `falsifier_2.staged` flipping True.

## 9. Receipts (built 2026-07-16)

**Gate**: `api/test_settle_verb.py` — **41/41 PASS** (the placement ladder incl. both no-fuzzy-match cases; the posture carries no kernel lever; the not-a-primitive ratchet; the citation; the meter). W0 gate 21/21 still green. FE: **`✓ Compiled successfully`** in a clean HEAD worktree (the shared tree carries a parallel lane's Studio WIP — `next build` there lies; the worktree+symlinked-node_modules pattern is the honest gate).

**Live end-to-end probe** — settled a real bound lane (`deck.html`, sonnet, 2 messages):

```
path:        /workspace/operation/sample/2026-07-15-6-slide-sample-deck-drafted.md
revision:    revision_kind=derivation
             derived_from=["/workspace/operation/sample/deck.html"]
             authored_by="member:2abf3f96-… via anthropic/claude-sonnet-4-6"
             message="settled from the lane 'deck.html' (session 130e1bef-…)"
embedded:    true          ← bird 3, the retrofit fix
metered:     slug=settle, has_join_key=true, 559 in / 118 out, $0.003447
falsifier_2: {"staged": true, "settles": 2}   ← W0's instrument reads the verb it was built for
```

**Every claim verified, not assumed:**
- **The placement ladder's rung 1 fired for real** — a lane bound to `operation/sample/deck.html` filed its thinking at `operation/sample/`, beside the thing it was about. Not a fixture: the live binding drove it.
- **Collision handling fired for real** — the second probe landed `-2`, never overwriting the first. Two settles are two acts.
- **`staged: true`** closes the W0→settle loop end-to-end: the instrument built one commit earlier now reads the verb it was built to measure. This is the only ordering in which that sentence is true.

**The bug the probe caught (§6, corrected).** The spec's original citation design was wrong and only a live write proved it: `write_revision(metadata=…)` writes `workspace_files.metadata` — the *file* row — which the next revision overwrites. This settle's provenance would have vanished on the note's first edit. Fixed to ride the revision `message` (immutable, per-revision, already in `trace`). **A gate over fixtures would never have caught this** — it needed a real row in a real table.

**Probe residue, named (operator's call, NOT cleaned).** The probe wrote to the live workspace and I stopped short of deleting from the shared ledger — that permission was for building, not for clearing rows. Currently present in prod:

- 2 × `workspace_files` + 2 × `workspace_file_versions` at `/workspace/operation/sample/2026-07-15-6-slide-sample-deck-drafted{,-2}.md`
- 2 × `execution_events` rows with `slug='settle'` (~$0.0087 total, real spend on the one ledger)

These are honest artifacts of a real act, not corruption — the notes are genuine derivations of a genuine conversation. **But they are test residue in the operator's commons and `falsifier_2.settles=2` is currently 2 probe settles, not 2 felt ones.** Delete them (files → versions → events, in that FK order) before the falsifier window is read, or accept them as the baseline's first two rows with this note as their provenance.

**Not covered**: the FE affordance driven by a human click (compiles clean; the beat wants an eye on it), and a settle over an *unbound* chat lane (rung 3/4 of the ladder are gate-covered but not prod-probed — the only lane with ≥2 messages in the live workspace was bound).

## 10. One-line statement

**Settle is a member's gesture, not a model's capability: one bounded turn distills the conversation, the kernel places it at the think-home, cites what it can honestly cite, and embeds it — the derive organ that never fired, with a hand on it.**
