# Primitive Surface & Agent-Setup Re-assessment — YARNNN vs the Claude Code Reference Harness

**Date**: 2026-06-12
**Trigger**: the narrative shift across one week — ADR-337 shipped the working-tree verbs (debugging/testing register), the housekeeping-genesis eval exercised them organically, the round-economics audit reframed the question from "do the verbs work" to "is perception economical," and ADR-339 fixed the contract. The natural next register is systematic: **re-assess the whole primitive surface + agent setup against the strongest extant reference harness (Claude Code), as a dedicated topic.**
**Source base**: `docs/analysis/src_claudeCC/` (Claude Code source snapshot, March 2026) + `docs/analysis/claude-code-prompt-discipline-comparison-2026-05-26.md` (prior comparison: prompt-envelope, error surfacing, loop completion, memory aging) + `docs/analysis/wake-round-economics-audit-2026-06-12.md` (fresh receipts).
**Discipline rule** (inherited from the 2026-05-26 doc): not conformance theater. Every item is one of (a) **confirm** a YARNNN derivation against independent precedent, (b) **sharpen** an under-specified derivation, (c) **invert** a default the comparison shows was backwards, (d) **original territory** — Claude Code has no analogous concern. Plus the ADR-225 lesson: **demand-pull** — nothing ships without a named consumer or a named trigger.

---

## 0. What is already settled (do not re-derive)

| Borrowed / rejected | Where ratified |
|---|---|
| Typed prompt-section registry + static/dynamic boundary + `DANGEROUS_` friction | ADR-302 D5/D6 (from `systemPromptSections.ts`, `prompts.ts:560-577`) |
| `is_error: true` always-surface; no mid-loop intervention; round budgets as cost ceilings | ADR-303 (from `query.ts:140`, `query.ts:674`) |
| Memory aging with human-readable warnings | ADR-302 era (from `memdir/memoryAge.ts`) |
| Parameter contracts follow Claude Code shapes where trained priors exist; names + safety semantics are YARNNN's | ADR-337 decision rule (EditFile ≈ Edit) |
| Tool-output-drop-first compaction; filesystem-as-memory; compact index | ADR-221, ADR-159 |
| Recursive metadata listing; exact-search legibility; batching as capability doc | ADR-339 (yesterday) |
| Rejected: token-budget anchors in prompts; per-MCP-server prompt sections; streaming tool-exec overlap | 2026-05-26 doc §"should NOT adopt" |

---

## 1. Perception (post-ADR-339 state)

**Verdict: (c)-inverted yesterday; now (d) original-territory ahead.** The audit proved the pre-339 surface had a better ledger than git and a worse `ls` than POSIX; ADR-339 closed it. Post-fix, attribution-shaped questions ("what did the Reviewer touch since yesterday") are one indexed call — no Claude Code composition (`find` + per-path `git log`) matches that, and git only sees committed state at claimed authorship. Remaining candidates:

- **A1 — workspace-level revision feed** (`git log` analog: last-N revisions across all paths, one call). `ListRevisions` is per-file; the audited wake spent 2 legitimate rounds on per-file provenance. *Demand-pull. Trigger: a wake observed spending ≥3 rounds on multi-file provenance reconstruction.*
- **A2 — richer exact search** (regex, OR-terms, context lines — Grep parity). The audit's 3 zero-yield rounds were phrase-vs-OR confusion; ADR-339 D2's legibility echo may dissolve the demand (the model now learns mid-wake to issue per-term calls). *Demand-pull. Trigger: post-D2 wakes still burning ≥2 rounds on search-term reformulation.*
- **A3 — ReadFile windowing** (offset/limit — `FileReadTool` has it; YARNNN reads whole files). Current workspace files are ≤15KB; the 0-byte class is dead; EditFile's exact-string contract doesn't need line numbers. *Demand-pull. Trigger: first wake where a single ReadFile result exceeds ~20K tokens.*

## 2. Emission discipline — the one high-confidence gap left

**Verdict: (b)-sharpen.** Claude Code's parallel-call steering is a **system-prompt paragraph**, verbatim at `src_claudeCC/constants/prompts.ts:310` ("You can call multiple tools in a single response… maximize use of parallel tool calls…"). ADR-339 D3 placed one sentence in two *tool descriptions* — a level below where the reference puts it. The audited wake was 20/20 strictly serial.

**B1 — promote batching steering to the Reviewer persona frame** (as an ADR-302 registered static section, mirroring `prompts.ts:310`'s shape). This remains capability documentation, not the ADR-303-deleted urgency class.

**Deliberately HELD until after Friday 2026-06-13 22:00 UTC** (revision-audit wake): that wake runs with D1+D2+D3 live but no system-prompt steering — a free natural experiment isolating whether tool-description-level steering suffices. If the wake still emits one call per round, B1 ships with its necessity proven; if batching appears, B1 is unnecessary and the cheaper placement won. Shipping B1 today would destroy the attribution.

## 3. Context economics

- **Deferred tool schemas** (Claude Code's ToolSearch pattern — rarely-used tools load on demand). **Reject for now**: the Reviewer's 24 tool schemas live in the *cached* prefix — the audited wake paid 585K cache-read vs 45.7K fresh tokens; schema weight is amortized to near-zero. Revisit only if the surface grows past ~40 tools.
- **Wake envelope vs lazy session reads** — **(d) original territory, confirmed correct.** Claude Code lazy-reads CLAUDE.md and files because a human pays in patience; a budgeted wake front-loads governance (ADR-276) because rounds are metered. The audit validated the envelope: zero model re-reads of envelope-resident files.
- **Backend hygiene** (from the audit, no model impact): envelope gather reads MANDATE 4×/IDENTITY 2× per assembly; working-memory compact index rebuilt twice mid-wake by the narration path. *Ship-anytime `asyncio.gather` dedup; no urgency, no behavior change.*

## 4. Delegation & work tracking

- **Sub-agents**: YARNNN has the capability (`DispatchSpecialist`, ADR-261 D7 — explicitly the Claude Code sub-agent shape) but not the *guidance*. Claude Code steers: "subagents are valuable for parallelizing independent queries or **protecting the main context window from excessive results**" (`prompts.ts:319`). The Reviewer's persona frame wires constraint pass-through but never says when to delegate reads. *Demand-pull. Trigger: a wake whose tool results blow past ~60K fresh input tokens — post-339 perception makes this unlikely soon.*
- **Mid-wake plan persistence**: Claude Code's TodoWrite has a YARNNN-native answer already — `standing_intent.md` + the ADR-303 P4 dispatcher write proved its worth in the housekeeping wake (the exhausted plan survived to seed the next wake). **(d) original territory; no change.** The substrate IS the todo list.
- **Approval gating**: ADR-307's per-action permission gate ≥ Claude Code's session-level plan/accept modes for this trust model. **(a) confirm; no change.**

## 5. Loop mechanics — one unratified stance cell

**E1 — round-0 `tool_choice={"type":"any"}`** (`reviewer_agent.py:1124`). ADR-303 bans forcing on mid-loop/terminal rounds and the 2026-05-26 doc ratified "never forced" citing `query.ts:674` — but round 0 forces. This is either (i) a deliberate wake-contract cell ("a wake must begin by acting — perception or verdict, never bare prose") that was never written down, or (ii) drift predating ADR-303. The behavior is plausibly correct for wake-shaped invocations (no human to talk to on round 0); the gap is that no canon says so. *Action: one-paragraph ratification or removal — decide in the next ADR-303-adjacent commit, not urgent. Note: `tool_choice:"any"` also disables extended thinking on that round — worth weighing in the same paragraph.*

## 6. The composition boundary (the Bash question, settled but worth naming the consequence)

ADR-337 D6 excluded Bash/REPL deliberately; nothing here re-litigates it. The structural consequence the comparison makes explicit: Claude Code buys generality with a Turing-complete escape hatch and pays in auditability (a `bash` call's effects are opaque to the harness); YARNNN buys attribution + gating + revertibility with a closed verb set and pays in ADR-latency per new verb. **The mitigation is now demonstrated, not theoretical**: eval (00:49 UTC) → receipts → ADR-339 ratified+deployed (01:32 UTC next day) — the syscall ABI renegotiates from receipts in ~25 hours. That loop, not any single primitive, is the actual answer to the generality gap. Keep investing in it (scenario library, gates, the audit pattern) over widening the verb set speculatively.

## 7. No-analog-needed inventory (for completeness)

| Claude Code mechanism | YARNNN equivalent | Status |
|---|---|---|
| Hooks | `_hooks.yaml` substrate-event hooks (ADR-296) | have |
| Skills / SKILL.md | `/workspace/specs/` capability library (ADR-275) + render skills (ADR-118) | have |
| CLAUDE.md | `_workspace_guide.md` + wake envelope (ADR-276) | have |
| Worktree isolation | branching deferred (ADR-209 D10) — single-writer-per-path (ADR-286) covers the concurrency need | correct absence |
| Plan mode | proposals queue + ADR-307 gate | have (stronger shape) |
| Compaction | conversation.md + tool-output-drop (ADR-221) | have (borrowed) |

---

## 8. Prioritized disposition

**Measure first — Friday 2026-06-13 22:00 UTC revision-audit wake** (also the ADR-275 criterion-d measurement):
1. Round count + serial-vs-batched emission under the new contract → decides **B1**.
2. Search-term behavior post-D2 echo → decides **A2**.
3. Canary re-baseline (output tokens shift DOWN by design — judge by judgment content).

**Ship-anytime (no model impact)**: envelope-gather dedup + compact-index double-rebuild fix (§3).

**Ratify-or-remove (doc-level)**: E1 round-0 tool_choice stance (§5).

**Demand-pull registry (named triggers)**: A1 revision feed, A3 ReadFile windowing, D-guidance sub-agent context protection, ADR-339 D5 push-shaped sensors.

**Rejected with reasons**: deferred tool schemas (cache amortizes), Bash/REPL (ADR-337 D6 + §6), round-budget changes (ADR-303 + ADR-339 D4), streaming overlap & token-budget prompt anchors (2026-05-26 doc, unchanged).

## 9. The meta-rule this re-assessment ratifies

The ADR-337 decision rule generalizes into the standing test for all future borrowing:

> **Borrow trained-prior shapes and prompt-discipline mechanics; never borrow scale assumptions or trust models.**

Claude Code is the right reference for *how the model has been trained to act* (tool contracts, parallel-call steering, error surfacing, compaction order) — those transfer because the same model sits in both harnesses. It is the wrong reference for *what the world looks like* (monorepo vs operator-scale workspace — which is why its `LS` is lazily one-level and YARNNN's post-339 `ListFiles` is eagerly recursive, and both are correct) and for *who is trusted with what* (interactive human supervision vs autonomy ladder + attribution + gates). Every candidate above was sorted by this test; future comparisons should start from it.
