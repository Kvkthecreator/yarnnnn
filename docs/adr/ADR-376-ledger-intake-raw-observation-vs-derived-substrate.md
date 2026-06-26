# ADR-376 — Ledger Intake: Raw Observation vs Derived Substrate

> **Status**: **Accepted** (2026-06-26). Foundational (a FOUNDATIONS amendment); phased, conformance-per-transport. **MCP slice IMPLEMENTED** (2026-06-26): `inbound/` root + raw-lane routing (`inbound/mcp/{client}/{slug}.md`) + derive-and-cite placement wake + recall/trace re-spec (derived-first, `derived_from` walk). Gate `test_adr376_ledger_intake.py` 7/7; `test_adr368_memory_surface.py` 10/10; live `probe_mcp_memory_surface.py` 11/11. Built on the merged ADR-373 re-key (no keying coupling — `inbound/` writable under today's class-default policy; per-`{client}` sublane is a convention the per-principal grant later enforces). Remaining transports (uploads recognized; perception/connectors/chat/A2A) are follow-on slices against the same ratified invariant.
> **Date**: 2026-06-26
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: [`docs/analysis/the-ledger-intake-axiom-raw-observation-vs-derived-substrate-2026-06-26.md`](../analysis/the-ledger-intake-axiom-raw-observation-vs-derived-substrate-2026-06-26.md) — the axiom, the four-path intake audit (the receipt that proves it load-bearing), the `operation/memory/` re-examination, and the five open questions (all five settled below).
> **Sibling**: [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) (the multi-principal re-key). The two are siblings from the same discourse week: **per-observation intake (this ADR) ‖ per-principal authorization (ADR-373)** — both collapse an N-shaped problem into "N is data" (*one intake model, the source is data* ‖ *one model, the principal count is data*). This ADR **strengthens** ADR-373's D5 (single-writer / steward-reconciliation) by giving its "different principals write different paths → steward reconciles into its own `reviewer:` revision" reasoning its literal two-object form (raw contributor-objects → derived seat-object). It **evolves** ADR-373's *de facto* `operation/memory/` raw region (D3 table, "in practice") into the named `inbound/` raw lane — a namespace evolution, not a contradiction (§6).
> **Amends**: [FOUNDATIONS](../architecture/FOUNDATIONS.md) — Axiom 1 ninth sub-clause + Derived Principle 32 (v9.12). This ADR is what those reference (it replaces the `ADR-PENDING` placeholders written at amendment time).
> **Preserves**: [ADR-209](ADR-209-authored-substrate.md) (the single write path `write_revision()` — the raw lane and the derived object are *both* ordinary attributed revisions; no new write path), [ADR-286](ADR-286-single-writer-per-path.md) (single-writer — the raw lane is per-principal single-writer; the derived object is seat single-writer), [ADR-320](ADR-320-constitution-region-topological-cut.md)/[ADR-366](ADR-366-autonomy-mode-as-execution-breadth.md) (`inbound/` joins `uploads/` *outside* the constitution/operation/governance cut — it does not add a sixth semantic-class root inside the cut), [ADR-330](ADR-330-ground-truth-intake.md) (the outcome-attestation discipline this generalizes — outcomes keep their event-row raw form), [ADR-335](ADR-335-perception-field.md) (the perception form-contract this completes on the retention axis), [ADR-368](ADR-368-memory-first-interop-surface.md) (the memory verbs + placement seat — placement evolves from *rewrite-in-place* to *derive-and-cite*), [ADR-357](ADR-357-citation-binds-to-source-not-internal-path.md) (DP31 — the output twin; this is the input twin).
> **Dimensional classification** (Axiom 0): **Substrate** (Axiom 1 — *how* state evolves: raw retained, understanding derived-and-citing) + **Purpose** (Axiom 3 — the derive step is a purposeful act distinct from capture).

---

## 1. The decision in one sentence

**Every contribution to the substrate enters as an attributed raw observation; what the workspace makes of it is a separate, attributed, derived act; the raw is never rewritten and the derived always cites its source — `retain + attribute + cite`, system-wide across every context-in transport.**

This is **how context enters the kernel at large** — not an MCP feature. It is the one git property the authored-substrate floor (ADR-209) did not yet carry: *a commit never silently overwrites what it records*. The raw observation persists as its own object, distinct from the understanding derived from it — which is what turns the moat's headline (*which principal contributed each version, and how the seat reconciled them*) from **approximately** legible (in-place edit history) to **structurally** legible (raw contributor-object → derived seat-object, walked by a structured `derived_from` citation).

## 2. Why this is foundational (a FOUNDATIONS amendment, not a feature)

The discourse escalated from an MCP-scoped raw-vs-processed question to an axiom because the raw/derived separation is a property of **the ledger** (the three-rung framework's Rung 1), not of any one transport. Seven transports feed context in today (MCP `remember`, platform connectors, human uploads, the perception field's web/RSS watches, ground-truth intake, chat, A2A-spec'd). An intake discipline that lives in the MCP layer is in the wrong place. The amendment lands as:

- **Axiom 1, ninth sub-clause** — *the raw observation is retained; understanding is a separate derived act* — the retention/separation completion of the eighth sub-clause (ADR-335: reality enters only as an observation). The eighth fixes the *form* reality takes entering; this fixes that the observation *persists* distinct from the understanding derived from it.
- **Derived Principle 32** — the full derivation, the audit, the diagnostic test, and the dull-rule dividend.

## 3. The audit that proves it is load-bearing (the receipt)

Of the four substrate-writing intake paths, **two already obey the axiom and are clean; two violate it with the exact predicted symptoms.** (All verified against the live repo 2026-06-26; receipts in the discourse base §3.)

| Path | Raw lands | Derived lands | Obeys? | Symptom if not |
|---|---|---|---|---|
| **Uploads** (human) | `uploads/{file}` — immutable, `managed_by: user`, outside the topology cut | reasoned-against; never rewritten | ✅ | — |
| **Ground-truth** (ADR-330) | raw outcome event-rows (attested) | `operation/{domain}/_money_truth.md`, regenerated | ✅ | — |
| **MCP `remember`** | `operation/memory/{slug}.md` | *same file, rewritten in place* by the placement wake | ❌ **conflates** | foreign origin demoted to a parent-pointer; cross-principal `trace` approximate, not structural |
| **Web/RSS watch** (ADR-335/336) | **nothing** — only the distilled `_watch_signal.yaml` is kept | the signal | ❌ **discards** | a signal's driving observation is unrecoverable; the watch is unfalsifiable |

**The two clean paths are the axiom already discovered twice** — `uploads/` and ground-truth each independently arrived at "keep the raw, derive separately." The axiom names what they share and demands the other transports match. **The two violations have different failure modes (conflate vs. discard), both fixed by the same rule.** This is the strongest possible evidence the axiom is real: where it is obeyed the substrate is clean; where it is broken the symptoms are exactly what the axiom predicts.

## 4. The decisions (the five open questions, settled)

### D1 — Form: a 9th Axiom-1 sub-clause + Derived Principle 32 (not DP-only)

Mirror how ADR-335 landed (8th sub-clause + DP27): the retention invariant gets a sub-clause under Axiom 1 *and* a DP carrying the derivation. Most discoverable from Axiom 1's body; consistent with the DP25/DP27 precedent. **Done** in the v9.12 amendment.

### D2 — Raw namespace: `inbound/` sibling to `uploads/` (not a fold-in, not deferred)

The raw lane for **machine/external** contributions is a new root **`inbound/{transport}/{principal}/{timestamp}-{slug}.{ext}`** — e.g. `inbound/mcp/claude.ai/2026-06-26-acme-corp.md`, `inbound/slack/general/…`, `inbound/web/{source}/…`. Append-only, immutable, `authored_by` = the contributing principal. It is a **sibling to `uploads/`** (the *human* raw root), **not** a fold-in:

- Both sit **outside** the constitution/operation/governance topology cut (ADR-320) — `inbound/` joins `uploads/`, `agents/`, `working/` in the "not part of the cut" set. It is **not** a sixth semantic-class root inside the cut; the five-(six-)root permission topology is unchanged.
- `uploads/` keeps its shipped `managed_by: user` semantics untouched (least disruption — the chosen lean). The **model** is unified (`uploads/` is the N=human case of the same raw-lane shape) even though the **namespaces** stay separate. The human/machine provenance line is a *namespace fact*, not a path convention buried inside a human namespace.
- `CALLER_WRITE_POLICY` (per ADR-373 D3, the per-class default grant) grants each principal-class write to **its own** `inbound/{transport}/` sublane — single-writer-per-path at the sublane granularity (§6 reconciles this with ADR-373's table).

### D3 — Citation: a structured `derived_from`, not prose

When the derive step writes the understanding into `operation/` (or the program's structured tree), the derived object carries a **structured back-reference** — `derived_from: <raw path or revision-id>` — so `trace` walks raw↔derived **mechanically**. This mirrors DP31's `source_ref` (a citation binds to a resolvable referent). Prose citation would leave `trace` unable to walk the chain — weakening the very differentiator the axiom hardens. The structured field is what makes the multi-stage `trace` chain (*raw contributor → derived seat-object → ground-truth revision*) real rather than narrative.

### D4 — The invariant is `retain + attribute + cite`, NOT a uniform mechanism

The axiom governs the **invariant**; the **mechanism** (a file in `inbound/` vs. an attested event-row) is **per-transport**. This is what keeps it dull-correct rather than dull-overreaching:

- **Structured attested intake** (Axiom 8 outcomes, ADR-330) keeps its raw as **event-rows folded into a regenerated summary** — it is *not* forced into an `inbound/` file lane it does not need. It already obeys the invariant; recognized as an instance, not changed.
- **Unstructured contribution** (MCP, uploads, web, A2A) keeps its raw as **immutable files** in the raw lane.

The axiom says *raw is retained + attributed + cited*; it does **not** say *raw is always a file in `inbound/`*.

### D5 — Perception retention is bounded to CITED observations (not a crawl archive)

The web/RSS violation is fixed by retaining the observations a derived act **cites** — the evidence behind a judgment — **not** every fetched byte. A watch that distills 100 articles into one signal retains the articles it *cited*, not all 100. This bounds the raw lane's growth and keeps it honest: **the raw lane is evidence, not a crawl archive.**

## 5. `operation/memory/` is the concrete casualty (and the answer to "revisit it, or not")

`operation/memory/{slug}.md` is **one namespace doing two jobs**: the raw inbox (capture) **and** sometimes the derived home (when placement is "leave in inbox"). The axiom forbids one namespace being both — which is *precisely why* the ADR-368 placement wake has to **rewrite the dump in place** (there is nowhere else for the derived object to go). Conformance:

1. Route the raw MCP dump to **`inbound/mcp/{client}/…`** (immutable, `authored_by = yarnnn:mcp:<client>`).
2. Change the placement wake from **move/rewrite** to **derive-and-cite**: the seat reads the raw observation and authors a *new* `operation/…` object carrying `derived_from: <inbound path>`, attributed `reviewer:ai`. "Leave in inbox" becomes "no derived object yet" — the raw simply stays in `inbound/`, un-derived, which is legible (vs. today's ambiguous in-place file).
3. Re-spec `recall`/`trace`: read **derived-first, raw-as-citation**; `trace` walks `derived_from` to surface the *raw contributor → derived seat* chain.

This is **not a local rename** — it replaces an MCP-special-case (`operation/memory/`, an MCP-shaped name in an operation-shaped root) with the **transport-neutral raw lane** the axiom requires for all seven paths.

## 6. Reconciliation with ADR-373 (the sibling, Accepted same day)

ADR-373 is **strengthened, not contradicted**:

- **ADR-373 D3 grant table** names `foreign-llm (mcp) → operation/ commons … the operation/memory/ inbox **in practice**` (line 66) — *de facto* today's shape, not a permanent commitment. This ADR evolves the practice: the foreign-llm grant region becomes **`inbound/mcp/`** (plus the existing `operation/` commons for any non-dump writes). **ADR-373's grant table gets a one-line update** (the `foreign-llm`/`platform`/`a2a` default-grant regions point at their `inbound/{transport}/` sublanes for raw intake). This is additive to the per-class-default-grant model, not a restructure.
- **ADR-373 D5 single-writer** ("different principals write different paths; no two principals ever co-write one file") is made **more** true: per-principal `inbound/{transport}/{principal}/` sublanes are *more* sharply single-writer than a shared `operation/memory/`. No merge/CRDT — same exclusion, sharper.
- **ADR-373 D5 steward-reconciliation** ("both writes succeed, attributed, appear in `trace`; the steward reconciles them into its own `reviewer:` revision") **is** this ADR's derive-and-cite step, named. ADR-373 described the two halves (raw contributions ‖ derived seat-revision) and *relied on* their separation; this ADR makes the raw half immutable and the derived half citing. The sibling dependency is mutual: ADR-373's conflict-is-closed-by-construction argument is only literally true once the raw and derived are distinct objects — which is exactly what this ADR establishes.

**Net**: one one-line update to ADR-373's D3 grant table (raw regions → `inbound/` sublanes); no change to its decisions, its single-writer reasoning, or its re-key. The two ADRs compose.

## 7. Implications across the architecture (the totality — honest)

| Surface | Change |
|---|---|
| **FOUNDATIONS** | Axiom 1 ninth sub-clause + DP32 (done, v9.12). |
| **Topology (ADR-320/373)** | `inbound/` joins `uploads/` outside the cut; per-class default grants point raw regions at `inbound/{transport}/` sublanes. No new in-cut root. |
| **All 7 transports** | Conform to `retain + attribute + cite`. MCP (rewrite→derive-cite), perception (retain cited observations), connectors (sync lands raw in `inbound/{platform}/`, derive into `operation/`); uploads + ground-truth already conformant (recognized, unchanged); chat + A2A inherit. **Conformance is the work; the axiom is the spec.** |
| **`recall`/`trace`** | Derived-first, raw-as-citation; `trace` walks `derived_from`. Re-spec, not rebuild. |
| **Embedding** | Embed the **derived** layer (the understanding fuzzy recall ranks); raw is path/citation-addressed (a receipt). |
| **Four-flow model (DP26)** | "context-in" gains its first-class shape: the raw lane *is* what context-in writes; the derive step is the context-in→work boundary. |

**Explicitly NOT in scope** (the dull-rule dividend — savings stated so they are not silently re-added): no merge/CRDT/OT (raw lanes per-principal single-writer); no new authorization vocabulary (ADR-373's per-principal grant governs who-writes-which-`inbound/`-sublane); no format engine (a rule that doesn't care what's entering cannot generate format-specific machinery — the "variety of formats" problem **dissolves**).

## 8. Implementation slices (cheapest honest first, audit-driven order)

Fix the two **violating** paths first (they have symptoms); **recognize** the two conformant paths (no change).

1. **MCP (first slice — seam half-built, live test exists at `4946a45`)**: add the `inbound/` root + the `inbound/mcp/` grant; route raw dumps there immutably; change the placement wake to derive-and-cite into `operation/` with `derived_from`; re-spec `recall`/`trace` to derived-first + walk the citation. Ship behind the existing memory-surface gate.
2. **Perception (second slice)**: retain cited observations in `inbound/web/{source}/`; the distilled signal carries `derived_from` to the observations it cited.
3. **Connectors / chat / A2A**: conform as each lands its own follow-on, all against the one ratified invariant.
4. **Recognize** `uploads/` + ground-truth as instances (doc-only — they already obey).

Each slice is independently shippable; the axiom is ratified once (here) and inherited, not re-litigated per transport.

## 9. Open follow-ons (recorded, not blocking)

- **The `derived_from` field shape** — a single path/revision-id, or a list (a derived object synthesizing several raw observations)? (Lean: a list — synthesis is the common case; a single is the degenerate one.)
- **`inbound/` retention/GC policy** — raw is immutable, but is it permanent? (Lean: permanent for cited observations [they are evidence]; a GC pass may reclaim *un-cited, un-derived* `inbound/` entries past a horizon — but only those, and only with the same single-writer discipline.)
- **The ADR-373 D3 grant-table one-liner** — land it in ADR-373 directly (an amendment note) or carry it here as the authoritative statement? (Lean: an amendment note in ADR-373 pointing here, so its grant table stays self-consistent.)

---

## Diagnostic test (DP32, restated for implementers)

An intake path that **rewrites the contributor's raw in place**, that **discards the observation a derived act relied on**, or that lets a **derived `operation/` file omit its `derived_from` citation** — each violates this ADR. The fix is always the same shape: **land raw immutably + attributed; derive separately + citing.**
