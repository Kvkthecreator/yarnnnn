# ADR-175: Generic Roster Model — Domain-Inferred Agent Initialization

**Date:** 2026-04-13
**Status:** Superseded by ADR-176 (Work-First Agent Model, 2026-04-13) — never implemented
**Authors:** KVK, Claude
**Supersedes:** ADR-140 (Agent Workforce Model — Pre-Scaffolded Roster, signup initialization only)
**Extends:** ADR-140 (agent class model and capability bundles preserved), ADR-174 (Filesystem-Native Workspace — depends on fluid task creation and filesystem-first discovery)

---

## Context

ADR-140 established a pre-scaffolded roster of 10 agents created at signup: 5 domain-stewards (Competitive Intelligence, Market Research, Business Development, Operations, Marketing & Creative), 1 synthesizer (Reporting), 3 platform-bots (Slack Bot, Notion Bot, GitHub Bot), and 1 meta-cognitive agent (Thinking Partner).

The domain-steward names and their pre-assigned context domains (`competitors`, `market`, `relationships`, `projects`, `content_research`) encode a specific ICP assumption: a solo founder or small team doing broad strategic work across those five functions. This assumption is load-bearing at signup — every user gets the same 5 domain-stewards regardless of what they actually do.

**The risk:** A user who runs an agency tracks `clients`, `campaigns`, and `vendors` — not `competitors` and `market`. An investor tracks `portfolio`, `pipeline`, and `deal_flow`. A product team tracks `users`, `features`, and `roadmap`. The pre-scaffolded domain names are wrong for any ICP that isn't the one assumed at design time. Worse, the wrong agent names create friction: users see "Competitive Intelligence" and "Market Research" when they need "Client Work" and "Campaigns." The roster looks like it was built for someone else.

The agent class model (domain-steward / synthesizer / platform-bot / meta-cognitive) is correct and universal — every user needs these classes regardless of ICP. What is ICP-specific is the domain names the stewards own.

This ADR separates those two concerns: class structure is fixed at signup; domain assignment is deferred to the user's first work.

**Dependency:** This ADR depends on ADR-174 (fluid task creation, filesystem-first discovery). Domain-inferred initialization requires that TP can create domain stewards on demand and that those agents' context directories appear automatically in the compact index without a registry update.

---

## Decision

### The Principle

**Agent classes are universal. Domain names are user-specific. Signup creates classes; work creates domains.**

### What Changes at Signup

`DEFAULT_ROSTER` is reduced to the universal infrastructure layer:

| Agent | Class | Domain | Created at |
|-------|-------|--------|-----------|
| Thinking Partner | meta-cognitive | none | signup |
| Reporting | synthesizer | none (cross-domain) | signup |
| Slack Bot | platform-bot | slack (temporal) | signup, activated on platform connect |
| Notion Bot | platform-bot | notion (temporal) | signup, activated on platform connect |
| GitHub Bot | platform-bot | github (temporal) | signup, activated on platform connect |

5 agents at signup instead of 10. No domain-stewards created until work demands them.

**Cold-start handling:** A user with 0 domain-stewards still has TP and Reporting. TP's first conversation assigns work and creates domain stewards as a natural part of that conversation — not as a separate onboarding step. TP creates domain stewards from the `domain_steward` generic template (see below), optionally specializing from the scaffold library when a known domain type matches.

### The Generic Domain Steward Template

A new `domain_steward` template is added to `AGENT_TEMPLATES`. It carries the full domain-steward capability bundle but no pre-assigned domain. TP writes the domain into the agent's `AGENT.md` from the user's first task.

```python
"domain_steward": {
    "class": "domain-steward",
    "domain": None,  # assigned by TP from first task
    "display_name": "Research Agent",  # overwritten by TP at creation
    "tagline": "Tracks and analyzes a specific domain",
    "capabilities": [
        "web_search", "read_workspace", "search_knowledge",
        "read_slack", "read_notion", "read_github",
        "investigate", "produce_markdown", "chart", "mermaid", "compose_html",
    ],
    "description": "A domain steward. Maintains a specific context domain, "
                   "accumulates intelligence across runs, produces deliverables "
                   "synthesized from accumulated context.",
    "default_instructions": "Your domain will be assigned from your first task. "
                            "Once assigned, maintain your context domain: research "
                            "entities, update profiles, log signals, rewrite synthesis. "
                            "When producing deliverables, synthesize from accumulated context.",
    "methodology": {
        # Inherits the generic output, research, and rendering playbooks
        # Domain-specific methodology appended to AGENT.md by TP at first task assignment
        "_playbook-outputs.md": GENERIC_OUTPUT_PLAYBOOK,
        "_playbook-research.md": GENERIC_RESEARCH_PLAYBOOK,
        "_playbook-rendering.md": _PLAYBOOK_RENDERING,
    },
}
```

### The Scaffold Library Remains Intact

The existing 5 domain-specific templates (`competitive_intel`, `market_research`, `business_dev`, `operations`, `marketing`) are **not deleted**. They become the scaffold library — curated, well-crafted starting points that TP draws from when the user's work matches a known domain type.

When TP creates a domain steward, it chooses:

1. **From the scaffold library** if the domain clearly matches a known type. User says "I need to track our competitors" → TP creates from `competitive_intel` template, which carries the specialized methodology playbooks for competitive intelligence work.

2. **From the generic template** if the domain is novel or user-specific. User says "I need to track our clients" → TP creates from `domain_steward` template, writes a domain-specific `AGENT.md`, and the agent's methodology develops through feedback and task execution.

TP records which template was used in `AGENT.md` under a `## Scaffolded From` section (informational only, not load-bearing for pipeline logic).

### Agent Creation Flow (Post-ADR-175)

```
User first conversation / first task upload
    ↓
TP reads compact index: no domain stewards present
    ↓
TP identifies work domain from task content / upload / user statement
    ↓
TP matches against scaffold library:
  - Known domain → create from specific template (e.g., competitive_intel)
  - Novel domain → create from generic domain_steward template
    ↓
TP calls ManageAgent(action="create", role="competitive_intel"|"domain_steward", title="...", domain="...")
    ↓
Agent created → AGENT.md written with domain assignment
    ↓
First task assigned to new agent → execution begins
    ↓
Context directory appears in compact index at next working memory build
```

### What Does Not Change

**The agent class model.** domain-steward / synthesizer / platform-bot / meta-cognitive is the correct universal taxonomy. These classes are fixed at signup via the reduced roster.

**The capability bundles.** `web_search`, `read_workspace`, `investigate`, `compose_html`, etc. are correct and map to agent classes, not domain names. The generic `domain_steward` template carries the full domain-steward capability bundle.

**The methodology playbooks.** The existing playbooks (output, research, rendering) are preserved in the scaffold library. Generic stewards start with the generic versions; specialized stewards get the domain-specific craft. Both can be extended by feedback distillation (ADR-117) over time.

**Platform bots.** 1:1 with platform connections. Unchanged — they own temporal context directories, not canonical domains.

**Reporting (synthesizer).** Cross-domain by design — reads from all context domains regardless of what they're named. Unchanged.

**ManageAgent(action="create").** The primitive is unchanged. ADR-175 changes what TP chooses to create at what time, not how creation works mechanically.

---

## Architecture Integration

### Relationship to Existing ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-140 (Agent Workforce Model) | Supersedes the signup initialization model. Agent class taxonomy, capability bundles, and three-class structure (steward/synthesizer/bot) preserved. `DEFAULT_ROSTER` shrunk; domain-specific templates demoted to scaffold library. |
| ADR-174 (Filesystem-Native Workspace) | Depends on. Fluid task creation (Decision 4) enables TP to create domain stewards on demand. Filesystem-first discovery (Decision 1) ensures new agent context directories appear in compact index automatically. |
| ADR-138 (Agents as Work Units) | Consistent with. Agents are WHO (identity, domain expertise, memory). Tasks are WHAT. Domain assignment is an identity property written to `AGENT.md`, not a task property. |
| ADR-144 (Inference-First Shared Context) | Extends the inference-first principle from workspace identity to agent roster. Just as IDENTITY.md is inferred from user content, domain steward identities are inferred from user work. |
| ADR-164 (Back Office Tasks / TP as Agent) | Unaffected. TP's meta-cognitive role, back office tasks, and roster position are unchanged. |
| ADR-117 (Feedback Substrate) | Unaffected. Feedback distillation (edits → style.md → AGENT.md preferences) works identically for generic and specialized domain stewards. |

### Onboarding Implications

The reduced signup roster changes the first-session experience:

- **Cold workspace compact index:** TP sees 5 agents (TP + Reporting + 3 bots), 0 domain stewards, 0 context domains, 0 tasks. This is the honest cold-start state.
- **TP's first conversation posture:** TP reads the sparse index, understands the user is new, and its first goal is to identify the user's work domains and create domain stewards for them. This is not a separate onboarding flow — it is TP's natural response to seeing an empty workspace.
- **Suggestion chips (ADR-144):** Cold-start suggestion chips ("Tell me what you're working on", "Upload a document", "Connect Slack") remain unchanged. The empty agents state is a new signal TP uses to understand it should create stewards, not just infer identity/brand.
- **No regression for platform-connect users:** If a user connects Slack before their first chat, the Slack Bot activates and begins its slack-digest task immediately — same as current behavior. Domain stewards are created when the first substantive task or conversation happens.

---

## Implementation Phases

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | Proposed | `domain_steward` generic template in `AGENT_TEMPLATES`. `DEFAULT_ROSTER` reduced to 5 universal agents. `GENERIC_OUTPUT_PLAYBOOK` + `GENERIC_RESEARCH_PLAYBOOK` extracted from existing domain templates. |
| Phase 2 | Proposed | TP prompt updated: empty-agents detection in compact index triggers domain-inference posture. ManageAgent create guidance updated — scaffold library matching logic documented in TP tools prompt. |
| Phase 3 | Proposed | `ManageAgent(action="create")` extended to accept `domain` param written to `AGENT.md`. Context directory scaffolded at agent creation from CONVENTIONS.md structure (ADR-174). |

**Prerequisite:** ADR-174 Phase 1 (filesystem-first discovery) must ship before Phase 2 of this ADR — TP needs to see new context directories in the compact index as they are created, without a registry update.

---

## Consequences

**Positive:**
- The roster is no longer an ICP bet. Any user — agency, investor, product team, founder — gets the same universal infrastructure and domain stewards that reflect their actual work.
- Domain names match user mental models because they come from the user's own language, not from a pre-declared taxonomy.
- The scaffold library (5 domain-specific templates) retains its value as curated craft. Users whose work matches known domain types get specialized methodology playbooks for free.
- Workspace context directories are created only for domains that actually exist in the user's work. No empty `/workspace/context/market/` folder for a user who never does market research.

**Constraints:**
- Cold start is slightly more involved: TP must identify domains and create stewards before any domain-specific work can run. This is one additional step on the critical path for new users.
- TP's domain inference must be reliable. If TP creates a "Sales Pipeline" agent when the user actually wanted a "Client Relationships" agent, renaming it requires TP to rewrite `AGENT.md` and potentially migrate context files — not hard, but friction. Domain names should be confirmed with the user before the agent is created.
- The scaffold library matching heuristic (when to use `competitive_intel` template vs. generic `domain_steward`) lives in TP's prompt, not in code. It is a judgment call, not a deterministic rule. Over time this can be made more precise based on observed patterns, but initially it depends on prompt quality.

**Risk: Domain fragmentation.** If TP creates too many narrow domain stewards (one per task rather than one per domain), the workspace becomes fragmented: 8 agents each with 3 files rather than 3 agents each with 25 files. The moat thesis depends on accumulation depth, not breadth. TP's domain creation guidance must emphasize: create a new agent only when the work implies a genuinely new durable context domain — not for every new task type within an existing domain.
