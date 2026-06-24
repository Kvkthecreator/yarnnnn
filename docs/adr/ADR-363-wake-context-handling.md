# ADR-363 — Wake Context Handling: cross-wake memory ratified (re-derived), within-wake-loop context wired-but-dormant

**Status**: **Accepted** (2026-06-24) — the context-handling question is **settled**: D1 ratified, D2/D6 rejected, D5 resolved from cadence data, D3 wired-but-dormant, D4 deferred behind D3. No decision remains open. (Individual mechanisms carry their own live/latent/deferred state below; the *adjudication* is complete.)
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

**The wake's measured cost shape (the fact that grounds every cost call below).** Production data, funded workspace, 30 days, 188 judgment wakes:
- **Wakes are sparse, not clustered**: median inter-wake gap **~3.8h**; only 2 of 188 gaps under 5 min; 59 gaps over 1h. The next wake almost never fires inside a cache TTL.
- **The cache win is therefore *intra-wake*, not cross-wake**: cache-hit % climbs with the round count (50% at 1–3 rounds → **72% at 9+ rounds**) while `cache_create` stays flat (~one governance write). Rounds 2..N re-reading the round-1 governance prefix *inside one wake* is where caching pays — not a later wake reading an earlier wake's cache.
- **The same surface carries the cost tail**: the 9+round wakes average ~393k cache-read tokens of accumulated prefix; that intra-wake bloat is exactly what D3 context-editing would prune.

So the cost axis has **one surface**: the long multi-round wake. Caching already discounts re-reads on it; context-editing would prune the bloat on it; the TTL question is settled by the sparse cadence on it. This is the unified cost model §7 closes with.

## 3. Decisions

### D1 — RATIFY cross-wake filesystem-as-memory for the wake era (re-derived, not inherited)

A wake's cross-wake memory-of-record stays **authored substrate** read back through the wake envelope (governance + `standing_intent.md` + `judgment_log.md` + mirror heads). This *extends* the lineage's chat-surface conclusion (ADR-159/221) to the wake — but on **re-derived** grounds, stated explicitly so it is a decision, not an inheritance:

- **Moat**: cross-wake memory-of-record in provider state (sessions) is unportable + unattributed — it directly contradicts the moat thesis (substrate is the asset, ESSENCE). Filesystem-native keeps it portable + attributed.
- **Cost**: the re-read cost that a provider session would save is **already recovered by prompt-caching** (`66a9090`, ~40% cut). A session would save the same tokens and no more, while paying the moat cost. The cost argument that might once have favored sessions is *neutralized by caching*.

This closes Finding A: filesystem-native is now adjudicated *for the wake*, on the moat + the caching measurement — not assumed.

### D2 — REJECT provider sessions for cross-wake memory (re-derived rationale)

Documented as a *decision*, not an omission: provider-managed sessions move memory-of-record off authored substrate (moat cost) for a cost benefit that caching already captures (no marginal gain). Rejected. Re-openable only if a future measurement shows caching cannot capture the cost benefit — which D1's evidence makes unlikely.

### D3 — WIRE context-editing for the within-wake tool-loop, DORMANT pending a demonstrated need (revised 2026-06-24 after the probe)

The one territory the lineage never reached. A wake's tool-loop accumulates `tool_use`/`tool_result` blocks across rounds; the loop hits its round ceiling (`max_rounds = 3 if use_sonnet else 20`, `reviewer_agent.py:1392`). The lineage's `conversation.md` rollup is *cross-session* (chat); it has no within-wake-loop analogue.

**Decision (as built)**: Anthropic **context-editing** (`clear_tool_uses_20250919`, beta `context-management-2025-06-27`) is **wired into the wake loop but OFF by default** — gated on `YARNNN_CONTEXT_EDIT`, with `trigger` + `keep` as env-tunable variables. It prunes stale tool results from the loop's transcript — **pure within-call prune, nothing provider-retained, zero moat wrinkle** (memory-of-record is the substrate the agent already wrote, untouched). `services/anthropic.py::chat_completion_with_tools[_stream]` gain an optional `context_management` passthrough that routes through `client.beta.messages.*` only when set; `None` preserves the exact pre-ADR-363 non-beta cached path.

- **Moat**: ✅ safe — within-call only; the durable record is the substrate writes, not the pruned tool blocks.
- **Safety (MEASURED)**: ✅ in the funded keep-sweep, no arm flipped the verdict to None at `keep=3` or `keep=6` — mid-loop pruning did **not** break judgment. The discourse's mid-loop-safety worry did not materialize in this run.
- **Cost (UNTESTED, not falsified)**: the funded keep-sweep was **inconclusive** — the three arms hit 5/14/11 rounds on the identical prompt, so wake-to-wake variance swamped any prune effect, and the probe failed to capture `applied_edits` so it could not confirm the prune even fired. See [`2026-06-24-adr363-d3-context-editing-INCONCLUSIVE`](../evaluations/2026-06-24-adr363-d3-context-editing-INCONCLUSIVE.md).

**Why dormant, not adopted**: the premise is **thin** in production — verdict=None is rare (1 in 30 days on the funded workspace) and ceiling-hitting wakes are a small tail, so the measurable D3 win is at most a marginal cost trim on a few wakes, not a behavioral fix. Spending more funded balance to isolate a marginal win against high wake-variance is poor return. The mechanism ships **dormant + instrumented** (`_parse_response` now logs `applied_edits`); a demonstrated production cost problem — or a deliberate variance-controlled re-run (long deterministic recurrence, ≥2× per arm, lowered trigger, confirmed prune) — pulls it on. The corrected probe design is recorded in the finding.

**Status**: D3 stays **Proposed** (wired-but-dormant). It does NOT flip to Implemented on this measurement; the cost claim is explicitly untested. Promotion requires the variance-controlled re-run reading ADOPT.

### D4 — DEFER within-wake compaction (gated behind a D3 that has not fired; distinct from the chat case ADR-221 closed)

ADR-221 deleted *cross-session* in-session LLM compaction (`maybe_compact_history`) in favor of filesystem `conversation.md`. That decision stands for the chat surface. The **within-wake-loop** case is different and was never examined: a wake that needs to *retain summarized earlier rounds* (not just prune them) has no filesystem-rollup substitute (the rollup is cross-wake; this is intra-wake).

**Decision (resolved 2026-06-24): DEFER, do not build.** D4 is the *fallback for when D3 pruning is insufficient* — its trigger condition is "context-editing alone cannot keep a wake under the ceiling." But D3 is dormant and its sufficiency was never even tested (the keep-sweep was variance-confounded). A fallback to an untriggered primary has no live precondition. Compaction also carries a real wrinkle D3 does not: the summary is **provider-generated** within-wake text (ephemeral, never cross-wake memory-of-record, so the *durable*-substrate moat is untouched — but still a provider artifact in the loop, vs D3's pure prune). Given the thin premise (§2: the long-wake tail is small; D3 itself isn't banked), adding a provider-summary mechanism on top is unjustified now. **Re-open only when** a demonstrated production case shows wakes truncating *after* D3 pruning is on and tuned — i.e. D3 must fire, be insufficient, and the loss be real, before D4's precondition exists. Singular-implementation note preserved: D4 would NOT reintroduce the chat-surface compaction ADR-221 deleted — it is a distinct intra-wake mechanism with no filesystem alternative.

### D5 — KEEP the 5-minute governance cache TTL; 1h is NOT justified (resolved 2026-06-24 from cadence data)

The open question was whether sparse-wake workspaces would benefit from the 1-hour cache TTL (`ttl: "1h"`, 2× write, holds across idle gaps) over the current 5-minute default. The cache-economics break-even: 1h needs ≥3 reads within the hour to pay its 2× write.

**Decision (resolved from data, no funded spend needed): KEEP 5-minute. Do not adopt 1h.** The §2 cadence finding settles it: wakes are sparse (median gap ~3.8h; only 2 of 188 gaps under 5 min), so the next wake almost never fires inside *either* TTL — and the measured cache value is **intra-wake** (hit % rises with round count, peaking at 72% on 9+round wakes), which the 5-minute window already fully covers (wakes complete well within 5 min). A 1h TTL would pay a 2× write premium to capture cross-wake reads that the cadence shows almost never arrive — strictly worse economics on this profile. The intuition behind D5 (sparse wakes favor longer TTL) was *backwards*: sparse cadence means cross-wake caching can't pay regardless of TTL, so the cheaper write wins. **Re-open only if** a workspace emerges with genuinely clustered wakes (multiple judgment wakes per hour) — then the 1h break-even could flip, and a per-workspace cadence-derived TTL would be worth building. No such profile exists today; the global 5-min default stands. Pure cost, moat-neutral. **No code change** (5-min is already the default).

### D6 — REJECT the memory-tool interface as a mechanism, KEEP its shape as discipline (re-derived)

The Anthropic memory tool (`memory_20250818`) is a read/write `/memories` interface the host backs. YARNNN's `persona/` *is* that dir already; exposing it through the memory-tool interface is re-plumbing a working path (envelope pre-load + ReadFile) for marginal benefit. **Decision**: reject the interface as a mechanism (no measured win, adds plumbing); KEEP the memory-tool *discipline* (structured, one-concept-per-file, consult-before-acting) as guidance for how the agent uses `persona/`. Re-open only if a concrete pain emerges.

## 4. What this does NOT do

- **No change to cross-wake memory-of-record.** It stays authored substrate (D1). No provider sessions (D2), no memory-tool storage (D6).
- **No reintroduction of chat-surface compaction.** D4's intra-wake compaction is distinct from the cross-session compaction ADR-221 deleted.
- **No change to the chat surface.** ADR-159/221's chat-turn context model is untouched; this ADR is wake-scoped. (If the chat surface later wants context-editing too, that's a follow-on.)
- **No self-improvement / eval work.** Those are Concerns 2 + 3, PENDING and gated behind this (§6).

## 5. Implementation scope

**D3 — BUILT (dormant), 2026-06-24:**
1. `services/anthropic.py` — `chat_completion_with_tools` + `_stream` gained an optional `context_management` passthrough; when set, the call routes through `client.beta.messages.*` with `context-management-2025-06-27` joined to the existing `prompt-caching` beta (one comma-joined header). `None` preserves the exact pre-ADR-363 non-beta cached path. `_parse_response` logs `applied_edits` for probe observability.
2. `agents/reviewer_agent.py` (~1392) — the wake loop builds a `clear_tool_uses_20250919` config and passes it to both call sites, **gated on `YARNNN_CONTEXT_EDIT`** (off by default). `trigger` (default 24k, not the API's 100k) + `keep` (default 6, not the API's 3) are env-tunable probe variables with safety-derived defaults.
3. Probe: `api/scripts/operator/probe_context_editing_local.py` (3-arm keep-sweep). **Result: inconclusive on cost, clean on safety** — see [the finding](../evaluations/2026-06-24-adr363-d3-context-editing-INCONCLUSIVE.md).

**Outcome**: D3 ships **wired-but-dormant**. The safety question is answered (no verdict-flip); the cost question is untested (variance-confounded) and the production premise is thin, so the mechanism stays off-by-default until a demonstrated need pulls it on. D3 remains **Proposed**, NOT Implemented.

**D4/D5 — resolved, no code:**
4. **D4 (within-wake compaction): DEFERRED** — gated behind a D3 that has not fired and was never shown insufficient; its precondition doesn't exist. Re-open only when wakes truncate *after* D3 is on and tuned.
5. **D5 (cache TTL): RESOLVED to keep 5-min** from cadence data — wakes are too sparse for cross-wake caching to pay any TTL; the cache value is intra-wake and the 5-min window already covers it. No code change (5-min is the existing default). 1h would be strictly worse economics on this cadence.
6. D2 + D6 are documented rejections (no code).

**Probe-before-canon (honored)**: D3 was gated on a funded measurement and is NOT promoted to Implemented because the measurement did not read ADOPT on cost. The probe-before-canon discipline worked as intended — it stopped a marginal, unproven win from being canonized as adopted. D5 was resolved *from existing telemetry* (no funded spend) once the cadence question was framed — the cheaper kind of measurement, and the right first reach. D1/D2/D6 are decisions ratified by the re-audit.

## 6. Sequence + the pending concerns (explicit)

This ADR is **Concern 1, first in sequence**. The other two concerns are PENDING and gated behind it:

| Concern | Status | Gated behind |
|---|---|---|
| **1. Context handling (this ADR)** | **SETTLED** — D1 ratified, D2/D6 rejected, D5 resolved (keep 5-min), D3 wired-but-dormant, D4 deferred. Floor is stable for Concern 2. | — (first) |
| **2. Continuity eval + snapshot/restore harness** | PENDING (sketched: discourse doc §2; no ADR yet) | Concern 1 stable |
| **3. Self-improvement / Inspector seat** | PENDING ([ADR-361](ADR-361-verdict-rule-binding.md) + [ADR-362](ADR-362-inspector-auditor-seat.md) drafted, Proposed) | Concerns 1 + 2 stable |

The continuity eval (Concern 2) is the precondition gate for the Inspector (Concern 3): self-improvement is fiction if the wake doesn't reliably perceive prior substrate, and *that* perception is partly a function of the context-handling decisions here (D1/D3). So Concern 1 must stabilize first — its decisions shape what Concern 2 measures.

## 7. The settled thesis (the governing conclusion)

The context-handling question for the wake is now **fully adjudicated** — every mechanism dispositioned, the cost model grounded in measured production data, the moat held throughout. The thesis in one frame:

**Cross-wake memory is authored substrate, and that is not a cost compromise — it is cost-free given caching.** Filesystem-native (D1) survives a from-scratch re-derivation, re-adjudicated *for the wake* (not inherited from the chat surface) on the moat + the caching measurement. Provider sessions (D2) and the memory-tool interface (D6) are rejected on merits: they move memory-of-record off authored substrate (a moat cost) for a cost benefit that caching already captures (no marginal gain). The moat and cost-efficiency are not in tension here — they point the same way.

**The wake's entire cost surface is one thing: the long multi-round wake** (§2). Caching (`66a9090`, the banked win) discounts the governance prefix re-read on it — and crucially that win is **intra-wake** (hit % rises to 72% on 9+round wakes), not cross-wake, because the cadence is too sparse (median ~3.8h gap) for a later wake to read an earlier wake's cache. That single fact resolves three decisions at once: it confirms D1's cost case (the re-read is recovered), it settles D5 (keep 5-min TTL — 1h can't pay against sparse cadence; the intuition was backwards), and it locates the *only* remaining cost lever — pruning the accumulated tool-result bloat on that same long-wake surface, which is D3.

**The within-wake levers (D3 context-editing, D4 compaction) are real but latent, against a thin tail — so they ship dormant, not adopted.** D3 got wired and funded-probed; the result was *honest, not flattering*: **moat-safe and judgment-safe** (no verdict flipped to None at keep=3 or keep=6 — the mid-loop-safety worry did not materialize), but its **cost benefit is untested** (the keep-sweep was variance-confounded; `applied_edits` capture was missing, now fixed) against a **thin production premise** (verdict=None rare — 1 in 30 days; ceiling-hitting wakes a small tail). So D3 is wired-but-dormant and D4 (its fallback) is deferred behind it. Adopting either now would canonize a marginal, unproven win — exactly what probe-before-canon exists to prevent, and what it prevented here.

**The disposition, complete:**

| Decision | Disposition | Basis |
|---|---|---|
| D1 cross-wake filesystem-as-memory | **Ratified (live)** | moat + caching re-derivation |
| D2 provider sessions | **Rejected** | moat cost, no marginal benefit over caching |
| D3 within-wake context-editing | **Wired, dormant (Proposed)** | moat-safe + judgment-safe (measured); cost untested vs thin premise |
| D4 within-wake compaction | **Deferred** | gated behind a D3 that hasn't fired; no live precondition |
| D5 governance cache TTL | **Resolved: keep 5-min** | cadence data — sparse wakes, intra-wake cache value |
| D6 memory-tool interface | **Rejected as mechanism, kept as discipline** | re-plumbing a working path; no measured win |

The clean cost win this session was **caching**; the within-wake mechanisms are latent levers, not banked ones, and the ADR is honest about which is which. Eval and self-improvement (Concerns 2 + 3) remain PENDING, gated behind this now-settled floor.
