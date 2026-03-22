# From Skills to Capabilities: Agent-Native Capability Model

> **Status**: Design Decision
> **Date**: 2026-03-22
> **Implements**: ADR-130 (Agent-Native Output & Capability Substrate)
> **Supersedes**: ADR-118's implicit "skill = format builder" model

---

## The Problem

ADR-118 defined skills as format builders — each skill takes a constrained input spec and produces a specific file format. This conflates three concerns:

1. **What can this agent do?** → hardcoded by role (`SKILL_ENABLED_ROLES`)
2. **How should the output look?** → determined by which skill is called
3. **What file do you need?** → the skill IS the file format

The result: agents that need rich visual output must learn python-pptx's object model via a JSON DSL. Agents that gain seniority don't gain new capabilities. Multi-agent composition requires format-specific assembly per output type. The recursive perception loop breaks on binary files.

## The Reframe

**A capability is what an agent can do.** Not what file format it produces. Not what tool it calls. What cognitive or productive action it can take within its domain.

Capabilities are:
- **Earned** — gated by seniority, feedback history, and role portfolio
- **Composable** — multiple capabilities combine to produce richer work
- **Discoverable** — other agents can query what capabilities a peer has
- **Workspace-native** — recorded in AGENT.md, updated by Composer on promotion

---

## Capability Taxonomy

### By tier (progression)

| Tier | Available when | Examples | What it enables |
|---|---|---|---|
| **1: Core** | All agents, from creation | read, search, synthesize, produce_markdown | Basic output: structured text from sources |
| **2: Domain** | Role-specific, from creation | research, monitor, data_analysis, coordination, preparation | Role-appropriate tools and primitives |
| **3: Expressive** | Associate seniority (earned) | visualization, rich_composition, cross_agent, layout_hint | Rich output: charts, multi-section, agent references |
| **4: Autonomous** | Senior + user authorization | write_back, action, self_direction | Consequential external actions |

### By nature (what the capability produces)

| Nature | Capabilities | Output type | Where stored |
|---|---|---|---|
| **Cognitive** | research, monitor, data_analysis, coordination | Knowledge (narrative, analysis, structured data) | `output.md` |
| **Productive** | visualization, rich_composition | Assets (SVG charts, diagrams, composed images) | `assets/` folder |
| **Interactive** | cross_agent, layout_hint | Metadata (references, layout mode) | `manifest.json` |
| **External** | write_back, action | Side effects (Slack posts, emails, Notion updates) | External platforms + activity log |

---

## Migration from Current System

### What changes

| Current | New | Migration |
|---|---|---|
| `SKILL_ENABLED_ROLES = {"synthesize", "research", "monitor", "custom"}` | `ROLE_BASE_CAPABILITIES` mapping role → Tier 1+2 capabilities | Phase 3: replace constant, update all references |
| `_fetch_skill_docs()` → inject all SKILL.md | `_fetch_capability_docs()` → inject only capability-relevant docs | Phase 4: scope injection to earned capabilities |
| `RuntimeDispatch(type, input, output_format)` | `RenderAsset(type, input)` for assets; export via platform | Phase 4: new primitive, Phase 6: remove old |
| Role-based skill injection in system prompt | Capability-based tool injection | Phase 3: capability-aware prompt building |
| No capability metadata in workspace | `AGENT.md ## Capabilities` section | Phase 3: seed at creation, update on promotion |

### What stays the same

- **Two-filesystem architecture** (ADR-118) — capability filesystem (render service) + content filesystem (workspace). Preserved.
- **SKILL.md conventions** — asset capabilities still have SKILL.md files. Preserved for chart, mermaid, image.
- **Skill auto-discovery** — render service still discovers capabilities from folder structure. Preserved.
- **Role portfolios** (ADR-117) — career tracks and duty progression. Extended with capability requirements.
- **Feedback-gated progression** — seniority from run count + approval rate. Unchanged, now also gates capability tiers.

### What gets deleted (Phase 6)

- `SKILL_ENABLED_ROLES` constant in `agent_framework.py`
- Format-builder skills: `render/skills/pptx/`, `render/skills/pdf/`, `render/skills/html/`, `render/skills/xlsx/`, `render/skills/data/`
- `RuntimeDispatch` primitive (replaced by `RenderAsset`)
- Format-specific SKILL.md injection in `_build_headless_system_prompt()`

---

## Capability × Agent Framework Integration

### Current wiring (disconnected)

```
agent_framework.py
├── SKILL_ENABLED_ROLES (hardcoded by role name)
├── ROLE_PORTFOLIOS (duties by seniority, no capability link)
└── classify_seniority() (returns level, no capabilities)

agent_execution.py
├── _fetch_skill_docs() (fetches ALL skill docs if role matches)
├── _build_headless_system_prompt() (injects skills section if role matches)
└── generate_draft_inline() (checks SKILL_ENABLED_ROLES for injection)

agent_creation.py
├── create_agent_record() (seeds AGENT.md with capability ref if role matches)
```

### Proposed wiring (integrated)

```
agent_framework.py
├── ROLE_BASE_CAPABILITIES (role → Tier 1+2 capabilities)
├── SENIORITY_UNLOCKS (seniority → Tier 3+4 capabilities)
├── ROLE_PORTFOLIOS (duties with capabilities_required field)
├── classify_seniority() (returns level + unlocked capabilities)
└── get_agent_capabilities(role, seniority, earned_duties) → set

agent_execution.py
├── _fetch_capability_docs(capabilities) (fetches docs for earned capabilities only)
├── _build_headless_system_prompt() (capability-aware injection)
└── generate_draft_inline() (calls get_agent_capabilities, scopes tools)

agent_creation.py
├── create_agent_record() (seeds AGENT.md ## Capabilities from role)

agent_pipeline.py
├── build_role_prompt() (references agent's capabilities in prompt)
├── ROLE_PROMPTS (capability-aware generation instructions)
```

---

## Marketplace Foundation (Phase 7+)

The capability model creates a foundation for external capability import:

### MCP tools as capabilities
When a user connects an MCP server with custom tools, those tools could map to agent capabilities. An MCP tool `analyze_sentiment` becomes a Tier 2 capability available to agents in the user's workspace.

### Ecosystem alignment
The AI tool ecosystem is converging on "agents that use tools." Our capability model aligns:
- **MCP tools** → map to capabilities
- **Claude Code skills** → asset capabilities follow the same SKILL.md pattern
- **Agent-to-agent protocols (A2A)** → capability metadata in AGENT.md enables discovery

### What makes this a platform, not just an app
The capability model means YARNNN can accommodate capabilities we haven't built:
- External MCP servers add capabilities without code changes
- New asset renderers (3D, audio, video) plug into the asset tier
- User-defined capabilities (custom MCP tools) become part of the agent's repertoire
- The capability registry + workspace metadata make all of this discoverable

This is the difference between "we built 8 format converters" and "agents can acquire and exercise any capability the ecosystem provides."

---

## Example: Before and After

### Before (format-builder model)

A synthesize-role agent produces a quarterly report:
1. Agent generates text content
2. Agent calls `RuntimeDispatch(type="chart", input={data}, output_format="png")` → chart uploaded to storage
3. Agent calls `RuntimeDispatch(type="presentation", input={title, slides}, output_format="pptx")` → PPTX with blank template styling
4. PPTX delivered as email attachment
5. Downstream agents cannot read PPTX

### After (capability model)

A synthesize-role agent with `data_analysis` + `visualization` capabilities (earned at associate):
1. Agent analyzes data, produces structured markdown with metric tables
2. Agent calls `RenderAsset(type="chart", input={data})` → SVG in `assets/` folder
3. Agent references chart: `![Revenue Trend](assets/revenue-trend.svg)`
4. `output.md` + `assets/` saved to workspace
5. Platform composes HTML (dashboard layout mode) → renders in-app + emails as HTML body
6. Downstream agents read `output.md` — structured, parseable, composable
7. User clicks "Download PDF" → platform exports HTML → PDF on demand
