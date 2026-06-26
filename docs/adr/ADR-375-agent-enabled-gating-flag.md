# ADR-375 — `AGENT_ENABLED`: Gating the Steward Layer Behind One Flag

> **Status**: **Proposed** (2026-06-26). Doc-first. Backend: ~3 flag checks + one registry filter. No schema, no deletion, no new substrate. Reversible by toggling the flag.
> **Date**: 2026-06-26
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: [`interop-first-pivot-and-agent-gating-2026-06-25`](../analysis/interop-first-pivot-and-agent-gating-2026-06-25.md) §6 (the four chokepoints + the feasibility audit: "gating the agent is a feature-flag, not a rebuild") + [`the-three-rung-framework-and-the-multi-principal-wedge-2026-06-26`](../analysis/the-three-rung-framework-and-the-multi-principal-wedge-2026-06-26.md) (the steward is the gated rung; ledger+membrane are the base product).
> **Companion**: [ADR-374](ADR-374-presentation-ia-substrate-face-and-the-steward-posture.md) — that ADR sets the *target IA* when the steward is off; this ADR is the *switch*. They share one input (steward-presence) and ship together.
> **Preserves**: [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) (the substrate floor — gating the steward does not touch substrate; `write_revision` fires no wake, the producer is already decoupled from the consumer), [ADR-296](ADR-296-continuous-judgment-cycle.md)/[ADR-298](ADR-298-reviewer-wake-queue-and-pace.md) (the wake architecture — gated at its entry points, not modified), [ADR-307](ADR-307-unified-permission-taxonomy.md) (the gate is untouched; a foreign write still commits and still attributes when the steward is off — it just is not judged).
> **Dimensional classification** (Axiom 0): **Trigger** (Axiom 4 — whether the wake sources fire) + **Channel** (Axiom 6 — whether the steward surfaces appear).

---

## 1. The decision

**One environment flag, `AGENT_ENABLED` (default unset → treated per deployment policy), gates the steward layer at four pre-isolated chokepoints. When off: nothing wakes the Reviewer, and the steward surfaces vanish from the nav. The substrate floor (ledger + membrane) runs identically — files write, revisions attribute, the interop face serves cross-LLM, connectors ingest — with zero steward dependency.**

This is what makes the interop-first launch real (interop-first-pivot §2): the base product ships with the steward gated to beta; the flag flips per-workspace (or per-deploy) when trust + substrate density warrant exposing judgment.

## 2. Why this is a flag, not a rebuild (the seam was pre-cut)

The feasibility audit (interop-first-pivot §6 Finding 2) found the architecture already cut this seam:

- **`write_revision()` contains zero wake/Reviewer calls** — the producer (file writes) is decoupled from the consumer (the steward) by a scheduler poll, not a synchronous call. Writing a file fires nothing. (The one synchronous write→wake site is the MCP foreign-write adapter, deliberately isolated and "never raises" — substrate commits regardless of wake outcome.)
- **DB schema is cleanly partitioned** — substrate tables and agent tables (`wake_queue`, `action_proposals`, `execution_events`) share only `auth.users` (post-ADR-373: only the workspace membership). No cross-layer FKs. Agent off → agent tables stay empty (no migration); independently safe.
- **Frontend nav is 100% backend-driven** — filtering the surface registry removes steward surfaces from the UI with zero FE code change.

So the flag is ~3 checks + a list filter, not a fork.

## 3. The four chokepoints (confirmed against live code, 2026-06-26)

| # | Chokepoint | Symbol : line | Action when `AGENT_ENABLED` is OFF |
|---|------------|---------------|-------------------------------------|
| 1 | Scheduler **drain + hook-walker + due dispatch** (the cleanest single gate) | [`unified_scheduler.py`](../../api/jobs/unified_scheduler.py): `dispatch_due_invocations` (:317 call), `walk_hooks` (:335 call), `drain_all_users_with_pending` (:371 call) — all inside `run_unified_scheduler` | Wrap the block in `if AGENT_ENABLED:` → nothing ever wakes the Reviewer. **Gate the walker AND the drain as a unit** (interop-first-pivot §7 risk 2: gating only the drain leaves flagged-off workspaces silently accumulating undrained `wake_queue` rows). |
| 2 | Wake **enqueue** gateway (belt-and-suspenders) | [`wake.py:118`](../../api/services/wake.py#L118) `submit_wake_proposal` | Early-return disabled. #1 alone suffices; #2 makes the off-state defensive (no row ever enqueued). |
| 3 | Addressed (chat→Reviewer) path | [`feed.py:1126`](../../api/routes/feed.py#L1126) `wake_sources.addressed.stream` (+ manual-fire callers in `routes/agents.py`, `routes/recurrences.py`, `routes/admin.py`) | Per ADR-374 D2: the base product has no native chat, so the addressed path has no caller. If a thin assistant ever exists, it must not reach this path when the flag is off. |
| 4 | Surface catalog (nav) | [`kernel_surfaces.py:203`](../../api/services/kernel_surfaces.py#L203) `KERNEL_SURFACES` | Filter out the steward-coupled surfaces. Backend-driven → zero FE change. |

**Filter at #4 — steward surfaces (off):** `agents`, `queue`, `notifications`, `autonomy`, `program`, `recurrence`, `expected-output`, `activity`.
**Keepers (always on — ledger + membrane + constitution mirrors):** `files`, `context`, `connectors`/`sources`, `settings`/`workspace-settings`, `identity`/`mandate`/`principles`, `home` (substrate-forward empty state per ADR-374 D1/D3), `budget`.

## 4. The decisions

### D1 — `AGENT_ENABLED` is the single steward-presence input

One flag, read at the four chokepoints. It is also the input ADR-374 reads to choose the at-rest face (membrane when off, operating cockpit when on). **One source of truth for steward-presence** — no per-chokepoint divergence.

### D2 — Gating granularity: per-deploy now, per-workspace forward-compatible

Ship as an **environment flag** (per-deploy) for the launch shape (the whole deployment is interop-first; the steward is beta-gated globally). The flag's *consumers* should read it through a single resolver (`is_agent_enabled(workspace_id=None)`) so that when density-gating arrives (interop-first-pivot §5 decision 3 — open the beta per-workspace on substrate density), the resolver gains a per-workspace branch **without touching the four chokepoints.** Per-workspace is forward-compatible, not built now.

### D3 — OFF degrades to substrate-only; nothing breaks, nothing is judged

When off: a foreign `remember` still commits to `operation/memory/` and still attributes `yarnnn:mcp` (ADR-307 gate + ADR-209 write path are untouched) — it simply is **not placed/judged** (the wake never fires). `recall`/`trace` work fully (they read substrate, no steward). Connectors ingest. Files/revisions/the interop face are complete. **The base value loop closes with zero steward dependency** (interop-first-pivot §4 invariant). The dump waits in the inbox; if the flag later flips on, the steward's first drain picks up the accumulated inbox — graceful, no data loss.

### D4 — No deletion; the steward layer is dormant, not removed

Gating is `if`-guards + a registry filter. The wake architecture, the Reviewer, the proposal/queue stack all remain in the codebase, untouched, dormant. This preserves single-codebase / no-fork (interop-first-pivot §2: the fork is rejected; the flag solves brand-isolation at a fraction of the cost) and makes the beta a flip, not a re-integration.

## 5. What this does NOT do

- **Does not touch substrate, the gate, the write path, or attribution.** Off-state writes still commit + attribute; they are just unjudged (D3).
- **Does not delete the steward layer** (D4) — dormant, not removed; no migration to flip on.
- **Does not decide the IA** — that's ADR-374. This decides the *switch*; that decides the *face*.
- **Does not build per-workspace density-gating** (D2) — forward-compatible via the resolver, demand-gated.
- **Does not gate the substrate_event MCP→wake adapter separately** — it is reached only via #2's `submit_wake_proposal`; gating #2 covers it. (The adapter "never raises," so even if reached, the dump already committed — D3 holds.)

## 6. Implementation sequencing (doc-first)

1. This ADR + ADR-374 (they share the steward-presence input).
2. `is_agent_enabled(workspace_id=None)` resolver (one module; env read now, per-workspace branch deferred).
3. The four chokepoint guards (§3) — #1 (walker+drain unit) and #4 (registry filter) are the load-bearing two; #2 defensive; #3 is no-op while base has no chat (ADR-374 D2).
4. Verify off-state: foreign `remember` commits + attributes + does NOT wake; nav shows only keepers; Home reads as the membrane face.
5. **Render parity** (CLAUDE.md §5): `AGENT_ENABLED` must be set consistently on **API + Unified Scheduler** (the scheduler is where chokepoint #1 lives — a drift where the API thinks agent-off but the scheduler still drains is the exact failure mode the parity check exists to catch). MCP server + render gateway are unaffected (they hold no wake-trigger).
6. Regression gate `api/test_adr375_agent_gating.py` — off-state: no wake enqueued on a foreign write; registry excludes steward surfaces; substrate write still commits + attributes.

No code until this ADR ratifies.

## 7. Rejected alternatives

- **Fork the repo (the original "freddyy.ai" proposal).** Rejected (interop-first-pivot §2) — a permanent porting tax; the flag solves the same brand-isolation at a fraction of the cost. If an escape hatch is wanted, a tagged git snapshot, not a maintained fork.
- **Delete the steward layer for the base build.** Rejected (D4) — re-integration cost on beta; dormant-behind-a-flag is reversible.
- **Gate only the drain, not the walker.** Rejected (interop-first-pivot §7 risk 2 / §3 #1) — flagged-off workspaces would silently accumulate undrained `wake_queue` rows. Gate the walker+drain block as a unit.
- **Per-workspace gating from day one.** Deferred (D2) — forward-compatible via the resolver; density-gating is demand-gated (interop-first-pivot §5 decision 3), not launch-critical.
- **A surface-level-only gate (hide the tabs, leave the wakes firing).** Rejected — the steward would still act in the background on an "agent-off" workspace, burning budget and producing proposals no surface shows. The Trigger gate (#1/#2) is the load-bearing one; #4 is cosmetic without it.
