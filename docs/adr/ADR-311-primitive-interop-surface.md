# ADR-311 — The Primitive Interop Surface: Kernel File + Revision Primitives, MCP-Mode, Scoped to the Commons

**Status:** Proposed (2026-06-01)
**Supersedes:** ADR-310's three-intent-tool *implementation* of the interop face (`work_on_this` / `pull_context` / `remember_this`). ADR-310's D1 two-faces frame, D2 read/write disciplines, D4 per-request identity, and D5 shared-workspace deferral all **survive** — relocated onto the primitive surface. Fully supersedes ADR-169 (already superseded by ADR-310; this completes the tool-surface dissolution).
**Amends:** FOUNDATIONS Axiom 1 (the "files are the universal interface across … MCP" clause becomes literally the product surface) + Axiom 6 (the "Foreign LLM via MCP" Channel row's shape changes from "3 intent tools" to "file-primitive responses over the commons"); `docs/architecture/primitives-matrix.md` (reverses two MCP-mode rules — see §6); THESIS (sequencing note, Resolution B — no content change, no re-rank).
**Preserves:** FOUNDATIONS Axioms 1–9, THESIS four commitments, ADR-209 Authored Substrate, ADR-222 OS framing (the substrate↔kernel boundary this ADR leans on), ADR-307 uniform permission gate, ADR-310 D1/D2/D4/D5, the frozen `submit_wake_proposal` interface.
**Dimensional classification:** Channel (primary, Axiom 6) + Substrate (the thing served) + Identity (the foreign caller is `external:<client>`, scoped to one resolved operator).
**Discourse trail (Hat B):** [interop-surface-axiomatic-derivation-2026-06-01.md](../analysis/interop-surface-axiomatic-derivation-2026-06-01.md) (the ratified frame), [sequenced-moat-strategy-2026-06-01.md](../analysis/sequenced-moat-strategy-2026-06-01.md) (the strategic frame).

---

## 1. Context — the altitude correction

ADR-310 ratified the **interop face**: the cross-LLM/MCP capability is not a second moat but the *distribution face of the one moat* (authored substrate under a persona-bearing judgment seat). It implemented that face as ADR-169's inherited **three intent-shaped tools** — `work_on_this` (curated session bundle), `pull_context` (ranked chunks), `remember_this` (write-back).

A subsequent axiomatic re-derivation found those tools sit at the **wrong altitude**. They encode *intents* (curated use-cases) where the substrate's own nature — a filesystem (Axiom 1) — calls for *primitives* (the composable file operations a foreign LLM assembles into intent itself). This is the Claude Code model: `Read`/`Glob`/`Grep`/`Edit` over a repo, from which the foreign LLM composes "understand this codebase." An intent surface is a **second vocabulary** bolted on the kernel's existing file primitives — a Singular-Implementation violation (Principle 7).

The kernel already has `ReadFile` / `WriteFile` / `SearchFiles` / `ListFiles` / `QueryKnowledge` / `ListRevisions` / `ReadRevision` / `DiffRevisions` (ADR-168, ADR-209). The interop surface should be **those same primitives in MCP mode, scoped to the commons** — not a parallel set.

## 2. Decision — the surface IS the kernel's file + revision primitives, MCP-mode, scoped

### D1 — Primitive surface, not intent surface (the altitude)

The interop face exposes **primitive substrate operations**, not intent-shaped tools. Every v1 intent collapses into a composition the foreign LLM does itself:

| Old intent tool | Primitive composition the LLM does itself |
|---|---|
| `pull_context(subject)` | `QueryKnowledge(subject)` → `ReadFile(top hits)` |
| `work_on_this(subject)` (session-prime) | `ListFiles(/context/{domain}/)` → `ReadFile(entity files)`. *No tool.* |
| "what's in here?" (discover) | `ListFiles(/workspace/context/)` — it's `ls`. *No tool.* |
| `remember_this(content)` | `WriteFile(path, content)` |
| "how did this fact evolve?" | `ListRevisions(path)` → `DiffRevisions(a,b)` |

The hard intent-altitude questions (which-phase-does-`work_on_this`-belong-to) **dissolve** at primitive altitude: session-priming is never a tool, it's a composition available the moment the primitives exist. Lower altitude → fewer arbitrary decisions → more future-proof.

The three intent tools (`work_on_this` / `pull_context` / `remember_this`) are **deleted** (Singular Implementation). Their behavior is composed by the foreign LLM from the primitives below.

### D2 — The Phase-1 surface (operator-confirmed §7 decisions)

| Primitive (exists in ADR-168/209 matrix) | Operation | Claude Code analog | Phase-1 scope |
|---|---|---|---|
| **`ReadFile`** | read a path's content + riders | `Read` | the commons (`/workspace/context/` + operator-readable authored substrate) |
| **`ListFiles`** | enumerate paths under a prefix | `Glob` / `LS` | same |
| **`SearchFiles`** | literal / structural (BM25) search | `Grep` | same |
| **`QueryKnowledge`** | semantic / embedding ranked query | (no CC analog) | accumulated `/workspace/context/` domains |
| **`WriteFile`** | write a path, attributed + gated | `Edit` / `Write` | the commons, minus the governance lock-set (§D4) |
| **`ListRevisions` / `ReadRevision` / `DiffRevisions`** | inspect the authored history of a path | `git log` / `git diff` (no CC tool analog) | same as read scope |

**§7.2 decision — both search primitives.** `SearchFiles` (literal/structural) AND `QueryKnowledge` (semantic) are both exposed; the foreign LLM chooses, exactly as Claude Code chooses Grep vs a semantic search. Today's `pull_context` wrapped only `QueryKnowledge`; the primitive surface exposes both.

**§7.1 + §7.3 decision — raw `WriteFile` + all three revision reads.** The foreign LLM gets raw `WriteFile` (the gate enforces the lock-set per §D4 — a blocklist, not an allowlist) and all three revision-archaeology reads (`ListRevisions` / `ReadRevision` / `DiffRevisions`). This is the maximal differentiator: see §3.

### D3 — Riders are what `ReadFile` / `ListRevisions` already return

ADR-310 D2's read-side discipline ("judgment provenance travels with the fact") relocates onto the primitives. At primitive altitude it is simpler than a special read contract: **riders are just the fields the authored substrate already carries.**

- **content** — the floor (Axiom 1).
- **authored_by** — the ADR-209 attribution on every revision. *The Phase-1 moat, surfaced.*
- **revision chain** — `ListRevisions` / `DiffRevisions` expose it. *The Phase-1 differentiator (§3).*
- **judgment-standing** — populated in **Phase 2**, when a Reviewer verdict exists for the path (verdicts are already substrate at `decisions.md`). Phase-1 reads don't carry it; Phase-2 reads do. **Same primitive, thicker return.**

`ReadFile` in Phase 1 returns content + attribution + history (substrate moat); in Phase 2 *also* returns judgment-standing (judgment moat). The primitive doesn't change between phases — its return enriches.

### D4 — All consequence at the gate (the invariant — ALREADY MET, ratified here)

A foreign LLM holding raw `WriteFile` can attempt any commons path. This is safe **only** if the invariant holds:

> Every foreign `WriteFile` (and every consequential primitive) traverses the **single ADR-307 permission gate** at `execute_primitive`. It never self-gates, never bypasses (Principle 23).

**The derivation flagged this invariant as a hard prerequisite and verified it was UNMET when the derivation was written.** It is now **MET** — built in the ADR-310 follow-on commits *before* this ADR. Substrate receipts (verified 2026-06-01):

- `services/primitives/permission.py:179-187` — a dedicated `caller_identity == "yarnnn:mcp"` branch that **precedes** the `non_reviewer_caller` short-circuit (line 190). The foreign caller therefore does *not* inherit the operator/headless free-pass. Path-addressed writes (`WriteFile`) under a locked subtree → `DENY`; all other foreign writes → `APPLY` (and fire the eventually-judged wake per ADR-310 D2). *(commit `a33d062` — "gate foreign-LLM writes — close the live no-op-gate safety gap")*
- `services/workspace_paths.py:224-227` — `DEFAULT_MCP_WRITE_LOCK_PREFIXES = ("review/", "context/_shared/")`. Two subtree prefixes cover, in one stroke: operator-authored intent (MANDATE/IDENTITY/BRAND/CONVENTIONS/PRECEDENT), governance yaml (`_autonomy`/`_pace`/`_preferences`/`_token_budget`), `_operator_profile`/`_risk`, AND the Reviewer's own seat substrate. A foreign `WriteFile` under either prefix `DENY`s.
- `services/authored_substrate.py::read_revision` — defense-in-depth `user_id` filter on the revision content fetch, so a caller-supplied `revision_id` (now reachable via the MCP-exposed `ReadRevision`/`DiffRevisions`) cannot read another workspace's revision by UUID. *(commit `0723e5a` — "close cross-workspace revision-read leak before MCP-exposing ReadRevision")*
- Regression gate `api/test_adr310_mcp_write_gate.py` → **12/12 pass** (MANDATE/principles → DENY; memory/context-domain → APPLY; reads never gate; non-MCP callers unchanged).

The MCP lock-set is **broader** than the Reviewer's by design: the Reviewer is trusted to edit operational content ("same trust model as Claude Code editing CLAUDE.md"); a foreign LLM is not — it may contribute to the commons (context domains, memory, feedback) but must never silently rewrite governing intent or the Reviewer seat.

This is what makes "foreign LLM holds `WriteFile`" safe the way "Claude Code holds `Edit`" is safe: Claude Code is safe because *you're* in the loop; YARNNN's foreign `WriteFile` is safe because *the gate* is in the loop. **The gate is now genuinely in the loop for this caller.**

### D5 — The foreign-caller threat-model audit lens (canonized)

Two leaks of one structural class were found and fixed during this arc:
1. **The no-op-gate leak** — a foreign write inherited the `non_reviewer_caller` free-pass (closed: `a33d062`).
2. **The cross-workspace revision-read leak** — a UUID-addressed revision read could cross the workspace boundary (closed: `0723e5a`).

Both share a class: **a foreign caller reaching past its scope because a primitive's gate/filter assumed a trusted caller.** This ADR canonizes the audit lens for every future MCP-exposed primitive:

> **Before exposing a primitive on the interop surface, audit it against the foreign caller:** (a) does its permission gate distinguish the foreign caller from operator/Reviewer/headless? (b) is every substrate read/write scoped by `user_id` at the data layer, not only by a caller-trust assumption? (c) can a caller-supplied identifier (path, revision_id, slug) reach outside the caller's own scope? A "no" to any is a leak of the §D5 class.

### D6 — Per-request identity + shared-workspace (inherited from ADR-310, unchanged)

D4 (per-request identity — each operator authenticates as themselves; MCP calls reach *their own* judged substrate; no schema change) and D5 (shared-workspace is the separate, demand-gated, foundational `user_id → workspace_id` re-key — out of scope) survive from ADR-310 verbatim. This ADR adds nothing to them; it only relocates the *tool surface* onto primitives.

### D7 — Protocol-agnostic verbs (§7.5 decision)

Axiom 1 says "interoperability protocols (MCP)" — plural. The interop surface is canonized as **protocol-agnostic**: the **file + revision verbs are the contract**; MCP is the **first binding**. Direct-API and A2A are future bindings of the same verb contract. This costs nothing now (only the MCP binding is implemented) and means a second protocol never requires a surface reframe — only a new binding of the existing verbs.

## 3. Why revision-archaeology is the killer primitive

Revision-archaeology was *excluded* by the old canon as "not intent-shaped" (primitives-matrix line 276). Under D1, **exposing the attributed revision chain across the boundary is the single most differentiating thing the surface can do** — it is *attribution-as-structural* (ADR-209), made operable.

A foreign LLM asking "who authored this claim and how did it evolve?" exercises the Phase-1 moat (THESIS Commitment 4) directly. **No competitor's agent-filesystem has an attributed, walkable revision chain to expose.** A storage MCP server (Notion, Linear, GitHub) returns whatever is stored, no provenance, no history-with-authorship. YARNNN returns content + *who authored it* + *how it evolved* + (Phase 2) *whether it's been judged*. This is the agent-Dropbox's killer primitive, and §7.1/§7.3's "all three revision reads" decision surfaces it in full.

## 4. The phasing (both moats, clean — Resolution B)

| Phase | What ships | Moat | Primitive surface |
|---|---|---|---|
| **Phase 1** | The attributed agent filesystem, operable by any LLM | **Substrate moat** (Commitment 4) | `ReadFile` · `ListFiles` · `SearchFiles` · `QueryKnowledge` · `WriteFile` (gated, attributed) · `ListRevisions`/`ReadRevision`/`DiffRevisions` — all scoped to one operator (D6) |
| **Phase 2** | Judgment thickens | **Judgment moat** (Commitments 1–3) | *Same primitives.* `ReadFile` return gains judgment-standing; `WriteFile` already wakes the Reviewer (shipped, `2ef6721`). |
| **Phase 3** | Cross-operator / shared | (network) | *Same primitives.* Scope resolves to `workspace_id`; gate gains membership policy. |

**The primitive surface is identical across all three phases** — only return-richness (Phase 2) and scope-resolution (Phase 3) evolve. You never redesign the surface; you thicken what it returns and widen what it reaches. Governance for shared workspaces is a *gate-membership-policy* addition at the same ADR-307 gate — never a tool-surface redesign.

This is the **two-moats-phased** thesis made concrete: substrate is the Phase-1 face, judgment is the Phase-2 face; the four THESIS legs remain the definition of autonomy — the sequence is rollout, not re-rank. **Discipline this imposes:** judgment-as-Phase-2 must stay a *first-class* moat, not a starved one — the substrate-moat thesis only holds if the judgment face stays excellent.

## 5. The boundary that makes this safe (ADR-222 substrate↔kernel line)

The foreign LLM **operates the substrate (the filesystem commons) but not the kernel machinery** (workforce / lifecycle / Reviewer-control). The boundary is drawn at the ADR-222 substrate↔kernel line, *not* at the old "thinking-mode vs management-mode" line.

A foreign LLM is *userspace with a filesystem*; it is not the kernel. It can `ReadFile` / `WriteFile` / `ListRevisions` the commons; it cannot `Schedule` / `ManageAgent` / `ManageDomains` / drive the Reviewer — **because those aren't filesystem operations**, not because the LLM is "only thinking." This corrects the primitives-matrix line 276 rationale ("the user in a foreign LLM is in thinking mode, not workforce-management mode") to the dimensionally-correct one (kernel operations are not filesystem operations).

## 6. What this supersedes / amends (named — canon edits gated on operator approval of this ADR)

- **`docs/architecture/primitives-matrix.md`** — reverses two MCP-mode rules:
  - (a) MCP is now **primitive-shaped**, not intent-shaped. The MCP-mode column turns on for `ReadFile`, `ListFiles`, `SearchFiles`, `QueryKnowledge`, `WriteFile` (gate-locked), `ListRevisions`, `ReadRevision`, `DiffRevisions` — scoped to the commons. The three intent tools are removed from the surface description.
  - (b) Revision-archaeology primitives **ARE** exposed on MCP (was line 276: "deliberately NOT exposed … substrate-archaeology-shaped"). Reversed per §3.
  - The line-276 rationale corrects from "thinking-mode vs management-mode" to the substrate↔kernel boundary (§5).
- **ADR-310** — D1 two-faces survives; the "3 intent-shaped tools" implementation is superseded by the primitive surface. D2 disciplines survive (relocated onto primitives, §D3). D4 + D5 survive unchanged.
- **ADR-169** — fully superseded (completes the dissolution ADR-310 began).
- **THESIS.md** — sequencing note only (Resolution B): Commitment 4 = Phase-1 face, Commitments 1–3 = Phase-2 face; no commitment content change, no re-rank.
- **FOUNDATIONS** — Axiom 1's "files are the universal interface (MCP)" clause becomes *literally the product surface*, not a stated benefit; Axiom 6's "Foreign LLM via MCP" Channel row's shape changes from "3 intent tools" to "file-primitive responses over the commons."
- **GLOSSARY** — add: **interop face** (the distribution channel of the one moat — judged substrate reached from any LLM), **the commons** (the operator's authored substrate slice the interop surface reads/writes — `/workspace/context/` + readable authored substrate, minus the MCP governance lock-set), **attributed agent filesystem** (the Phase-1 product noun — a filesystem where every revision carries `authored_by`, walkable across any LLM). The OS-framing vocabulary (kernel/userspace/syscall) already covers the rest.

## 7. Implementation phases

1. ✅ **The gate invariant (§D4)** — *already shipped* (`a33d062` no-op-gate fix + `0723e5a` cross-workspace revision-read fix + `DEFAULT_MCP_WRITE_LOCK_PREFIXES`). Regression gate `test_adr310_mcp_write_gate.py` 12/12. This ADR ratifies the shipped gate as the canonized "all-consequence-at-the-gate" invariant (operator §7.4 decision: ratify already-shipped gate, doc-first).
2. **This ADR** — doc-only ratification of the frame + the four §7 decisions + the §D5 audit lens.
3. **Canon cascade** (gated on operator approval of this ADR) — primitives-matrix reversal + Axiom 1/6 amendment + THESIS sequencing note + GLOSSARY terms.
4. **MCP binding rebuild** — delete the three intent tools from `api/mcp_server/server.py`; expose the primitive surface (D2) as MCP tools that dispatch through `execute_primitive` (the fourth caller, ADR-164 runtime-agnostic). Scope reads/writes to the commons; turn on the gate's MCP branch (already built) for `WriteFile`; expose the revision-archaeology reads. `api/services/mcp_composition.py`'s intent-composition helpers (`compose_subject_context`, `classify_memory_target`, `dispatch_remember_this`) dissolve — the foreign LLM composes intent itself.
5. **Phase 2 (judgment rider)** — `ReadFile` return gains judgment-standing when a verdict exists for the path. Additive; verdicts are already substrate.
6. **Phase 3 (cross-operator)** — DEFERRED, demand-gated (ADR-310 D5). The `user_id → workspace_id` re-key + membership + RLS. The primitive surface is unchanged; only scope-resolution + gate-membership are added.

## 8. Rejected alternatives

- **Keep the three intent tools** — a second vocabulary bolted on the kernel's file primitives (Singular Implementation violation). The intents are compositions the foreign LLM does itself; the hard "which-phase" questions dissolve at primitive altitude. Rejected (D1).
- **Path-scoped (allowlist) WriteFile instead of raw + lock-set** — the gate's lock-set already achieves the safety property as a blocklist (governance + Reviewer seat DENY, commons APPLY). An allowlist would be a parallel mechanism for the same outcome. Operator chose raw + lock-set (§7.1). Rejected.
- **Defer revision-archaeology to Phase 2 / `ListRevisions`-only** — revision-archaeology is the Phase-1 *killer primitive* (§3); deferring it starves the differentiator that's already shipped (ADR-209). Operator chose all three reads (§7.3). Rejected.
- **MCP-specific (non-protocol-agnostic) verbs** — would require a surface reframe when a second protocol (direct-API, A2A) arrives. Protocol-agnostic costs nothing now. Operator chose protocol-agnostic (§7.5). Rejected.
- **Hold the ADR until the binding rebuild also ships** — risks a large undocumented in-flight change on shared `main`; the gate invariant is already shipped and is the load-bearing safety property, so doc-first ratification is honest about done-vs-owed. Operator chose ratify-now (§7.4). Rejected.
