# Cross-analysis: ADR-298 against OpenClaw, Hermes, and durable-execution platforms

**Date**: 2026-05-22
**Subject**: ADR-298 (single-lane execution, two-lane drain, pace as first-class operator dial)
**Verdict**: Architecture is independently load-bearing. Convergence with production agent runtimes is the right kind of evidence; the YARNNN-distinctive parts (pace, recurrence-population-time enforcement, queue-as-transient-compute) are net additions to the design space, not deviations needing apology.

---

## Short version

ADR-298's core architecture is independently load-bearing. The two systems most often invoked as YARNNN's "we should be more like them" reference points — OpenClaw and Hermes — have either (a) converged on the same primitives ADR-298 proposes, or (b) explicitly lack the property ADR-298 is now adding. Where ADR-298 is doing something distinctive — pace as a first-class operator dial, recurrence-population-time enforcement, and queue-as-transient-compute per Axiom 1 — those are net additions to the design space, not deviations from established practice that need apology.

Below: primitive-by-primitive.

---

## 1. Single-lane execution per workspace (D1)

This is the cross-analysis result that most matters: the strongest, most production-hardened agent runtime in the open-source ecosystem made exactly the same call, for exactly the same reasons, before YARNNN did.

OpenClaw's central architectural commitment is what their docs call the **single-writer rule**: only one agent run should touch a given session at a time, enforced via a lane-aware FIFO queue where each session gets its own lane (`session:<key>`) that guarantees only one active run per session. The failure modes they cite as motivation are the same failure modes ADR-298 §1 cites: tool calls interleaving in the wrong order, two runs both mutating the same session transcript, duplicate sends or contradictory actions, the agent continuing a plan that's already obsolete.

The framing in the OpenClaw architecture analysis is worth quoting because it almost exactly mirrors §3 of ADR-298: prioritize serial execution until the workflow is stable; make concurrency a system-level decision using explicit lane queues. And from the multi-agent governance side: don't let six specialists run simultaneously if three will do.

Hermes (Nous Research) reaches the same conclusion through a different surface. Its SessionDB uses WAL (Write-Ahead Logging) mode for concurrent readers and a single writer, and the gateway identifies unique conversations using a composite key that incorporates the platform, user, and chat context, ensuring that a single user can maintain distinct conversation states across different groups or DM channels — i.e., partitioning per session and serializing writes within a partition. The Python-library docs put it even more bluntly: **create one AIAgent per thread or task. Never share an instance across concurrent calls.**

So when ADR-261 D3 originally canonized "parallel concurrent Reviewer sessions" as an architectural guarantee, that was the position out-of-step with the field. ADR-298 isn't a retreat; it's a convergence toward the pattern the rest of the production agent ecosystem has already settled on. The §4 amendment is best read not as "we got it wrong" but as "the operating-system layer of the agent ecosystem has hardened around a particular invariant, and we're aligning with it."

**Where ADR-298 is stronger than OpenClaw's framing**: OpenClaw treats the single-writer rule as a system-level decision with no axiomatic justification beyond "race conditions are bad." ADR-298 grounds it in two layered claims — substrate coherence under ADR-209's revision chain, and prudential choice given observed failure modes (§3) — and explicitly carves out the right to revisit if production data shifts. That epistemic discipline ("single-lane is currently-right, not eternally-right," §2 D1) is something I haven't seen articulated this cleanly in OpenClaw's or Hermes's docs. It's defensible engineering and defensible communication.

---

## 2. Queue as transient compute, not state (D2)

This is the most distinctive YARNNN choice in the ADR and the one I'd most expect a reviewer to push on. The defense is strong.

OpenClaw's lane queue is implementation detail — it doesn't appear in the operator surface, doesn't get persisted as inspectable artifact, and isn't framed as ontologically meaningful. Hermes's job state lives in `~/.hermes/cron/jobs.json` but that file is **configuration** (declared jobs), not **queue** (pending fires) — the actual scheduler tick loads due jobs from `jobs.json`, creates a fresh AIAgent, runs the job prompt, updates job state and `next_run` with no intermediate "pending fires" artifact persisted as user-readable state.

So both reference systems treat the wake-pending-execution boundary as ephemeral. ADR-298 D2 makes this implicit consensus explicit and grounds it in Axiom 1, with §6 Scenario L (queue reconstructable from filesystem state + DB telemetry after total wipe) as the falsifiability check. That's a more rigorous framing than either OpenClaw or Hermes provides for the same architectural commitment.

**One place I'd push**: D2's claim that the queue is "more like `execution_events` than like `_recurrences.yaml`" is correct but understates a distinction worth naming. `execution_events` is historical telemetry (immutable, append-only, GC'd by age). `wake_queue` is imminent compute (mutable, locked, dequeued). Both are non-substrate, but they have different lifecycle shapes. If a future reviewer challenges "why not just append to `execution_events` with status='pending'?", the answer is: locking and dedup semantics on a high-write append-only telemetry table get expensive fast, and the FIFO drain pattern wants its own indexed surface. That's worth a sentence somewhere in §2.

---

## 3. Two-lane drain: paced + live (D3)

OpenClaw uses a two-stage queue pattern — per-session lane plus global lane — for almost identical reasons. The blog post on it: each session gets its own lane, and then each run also goes through a global lane, with the explicit goal being LLM runs are expensive, inputs can arrive back-to-back (message + webhook + heartbeat), shared resources shouldn't be contended, upstream rate limits shouldn't get accidentally DDoS'd by your own agent.

Note the alignment: OpenClaw's "message + webhook + heartbeat" maps almost 1:1 to ADR-298's "addressed + substrate_event + cron_tick." Both systems recognized that wake sources have different latency requirements and built a two-lane drain to handle them.

**Where ADR-298 is doing something genuinely new**: OpenClaw's second lane is a **global concurrency lane** (throttle against upstream rate limits). ADR-298's second lane is a **pace-policy lane** (throttle against operator-declared cadence intent). Those are different abstractions in service of different goals. OpenClaw is solving a resource-protection problem. ADR-298 is solving an operator-legibility-of-agent-cost-and-cadence problem. Both are valid; ADR-298's framing is more product-distinctive.

**Risk the §6 scenarios don't fully address**: Scenario B says 10 substrate-event wakes enqueue at live lane within 30s, Reviewer drains one at a time at ~60s each, total wall-clock: ~10 minutes. That's an honest cost statement. But there's a related case the scenarios skip: what if a single substrate-event wake takes 90s and the operator is actively chatting? The chat addressed-wake enqueues and waits 90s before its first token. OpenClaw and Hermes both treat "operator is actively present" as a higher-priority signal than scheduled work. ADR-298 doesn't currently express that priority, because both `addressed` and `substrate_event` are in the live lane with FIFO drain. This may be deliberate (operator typing while agent is mid-audit is uncommon enough not to matter) but it deserves an explicit decision rather than a default-by-omission.

---

## 4. Cross-source dedup at queue layer (D6)

This is a clear improvement over ADR-272's per-source dedup and over both reference systems.

OpenClaw's dedup story, as documented: idempotency helpers and deduplication use job IDs and payload hashing to skip duplicates, integrated with OpenClaw's event store. That's a single-axis dedup (job ID), which is enough when there's only one job-arrival path. It does not solve the cross-source problem ADR-298 §1 calls out — where two different wake-source paths could legitimately fire on the same underlying operator intent. OpenClaw doesn't have this problem because OpenClaw has fewer wake-source axes; YARNNN inherited it from the ADR-296 v2 five-source model.

ADR-298's resolution — UNIQUE constraint on `(user_id, wake_source, dedup_key)`, with per-source dedup-key derivation — is the right shape. The interesting subtlety is D6's explicit non-decision: "The cross-source case (substrate-event + addressed referring to the same operator intent) is not deduped — they have different dedup keys because they're different judgment shapes. Both run, serialized via single-in-flight."

This is correct and Scenario H illustrates it well. But I'd note: **this only works because of D1 (single-lane).** In a parallel-concurrent world, the un-deduped substrate-event + addressed pair would race; in single-lane FIFO, the second one reads the first one's output via `judgment_log.md` and stays coherent. D6's correctness is load-bearing on D1. Worth making that dependency explicit somewhere in §2 — if someone in a future ADR proposes relaxing D1 ("maybe we can parallelize live-lane wakes since they have different dedup keys"), the answer is no, because then the un-deduped cross-source pair starts racing again.

---

## 5. Pace as first-class operator authority (D4, D5, D7, D8, D11)

This is where YARNNN is doing something neither reference system does, and where the distinctive product thesis lives.

OpenClaw treats cadence as an implementation concern: for proactive agents, a simple cron + checklist file is enough. You do not need a complex scheduling system. Cron expressions go in config, scheduler ticks fire them, done. No operator-facing pace abstraction.

Hermes is similar: crons prevent the agent from being purely reactive — you get proactive, scheduled work without managing infrastructure, but the granularity is per-job. Each cron has its own schedule. There's no workspace-level "how often does the agent work overall" knob. The closest Hermes comes is the safety constraint that a session started by a cron job cannot create new cron jobs — which prevents runaway cron proliferation but doesn't give the operator a cadence policy lever.

ADR-298's pace concept is genuinely product-distinctive: **pace as a declarative budget on aggregate cadence intent, enforced at recurrence-declaration time (D5) rather than runtime, with bundle-declared minimums (D7) that prevent operator misconfiguration.** This is the lever neither OpenClaw nor Hermes has, and it maps directly to a real operator question — "how often does my agent work?" — that those systems leave the operator to figure out from a list of individual cron expressions.

**Design-strength check**: D5 enforces pace at `Schedule()` call time, but pace can change after recurrences exist (Scenario F). Scenario F handles the "operator drops to slower pace" case by requiring operator-explicit reconciliation. That's correct. But Scenario E ("operator increases pace") says "Existing scheduled recurrences continue at their declared cron schedules; pace allows new recurrences up to hourly density." Fine. **The case not covered**: operator drops pace from `daily` to `weekly` while paced lane has 4 daily wakes already queued. What happens to the queued wakes? Run them all (overrunning the new pace once)? Drop the excess? Let them drain at new pace and accumulate backlog? The ADR is silent. I'd expect the answer is "queued wakes drain at the new pace, excess gets dropped via Scenario F's Clarify-driven recurrence reconciliation," but it should be stated.

D11's framing of pace/autonomy/persona as the "operator dial trifecta" is the right level of conceptual ambition for an ADR ratifying this much surface area. Three axioms, three files, three orthogonal dimensions. That's a clean product story. None of the reference systems articulate their operator surface this cleanly — OpenClaw documentation is implementation-shaped, Hermes is feature-list-shaped. YARNNN here is doing the work of being legibly opinionated about the operator's control surface, which is a differentiator if the product reaches operators who care about that legibility.

---

## 6. What ADR-298 does not address that the reference systems do

Three things worth flagging because future operators / reviewers / Anthropic-feedback-loop interlocutors will ask.

### Stale-lock detection

ADR-298 §8 acknowledges this as an open question (~180s threshold). OpenClaw has a similar mechanism with no published threshold but documented existence. Hermes uses `delegate_task` synchronous semantics: if the parent turn is interrupted, active children are cancelled and their work is discarded — i.e., a different model (cancel-on-parent-fail rather than reclaim-on-stale-lock). The reclaim model in ADR-298 §6 Scenario J is the right call for a single-Reviewer-per-workspace architecture, but the threshold needs empirical tuning. **I'd suggest starting at 2× the p95 session duration from production telemetry rather than picking 180s as a round number.**

### Durable execution semantics

Inngest and Temporal both treat each LLM call within a workflow as an independently retryable step with persisted result, so if the enrichment API rate-limits on the 15th contact, the workflow pauses, waits according to the backoff schedule, and retries. The first 14 enrichments don't re-run because their results are already persisted. ADR-298's model is coarser — the unit of retry is the whole Reviewer wake. For wakes that involve many tool calls, a mid-wake failure means re-running everything. This is probably fine for the current Reviewer cost profile (30-75s sessions) but if Reviewer sessions get longer or more tool-heavy, the cost of coarse-grained retry will start hurting. Not a blocker for ADR-298, but worth flagging as a future-ADR seed: **"if session duration grows past ~3min, consider step-level memoization."**

### Multi-workspace fairness

D7's "max of all active bundles' minimums" is correct for within-workspace pace composition. The cross-workspace fairness question (what happens when 100 workspaces all hit hourly pace simultaneously and the shared LLM rate limit gets contended) isn't ADR-298's problem to solve, but it's the next problem after this one ships. OpenClaw's global lane does some of this work; Inngest's multi-tenant aware prioritization, concurrency, throttling, batching, and rate limiting is the mature shape. Worth a forward-pointer in §7 ("Does not address cross-workspace fairness — separate concern, future ADR").

---

## 7. Net verdict

ADR-298 holds up well under cross-system comparison. The five-source enqueue → single-lane drain → two-lane policy → cross-source dedup architecture is convergent with OpenClaw's and Hermes's hard-won production patterns, which is the right kind of evidence: not "we copied them," but "we and they independently arrived at the same primitives under the same failure modes." That convergence is the strongest possible signal that the architectural commitments are correct rather than fashionable.

**The pace dial (D4-D11) is genuinely YARNNN-distinctive** and is the part of ADR-298 that does more than the reference systems, not less. It's also the part most exposed to product-fit risk — pace only matters if operators have aggregate-cadence intent in their heads when they think about their agent. If they don't, pace becomes a setting they ignore, and the architecture's elegance doesn't recoup itself. But that's a product-validation question, not an architecture-correctness question. ADR-298 the architecture stands up.

The §3 evidence-driven, prudential-not-axiomatic framing of the ADR-261 D3 reversal is unusually disciplined and is the part I'd most call out as a strength. Reversing a previously-canonized architectural guarantee is the kind of thing that erodes trust in a system's ADR record if done sloppily; ADR-298 does it with cited production telemetry, an explicit amendment table, and a self-aware "this is current-best, not eternal-best" caveat. That's the right way to do it.

---

## Three specific things to add before flipping to Implemented

1. **State the D6→D1 dependency explicitly.** Cross-source non-dedup is only safe because of single-lane drain. Future-proofs against later relaxation pressure.
2. **Cover the pace-drop-with-pending-queue case** that Scenario F currently elides.
3. **Forward-pointer to durable-execution and cross-workspace-fairness** as scoped-out adjacent concerns, so the next ADR's seam is pre-drawn.

None of those are blockers. They're polish on a structurally sound document.

---

## Sources

- OpenClaw architecture (concurrency, two-lane queue pattern): The Agent Stack Substack — *OpenClaw Architecture Part 2: Concurrency*
- OpenClaw multi-agent governance: Vertu — *OpenClaw / ClawdBot architecture*; Lumadock — *OpenClaw multi-agent coordination governance*
- OpenClaw cron / dedup: Sparkco — *OpenClaw cron jobs scheduling*
- OpenClaw architecture lessons: Agentailor — *OpenClaw architecture lessons for agent builders*
- Hermes SessionDB / WAL / composite session key: DeepWiki — *NousResearch/hermes-agent §7.3 Session and Media Management*; Nousresearch developer docs — *Architecture*
- Hermes cron model + safety constraints: MindStudio — *Hermes Agent 5-pillar architecture*; Analytics Vidhya — *Hermes Agent guide*
- Hermes delegation patterns: Nousresearch — *Delegation patterns*
- Durable execution comparison: Inngest — *Durable execution: key to harnessing AI agents*; Inngest product docs
