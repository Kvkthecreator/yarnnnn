# YARNNN Technical Architecture Brief

**Supplemental to IR Deck — March 2026 (v2)**
**Kevin Kim · kvkthecreator@gmail.com · yarnnn.com**

---

## The Core Insight: Claude Code Online — For Teams

Claude Code proved that structured instructions (SKILL.md) + local tools + a filesystem = indefinitely expandable agent capabilities. YARNNN applies this exact model — but persistent, autonomous, multi-agent, and cloud-native.

**Two-filesystem architecture:**

The capability filesystem lives on the output gateway (a Docker service with pandoc, python-pptx, matplotlib, pillow). Skills are folders: `render/skills/chart/SKILL.md`, `render/skills/mermaid/scripts/render.py`. Adding a new output capability means adding a skill folder — same expansion model as Claude Code. Eight skills are live today.

The content filesystem lives in a virtual filesystem over Postgres (`workspace_files`). Each agent has a workspace: `AGENT.md` (behavioral identity), `memory/preferences.md` (learned from edits), `thesis.md` (accumulated understanding), output folders with manifests. Each project has a charter: `PROJECT.md` (objective), `TEAM.md` (roster + capabilities), `PROCESS.md` (output spec, cadence, phases). This is the accumulating substrate — every pulse reads from it, every run writes to it.

The deliberate separation: capabilities are platform-wide and curated; content is user-scoped and accumulating. Same interface pattern, different services, different lifecycles.

**What this means for investors:** YARNNN's capability surface expands the same way Claude Code's does — structurally, not through custom engineering per feature. And the filesystem convention is marketplace-compatible: imported skills (MCP tools, Claude Code marketplace, external APIs) plug in via the same SKILL.md interface.

---

## Agent Types: The Product Catalog

Every agent is one of 8 specialist types — a "hire" the user adds to their project team. Three registries define the capability substrate:

1. **Agent Type Registry** — 8 user-facing types (briefer, monitor, researcher, analyst, drafter, writer, planner, scout) + PM infrastructure. Each type is a deterministic bundle of capabilities. No earning, no progression, no seniority gates.

2. **Capability Registry** — maps each capability to its category, runtime, tool, and skill docs. `chart` → Python runtime → matplotlib → `render/skills/chart/SKILL.md`.

3. **Runtime Registry** — where compute happens. Internal (API service), Python render (Docker gateway), Node Remotion (future), external APIs.

Capabilities are fixed at creation by type. Development is knowledge depth — accumulated memory, learned preferences, refined domain expertise — not capability breadth. An analyst on its 50th run doesn't gain new tools; it has 50 cycles of accumulated observations about what matters in this user's data.

**What this means for investors:** The type system is the product offering. Users "hire" agent types the way they'd hire team members. New types can be added to the registry without framework changes — the registries are the expansion path.

---

## Coordinated Execution: PM Phase Dispatch

Most "AI agent" products run agents independently. YARNNN coordinates them as a team.

**The execution model:**

Every project has a PM agent that owns the heartbeat. Contributors don't pulse independently — the PM dispatches them in structured phases:

```
PM pulses every 2h
  → Reads work plan (phases with dependencies)
  → Checks: what phase are we in? What's blocking?
  → Dispatches contributor(s) for current phase
  → Injects cross-phase context (prior phase outputs → next phase briefs)
  → Contributors execute within phase context
  → PM reads contributor self-assessments
  → PM advances phase, re-steers, or triggers assembly
```

**Three-tier pulse funnel (cheap-first):**
- Tier 1 (deterministic): Fresh content? Budget? Cadence met? Zero LLM cost. ~80% of pulses resolve here.
- Tier 2 (Haiku self-assessment): Agent reads own workspace, decides whether to generate. ~$0.001/pulse.
- Tier 3 (PM coordination): PM reads contributor state, dispatches phases, gates quality. ~$0.01/pulse.

**Charter-driven cadence enforcement** prevents runaway execution. The `PROCESS.md` file specifies cadence (e.g., "weekly on Monday"); Tier 1 enforces it deterministically. Result: predictable cost — ~$0.50/month per project at steady state.

**What this means for investors:** This is coordination intelligence, not just individual agent quality. A weekly competitive brief where researcher → analyst → writer → PM assembly is structurally different from three independent agents producing uncoordinated outputs. And the coordination improves with tenure — PM learns which handoffs work, which contributors need steering, what assembly cadence produces the best deliverable.

---

## Feedback-to-Intelligence Loop

The claim that "agents improve with tenure" is structural, not aspirational. Three concrete mechanisms:

**1. Edit distillation (ADR-117):** When a user edits an agent's output, the system categorizes the edit (tone, structure, content, emphasis), extracts the implicit preference, and writes it to `memory/preferences.md`. Next run, these preferences are injected into the agent's system prompt. The agent literally learns "this user prefers bullet points over paragraphs" or "always lead with revenue numbers." Implemented and running in production.

**2. Agent self-reflection (ADR-128):** After every run, the agent writes a self-assessment to `memory/self_assessment.md` — mandate fitness, domain fitness, context currency, output confidence. These assessments form a rolling trajectory (5 most recent). The PM reads contributor trajectories to inform steering decisions. An agent that repeatedly flags "low context currency" gets dispatched with richer context next cycle.

**3. Multi-agent coherence protocol (ADR-128):** Four flows keep conversation, filesystem, and agent cognition in sync: contributors write self-assessments → PM reads trajectories → chat directives persist to `memory/directives.md` → contributors read PM project assessments. The team stays aligned without human coordination.

**What this means for investors:** Week 12 outputs require zero corrections not because the LLM got smarter, but because 12 weeks of structural feedback shaped every team member's behavior and the PM's coordination patterns. This is the mechanism behind the switching cost — a competitor's team starts from Week 1.

---

## Work-First Onboarding: Describe, Don't Configure

Most AI tools start with "connect your platforms." YARNNN starts with "describe your work."

A two-step onboarding (completable in 60 seconds): (1) "How is your work structured?" — single-focus vs. multi-scope, (2) define work scopes with context. A single Sonnet inference extracts structured work units. Each work unit becomes a project via `scaffold_project()` — deterministic creation of PM + typed contributors + three-file charter.

Platform connections happen after (or in parallel) and enrich existing work-scoped projects. Slack channels map to client projects. Notion pages map to knowledge domains. The platform is the data source; the work description is the organizing principle.

**What this means for investors:** The user describes "3 clients and a product launch" and gets 4 correctly-scoped projects with coordinated agent teams — not a generic Slack recap. The system understands work structure, not just platform topology. And work descriptions carry implicit lifecycle: "3 clients" implies persistent recurring work; "board deck" implies bounded deliverable. The system infers this — the user doesn't configure it.

---

## Engineering Velocity & Rigor

**136 Architecture Decision Records** document every significant design choice — from memory architecture (ADR-059) to project charter separation (ADR-136). Each ADR captures context, alternatives, rationale, and implementation status. This is the substrate that enables a solo founder to maintain architectural coherence across a complex multi-service system.

**Full-stack implementation by a single technical founder:**
Next.js frontend, FastAPI backend, Supabase (Postgres), Claude API, Docker output gateway. Two platform integrations (Slack, Notion) with OAuth, paginated sync, and tier-based rate limiting. MCP server with OAuth 2.1 for Claude.ai/ChatGPT interop (9 tools). Five Render services. HTML compose engine with 8-skill library. Work budget governor. PM-coordinated phase dispatch. Three-tier pulse architecture.

**What this signals:** The architecture isn't a prototype that needs to be rebuilt. It's production infrastructure with the engineering rigor of a team — built by one person who made 136 deliberate decisions instead of 136 shortcuts.

---

*kvkthecreator@gmail.com · yarnnn.com*
