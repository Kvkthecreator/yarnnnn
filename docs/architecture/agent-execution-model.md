# Architecture: Agent Execution Model

**Status:** Canonical
**Date:** 2026-02-19
**Supersedes:** ADR-016 (Layered Agent Architecture) — work agent delegation model
**Codifies:** ADR-061 (Two-Path Architecture Consolidation)
**Related:**
- [ADR-061: Two-Path Architecture](../adr/ADR-061-two-path-architecture.md)
- [ADR-068: Signal-Emergent Deliverables](../adr/ADR-068-signal-emergent-deliverables.md) — extends Path B with Signal Processing phase
- [ADR-042: Deliverable Execution Simplification](../adr/ADR-042-deliverable-execution-simplification.md)
- [ADR-045: Deliverable Orchestration Redesign](../adr/ADR-045-deliverable-orchestration-redesign.md)
- [Supervision Model](supervision-model.md) — the complementary UI/UX framing

---

## The Core Principle

YARNNN has exactly two execution paths. They are strictly separate and must remain so.

**Thinking Partner (TP)** is a conversational agent. It does not generate deliverable content.

**The Backend Orchestrator** generates deliverable content. It is not conversational.

This is not a style preference — it is a load-bearing architectural constraint. Mixing the two paths produces systems that are harder to reason about, harder to cost, and harder to extend.

---

## Two Paths

### Path A — Thinking Partner (Real-time)

```
User ←→ TP
```

| Property | Value |
|---|---|
| Character | Conversational, Claude Code-like |
| Latency | <3 seconds |
| Scope | Session-scoped |
| Tools | Primitives: Read, Write, Edit, Search, Execute, platform tools |
| Entry point | `/api/chat` |
| Agent | `ThinkingPartnerAgent` (`api/agents/thinking_partner.py`) |

**TP's responsibilities:**
- Answer questions (searches memory, platform data, documents)
- Execute one-time platform actions (send Slack message, create Gmail draft)
- Create and configure deliverables when the user explicitly asks
- Read and explain existing deliverable versions

**TP explicitly does NOT:**
- Generate recurring deliverable content (that is Path B)
- Run long-polling or multi-step background research
- Proactively initiate actions outside a user session

> **The rule:** TP creates deliverable *configuration*. The orchestrator generates deliverable *content*.

---

### Path B — Backend Orchestrator (Async)

```
Trigger → Orchestrator → Output → Notification
```

| Property | Value |
|---|---|
| Character | Scheduled, type-driven, non-conversational |
| Latency | Latency-tolerant (seconds to minutes) |
| Scope | User-scoped, not session-scoped |
| Tools | Execution strategies (platform fetch, web research) |
| Entry point | `unified_scheduler.py` (cron `*/5 * * * *`) or `/api/deliverables/{id}/run` |
| Agent | `DeliverableAgent` (`api/agents/deliverable.py`) |

**Orchestrator's responsibilities:**
- **Signal Processing phase** (ADR-068): Extract behavioral signal from connected platform data, reason over what the user's world warrants, create signal-emergent deliverables
- **Analysis phase** (ADR-060): Mine TP session content for recurring patterns, create analyst-suggested deliverables
- **Execution phase**: Execute deliverables on schedule or on manual trigger, select and run execution strategy based on `type_classification.binding`, produce `deliverable_versions` records, deliver outputs (email, Slack, Notion)

**Orchestrator explicitly does NOT:**
- Participate in conversation
- Hold session state
- Respond to user messages directly

---

## The Boundary in Code

```python
# Path A: TP creates the deliverable configuration
# api/agents/tp_prompts/behaviors.py

User: "Set up a weekly digest of #engineering"
→ TP calls Write(ref="deliverable:new", content={title: ..., schedule: ..., sources: ...})
→ TP responds: "Created. It will run every Monday at 9 AM."

# Path B: Orchestrator generates the content — no TP involvement
# api/services/deliverable_execution.py

unified_scheduler.py (cron)
  → execute_deliverable_generation(client, user_id, deliverable)
      → get_execution_strategy(deliverable)     # based on type_classification.binding
      → strategy.gather_context(...)            # fetch from platforms
      → generate_draft_inline(...)              # single LLM call → DeliverableAgent
      → deliver_version(...)                    # email / Slack / Notion
```

The `ThinkingPartnerAgent` is never invoked in the orchestrator path. The `DeliverableAgent` is never invoked in the chat path.

---

## Execution Strategies (Path B)

Complexity in Path B lives in the *strategy*, not in agent proliferation.

| Binding | Strategy | Description |
|---|---|---|
| `platform_bound` | `PlatformBoundStrategy` | Single platform fetch (Slack, Gmail, Calendar) |
| `cross_platform` | `CrossPlatformStrategy` | Parallel fetch across multiple platforms |
| `research` | `ResearchStrategy` | Web research via Anthropic native tool |
| `hybrid` | `HybridStrategy` | Web research + platform fetch in parallel |

Strategy is selected at execution time from `deliverable.type_classification.binding`. The same `DeliverableAgent` handles all cases — strategy determines what context it receives.

---

## What This Means for Proactive / Autonomous Deliverables

The proactive autonomy roadmap is implemented through **ADR-068: Signal-Emergent Deliverables** — entirely within Path B. TP is not involved.

**Correct framing (all Path B):**

| Concept | Belongs in | Rationale |
|---|---|---|
| "What happened in user's world?" | Signal Processing phase — live platform API queries | Deterministic, fresh external state, no LLM |
| "What does this warrant?" | Signal Processing phase — orchestration agent reasoning pass | Single LLM call over signal summary |
| Drift detection, conflict detection, meeting prep | Signal-emergent deliverable creation | `origin=signal_emergent`, `trigger_type=manual` |
| Cross-signal correlation (Notion + Slack) | Signal summary input to orchestration agent | Cross-platform extraction, not cross-platform agent |
| Review-before-send gate | `governance=manual` on signal-emergent deliverable | Existing mechanism — no new UX pattern needed |
| User promotes output to recurring | `promote-to-recurring` endpoint | `trigger_type` updated; `origin` preserved as provenance |

**Incorrect framing (violates the boundary):**

- "TP runs autonomously with a task brief" — TP is conversational, not a batch processor
- "Wire TP to run deliverable generation" — TP does not generate deliverable content
- "Condition evaluation layer for TP" — conditions are evaluated in the orchestrator, not in a session

The mental model: proactive deliverables are not TP being more autonomous. They are the orchestrator gaining a **signal processing phase** that observes the user's platform world directly — without waiting for the user to report it — and creates deliverables in response.

See [ADR-068](../adr/ADR-068-signal-emergent-deliverables.md) for the full decision, schema addition, and implementation sequence.

---

## Relationship to the Supervision Model

The [Supervision Model](supervision-model.md) covers the UI/UX dimension: deliverables are *objects the user supervises*, TP is *how they supervise*. That framing remains correct and is complementary to this document.

This document covers the *execution* dimension: how content is actually produced. The supervision model says nothing about execution paths — it was written before ADR-061 clarified them.

Together:

| Document | Domain | Answers |
|---|---|---|
| Supervision Model | UI/UX, product framing | How do users interact with and supervise the system? |
| Agent Execution Model (this doc) | Backend architecture | Which code paths produce deliverable content, and which don't? |

---

## Anti-Patterns

**Using TP for deliverable content generation**
TP is session-scoped and latency-sensitive. Deliverable generation can be slow (multi-platform fetch, multi-search). Putting generation in TP blocks the session, obscures cost, and violates the separation that makes both paths predictable.

**Creating new agents for new deliverable complexity**
ADR-061 notes that the prior "layered agent" model (TP delegates to specialized work agents) was never realized and produced dead code. Complexity belongs in execution strategies, not new agent classes.

**Treating the orchestrator as a chat participant**
The orchestrator doesn't hold conversation state. It knows the deliverable, the user's context (via `user_context`), and the platforms. It does not know what the user said five minutes ago — and it shouldn't need to.
