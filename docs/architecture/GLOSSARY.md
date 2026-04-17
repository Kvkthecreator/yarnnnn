# YARNNN Glossary

> **Status**: Canonical
> **Date**: 2026-04-17
> **Authors**: KVK, Claude
> **Ratified by**: ADR-189 (Three-Layer Cognition)
> **Supersedes**: `naming-conventions.md` (to be retired after the ADR-189 rename pass lands)

---

## Purpose

One word, one concept, one layer.

This glossary is the single source of truth for YARNNN terminology. Every ADR, architecture document, prompt, surface string, and marketing artifact must use the terms defined here. Drift triggers a correction PR — this is not soft guidance.

The glossary exists because YARNNN operates across three layers of cognition (the product, the role palette, the authored workers) and three kinds of readers (users, developers, investors). Without discipline, the same word collapses layers and confuses readers. With discipline, every term lands on exactly one thing at exactly one layer.

---

## Enforcement rule

1. **New ADRs must use glossary terms.** If a concept requires a word the glossary doesn't have, add it here first, then use it in the ADR.
2. **Retired terms cannot appear in active docs or code comments.** They may persist as internal DB slugs (e.g., the `thinking_partner` role value) where migration cost exceeds reader benefit — those exceptions are listed in the Exceptions table.
3. **Renames propagate in a single commit.** When a term is added, changed, or retired, every active doc and every prompt must move in the same PR. No staged rollouts.
4. **User-facing strings must pass the instinct test.** A non-technical user reads the term and immediately knows what it means. If a term needs a definition before it's useful, it's the wrong term.

---

## Entities

The things YARNNN manipulates. Each has exactly one name.

| Term | Definition | Notes |
|------|-----------|-------|
| **YARNNN** | The product AND the conversational super-agent the user addresses. When the user "talks to YARNNN," they are talking to the meta-cognitive layer. There is no separate name for the conversational layer — product and agent share the name. | Replaces "TP" and "Thinking Partner" as user-facing terminology. The internal DB role slug `thinking_partner` persists (migration exception — see Exceptions table). |
| **Agent** | An identity-explicit, user-created, domain-scoped worker. Appears on `/agents`. Has an AGENT.md identity file, accumulated domain context, and a developmental trajectory. Created by the user through conversation with YARNNN. | This is the *only* thing the word "Agent" refers to in user-facing contexts. Not YARNNN. Not Specialists. Not platform bots. |
| **Specialist** | A role-typed capability YARNNN draws from when drafting a team for a task. There are six: Researcher, Analyst, Writer, Tracker, Designer, Reporting. Specialists have role-scoped stylistic memory (ADR-117) but no domain identity. | Specialists are YARNNN's palette. Users do not address Specialists by name, do not see them on `/agents`, and cannot create or delete them. They are infrastructure. |
| **Platform Bot** | A mechanical agent scoped to one external API. Activated when the user connects the corresponding platform. Examples: Slack Bot, Notion Bot, GitHub Bot, Commerce Bot, Trading Bot. | Distinct class from Agents and Specialists. Platform Bots are mechanical (no LLM cognition of their own beyond scoped tool use) and own temporal context directories. |
| **Team** | The set of Specialists and/or Agents assigned to a specific task. Declared in TASK.md's `## Team` section. Drafted by YARNNN per task. | "Team" is always per-task. A workspace does not have "a team." A workspace has Agents plus YARNNN, and each task has a team. |
| **Task** | A defined work unit with an objective, cadence, delivery, and success criteria. Lives in `/tasks/{slug}/TASK.md`. Unchanged from ADR-138. | Tasks are the WHAT. Agents and Specialists are the WHO. |
| **Domain** | An accumulated context area at `/workspace/context/{domain}/`. Created by work demand, not pre-scaffolded. Shared across all tasks. Unchanged from ADR-151 / ADR-176. | Domain names come from user language (e.g., `competitors/`, `clients/`), not from a pre-declared registry key. |
| **Workspace** | The user's YARNNN environment. Contains Agents, tasks, Domains, uploaded documents, workspace identity files (IDENTITY.md, BRAND.md). | **Not** a synonym for "roster." The word "roster" is retired — a workspace holds Agents, not a roster. |

---

## Verbs

What actors do. Different actors get different verbs when the cardinality or permanence of the act differs.

| Verb | Actor | Object | Cardinality |
|------|-------|--------|-------------|
| **Create** | User (through conversation with YARNNN) | an Agent | One-shot. Produces persistent identity. |
| **Draft** | YARNNN | a Team | Per-task. Iterative. Re-drafted every task cycle from the Specialist palette. |
| **Evolve** | Feedback loop | an Agent or a Specialist | Continuous. Agents evolve domain identity; Specialists evolve role-scoped stylistic memory. |
| **Scaffold** | System | a workspace | Once, at signup. Reserved for workspace-level setup. Never used for agent creation. |

**Asymmetry is deliberate.** The user *creates* an Agent (generic, neutral, universally understood). YARNNN *drafts* a Team (precise about the iterative per-task selection nature of the act). Collapsing these to a single verb loses information.

---

## Identity layers

What develops, and where.

| Layer | Scope | Substrate | Developer |
|-------|-------|-----------|-----------|
| **Workspace identity** | YARNNN-scoped (the user's work context) | `/workspace/IDENTITY.md`, `/workspace/BRAND.md` | User (via YARNNN, usually through inference on uploaded documents) |
| **Specialist memory** | Role-scoped stylistic preference | ADR-117 distillation artifacts (`style.md`), role-keyed | Feedback loop across all tasks that used the specialist |
| **Agent identity** | Domain-scoped, user-created | `/agents/{slug}/AGENT.md` + accumulated Domain context the Agent is responsible for | User (initial creation via conversation) + feedback loop (evolution) |

The split matters because **Specialists and Agents develop along different axes**. A Specialist gets better at style and preference. An Agent gets better at domain knowledge. Conflating them (the old ADR-117 framing that treated "agent memory" as one thing) produced the confusion that ADR-189 resolves.

---

## Retired terms

These words no longer appear in active documentation, prompts, or user-facing surfaces. Every occurrence in new work is a correction-PR trigger.

| Retired | Replacement | Reason |
|---------|-------------|--------|
| TP (user-facing) | YARNNN | The product and the conversational agent share a name. No separation. |
| Thinking Partner (user-facing) | YARNNN | Same as above. |
| Roster | — (no replacement) | Workspaces hold Agents, not a roster. Fixed signup roster is retired (ADR-189). |
| Hire (as verb for agent creation) | Create | "Hire" implies a pre-existing catalog of workers. YARNNN does not have such a catalog. |
| Compose a team | Draft a team | "Compose" is mechanical/musical register. Draft is precise about iterative selection. |
| Author (as verb for agent creation) | Create | Considered and rejected — "Create" is more neutral and universally understood. The ownership register lives in *how* the act happens (through conversation), not in the verb. |
| Specialist (meaning "signup-scaffolded identity") | Agent (if identity-explicit) or Specialist (if role palette) | The old double meaning was the source of ADR-189's confusion. After ADR-189, "Specialist" refers only to the role palette. |
| Craft | Specialist | Considered during discourse and rejected — artisanal register was ambiguous. Specialist is the precise word. |
| Domain-steward, Competitive Intelligence, Market Research, Business Development, etc. (ICP roster names) | — (deleted) | Retired by ADR-176. |
| Create a team | Draft a team | Teams are re-drafted per task, not created once. "Create" would muddy the iterative cardinality. |

---

## Exceptions

Cases where a retired term persists by necessity, and the migration cost exceeds the reader benefit.

| Location | Term that persists | Why |
|----------|-------------------|-----|
| `agents.role` DB column value | `thinking_partner` | Migration 142 (ADR-164) locked this value into the constraint. Renaming would require a DB migration with negligible user benefit — the value is never surfaced outside DB internals. |
| `api/services/agent_framework.py` `ROLE_PULSE_CADENCE` key | `thinking_partner` | Matches DB slug. Internal only. |
| Historical ADRs (140, 164, 176, 186, etc.) | References to "TP" and "Thinking Partner" | ADRs are historical artifacts. They are not rewritten when terms change; they stand as dated records of the decisions in force at their time. New ADRs supersede them; the supersession is the record. |

All other appearances of retired terms — prompts, active architecture docs, new code, UI strings, marketing — must use replacements.

---

## Product promise (canonical one-liner)

Every external-facing statement of what YARNNN is must be traceable to one of the two phrasings below. Other copy may riff on these for voice variation, but the substance must be preserved.

**Primary:** *Describe your work. Create the agents that do it.*

**Secondary (short form):** *Your work, your agents.*

These replace the prior canonical one-liner ("Persistent agents with accumulated context do recurring work products for you") in user-facing copy. The prior framing remains valid for internal/architectural contexts where the accumulation mechanism is the point.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-17 | v1 — Initial glossary ratified by ADR-189. Supersedes `naming-conventions.md`. YARNNN as super-agent, Specialist as palette, Agent as user-created identity, Create/Draft/Evolve/Scaffold verb discipline, identity-layer split (workspace/specialist/agent). |
