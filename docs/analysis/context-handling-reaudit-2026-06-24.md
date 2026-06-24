# Concern 1 — Context handling at large: a from-scratch re-audit (treating the lineage as falsifiable)

**Date**: 2026-06-24
**Hat**: B (architecture evaluation). A re-audit, not yet an ADR. No code moved.
**Operator directive (load-bearing)**: do NOT take filesystem-native (Axiom 1) as de-facto truth. The 2026-02→04 context lineage decisions (ADR-059/064/067/159/169/221) are **inputs to question, not conclusions to ratify** — even though this session's governance-caching win points toward the status quo (that's exactly when to re-audit rather than rationalize).
**Method**: extract what the lineage decided + why (done — see the structured extract that fed this doc), map the API as it is *today* (not 2026-04), then evaluate each mechanism from scratch against two axes: **moat-safety** (authored/attributed/portable) and **cost/latency**. Falsifiable: each mechanism can come out adopt / reject / re-open.
**Scope correction (the reason this doc exists)**: ADR-361/362 were drafted for Concern 3 (self-improvement / the Inspector seat) and mis-implied as the "next step" after a context-handling discussion. They are NOT context handling. Concern 1 had no ADR. This doc is Concern 1's precursor, and it is *first* in the operator's sequence (context → eval → self-improvement).

---

## 0. The two findings that reframe the whole audit

Before evaluating mechanisms, two facts from the extraction change the question itself:

### Finding A — the entire lineage predates the Reviewer-loop era and is about the CHAT surface, not the wake

Every context ADR (ADR-059 Feb → ADR-221 Apr 2026) is about **YARNNN-the-chat-surface** (TP / thinking-partner): `chat_sessions`, conversation windowing, "20-message session," `conversation.md` written "every 5 user messages," session boundaries at 4h inactivity. The vocabulary is *conversation*, not *wake*.

**The Reviewer's stateless-wake model (ADR-256/260/296, May 2026) came LATER and inherited the filesystem-native conclusion by assumption — it was never independently adjudicated for the wake case.** The wake is a different problem from a chat session:
- A **chat session** is multi-turn, human-present, conversation-shaped — windowing the last N messages + on-demand file reads is the right model, and the lineage nailed it.
- A **wake** is single-shot (a fresh `messages` array every wake, `reviewer_agent.py:1369`), human-absent, with a large stable governance prefix + a bounded tool-loop. Its "history" isn't a conversation — it's *the prior wake's substrate writes*.

So the lineage's conclusion ("filesystem-native, point-don't-dump") is **proven for the chat surface and merely assumed for the wake.** The re-audit's real territory is the wake, which no ADR in the lineage actually examined.

### Finding B — the cost numbers are all chat-turn, $3/M, 2026-04 — none model a wake

Every cost claim (ADR-159 ~$1.20→$0.36/session; ADR-221 ~$0.008/turn) is a *chat turn* at Sonnet $3/M, 2026-04 pricing. A wake's cost shape is different: ~16k governance + multi-round tool-loop (the 20-round ceiling we hit this session). The governance-caching win (`66a9090`: uncached input 185k→110k per wake, ~40% cut) is the *first* cost measurement of the wake era — and it was a **prompt-caching** win on substrate-rendered bytes, the moat-safe path. The lineage's cost analysis simply doesn't cover this case.

**Net:** the audit must evaluate the *wake's* context handling against *today's* API, because the lineage covered neither.

---

## 1. The API as it is TODAY (not 2026-04) — the honest current surface

From the current claude-api reference (verified this session), the cross-call context/memory primitives available now:

| Mechanism | What it is | Memory-of-record location | Moat status |
|---|---|---|---|
| **Prompt caching** | Cache rendered prefix bytes; ~0.1× read, ~1.25× write; 4 breakpoints; min 4096 tok | stays in your substrate (caches the *rendered bytes*) | ✅ moat-safe — caches substrate, owns nothing |
| **Compaction** (`compact-2026-01-12`) | Server summarizes earlier history into a `compaction` block you pass back | the compaction block lives in *your* messages array, but the summary is provider-generated | ⚠️ within-conversation only; the summary is unattributed provider text |
| **Context editing** (`clear_tool_uses` / `clear_thinking`) | Prune stale tool results / thinking from the transcript | nothing retained provider-side; pure prune | ✅ moat-safe — within-call prune, no memory-of-record |
| **Memory tool** (`memory_20250818`) | Model reads/writes a `/memories` dir across sessions via tool calls | **a dir YOU back** — you implement storage | ✅ if backed by authored substrate; the *shape* is what `persona/` already is |
| **Managed-Agents sessions** | Anthropic retains conversation state server-side across turns | **provider-side** | ❌ unportable, unattributed memory-of-record |
| **Mid-conversation system messages** | `role:"system"` in `messages` without busting cache | your messages array | ✅ moat-safe; relevant to the wake (operator-authority injection) |

**The key correction to my own prior framing:** the memory tool is moat-safe *if you back it with your own substrate* — it's a tool *interface*, not provider storage. YARNNN's `persona/` IS a memory dir; the only question is whether to expose it through the API's memory-tool interface vs the current envelope+ReadFile. That's a smaller question than "adopt provider memory."

---

## 2. The wake's context handling, evaluated from scratch

Treating the wake (not the chat session) as the object, and the lineage's conclusion as falsifiable:

### 2a. The wake's cross-wake memory: substrate read-back

**Current**: each wake reconstitutes from authored substrate via the envelope — governance (cached now) + standing_intent + judgment_log + mirror heads. No provider session, no retained context.

**Falsification attempt**: could provider sessions do better? A session would retain the prior wake's conversation server-side, avoiding the substrate re-read.
- **Cost**: the re-read cost is what governance-caching *already* recovers (~40% cut, moat-safe). A session would save the same tokens but no more.
- **Moat**: a session moves memory-of-record provider-side — unportable, unattributed. Directly violates the moat thesis (ESSENCE: authored/attributed/portable substrate is the asset).
- **Verdict**: **REJECT sessions for cross-wake memory.** Not because "filesystem is axiom" but because the cost benefit is *already captured* by caching, and sessions pay a moat cost for a benefit we have without it. This is a *re-derived* rejection, not an inherited one — and it's stronger now because we have the caching measurement the lineage lacked.

### 2b. The wake's WITHIN-loop context: the genuinely-open sub-case

This is the one place the lineage genuinely didn't reach. A wake's tool-loop hits the 20-round ceiling (we saw it repeatedly this session — verdict=None, budget-exhausted). Within one wake, the loop accumulates tool_use/tool_result blocks. The lineage's `conversation.md` rollup is *cross-session* (chat) — it has no within-wake-loop analogue.

Two API mechanisms bear directly, both moat-safe (within-call only, no memory-of-record):
- **Context editing** (`clear_tool_uses_20250919`): prune stale tool results from the loop's growing transcript. Pure prune, nothing provider-retained. **Strong adopt candidate** for long wakes — it directly attacks the 20-round-ceiling token bloat without touching substrate.
- **Compaction** (`compact_20260112`): summarize the loop's earlier rounds. The summary is provider-generated (a mild moat wrinkle) but it's *within-wake ephemeral* — it never becomes cross-wake memory-of-record, so the moat (which is about *durable* substrate) is untouched. **Adopt candidate** for wakes that would otherwise truncate.

**Verdict**: **RE-OPEN within-wake-loop context as a real, un-adjudicated question.** Context-editing is the cleaner first move (pure prune, zero moat wrinkle); compaction is the fallback for wakes that need to retain summarized earlier rounds. This is the genuinely-new territory — and notably it might *raise the effective round budget* (the 20-round ceiling that's been failing wakes all session), which is a behavioral win, not just cost.

### 2c. The governance prefix: caching (done) + a possible extension

**Current**: governance block cached this session (`66a9090`). Proven ~40% uncached-input cut.

**Falsification attempt — is there a better mechanism?** The 1-hour cache TTL vs 5-min: governance changes rarely (only on a governing-file revision), so a 1h TTL (`ttl: "1h"`, 2× write but holds across idle gaps) might dominate for workspaces with sparse wakes. **Re-open as a tuning question** — measure whether wake cadence is dense enough for 5-min (current) or sparse enough to want 1h. Small, pure-cost, moat-neutral.

### 2d. The memory-tool interface question

**Current**: the wake reads `persona/` via the envelope (pre-loaded) + ReadFile (on-demand).

**Falsification attempt**: expose `persona/` through the API memory-tool interface instead?
- **Benefit**: the model gets a uniform read/write memory affordance; possibly cleaner than the bespoke envelope.
- **Cost**: it's a *re-plumbing* of a working path for marginal benefit; `persona/` is already authored substrate (the memory tool's storage would just be a view over it). No moat change (we back the storage), but no clear cost win either.
- **Verdict**: **REJECT as mechanism, KEEP as discipline.** The memory-tool *shape* (structured, one-concept-per-file, consult-before-acting) is good guidance for how the agent uses `persona/`; the *interface* adds plumbing without a measured win. Re-open only if a concrete pain emerges.

---

## 3. The re-audit verdict table (from scratch, falsifiable)

| Mechanism | Lineage's stance | Re-audit verdict (today, wake-focused) | Why (re-derived, not inherited) |
|---|---|---|---|
| **Prompt caching** | not in lineage (post-dates it) | **ADOPTED + extend** (TTL tuning) | Proven ~40% cut this session; moat-safe (caches rendered substrate). The lineage's cost analysis never covered it. |
| **Provider sessions** | implicitly rejected (filesystem-native) | **REJECT** (re-derived) | Cost benefit already captured by caching; sessions pay a moat cost (unportable memory-of-record) for nothing extra. Stronger rejection now *because* we have the caching measurement. |
| **Context editing** (prune) | not adjudicated for the wake | **RE-OPEN → likely ADOPT** | Within-wake-loop only, pure prune, zero moat wrinkle, directly attacks the 20-round ceiling. The genuinely-new territory. |
| **Compaction** (within-wake) | ADR-067 P3 tried it for CHAT, deleted by 221 for filesystem rollups | **RE-OPEN for the WAKE loop** (distinct from the chat case 221 closed) | 221 rejected *cross-session* LLM compaction in favor of `conversation.md`. The *within-wake-loop* case has no filesystem-rollup substitute and was never examined. Different problem. |
| **Memory tool** (interface) | not in lineage | **REJECT as mechanism, KEEP as discipline** | `persona/` is already the memory dir; the interface is re-plumbing for marginal gain. The shape is good guidance. |
| **Filesystem-as-memory** (cross-wake) | ADOPTED (159/221) | **RATIFY — re-derived, not inherited** | For *cross-wake* memory-of-record, filesystem-native + caching strictly dominates on moat AND matches on cost. The governance-caching win is fresh evidence FOR it. |
| **Cross-LLM interop** (MCP) | ADOPTED (169) | **RATIFY** | Out of Concern-1 scope (interop face, ADR-310/311) but consistent — substrate-as-truth is what makes cross-LLM determinism possible. |

**The honest bottom line of the re-audit:** the lineage's *cross-wake* conclusion (filesystem-native) survives a from-scratch re-derivation and is *strengthened* by this session's caching evidence — but it survives **because re-derived against the moat + today's cost**, not because it's axiom. The genuinely-open territory the lineage never reached is **within-wake-loop context** (context-editing + compaction for the tool-loop), which is a *new* problem (the wake era post-dates the lineage) and a real one (the 20-round ceiling has been failing wakes all session). That, plus caching-TTL tuning, is the actual Concern-1 work.

---

## 4. What the Concern-1 ADR should decide (scope, now grounded)

The re-audit shows the ADR is **narrower than "revisit filesystem-native" but more substantive than "ratify the status quo"** — because the substantive part is genuinely-new wake-loop territory the lineage never covered:

1. **RATIFY** cross-wake filesystem-as-memory for the wake era — but on re-derived grounds (moat + caching evidence), explicitly noting the lineage examined the *chat surface* and this extends the conclusion to the *wake* with new justification. Closes the "was filesystem-native ever adjudicated for the wake?" gap (Finding A).
2. **ADOPT** context-editing (`clear_tool_uses`) for long wake tool-loops — pure prune, moat-safe, attacks the 20-round ceiling. **This is the new substantive decision.** Probe: does it raise the effective round budget on wakes that currently truncate?
3. **EVALUATE** within-wake compaction as the fallback for wakes that need summarized earlier rounds (distinct from the cross-session case ADR-221 closed). Probe-gated.
4. **TUNE** governance cache TTL (5-min vs 1h) by wake cadence. Small, measure-driven.
5. **REJECT, with re-derived rationale** (not inherited): provider sessions (moat cost, no marginal benefit) + memory-tool-as-mechanism (re-plumbing). Document the rejection so it's a *decision*, not an omission.

**This is a legitimate ADR** — it ratifies one thing on new grounds, makes one genuinely-new adoption (wake-loop context-editing), and records two re-derived rejections. It honors the directive (nothing inherited as de-facto; everything re-derived) and it's tractable.

---

## 5. Sequence correction (restoring the operator's order)

The work order, corrected:
1. **Concern 1 ADR** (this re-audit → an ADR): ratify cross-wake filesystem-native on re-derived grounds + adopt wake-loop context-editing + TTL tuning + documented rejections. **FIRST in sequence** (was skipped).
2. **Concern 2** (continuity eval + snapshot/restore harness): proves the wake perceives prior substrate. SECOND.
3. **Concern 3** (ADR-361 + 362, the Inspector seat): self-improvement. **THIRD — already drafted, but explicitly gated behind 1+2.** The drafts stand; they were just sequenced ahead of their place.

---

## 6. The honest bottom line

The operator was right twice: (1) ADR-361/362 are Concern 3, not context handling — Concern 1 had no ADR and we jumped to the third concern first; (2) filesystem-native must not be inherited as de-facto truth. The from-scratch re-audit, done broad, finds: the lineage's *cross-wake* conclusion survives re-derivation and is strengthened by this session's caching evidence — **but** it was only ever adjudicated for the *chat surface*, never the *wake*, and the genuinely-open territory (within-wake-loop context — context-editing + compaction) is new, real, and tied to the 20-round ceiling that's been failing wakes. The Concern-1 ADR is therefore not a rubber-stamp: it re-derives the cross-wake ratification and makes a real new adoption for the wake loop. The moat is preserved (memory-of-record stays authored substrate; only within-call ephemera move to API mechanisms) AND cost improves (caching already; context-editing next) — exactly the not-mutually-exclusive outcome the directive asked for.
