# ADR-220: Authored Substrate in the Directory Registry

> **Status**: **Implemented** (2026-04-26).
> **Date**: 2026-04-26
> **Authors**: KVK, Claude
> **Dimensional classification**: **Substrate** (Axiom 1) primary — closes the read-side coverage gap so agents reason against operator-authored truth — with secondary **Identity** (Axiom 2, Operator authorship preserved through the registry contract).
> **Extends**: ADR-152 (Unified Directory Registry — adds one declarative field), ADR-151 (Shared Context Domains — operator-authored files are first-class alongside agent-managed synthesis), ADR-188 (Domain-Agnostic Framework — registry remains a curated template library, not a validation gate).
> **Implements**: docs/alpha/observations/2026-04-26-trader-e2e-paper-loop.md §A1 (the load-bearing gap that surfaced when the alpha-trader Analyst + Writer agents reported `_operator_profile.md` and `_risk.md` "absent" despite both files being present in the workspace).
> **Preserves**: ADR-141 pipeline shape, ADR-209 Authored Substrate semantics, ADR-176 capability split.

---

## Context

In the alpha-trader E2E run on 2026-04-26 (full report linked above), the trader pipeline executed end-to-end — substrate scaffolded, tasks fired, deliverables produced, AI Reviewer ran the full Simons 6-check framework, the autonomy ladder gated correctly. One gap was load-bearing: **two agents (Analyst, Writer) reported the operator's declared substrate as absent in their reasoning**, despite the files existing on disk.

Concretely:

- `/workspace/context/trading/_operator_profile.md` (4145 chars, signal definitions + universe + R-targets)
- `/workspace/context/trading/_risk.md` (1910 chars, decay thresholds + per-position limits)
- `/workspace/context/trading/_performance.md` (when accumulated, money-truth ledger per ADR-195 v2)

…all exist. The pipeline's `_gather_context_domains()` in `task_pipeline.py` injects:

1. The synthesis file declared in the directory registry (`overview.md` for trading — agent-managed, currently 84-char placeholder).
2. The tracker file (`_tracker.md`) when the domain has entity tracking.
3. A budget-bounded sample of entity files (`{ticker}.md` × N).

It does **not** inject `_`-prefixed operator-authored files. The agents have `ReadFile` available and *could* fetch them, but their prompts don't name those files as canonical reads — so they reason against (synthesis + tracker + entities) only and conclude "operator profile absent."

This is the gap between **"we wrote the files"** and **"the agent reasons over them."** The Reviewer's narrowing condition then fires on a phantom missing substrate, and the loop produces honest-but-blocked output ("BOOTSTRAP-BLOCKED — _operator_profile.md absent") despite the workspace being correctly populated.

The persona's identity *is* in those files. For the trader, `_operator_profile.md` is the system. Not having it in-prompt makes the Analyst structurally unable to evaluate signals. The same will be true for commerce (`_pricing.md`, `_inventory.md`), portfolio (`_summary.md`), or any future domain where operator authorship is the source of truth and agents are tenants reasoning against it.

---

## Decision

### D1 — Directory registry gains one declarative field: `authored_substrate`

`WORKSPACE_DIRECTORIES[domain]` adds an optional field declaring `_`-prefixed operator-authored files the pipeline injects verbatim alongside the synthesis when a task reads that domain.

```python
"trading": {
    "type": "context",
    "path": "context/trading",
    # … existing fields …
    "synthesis_file": "overview.md",         # agent-managed, cross-entity summary
    "tracker_file": "_tracker.md",           # entity index (existing convention)
    "authored_substrate": [                  # NEW — operator-authored canonical reads
        "_operator_profile.md",
        "_risk.md",
        "_performance.md",
    ],
},
```

The list is **canonical paths within the domain folder**. Files declared here are read on every task that includes the domain in `context_reads`, with the same content-budget treatment as synthesis (capped per file). Order in the list is presentation order.

`authored_substrate` defaults to `[]` (empty) — no behavior change for domains that don't declare it. ADR-188's "registry as curated template library" framing holds: domains that operate without canonical operator authorship (Slack/Notion temporal, knowledge corpora) declare nothing here.

**Why a registry field, not a per-task TASK.md declaration**: operator-authored substrate is a *property of the domain*, not of any one task. Every task that reads `trading` reasons against the same operator-declared signals + risk; declaring once at the registry level is singular implementation. ADR-176's universal-roster principle applies — workforce composition is contextual, but the substrate-shape framework is fixed.

### D2 — Helper `get_authored_substrate(key) -> list[str]` in `directory_registry.py`

Mirrors the shape of `get_synthesis_content` and `get_tracker_path`. Returns the declared list verbatim, or `[]` for domains without the field. Keeps the registry-shape API surface uniform — every "what's in this domain" question goes through one helper, never a raw `WORKSPACE_DIRECTORIES[k].get(...)` access from the pipeline.

### D3 — Pipeline injection in `_gather_context_domains()`

Authored substrate reads insert a new step **between** synthesis (Step 1) and entity loading (Step 2) in `_gather_context_domains()`:

```
Step 1: synthesis file (existing — agent-managed cross-entity summary)
Step 1b: authored substrate files (NEW — operator-declared canonical reads)
Step 2: entity files (existing — primary summary or objective-matched)
```

Rendered into the same `## Context Domain: {key}` section the pipeline already builds, but each authored file gets its own `### {filename} (operator-authored)` subsection so agent prompts can distinguish operator truth from agent-managed synthesis. Token budget: each authored file shares the same `max_content_per_file` cap (3000 chars) used for synthesis.

The agent prompt sees:
```
## Context Domain: trading

### overview.md (synthesis, updated 2026-04-26)
…cross-entity summary written by tracker over time…

### _operator_profile.md (operator-authored)
…full operator-declared signals, universe, R-targets…

### _risk.md (operator-authored)
…full operator-declared decay thresholds, position limits…

### _performance.md (operator-authored)
…money-truth ledger if it has accumulated…

### {ticker entity files…}
```

This makes operator authorship structurally legible in every prompt that touches the domain, without changing how agents *write* (synthesis is still agent-managed; authored substrate is still operator-managed; ADR-209 attribution preserved on both).

### D4 — No new ADR-209 author tag, no new authoring path

`authored_substrate` declares **paths the pipeline reads**. Authoring is unchanged: the operator (or YARNNN on the operator's behalf via `UpdateContext`) writes these files using the existing authored-substrate write path (`write_revision`, `authored_by="operator"`). The registry doesn't touch how files get written — it touches how they get read.

This preserves singular implementation: one write path (`services.authored_substrate.write_revision`), one read injection (`_gather_context_domains`), one registry source of truth.

### D5 — Trading + portfolio + commerce + revenue + customers seeded in this commit

In the same commit as the registry-field landing, the four currently-active domains that have operator-authored files declare them:

```python
"trading":   ["_operator_profile.md", "_risk.md", "_performance.md"]
"portfolio": ["_performance.md"]      # money-truth lives here in commerce flavor too
"commerce":  ["_pricing.md", "_unit_economics.md", "_performance.md"]    # placeholders for now; populated when alpha-commerce E2E runs
"revenue":   ["_performance.md"]
"customers": []                       # no canonical authored substrate today
```

Empty lists for domains not yet using the pattern remain harmless. When alpha-commerce runs and those `_pricing.md` / `_unit_economics.md` files come into existence, the pipeline picks them up automatically — no further code change needed.

### D6 — Out of scope

- **Authoring UI for `_*.md` files in /context surface.** Operator-authored files are already editable via the existing `UpdateContext` primitive and the `/context` surface; this ADR doesn't change either.
- **Validation that authored files exist.** Files declared in `authored_substrate` may legitimately be absent during early workspace bring-up (operator hasn't written them yet). The pipeline handles absence gracefully — same shape as missing synthesis (skip the section).
- **Cross-domain authored substrate (e.g., `_shared/MANDATE.md`).** Already injected by other paths (`workspace_paths.py`'s `MANDATE_PATH` is read in agent prompt assembly per ADR-207). This ADR scopes to per-domain authored substrate only.

---

## Consequences

### Positive

- **Operator authorship structurally legible.** Every agent reading the trading domain sees `_operator_profile.md` in its prompt. The Analyst can now evaluate signals against the operator-declared rules without needing tool rounds to discover them. The Writer can compose pre-market briefs with portfolio limits in scope. The pre-market brief stops saying "BOOTSTRAP-BLOCKED" when the substrate is in fact authored.
- **Singular implementation.** One registry field, one helper, one injection point. No parallel "operator-authored" storage. No second registry. ADR-188's template-library framing preserved — registries declare *shape*, workspaces fill *content*.
- **Composable across domains.** Same field, same helper, same injection — works for trading, commerce, portfolio, customers, revenue, and any future domain that wants the pattern. Adding a new authored-substrate file to a domain is one registry edit + one operator write.
- **No prompt surface change for agents.** Agents continue to use the same context format (`## Context Domain: {key}`) — they just see more authored content per domain. No new tool, no new instruction, no new model behavior to learn.

### Negative / risks

- **Token budget pressure.** Each domain that declares 3 authored files at 3000 chars each adds ~9KB of operator-authored content per domain read. For a task with `context_reads: ["trading", "portfolio"]` the prompt grows by ~12-18KB. Mitigation: per-file cap stays at 3000 chars (same as synthesis); operator-authored files that grow beyond that get truncated like everything else. If the pressure becomes a real problem, a follow-up ADR can introduce per-domain `authored_substrate_budget`.
- **Operator-authored file discovery.** A future operator might write a `_constraints.md` and expect agents to read it without registering the path. Mitigation: this is the same discovery problem that already exists for `_tracker.md` — convention is documented in `workspace-conventions.md`, registry declaration is the canonical mechanism.

### Out of scope (deferred)

- **Per-task overrides.** A task that wants only `_operator_profile.md` (not `_risk.md`) cannot declare that today. Skipped because the use case hasn't surfaced — domains with overlapping authored substrate sets are likely cohesive in practice. If a real conflict arises, add `authored_substrate_skip: list[str]` to TASK.md as a follow-up.
- **Lazy reads with summaries.** Today every authored file gets fully injected (capped). Future optimization: emit a one-line summary of each, agent uses `ReadFile` to expand on demand. Defer until token economics demand it; the alpha-trader run shows current shape is workable.

---

## Validation

The validation criterion is the same E2E that surfaced the gap. After this ADR lands and the registry seeding is applied, re-running `signal-evaluation` (or any task with `context_reads` including `trading`) must produce output that reasons against the operator-declared signal rules — not output that says `_operator_profile.md` "absent."

Expected post-fix behavior:
- Analyst reads `_operator_profile.md` from prompt context, sees Signal 1–5 with full entry conditions, sizing rules, R-targets.
- Analyst evaluates signals against current ticker state (when ticker state is populated; that's a separate gap — Tracker needs real market data, not solved by this ADR).
- Writer reads `_risk.md`, surfaces decay thresholds and position limits in the pre-market brief instead of "Cannot evaluate — `_risk.md` absent."

If the agent still says "absent" after this lands, the registry seeding or the helper wiring is wrong — that's the test gate.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-04-26 | v1 — Initial proposal + Implementation. Registry field + helper + `_gather_context_domains` injection step + 5-domain seeding (trading, portfolio, commerce, revenue, customers). One commit per the singular-implementation rule. |
