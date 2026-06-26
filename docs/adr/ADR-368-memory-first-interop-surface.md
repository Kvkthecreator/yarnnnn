# ADR-368 — The Memory-First Interop Surface: remember / recall / trace

> **Status**: **Accepted** (2026-06-25). Operator-ratified through the discourse trail below.
> **Amended by [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) (2026-06-26)**: the placement seat (D5) is confirmed **workspace-level, not per-user** — exactly as the placement adapter's own code comment already stated. The wake-scope re-key (`wake_scope = auth.user_id → resolved workspace_id`) is the named one-line change when the workspace becomes multi-principal; the memory verbs, the dump→placement model, and the integrity wake are otherwise unchanged. Single-writer-per-path means a multi-principal commons needs no merge layer — semantic conflict across principals is reconciled by the seat (ADR-373 D5).
> **Date**: 2026-06-25
> **Authors**: KVK + Claude
> **Discourse base**: [`docs/analysis/mcp-interop-face-vs-topology-2026-06-25.md`](../analysis/mcp-interop-face-vs-topology-2026-06-25.md) — the smoke-test that exposed the gap, the strategic frame (the moat is settled), and the host-reality finding that consumer chat hosts chain only ~3–5 tool rounds per turn.
> **Supersedes**: [ADR-311](ADR-311-primitive-interop-surface.md)'s **D1 conclusion** (pure primitive surface; delete all intent tools; the host LLM composes intent by chaining). ADR-311's D3/D4/D5/D6/D7 (the substrate truths — riders-are-fields, all-consequence-at-the-gate, the foreign-caller audit lens, per-request identity, protocol-agnostic verbs) are **PRESERVED and relocated** onto this surface. Also completes ADR-311's never-built implementation.
> **Preserves**: [ADR-310](ADR-310-judged-substrate-interop-face.md) (one moat, two faces — unchanged), [ADR-209](ADR-209-authored-substrate.md) (attribution-as-structural — the thing `trace` surfaces), [ADR-320](ADR-320-constitution-region-topological-cut.md) + [ADR-366](ADR-366-autonomy-mode-as-execution-breadth.md) (the live permission topology — this surface gates against `CALLER_WRITE_POLICY["mcp"]`, not ADR-311's dead `DEFAULT_MCP_WRITE_LOCK_PREFIXES`), [ADR-307](ADR-307-unified-permission-taxonomy.md) (the single gate at `execute_primitive`).
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6 — the "Foreign LLM via MCP" Channel row's shape) + **Substrate** (Axiom 1 — what is served) + **Identity** (Axiom 2 — `external:<client>` / `yarnnn:mcp`, scoped to one resolved operator).

---

## 1. The two corrections to ADR-311

ADR-311 was right that the *substrate's nature is a filesystem* and that *revision-archaeology is the killer capability*. It made two errors, surfaced 2026-06-25 by a live smoke-test of the connector + a host-behavior audit:

**Correction 1 — the interaction model, not the substrate model, governs the tool surface.** ADR-311 reasoned: substrate is files → expose file *primitives* → the host LLM composes intent (`pull_context` = `QueryKnowledge → ReadFile → ReadFile`) the way Claude Code composes `Read → Grep → Edit`. The leap is "the host will chain." **It won't, reliably, on our actual target.** Claude Code is an *agentic* host (15+ autonomous tool rounds). claude.ai / ChatGPT / Gemini connectors are *consumer chat* hosts that — undocumented but observed — execute ~3–5 tool rounds before yielding to the user (research trail in the discourse base; Anthropic publishes no per-turn round limit for connectors). A pure-primitive read that *requires* chaining to compose an answer burns the round budget fetching and stalls — on exactly the hosts where the "follows you across rooms" magic is supposed to happen. **Multi-step composition must live server-side (inside YARNNN, an agentic context with no round limit), not client-side (inside a round-limited consumer host).**

**Correction 2 — the primary use case is memory, not delegation.** ADR-311 implicitly shaped the surface as "operate on the substrate." The operator resolved the prior-unanswered primary-use-case question (discourse base §Part 2): **YARNNN-in-a-foreign-LLM is first a portable memory that follows the user across rooms.** The user inside ChatGPT is already working *in ChatGPT*; their reach for YARNNN is "let this room see what I know" (read) or "save what we concluded" (write) — not "YARNNN, go do work" (delegation). Delegation-from-a-foreign-LLM is plausible but unproven and carries an unsolved technical hinge (the addressed-wake path is streaming, not a sync tool-return). **It is deferred** (see §6).

These corrections do **not** reopen the moat. The moat — authored substrate under a persona-bearing judgment seat, two faces (ADR-310) — is settled and was re-validated 2026-06-10 against June-2026 competitive evidence. This ADR fixes the *implementation* of the interop face, two generations stale.

## 2. Decision — three memory-shaped verbs, composed server-side

### D1 — The surface is the user's memory mental model, not the kernel's verb taxonomy

A person does exactly three things with a memory that follows them across rooms: **put something in, get something out, trace how it changed.** The tool surface is those three verbs, named in plain language:

| Tool | User says | What it does | Nature |
|---|---|---|---|
| **`remember`** | "remember this" · "save that" · "note that" | Dumps the observation to the memory inbox (`operation/memory/`), attributed `yarnnn:mcp`; the wake invokes the Reviewer to file it where it belongs (D5). Synchronous commit. | write · sync · ~$0 |
| **`recall`** | "what do I know about X" · "what did I say about Acme" | Returns the accumulated material on a subject — **composed server-side** (retrieve + rank) into a reason-ready bundle in **one round**. YARNNN returns the material; the *host LLM* explains it. | read · sync · ~$0 |
| **`trace`** | "when did I decide that" · "how has my thinking on X changed" · "who added this" | Returns the **authored history** of a fact — who authored it, when, what changed across revisions. The ADR-209 revision chain, surfaced across the boundary. | read · sync · ~$0 |

**`recall` returns; it does not synthesize.** This is load-bearing for the memory-first frame: the host LLM holding the conversation does the explaining, over what YARNNN returns. A tool named `explain` (or that composed an answer) would be the deferred delegation nature leaking in. `recall` connotes *retrieval*, and that is exactly the contract.

### D2 — The verbs are compositions over kernel primitives, server-side (the Singular-Implementation preserve)

ADR-311's correct instinct survives: there is **no second vocabulary.** `recall` and `trace` do not re-implement retrieval — they *compose the existing kernel primitives inside the MCP server*, in one round from the host's perspective:

| Verb | Server-side composition (existing primitives, ADR-168/209) |
|---|---|
| `remember` | `WriteFile(scope='workspace', path='operation/…')` + integrity wake (`submit_foreign_write_wake`) |
| `recall` | `QueryKnowledge(subject)` → rank → (optionally `ReadFile` top hits) → composed bundle |
| `trace` | resolve subject → path → `ListRevisions(path)` → `DiffRevisions(a,b)` for the spans of interest |

The kernel primitives (`ReadFile`/`SearchFiles`/`WriteFile`/`ListRevisions`/`DiffRevisions`) remain the substrate contract and remain available to *agentic* hosts that genuinely chain (Claude Code, Desktop) — exposed `defer_loading` so a consumer host is never forced to compose with them but a power-host can. **The three memory verbs are the front door; the primitives are the deferred back door.** This reverses ADR-311 D1's "delete all intent tools" while keeping its "one vocabulary, server-side composition" discipline — the compositions are server-side, so they are not a parallel implementation, they are the kernel primitives wearing the user's words.

### D3 — `remember` is a DUMP into the memory inbox — placement is NOT deterministic

The bug that triggered this ADR: `remember_this`'s five-target enum (`memory | identity | brand | agent | task`, inherited from the pre-topology `UpdateContext`) routed the **default** to `system/notes.md` and `identity` to `persona/`+`constitution/` — **both locked for the `mcp` caller** under the live topology ([`CALLER_WRITE_POLICY["mcp"]`](../../api/services/workspace_paths.py#L243): a foreign LLM writes the `operation/` commons + `agents/`/`working/`/`uploads/`; locked from `governance/`/`contract/`/`constitution/`/`persona/`/`system/`). Three of five enum targets were kernel-incoherent; the default happy-path was dead (proven: discourse base §0).

**The enum is deleted — and so is the temptation to replace it with a smarter deterministic router.** The first draft of this ADR fell into exactly that: it routed dumps into `operation/{domain}/notes.md` using an ADR-151 `competitors`/`market`/`relationships` keyword table. That was a second wrong guess — live workspaces are **program-shaped** (`operation/reports/`, `operation/trading/`, `operation/specs/`), not the domain fiction that table encoded; and a foreign LLM's free memory must NOT be filed into a *program's* structured output tree, which the foreign caller doesn't understand and could corrupt.

**The correction (operator-directed): placement is a JUDGMENT, not a route.** The MCP layer does not decide where operator-contributed content belongs. It **captures the dump** in a dedicated memory inbox — `operation/memory/{subject-slug}.md` (subject-organized so the Reviewer and `trace` see dumps grouped) or `operation/memory/inbox.md` (unscoped) — attributed `yarnnn:mcp`, with **no placement claim**. `about` only organizes the inbox; it is not final placement. The Reviewer then files it (D5). The ADR-151 `DOMAIN_KEYWORDS` table + `_classify_domain` are deleted; `DOMAIN_ALIASES` survives only to normalize the optional `domain` filter a host LLM may pass to `recall`. The gate is still the authority — but the surface now never even *tries* to route, so the gate is a backstop, not the first line.

### D4 — Operator-visibility is a named requirement of the surface (the gap ADR-311 missed)

A foreign write that the operator cannot see is not trustworthy, regardless of how cleanly it is gated. ADR-311 specified the write gate but not the operator's *awareness* of foreign in/outs. The smoke-test exposed two holes (discourse base §6, probe P4):

- **Hole A** — the MCP→narrative emitter was session-gated: `_emit_mcp_narrative` wrote nothing unless the operator had an *active* workspace session. The modal cross-room case (user writes from ChatGPT with no YARNNN tab open) left **no feed trace.**
- **Hole B** — no notification path existed on the MCP write at all.

**Requirement (this ADR):** every foreign invocation produces a **durable, session-independent operator-facing trace.** Concretely: the MCP narrative emitter writes to the operator's daily session (get-or-create), not only to an already-active one — so the entry is waiting in the feed whenever the operator returns. The richer signals (a batchable `external_contribution` notification tier; a Management-Plane "what entered from outside" lane derived from `authored_by LIKE 'yarnnn:mcp'`) are named as the forward path (§6) but Hole A's close is in-scope here. The durable record was always correct (`authored_by` on the revision + ADR-162 provenance comment); this closes the *in-the-moment* awareness gap so the **operator has parity with the seat** on what entered from outside.

### D5 — The wake INVOKES the Reviewer to PLACE the dump (placement is judgment)

`remember` commits the dump to the inbox, then `submit_foreign_write_wake` fires a `substrate_event` wake — but the wake is no longer validation-only. Its `hook.prompt` **invokes the Reviewer to reason about where the dump belongs against the actual workspace structure and FILE it there** (move/copy into the right domain, entity file, agent feedback, or wherever its subject lives), preserving the content and its `yarnnn:mcp` origin — and, while placing it, to judge it against authored ground-truth. If the memory genuinely belongs as free memory, the Reviewer leaves it in the inbox.

This is the deepest-correct version of the surface: **placement lives with the judgment seat, not the least-context foreign caller.** The Reviewer understands the workspace and can write everywhere the foreign caller can't (locked only from `governance/`+`system/`); the contributing LLM understood neither — which is *why* placement is the seat's, not the tool's. The pre-revision wake prompt ("evaluate… otherwise stand down") is replaced — it told the Reviewer to do nothing when the dump was fine, which is exactly the placement work we now want it to do.

**Eventually-async, never blocks.** The dump is captured the instant `remember` returns; the Reviewer files it shortly after on the paced wake-queue drain (ADR-298). The two-step is **git-legible** (the moat made operable): the dump's `yarnnn:mcp` origin survives on its inbox revision; the Reviewer's placement is a **separate `reviewer:<id>` revision**; the `trace` verb shows the whole chain — *"contributed via claude.ai → filed to `operation/competitors/acme` by your Reviewer."* This is the attribution differentiator (ADR-209) doing real work: a foreign contribution and its judged placement are two distinct, attributed acts the operator can audit.

**Cost note:** every dump triggers one Reviewer invocation. This is intended (placement is judgment) and bounded by the existing ADR-298 wake machinery (single-lane paced drain). The alternative — batch triage — was considered and rejected for this pass: it lags placement (a `recall` right after a `remember` would see the dump still un-filed), breaking the ambient promise. Judgment-first per operator decision.

### D6 — Gate, identity, audit lens, protocol-agnosticism: inherited from ADR-311, re-based on live canon

- **All consequence at the gate** (ADR-311 D4) — preserved, but re-derived against the **live** mechanism: the `mcp` caller traverses the single ADR-307 gate at `execute_primitive`; `_is_path_locked('mcp', path)` against `CALLER_WRITE_POLICY["mcp"]` (ADR-320/366) is the lock, replacing ADR-311's now-deleted `DEFAULT_MCP_WRITE_LOCK_PREFIXES`. Conclusion identical (a foreign write outside its writable roots → `governance_locked`); the documented mechanism is corrected. Note that with the dump model the surface only ever *constructs* `operation/memory/` paths, so the gate is a backstop, not the first line.
- **The foreign-caller audit lens** (ADR-311 D5) — preserved verbatim: before exposing any primitive on this surface, audit (a) does its gate distinguish the foreign caller? (b) is every read/write `user_id`-scoped at the data layer? (c) can a caller-supplied identifier reach outside scope? `trace` exposing `ListRevisions`/`DiffRevisions` re-runs this lens (the cross-workspace revision-read leak was already closed: ADR-311 §D4, commit `0723e5a`).
- **Per-request identity** (ADR-311 D6 / ADR-310 D4) — unchanged. Each operator authenticates as themselves; calls reach their own judged substrate. Shared-workspace re-key remains the separate deferred foundational change.
- **Protocol-agnostic verbs** (ADR-311 D7) — the three verbs are the contract; MCP is the first binding. A2A / direct-API are future bindings, no surface reframe.

## 3. Why memory-first is the right primary (the sequencing logic)

The choice between *memory-led* (Model A) and *genuinely-both* (Model C) was made on **reversibility under uncertainty**, not preference (discourse base §objective cross-comparison):

- **Model A is a strict subset of Model C.** Ship A, and adding the delegation verb later is purely additive — zero rework of `remember`/`recall`/`trace`.
- **A delivers the full *substrate* moat** — portable attributed memory (`remember`/`recall`) + revision-archaeology (`trace`) — at low cost and HIGH conceptual clarity.
- **C's extra (cross-boundary delegation) has an unsolved technical hinge** — the addressed-wake path is streaming ([`stream_addressed_wake` + `StreamingResponse`](../../api/routes/feed.py)), not a synchronous tool-return; a delegation verb would have to either block on YARNNN's loop within the host's tool-call timeout (relocating the round-budget problem) or return an ack the foreign LLM can't act on — **and** an unproven demand (Axis 5: the user in a foreign LLM is already working there; delegation implies wanting to *watch/steer*, which the foreign host can't render — the natural delegation surface is YARNNN itself).

When the primary is uncertain and one option is a cheap, clear, forward-compatible subset of the other, **ship the subset and buy information.** That is this decision.

## 4. The bright cut (what keeps the surface from feeling "muddy")

The operator named the failure mode of a both-natured surface: *muddy* — the user can't predict whether a call stores or does work. This ADR makes the cut **bright**:

> The foreign LLM **reads and writes a store** (`recall` / `remember`) and **traces its history** (`trace`). It does **not** silently trigger *operations* (the program's work). The wake on a `remember` does **housekeeping on the memory itself** — the seat files the dump where it belongs and checks it against ground-truth. That is the seat tending its own substrate, not YARNNN doing the operator's delegated work. The bright line holds: contributing memory ≠ commissioning work.

The current build's muddiness is precisely `remember_this`-silently-wakes-the-Reviewer read as "YARNNN did something" — a Model-B act wearing a Model-A name. The bright cut dissolves it: the wake validates a write; it does not perform delegated work.

## 5. What this supersedes / amends (canon edits — gated on this ADR's acceptance)

- **Supersedes** ADR-311 D1 (pure-primitive surface / delete-all-intent-tools / host-chains-to-compose). ADR-311 D3/D4/D5/D6/D7 preserved + relocated (see D6 above). ADR-311 status → **Superseded by ADR-368** banner.
- **Amends** FOUNDATIONS Axiom 6 (the "Foreign LLM via MCP" Channel row: shape = three memory verbs composed server-side, + deferred primitives, not "3 intent tools" nor "file-primitive responses").
- **Amends** `docs/architecture/primitives-matrix.md` (the MCP-mode rows: the user-facing surface is the three verbs; the primitives are deferred-exposed, not the front door).
- **Updates** `docs/features/mcp/` (tool-contracts.md + README.md + workflows.md) to the memory-first three-verb framing; fixes stale `context/` → `operation/` paths throughout (post-ADR-320 relocation).
- **Preserves** ADR-310 (unchanged), ADR-209, ADR-307, ADR-320, ADR-366, Axioms 1–9.

## 6. Deferred (the Model-C horizon, named so it slots in cleanly)

- **Delegation-from-foreign-LLM** (`work_on_this` reframed as "YARNNN, take this on" — an addressed wake into the operation that does work and reports back). Deferred pending: (a) resolution of the sync-vs-stream tool-return hinge, (b) demonstrated demand. Additive when it lands; the three memory verbs are untouched. **`work_on_this` is NOT shipped in this ADR** — shipping it as a read-bundle (its ADR-169 shape) would be the muddiness this ADR removes.
- **Operator-visibility richer tiers** (D4 forward path): `external_contribution` batchable notification; Management-Plane "what entered from outside" lane.
- **Second protocol bindings** (A2A, direct-API) of the same three-verb contract.

## 7. Implementation

1. `services/mcp_composition.py` — delete the five-target `classify_memory_target` enum + `dispatch_remember_this` locked-root routing; `remember` writes `operation/` only. Add `compose_recall` (Query→rank) + `compose_trace` (resolve→ListRevisions→DiffRevisions) server-side compositions.
2. `mcp_server/server.py` — replace the three ADR-169 tools with `remember` / `recall` / `trace` (memory-first descriptions, proactivity instruction carried in the description + server `instructions` block); delete `work_on_this`. Expose the kernel primitives `defer_loading` for agentic hosts.
3. `mcp_server/server.py::_emit_mcp_narrative` — make session-independent (write to the daily session, get-or-create) per D4 Hole A.
4. Docs cascade (§5) + CHANGELOG.
5. Regression gate + re-run the probe (round-trip to `operation/` + session-independent narrative + integrity wake).

## 8. Rejected alternatives

- **Pure primitives (ADR-311 as-ratified)** — rejected: requires consumer-host chaining the hosts don't reliably do; the ambient read degrades on the target hosts; proactivity has no carrier. (Correction 1.)
- **Composition-only, no primitives exposed at all** — rejected: gives up the revision-archaeology differentiator (ADR-311 §3) for agentic hosts. `trace` surfaces it via composition; the deferred primitives keep the full back door for power-hosts.
- **Genuinely-both now (Model C)** — deferred, not rejected: unsolved sync-vs-stream hinge + unproven demand; A is the forward-compatible subset (§3).
- **Keep `remember_this`'s five-target enum, fix only the default** — rejected: leaves `identity`→locked still broken and preserves the topology-incoherent enum; the enum is the disease, not the default. (Discourse base §4.)
