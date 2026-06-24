# ADR-363 — Wake Context Handling: cross-wake memory ratified (re-derived), within-wake-loop context adopted

**Status**: Proposed (2026-06-24)
**Deciders**: KVK + Claude
**Dimensional classification** (Axiom 0): **Mechanism** (primary — how a wake's context is assembled and pruned) + **Substrate** (Axiom 1 — what persists across wakes) + **Channel** (Axiom 6 — Claude API channel discipline).
**Concern**: This is **Concern 1 of the three-concern split** (context handling · its eval · self-improvement) from [`context-continuity-and-self-improvement-2026-06-24.md`](../analysis/context-continuity-and-self-improvement-2026-06-24.md) — and **first in sequence**. Concern 2 (continuity eval + snapshot/restore harness) and Concern 3 ([ADR-361](ADR-361-verdict-rule-binding.md) + [ADR-362](ADR-362-inspector-auditor-seat.md), the Inspector seat) are **PENDING and gated behind this**.
**Re-audits / re-derives (does NOT inherit)**: the context lineage — [ADR-059](ADR-059-simplified-context-model.md), [ADR-064](ADR-064-unified-memory-service.md), [ADR-067](ADR-067-session-compaction-architecture.md), [ADR-159](ADR-159-filesystem-as-memory.md), [ADR-169](ADR-169-mcp-context-hub.md), [ADR-221](ADR-221-layered-context-strategy.md). Per operator directive, these are treated as falsifiable inputs, not de-facto truth.
**Builds on**: the governance-caching win this session (commit `66a9090`) — the first cost measurement of the wake era.
**Discourse base**: [`context-handling-reaudit-2026-06-24.md`](../analysis/context-handling-reaudit-2026-06-24.md) (the from-scratch re-audit) + [`context-continuity-and-self-improvement-2026-06-24.md`](../analysis/context-continuity-and-self-improvement-2026-06-24.md) §1.

---

## 1. The problem the re-audit surfaced (why this ADR is not a rubber-stamp)

The operator directive: do not take filesystem-native (Axiom 1) as de-facto truth — stress-test whether the approach should accommodate API conventions (sessions, memory tool, compaction, context-editing), *while preserving the moat AND improving cost* (not mutually exclusive). The broad re-audit produced two findings that make this a real decision, not a ratification:

**Finding A — the context lineage adjudicated the CHAT surface, never the WAKE.** Every ADR 059→221 (Feb–Apr 2026) is about YARNNN-the-thinking-partner: `chat_sessions`, conversation windowing, "20-message session," `conversation.md`. The **Reviewer wake** (a fresh stateless `messages` array every wake — `reviewer_agent.py:1369`) came LATER (ADR-256/260/296) and **inherited the filesystem-native conclusion by assumption.** "Is filesystem-native right?" is *proven for chat* and *merely assumed for the wake*. This ADR closes that gap by re-deriving the conclusion for the wake on its own merits.

**Finding B — every lineage cost number is a chat turn at 2026-04 Sonnet pricing.** None models a wake (~16k governance + a multi-round tool-loop). This session's governance-caching (~40% uncached-input cut) is the first wake-era cost datum — a moat-safe prompt-caching win the lineage never analyzed.

The wake is a different problem from a chat session: single-shot, human-absent, large stable governance prefix + a bounded tool-loop, whose "history" is the *prior wake's substrate writes*, not a conversation. It deserves its own adjudication.

## 2. The two axes every mechanism is judged on

1. **Moat-safety** — does memory-of-record stay authored / attributed / portable (ADR-209, the moat), or move to provider-managed state? Within-call ephemera (a tool-loop summary) are NOT memory-of-record; durable cross-wake state IS.
2. **Cost / latency** — measured against the wake's actual shape, with the governance-caching baseline.

The two are **not mutually exclusive** (governance-caching proved a mechanism can be moat-safe AND a cost win). The audit keeps them separate so a cost win is never bought with a moat cost.

## 3. Decisions

### D1 — RATIFY cross-wake filesystem-as-memory for the wake era (re-derived, not inherited)

A wake's cross-wake memory-of-record stays **authored substrate** read back through the wake envelope (governance + `standing_intent.md` + `judgment_log.md` + mirror heads). This *extends* the lineage's chat-surface conclusion (ADR-159/221) to the wake — but on **re-derived** grounds, stated explicitly so it is a decision, not an inheritance:

- **Moat**: cross-wake memory-of-record in provider state (sessions) is unportable + unattributed — it directly contradicts the moat thesis (substrate is the asset, ESSENCE). Filesystem-native keeps it portable + attributed.
- **Cost**: the re-read cost that a provider session would save is **already recovered by prompt-caching** (`66a9090`, ~40% cut). A session would save the same tokens and no more, while paying the moat cost. The cost argument that might once have favored sessions is *neutralized by caching*.

This closes Finding A: filesystem-native is now adjudicated *for the wake*, on the moat + the caching measurement — not assumed.

### D2 — REJECT provider sessions for cross-wake memory (re-derived rationale)

Documented as a *decision*, not an omission: provider-managed sessions move memory-of-record off authored substrate (moat cost) for a cost benefit that caching already captures (no marginal gain). Rejected. Re-openable only if a future measurement shows caching cannot capture the cost benefit — which D1's evidence makes unlikely.

### D3 — ADOPT context-editing for the within-wake tool-loop (the genuinely-new decision)

The one territory the lineage never reached. A wake's tool-loop accumulates `tool_use`/`tool_result` blocks across rounds; the loop hits its round ceiling (`max_rounds = 3 if use_sonnet else 20`, `reviewer_agent.py:1392`) — observed failing repeatedly this session (verdict=None, budget-exhausted). The lineage's `conversation.md` rollup is *cross-session* (chat); it has no within-wake-loop analogue.

**Decision**: wire Anthropic **context-editing** (`clear_tool_uses_20250919`, beta `context-management-2025-06-27`) into the wake loop's API calls (`chat_completion_with_tools` / `chat_completion_with_tools_stream` in `services/anthropic.py`). It prunes stale tool results from the loop's transcript — **pure within-call prune, nothing provider-retained, zero moat wrinkle** (memory-of-record is the substrate the agent already wrote, untouched).

- **Moat**: ✅ safe — within-call only; the durable record is the substrate writes, not the pruned tool blocks.
- **Cost**: prunes the tool-result bloat that accumulates across rounds.
- **Behavioral upside (the real prize)**: by clearing stale tool results, the effective working budget per round grows — **this may relieve the 20-round ceiling that has been truncating wakes all session** (the verdict=None failures). This is a correctness win, not just cost.

**Probe-gated**: ship behind measurement — does context-editing reduce truncation/verdict=None rate on wakes that currently hit the ceiling? If it doesn't move the ceiling behavior, it's still a cost win, but the behavioral claim must be measured, not assumed.

### D4 — EVALUATE within-wake compaction as the fallback (re-open, distinct from the chat case ADR-221 closed)

ADR-221 deleted *cross-session* in-session LLM compaction (`maybe_compact_history`) in favor of filesystem `conversation.md`. That decision stands for the chat surface. The **within-wake-loop** case is different and was never examined: a wake that needs to *retain summarized earlier rounds* (not just prune them) has no filesystem-rollup substitute (the rollup is cross-wake; this is intra-wake).

**Decision**: evaluate Anthropic **compaction** (`compact_20260112`, beta `compact-2026-01-12`) as the fallback for wakes that would truncate even after context-editing pruning. The summary is provider-generated (a mild wrinkle) but it is **within-wake ephemeral** — it never becomes cross-wake memory-of-record, so the moat (about *durable* substrate) is untouched. Probe-gated; adopt only if context-editing (D3) alone is insufficient. Singular-implementation note: this does NOT reintroduce the chat-surface compaction ADR-221 deleted — it is a distinct intra-wake mechanism with no filesystem alternative.

### D5 — TUNE the governance cache TTL by wake cadence (small, measure-driven)

Governance changes rarely (only on a governing-file revision), so the 1-hour cache TTL (`ttl: "1h"`, 2× write but holds across idle gaps) may dominate the current 5-minute TTL for workspaces with sparse wakes. **Decision**: measure wake cadence; choose 5-min (dense wakes) vs 1h (sparse wakes) per the cache-economics break-even (1h needs ≥3 reads within the hour to pay its 2× write). Pure cost, moat-neutral. Implement as a per-workspace or cadence-derived choice, not a global flip.

### D6 — REJECT the memory-tool interface as a mechanism, KEEP its shape as discipline (re-derived)

The Anthropic memory tool (`memory_20250818`) is a read/write `/memories` interface the host backs. YARNNN's `persona/` *is* that dir already; exposing it through the memory-tool interface is re-plumbing a working path (envelope pre-load + ReadFile) for marginal benefit. **Decision**: reject the interface as a mechanism (no measured win, adds plumbing); KEEP the memory-tool *discipline* (structured, one-concept-per-file, consult-before-acting) as guidance for how the agent uses `persona/`. Re-open only if a concrete pain emerges.

## 4. What this does NOT do

- **No change to cross-wake memory-of-record.** It stays authored substrate (D1). No provider sessions (D2), no memory-tool storage (D6).
- **No reintroduction of chat-surface compaction.** D4's intra-wake compaction is distinct from the cross-session compaction ADR-221 deleted.
- **No change to the chat surface.** ADR-159/221's chat-turn context model is untouched; this ADR is wake-scoped. (If the chat surface later wants context-editing too, that's a follow-on.)
- **No self-improvement / eval work.** Those are Concerns 2 + 3, PENDING and gated behind this (§6).

## 5. Implementation scope (sketch — not built by this ADR)

1. `services/anthropic.py` — `chat_completion_with_tools` + `_stream` gain optional `context_management` passthrough + the `context-management-2025-06-27` beta header (alongside the existing `prompt-caching` header). D3.
2. `agents/reviewer_agent.py` — the wake loop passes `context_management={"edits": [{"type": "clear_tool_uses_20250919"}]}` on its API calls; measure verdict=None / truncation rate vs the `max_rounds` ceiling (1392). D3 probe.
3. Cache TTL — governance block's `cache_control` gains a cadence-derived `ttl` (D5).
4. D4 (compaction) + D5 (TTL) are measure-then-adopt; D2 + D6 are documented rejections (no code).
5. Regression: the wake still composes/judges correctly with context-editing on (no loss of mid-loop substrate the agent needed); a funded wake shows reduced truncation OR equal behavior at lower token cost.

**Probe-before-canon**: D3 is the substantive change — gate it on a funded measurement (does it relieve the ceiling?) before Proposed→Implemented. D1/D2/D6 are decisions ratified by the re-audit; D4/D5 are measure-then-adopt.

## 6. Sequence + the pending concerns (explicit)

This ADR is **Concern 1, first in sequence**. The other two concerns are PENDING and gated behind it:

| Concern | Status | Gated behind |
|---|---|---|
| **1. Context handling (this ADR)** | Proposed → implement D3, measure D4/D5 | — (first) |
| **2. Continuity eval + snapshot/restore harness** | PENDING (sketched: discourse doc §2; no ADR yet) | Concern 1 stable |
| **3. Self-improvement / Inspector seat** | PENDING ([ADR-361](ADR-361-verdict-rule-binding.md) + [ADR-362](ADR-362-inspector-auditor-seat.md) drafted, Proposed) | Concerns 1 + 2 stable |

The continuity eval (Concern 2) is the precondition gate for the Inspector (Concern 3): self-improvement is fiction if the wake doesn't reliably perceive prior substrate, and *that* perception is partly a function of the context-handling decisions here (D1/D3). So Concern 1 must stabilize first — its decisions shape what Concern 2 measures.

## 7. The honest bottom line

The re-audit, done broad per the directive, finds the lineage's *cross-wake* conclusion survives a from-scratch re-derivation and is *strengthened* by this session's caching evidence — but it was only ever adjudicated for the *chat surface*, so this ADR re-derives it for the *wake* (D1) and documents the rejection of the alternatives on merits (D2/D6), not by inheritance. The genuinely-new, un-adjudicated territory is **within-wake-loop context** (D3 context-editing, D4 compaction fallback) — a real problem tied to the 20-round ceiling that's been failing wakes, and the substantive decision of this ADR. The moat is preserved (memory-of-record stays authored substrate; only within-call ephemera move to API mechanisms) AND cost/behavior improve (caching already; context-editing next) — the not-mutually-exclusive outcome the directive asked for. Eval and self-improvement remain PENDING, gated behind this.
