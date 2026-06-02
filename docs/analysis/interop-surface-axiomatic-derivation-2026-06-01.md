# Interop Surface — Axiomatic Derivation (v2, primitive altitude)

> **⚠️ STRATEGIC FRAMING PARTIALLY SUPERSEDED (2026-06-02) — see [judgment-as-center-2026-06-02.md](judgment-as-center-2026-06-02.md).**
> **Resolution B ("two moats, phased" — substrate = Phase-1 face, judgment = Phase-2 face)
> is superseded.** Judgment is the center; the portable attributed substrate is its
> trust-medium, not a co-equal phased face. **The primitive-surface derivation itself stands
> in full** — §1–§4 (gate invariant, primitive altitude, riders-as-return), §6, §7 (the
> primitive surface, revision-archaeology-as-differentiator, the foreign-caller threat-model
> lens) are all still correct *mechanics*. Only the strategic phasing the primitives were
> hung on is corrected. When the ratifying ADR (311) is reframed, keep the §1–§4/§6/§7
> mechanics; drop the Resolution-B phasing language.

**Date:** 2026-06-01
**Hat:** B (external developer surface — strategic/architectural discourse capture). Analysis, not canon. Recommends; does not amend. Ratified outcome lands as an ADR (superseding ADR-310 + ADR-169 tool surface) + GLOSSARY + primitives-matrix + a THESIS sequencing note.
**Origin:** operator asked for an *axiomatic, future-proof* re-derivation of the interop surface. Through discourse this deepened twice: (1) from intent-shaped tools to **primitive (Claude-Code-style) substrate operations**, and (2) a thesis-level resolution that **YARNNN has two moats, phased** — the attributed substrate (Phase-1 face) and the judgment seat (Phase-2 face).
**Supersedes:** the v1 four-verb intent-altitude derivation (DISCOVER/CONSULT/CONTRIBUTE/PRIME). v1 derived at the wrong altitude — it encoded *intents* (curated use-cases) where the substrate's own nature calls for *primitives* (composable file operations the foreign LLM assembles into intent itself).
**Companion:** [sequenced-moat-strategy-2026-06-01.md](sequenced-moat-strategy-2026-06-01.md), [ADR-310](../adr/ADR-310-judged-substrate-interop-face.md), [ADR-222](../adr/ADR-222-agent-native-operating-system-framing.md) (the kernel/substrate boundary this derivation leans on).
**Status:** Proposed framing for operator ratification. No code, no canon edits.

---

## 0. The two resolutions that set the altitude

Two discourse outcomes constrain everything below. Both are operator decisions, recorded here, not yet ratified into canon.

**Resolution A — primitive, not intent.** The interop surface exposes *primitive substrate operations* (the Claude Code model: `Read`/`Glob`/`Grep`/`Edit` over a repo), not intent-shaped tools (`work_on_this`, `pull_context`). The foreign LLM composes intent itself — "prime me for work on X" is the LLM globbing a domain and reading entity files, exactly as Claude Code composes "understand this codebase" from Glob+Read+Grep. This **reverses** the primitives-matrix rule that MCP is "intent-shaped, not substrate-archaeology-shaped," and **reverses** the deliberate exclusion of revision-archaeology primitives. Rationale: an intent surface is a *second vocabulary* bolted on the kernel's file primitives — a Singular-Implementation (Principle 7) violation. The kernel already has `ReadFile`/`WriteFile`/`SearchFiles`/`ListFiles`; the interop surface should be *those same primitives in MCP mode*, not a parallel set.

**Resolution B — two moats, phased (not re-ranked).** YARNNN has both moats; the phasing is their relationship:
- **Phase-1 face = the attributed substrate** (Commitment 4). Real and shippable now. The "attributed agent filesystem" — won on *attribution-as-structural*, the rider no competitor can commoditize (not "storage for agents," which is a crowded race).
- **Phase-2 face = the judgment seat** (Commitments 1–3: mandate, Reviewer, ground-truth). The compounding, hardest-to-copy moat. Sequenced second *because* it's the part competitors can't fast-follow, not because it's lesser.
- THESIS is untouched in *content*; it gains a **sequencing note** (Commitment 4 is the Phase-1 face; Commitments 1–3 are the Phase-2 face; the four legs remain the definition of autonomy — sequence is rollout, not re-rank). This matches strategy-doc §5 exactly.
- **Discipline this imposes:** judgment-as-Phase-2 must stay a *first-class* moat, not a starved one. The substrate-moat thesis only holds if the judgment face stays excellent.

The boundary that makes Resolution A safe (operator-confirmed): the foreign LLM **operates the substrate (the filesystem commons) but not the kernel machinery** (workforce / lifecycle / Reviewer-control). Drawn at the ADR-222 substrate↔kernel line — not at the old "thinking-mode vs management-mode" line. A foreign LLM is *userspace with a filesystem*; it is not the kernel. It can `ReadFile`/`WriteFile`/`ListRevisions` the commons; it cannot `Schedule`/`ManageAgent`/drive the Reviewer — **because those aren't filesystem operations**, not because the LLM is "only thinking."

---

## 1. The axiomatic derivation — the surface IS the kernel's file primitives, scoped

From the axioms, the interop surface is fully determined:

- **Axiom 1 (Substrate):** "Files are the universal interface across LLM providers and interoperability protocols (MCP)." The substrate *is* a filesystem. The natural operations on a filesystem are read / list / search / write / inspect-history. These already exist as kernel primitives (ADR-168).
- **Axiom 6 (Channel):** the foreign LLM is an addressed cognitive consumer. The channel is the file-primitive responses.
- **Axiom 2/9 (Identity):** a foreign call is an invocation with `Identity = external:<client>`, scoped to one resolved operator (ADR-310 D4 per-request identity). MCP is a *mode* of the Mechanism vocabulary, not a parallel runtime.
- **Principle 7 (Singular Implementation):** therefore the interop surface is **not new primitives** — it is the *existing* file-layer primitives, with their MCP-mode column turned on, scoped to the commons.

The derived surface (Phase 1):

| Primitive (exists in ADR-168 matrix) | Operation | Maps to Claude Code | Phase-1 scope |
|---|---|---|---|
| **`ReadFile`** | read a path's content + riders | `Read` | `/workspace/context/` + operator's authored substrate |
| **`ListFiles`** | enumerate paths under a prefix | `Glob` / `LS` | same |
| **`SearchFiles`** / `QueryKnowledge` | structural + semantic search | `Grep` + (semantic, no CC analog) | same |
| **`WriteFile`** | write a path, attributed + gated | `Edit` / `Write` | same |
| **`ListRevisions` / `ReadRevision` / `DiffRevisions`** | inspect the authored history of a path | `git log` / `git diff` (no CC tool analog — this is YARNNN's *differentiator* exposed) | same |

That last row is the point. Revision-archaeology was *excluded* by the old canon as "not intent-shaped." But under Resolution A + Resolution B, **exposing the revision chain across the boundary is the single most differentiating thing the surface can do** — it is *attribution-as-structural*, made operable. A foreign LLM asking "who authored this claim and how did it evolve?" is the Phase-1 moat (Commitment 4) exercised directly. No competitor's agent-filesystem has an attributed, walkable revision chain to expose. **This is the agent-Dropbox's killer primitive.**

---

## 2. Why intent collapses into composition (the v1 verbs, dissolved)

Every v1 intent-verb is now something the foreign LLM *composes* from primitives:

| v1 intent-verb | Primitive composition the LLM does itself |
|---|---|
| `pull_context(subject)` | `SearchFiles(subject)` → `ReadFile(top hits)` |
| `work_on_this(subject)` (PRIME) | `ListFiles(/context/{domain}/)` → `ReadFile(entity files)` → done. *No tool.* |
| DISCOVER ("what's in here?") | `ListFiles(/workspace/context/)` — it's just `ls`. *No tool.* |
| `remember_this(content)` | `WriteFile(path, content)` |
| "how did this fact evolve?" | `ListRevisions(path)` → `DiffRevisions(a,b)` |

The v1 derivation spent its energy deciding *how many intents* and *which phase each belongs to*. At primitive altitude **the question dissolves** — there are no intents to phase, only primitives the LLM assembles. `work_on_this`'s "is it Phase 1 or Phase 2?" agony (v1 §4) evaporates: session-priming is never a tool, it's a composition, available the moment the primitives exist. This is the strongest evidence Resolution A is correct: the hard questions at intent-altitude *stop existing* at primitive-altitude. **Lower altitude, fewer arbitrary decisions, more future-proof.**

---

## 3. The rider model survives — relocated to "what ReadFile returns"

v1's rider model (content + authored_by + judgment-standing + recency) was right but mis-placed as a special *read contract*. At primitive altitude it's simpler: **riders are just the fields `ReadFile` / `ListRevisions` already return**, because the authored substrate already carries them.

- **content** — the floor (Axiom 1).
- **authored_by** — the ADR-209 attribution on every revision. *This is the Phase-1 moat surfaced.*
- **revision chain** — `ListRevisions`/`DiffRevisions` expose it. *Phase-1 differentiator.*
- **judgment-standing** — populated in **Phase 2** when a Reviewer verdict exists for the path (verdicts are already substrate at `decisions.md`). Phase-1 reads simply don't carry it; Phase-2 reads do. **Same primitive, thicker return.**

This is exactly the both-moats phasing made concrete at the primitive level: `ReadFile` in Phase 1 returns content + attribution + history (substrate moat); `ReadFile` in Phase 2 *also* returns judgment-standing (judgment moat). The primitive doesn't change between phases — its return enriches. Clean.

---

## 4. The all-consequence-at-the-gate invariant — PROVEN UNMET today (hard ADR prerequisite)

Resolution A makes `WriteFile`-across-the-boundary a *much* sharper capability than `remember_this` (which classified + routed to safe targets). A foreign LLM holding raw `WriteFile` can write *any commons path*. This is safe **only** if the invariant holds:

> Every foreign `WriteFile` (and every consequential primitive) traverses the **single ADR-307 permission gate** at `execute_primitive` — gating on Mechanism now, and on `(contributor identity, target workspace, membership role)` in Phase 3. It never self-gates, never bypasses (Principle 23).

**Verified 2026-06-01 — the invariant is NOT satisfied today.** Code trace (definitive):
- `execute_primitive` (registry.py:652-673) *does* call `resolve_permission` for every primitive — the chokepoint is structurally present.
- BUT `resolve_permission` (permission.py:172-174) short-circuits: `if not getattr(auth, "reviewer_caller", False): return APPLY, "non_reviewer_caller"`. The autonomy check, queue logic, AND path-lock check all live *below* this line, inside a Reviewer-only branch (ADR-293 scoped autonomy gating to Reviewer-runtime calls).
- The MCP caller is `caller_identity="yarnnn:mcp"`, never `reviewer_caller=True`. So a foreign write exits at the short-circuit → APPLY → writes directly.
- **There is no path-lock for the MCP caller.** `_is_path_locked_for_reviewer` is invoked only in the Reviewer branch; and `MANDATE.md` / `review/principles.md` are deliberately NOT in the lock set anyway (listed as "unlocked operational content"). **A foreign MCP write can today reach `/workspace/context/_shared/MANDATE.md` and `/workspace/review/principles.md` with no gate, no lock, no queue.**
- The async Reviewer wake (shipped, commit `2ef6721`) is **post-hoc** — it fires *after* the write committed. It is "judge after," not "gate before."

So the eventually-judged model that's live is a reasonable posture for *low-stakes classifier-bounded targets* (memory, feedback — what `remember_this` actually routes to today), but it is **insufficient for a raw `WriteFile` primitive surface.** This converts §4 from an assertion into a **proven, currently-unmet requirement**: gating the `yarnnn:mcp` caller is a **hard prerequisite** of the primitive surface, not a §7 nicety. The ratifying ADR's first deliverable is: bring `caller_identity="yarnnn:mcp"` into the gated branch with its own policy (autonomy decision + an MCP write-lock-set covering governance paths).

This is what makes "foreign LLM holds WriteFile" safe the way "Claude Code holds Edit" is safe: Claude Code is safe because *you're* in the loop; YARNNN's foreign `WriteFile` is safe because *the gate* is in the loop. Today the gate is a no-op for this caller — **the safety model is the work, not a given.**

It also future-proofs governance (the shared-workspace frontier): once the MCP caller is gated, "who can write into whose commons" under Phase-3 shared/cross-operator workspaces is a *gate-membership-policy* addition — never a tool-surface redesign. **Gate the MCP caller first; then lock the primitives; then add cross-operator governance at the same gate.**

---

## 5. The phasing, at primitive altitude (both moats, clean)

| Phase | What ships | Which moat | Primitive surface |
|---|---|---|---|
| **Phase 1** | The attributed agent filesystem, operable by any LLM | **Substrate moat** (Commitment 4) | `ReadFile` · `ListFiles` · `SearchFiles`/`QueryKnowledge` · `WriteFile` (gated, attributed) · `ListRevisions`/`ReadRevision`/`DiffRevisions` — all scoped to one operator (ADR-310 D4) |
| **Phase 2** | Judgment thickens | **Judgment moat** (Commitments 1–3) | *Same primitives.* `ReadFile` return gains judgment-standing; `WriteFile` already wakes the Reviewer (shipped). Cockpit lights up. Programs activate. |
| **Phase 3** | Cross-operator / shared | (network) | *Same primitives.* Scope resolves to `workspace_id`; gate gains membership policy. The agent Dropbox becomes shared. |

Each phase adds exactly one axiom-cell's worth of change: Phase 1 = the primitives + single scope; Phase 2 = + judgment rider; Phase 3 = + cross-operator scope + gate-membership. **The primitive surface is identical across all three phases** — only return-richness and scope-resolution evolve. This is the maximally future-proof shape: you never redesign the surface, you only thicken what it returns and widen what it reaches.

---

## 6. What this supersedes / amends (named, not done)

- **primitives-matrix.md** — reverses two rules: (a) MCP is now *primitive-shaped*, not intent-shaped; (b) revision-archaeology primitives (`ListRevisions`/`ReadRevision`/`DiffRevisions`) ARE exposed on MCP (was: "deliberately NOT exposed"). The MCP-mode column turns on for the file-layer + revision primitives, scoped to the commons. The three intent tools (`work_on_this`/`pull_context`/`remember_this`) are **deleted** (Singular Implementation) — their behavior is composed by the foreign LLM from primitives.
- **ADR-310** — its D1 two-faces survives; its "3 intent-shaped tools" implementation is superseded by the primitive surface. D2's read/write disciplines survive (riders on read; gated+judged write) — relocated onto the primitives. D4 (per-request identity) and D5 (shared-workspace deferred) survive unchanged.
- **ADR-169** — fully superseded (already was, by ADR-310; this completes it).
- **THESIS.md** — sequencing note only (Resolution B): Commitment 4 = Phase-1 face, Commitments 1–3 = Phase-2 face; no commitment content changes, no re-rank.
- **FOUNDATIONS Axiom 6** — the "Foreign LLM via MCP" row's channel shape changes from "3 intent tools" to "file-primitive responses over the commons." Axiom 1's "files are the universal interface (MCP)" clause is now *literally* the product surface, not a benefit.
- **GLOSSARY** — add: "interop face," "the commons," "attributed agent filesystem." The OS-framing vocabulary (kernel/userspace/syscall) already covers the rest.
- **NARRATIVE.md / ESSENCE.md** — external re-beat (ADR-210-governed): the Phase-1 entry story may lead with "the attributed agent filesystem — every revision knows who authored it, across every LLM" rather than "cockpit for an autonomous operation." Still Path B; the noun shifts toward infrastructure. Operator flagged this is a real but acceptable reach.

---

## 7. Open decisions for the ratification pass

1. **Write boundary (the one real safety call):** does the foreign LLM get *raw* `WriteFile(any commons path)`, or a *path-scoped* WriteFile (e.g. can write `/context/` + feedback paths, but not `/review/` Reviewer substrate or `_shared/` governance)? Even with the gate, some paths (AUTONOMY, MANDATE, principles) are operator/Reviewer-authored — a foreign LLM writing them is a different risk class. **Recommendation:** the gate's path-lock model (`DEFAULT_REVIEWER_WRITE_LOCKS` precedent) extends to the MCP caller — raw WriteFile, but the gate enforces a default lock-set on governance paths. Decide the Phase-1 lock-set.
2. **Semantic vs literal read:** `SearchFiles` (literal/structural) and `QueryKnowledge` (semantic/embedding) are two different primitives. Expose both? Lead with which? (§ recommendation: both — the LLM picks, like Grep vs semantic.)
3. **Revision-archaeology scope:** all three (`ListRevisions`/`ReadRevision`/`DiffRevisions`) in Phase 1, or just `ListRevisions` (the catalog) with diff deferred? The differentiator argues for all three.
4. **The §4 gate-traversal check — VERIFIED 2026-06-01: the gate is a no-op for the `yarnnn:mcp` caller.** A foreign `remember_this` write applies directly with no autonomy decision, no path lock, no queue (short-circuits at permission.py:172 `non_reviewer_caller`). This is a real, currently-shipped safety gap (narrow today — one classifier-bounded tool — but structural). **Resolved into a hard prerequisite**: the ADR must gate the MCP caller. Open sub-decision: fix the *current* gap (stop-the-bleeding, MCP-isolated) now, or fold entirely into the broader ADR (see ordering decision below).
5. **Protocol-agnostic verbs:** Axiom 1 says "interoperability protocols (MCP)" — generalizing. Derive the primitives as *protocol-agnostic* (the file verbs are the contract; MCP is one binding; direct-API / A2A are future bindings)? Recommended — it's the most future-proof framing and costs nothing now.
6. **Vocabulary + THESIS sequencing note** — add glossary terms; draft the THESIS sequencing note (Resolution B) for operator review.

---

## 8. Recommendation

Adopt the **primitive interop surface** — the kernel's own file + revision primitives, MCP-mode, scoped to the commons, all consequence at the gate — as the axiomatic, future-proof shape, under the **two-moats-phased** thesis (substrate = Phase-1 face, judgment = Phase-2 face).

It is more future-proof than the v1 intent frame on every axis: fewer arbitrary decisions (intents dissolve into composition), Singular Implementation (no second vocabulary — same primitives, new mode), identical surface across all three phases (only return-richness + scope evolve), governance addable at the gate without tool redesign, and it surfaces the one uncopyable Phase-1 differentiator (the attributed revision chain) as a first-class primitive.

The non-negotiable that makes it safe: **all consequence at the one gate** (§4). Build that invariant first; the primitive surface is safe only because of it.

Ratify the *frame* (primitive surface + gate invariant + two-moats phasing + protocol-agnostic verbs). The specific path-lock-set and search-primitive choices (§7) follow.
