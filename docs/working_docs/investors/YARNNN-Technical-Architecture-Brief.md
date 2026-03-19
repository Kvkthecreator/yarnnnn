# YARNNN Technical Architecture Brief

**Supplemental to IR Deck — March 2026**
**Kevin Kim · kvkthecreator@gmail.com · yarnnn.com**

---

## The Core Insight: Claude Code Online

Claude Code demonstrated that structured instructions (SKILL.md) + local tools + a filesystem = indefinitely expandable agent capabilities. YARNNN applies this exact model — but persistent, autonomous, and cloud-native.

**Two-filesystem architecture:**

The capability filesystem lives on the output gateway (a Docker service with pandoc, python-pptx, matplotlib, pillow installed). Skills are folders: `render/skills/pptx/SKILL.md`, `render/skills/chart/scripts/render.py`. Adding a new output format means adding a skill folder — same expansion model as Claude Code.

The content filesystem lives in a virtual filesystem over Postgres (`workspace_files`). Each agent has a workspace: `AGENT.md` (behavioral identity), `memory/preferences.md` (learned from edits), `thesis.md` (accumulated understanding), output folders with manifests. This is the accumulating substrate — every run reads from it, every run writes to it.

The deliberate separation matters: capabilities are platform-wide and curated; content is user-scoped and accumulating. Same interface pattern, different services, different lifecycles. Agents read SKILL.md to learn how to construct high-quality output specs, then the gateway renders them. The agent never knows whether a skill runs locally in the container or calls an external API.

**What this means for investors:** YARNNN's capability surface expands the same way Claude Code's does — structurally, not through custom engineering per feature. Eight skills are live today (PDF, PPTX, XLSX, chart, diagram, HTML, data export, image). Each new skill is a folder, not a project.

---

## Autonomous Orchestration: The Composer Heartbeat

Most "AI agent" products require a human to create, configure, and manage agents. YARNNN's Composer is an autonomous management layer that runs the knowledge workforce without human prompting.

**How it works:**

A cron-triggered heartbeat periodically assesses the entire agent workforce. The assessment is substrate-aware — it reads:

- Platform content freshness (what's been synced, what's stale)
- Agent maturity signals (run count, approval rate, edit distance trend)
- Cross-agent consumption patterns (agent A's output appearing in agent B's manifest)
- Knowledge corpus gaps (platforms connected but underserved by agents)

Based on this assessment, Composer takes autonomous actions:

- **Creates agents** when it detects unserved patterns ("You have recurring 1:1s but no meeting prep agent")
- **Pauses underperformers** when edit distance stays high after multiple runs
- **Dissolves unused agents** when outputs go unread
- **Coaches via supervisor notes** written to agent workspaces (steering without reconfiguring)
- **Proposes projects** when cross-agent composition opportunities emerge

**Five bounded contexts:** Bootstrap (deterministic agent creation on platform connect), Heartbeat (periodic assessment), Composer (assessment + creation/adjustment), Project creation (multi-agent coordination), and Lifecycle management (pause/dissolve/promote).

**What this means for investors:** The system manages itself. User effort decreases over time while output quality increases — the inverse of every SaaS tool that requires ongoing configuration.

---

## Feedback-to-Intelligence Loop

The claim that "agents improve with tenure" is structural, not aspirational. Three concrete mechanisms:

**1. Edit distillation (ADR-117):** When a user edits an agent's output, the system categorizes the edit (tone, structure, content, emphasis), extracts the implicit preference, and writes it to `memory/preferences.md`. Next run, these preferences are injected into the agent's system prompt. The agent literally learns "this user prefers bullet points over paragraphs" or "always lead with revenue numbers." This is implemented and running in production.

**2. Agent self-reflection:** After every headless run, the agent writes observations to `memory/observations.md` — what it noticed about the content landscape, what seemed important, what was uncertain. These observations accumulate and inform future runs. An agent that's run 50 times has 50 runs worth of accumulated observations about the user's work context.

**3. Seniority progression:** Agents progress through levels — new, associate, senior — based on run count, approval rate, and edit distance trend. Senior agents earn expanded duty portfolios (additional responsibilities within their role). This is a concrete mechanism for capability expansion gated on demonstrated competence, not just time.

**What this means for investors:** Week 12 outputs require zero corrections not because the LLM got smarter, but because 12 weeks of structural feedback shaped the agent's behavior. This is the mechanism behind the switching cost — a competitor's agent starts from Week 1.

---

## Multi-Agent Project Coordination

YARNNN is evolving from a collection of independent agents to a coordinated agent workforce that produces assembled deliverables.

**The coordination model:**

- **Projects** are containers for multi-agent work. A project has intent (what it produces, for whom), contributors (which agents feed into it), an assembly spec (how parts combine), and delivery settings.
- **PM agents** are domain-cognitive coordinators. They assess contribution quality against project intent, steer contributors via briefs (`/contributions/{slug}/brief.md`), gate assembly on quality thresholds, and manage work budgets.
- **Assembly** is Composer-driven. When contributions have meaningfully changed, Composer reads the project's assembly spec, invokes output gateway skills (PPTX, PDF, charts), and writes the assembled output to the project's assembly folder with a manifest.
- **Work budgets** bound autonomous compute. Free tier: 60 work units/month. Pro: 1,000. Each agent run, assembly, or render consumes units. The system self-governs within budget constraints.

**What this means for investors:** This is the composition story — the moat beyond individual agent quality. A "Monday Executive Brief" project that pulls from Slack digest, Gmail digest, and market research agents, assembled into a PDF deck, is a deliverable no single-platform AI can produce. And it improves every week because every contributing agent improves every week.

---

## Engineering Velocity & Rigor

**122 Architecture Decision Records** document every significant design choice — from memory architecture (ADR-059) to project coordination (ADR-122). Each ADR captures context, alternatives considered, decision rationale, and implementation status. This isn't documentation for documentation's sake — it's the substrate that enables a solo founder to maintain architectural coherence across 8,000+ lines of backend logic, 4 platform integrations, 5 Render services, and a React frontend.

**Full-stack implementation by a single technical founder:**
Next.js frontend, FastAPI backend, Supabase (Postgres), Claude API, Docker output gateway. Four platform integrations (Slack, Gmail, Notion, Calendar) with OAuth, paginated sync, and tier-based rate limiting. MCP server with OAuth 2.1 for Claude.ai/ChatGPT interop. Nine MCP tools exposing agent discovery, knowledge search, and cross-agent reading.

**What this signals:** The architecture isn't a prototype that needs to be rebuilt. It's production infrastructure with the engineering rigor of a team — built by one person who made 122 deliberate decisions instead of 122 shortcuts.

---

*kvkthecreator@gmail.com · yarnnn.com*
