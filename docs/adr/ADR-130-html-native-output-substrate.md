# ADR-130: Agent Capability Substrate — Three-Registry Architecture

> **Status**: Phase 1a Implemented (registries + seniority deletion). Phase 1b (RuntimeDispatch→RenderAsset) proposed. Phases 2-3 proposed.
> **Date**: 2026-03-22 (revised)
> **Authors**: KVK, Claude
> **Supersedes**: ADR-118 Phase D (format-builder skills model), ADR-117 Phase 3 seniority-gated capabilities
> **Extends**: ADR-106 (Workspace), ADR-109 (Agent Framework), ADR-118 (Skills Layer), ADR-119 (Workspace Filesystem), ADR-120 (Project Execution)

---

## Context

YARNNN agents produce work. That work requires capabilities — tools, compute, and external integrations. The current system manages capabilities through scattered, disconnected mechanisms:

- `SKILL_ENABLED_ROLES` — a frozen set that gates RuntimeDispatch access by role name
- `ROLE_PORTFOLIOS` — seniority-based duty expansion that never actually gates capabilities
- `classify_seniority()` — feedback-based progression that controls duty expansion but nothing else
- `_fetch_skill_docs()` — fetches ALL 8 SKILL.md files regardless of what the agent needs
- `RuntimeDispatch` — a single tool that routes to one Python render service for all skill types

These mechanisms conflate three independent concerns:

1. **What can this agent do?** (capability) — currently hardcoded by role name
2. **Where does the work execute?** (runtime) — currently a single Python Docker service
3. **What type of agent is this?** (type definition) — currently a loose combination of role + scope + mode

### Why seniority-gated capabilities don't work

The seniority model (ADR-117) proposed that capabilities are "earned" through feedback-gated progression. In practice:

- `classify_seniority()` uses run count + approval rate — subjective LLM-judged metrics that create uncertainty
- The cold-start problem: new agents can't produce rich output → users don't see value → agents don't get approved → agents never earn capabilities
- Seniority gates add complexity at every pipeline touchpoint with no proven quality benefit
- The FOUNDATIONS axiom "agents develop inward" is about knowledge accumulation and behavioral refinement through feedback — it doesn't require mechanical capability gating

### Why one runtime isn't enough

The current render service runs Python with matplotlib, pandoc, python-pptx, openpyxl, pillow, and mermaid-cli. This works for charts and documents. It doesn't work for:

- **Video** — requires Node.js + Remotion + Chrome headless (already exists in `video/`)
- **Platform write-backs** — requires OAuth tokens + external API calls (Slack, Notion, Linear)
- **Interactive content** — requires browser-based rendering (future)
- **Marketplace skills** — external MCP tools with their own runtimes

### The three-layer insight

Capabilities decompose into three independent concerns with different lifecycle, ownership, and evolution patterns:

1. **Skill knowledge** (instruction layer) — documents that teach the LLM how to use a capability. SKILL.md format (Claude Code compatible). Can be marketplace imports or our own.
2. **Compute runtimes** (execution layer) — environments that execute capability work. Python, Node.js, external APIs. Each has its own dependencies, language, resource profile.
3. **Capability coordination** (registry layer) — the mapping between what agents can do and how it gets done. Static, versioned, deterministic.

---

## Decision

### Three registries, cleanly separated

The capability substrate is defined by exactly three static, versioned registries.

#### 1. Agent Type Registry — what bundles of capabilities exist

Each agent type is a deterministic capability set. No earning, no progression — the type IS the capability set. Personification comes from instructions (user-configurable, prompt-level), not from capability gating (mechanical, code-level).

```python
AGENT_TYPES = {
    "digest": {
        "capabilities": ["read_platforms", "synthesize", "produce_markdown", "compose_html"],
        "default_instructions": "Recap all activity...",
        "pulse_cadence": timedelta(hours=12),
        "prompt_template": "digest",
    },
    "monitor": {
        "capabilities": ["read_platforms", "detect_change", "alert",
                         "produce_markdown", "compose_html"],
        "default_instructions": "Monitor for changes...",
        "pulse_cadence": timedelta(minutes=15),
        "prompt_template": "monitor",
    },
    "research": {
        "capabilities": ["read_platforms", "web_search", "investigate",
                         "produce_markdown", "chart", "mermaid", "compose_html"],
        "default_instructions": "Proactive insights...",
        "pulse_cadence": "schedule",
        "prompt_template": "research",
    },
    "synthesize": {
        "capabilities": ["read_platforms", "cross_reference", "data_analysis",
                         "chart", "mermaid", "produce_markdown", "compose_html"],
        "default_instructions": "Synthesize activity...",
        "pulse_cadence": "schedule",
        "prompt_template": "synthesize",
    },
    "prepare": {
        "capabilities": ["read_platforms", "calendar_access", "profile_attendees",
                         "produce_markdown", "compose_html"],
        "default_instructions": "Auto meeting prep...",
        "pulse_cadence": timedelta(hours=12),
        "prompt_template": "prepare",
    },
    "pm": {
        "capabilities": ["read_workspace", "check_freshness", "steer_contributors",
                         "trigger_assembly", "manage_work_plan"],
        "default_instructions": "Coordinate this project...",
        "pulse_cadence": timedelta(minutes=30),
        "prompt_template": "pm",
    },
    # Future types: video, slack_writer, etc.
    # Added by extending this registry + deploying runtimes. No framework changes.
}
```

Agent creation picks a type and gets the full bundle. No dynamic resolution, no earned progression.

#### 2. Capability Registry — what can be done

Each capability defines what it enables, how the LLM learns to use it, and where it executes.

```python
CAPABILITIES = {
    # --- Cognitive (prompt-driven, no tool needed) ---
    "read_platforms":   {"runtime": "internal", "tool": None, "skill_docs": None},
    "synthesize":       {"runtime": "internal", "tool": None, "skill_docs": None},
    "detect_change":    {"runtime": "internal", "tool": None, "skill_docs": None},
    "cross_reference":  {"runtime": "internal", "tool": None, "skill_docs": None},
    "data_analysis":    {"runtime": "internal", "tool": None, "skill_docs": None},
    "alert":            {"runtime": "internal", "tool": None, "skill_docs": None},
    "investigate":      {"runtime": "internal", "tool": None, "skill_docs": None},
    "calendar_access":  {"runtime": "internal", "tool": None, "skill_docs": None},
    "profile_attendees":{"runtime": "internal", "tool": None, "skill_docs": None},

    # --- Tool-backed (internal tools) ---
    "web_search":       {"runtime": "internal", "tool": "WebSearch", "skill_docs": None},
    "read_workspace":   {"runtime": "internal", "tool": "ReadWorkspace", "skill_docs": None},
    "produce_markdown": {"runtime": "internal", "tool": None, "skill_docs": None},

    # --- Asset production (compute runtimes) ---
    "chart":            {"runtime": "python_render", "tool": "RenderAsset",
                         "skill_docs": "chart/SKILL.md", "output_type": "asset"},
    "mermaid":          {"runtime": "python_render", "tool": "RenderAsset",
                         "skill_docs": "mermaid/SKILL.md", "output_type": "asset"},
    "image":            {"runtime": "python_render", "tool": "RenderAsset",
                         "skill_docs": "image/SKILL.md", "output_type": "asset"},
    "video_render":     {"runtime": "node_remotion", "tool": "RenderAsset",
                         "skill_docs": "video/SKILL.md", "output_type": "asset"},

    # --- Composition (post-generation pipeline step) ---
    "compose_html":     {"runtime": "python_render", "tool": None,
                         "skill_docs": None, "post_generation": True},

    # --- Platform skills (external APIs, SKILL.md importable from marketplace) ---
    "write_slack":      {"runtime": "external:slack", "tool": "SlackWrite",
                         "skill_docs": "slack/SKILL.md", "output_type": "side_effect",
                         "requires_auth": True},
    "write_notion":     {"runtime": "external:notion", "tool": "NotionWrite",
                         "skill_docs": "notion/SKILL.md", "output_type": "side_effect",
                         "requires_auth": True},

    # --- PM-specific (internal coordination) ---
    "check_freshness":     {"runtime": "internal", "tool": "CheckContributorFreshness"},
    "steer_contributors":  {"runtime": "internal", "tool": "WriteWorkspace"},
    "trigger_assembly":    {"runtime": "internal", "tool": None},
    "manage_work_plan":    {"runtime": "internal", "tool": "UpdateWorkPlan"},
}
```

**Two sourcing modes** for skill knowledge:
- **Built-in**: capabilities we own (render service, compose engine) — SKILL.md authored by us
- **Imported**: capabilities from marketplace (platform write-backs, MCP tools) — SKILL.md copied/adapted from Claude Code skills marketplace

Both registered identically. An agent doesn't know or care which sourcing mode a capability uses.

#### 3. Runtime Registry — where compute happens

Each runtime is a deployment target with its own endpoint, auth, and resource profile.

```python
RUNTIMES = {
    "internal": {
        "type": "in_process",
    },
    "python_render": {
        "endpoint": "RENDER_SERVICE_URL",
        "protocol": "http_post",
        "auth": "render_secret",
        "timeout": 60,
    },
    "node_remotion": {
        "endpoint": None,  # Not yet deployed
        "protocol": "http_post",
        "auth": "render_secret",
        "timeout": 120,
    },
    "external:slack": {
        "type": "oauth_api",
        "auth": "user_oauth_token",
    },
    "external:notion": {
        "type": "oauth_api",
        "auth": "user_oauth_token",
    },
}
```

### The resolution path

```
Agent created with type "synthesize"
  → AGENT_TYPES["synthesize"].capabilities = [read_platforms, cross_reference,
       data_analysis, chart, mermaid, produce_markdown, compose_html]
  → For each capability, resolve from CAPABILITIES:
       chart → tool: RenderAsset, runtime: python_render, skill_docs: chart/SKILL.md
       mermaid → tool: RenderAsset, runtime: python_render, skill_docs: mermaid/SKILL.md
       compose_html → post_generation: True, runtime: python_render
  → Inject only chart/SKILL.md + mermaid/SKILL.md into system prompt
  → Provide only RenderAsset tool (scoped to chart + mermaid types)
  → After generation, run compose step
```

---

## Three-concern separation

| Concern | Owner | Mechanism |
|---|---|---|
| **Capability** | Agent type (deterministic at creation) | Agent Type Registry defines capability set |
| **Presentation** | Platform (layout modes) | Compose engine: markdown + assets → styled HTML |
| **Export** | Platform (on-demand, mechanical) | HTML → PDF, data → XLSX, HTML → image |

Agents produce structured content (markdown + asset references). The platform handles how it looks and how it ships.

### Layout modes (platform-owned)

| Mode | Visual treatment | Best for |
|---|---|---|
| **document** | Flowing text, max-width, reading-optimized | Reports, digests, analysis |
| **presentation** | Full-screen sections, large type | Executive reviews, team updates |
| **dashboard** | CSS grid, metric cards, KPI panels | Operational summaries, status |
| **data** | Dense tables, tabular nums, sticky headers | Data-heavy outputs, comparisons |

---

## What gets deleted

### Seniority gating system
- `classify_seniority()` in `agent_framework.py`
- `ROLE_PORTFOLIOS` seniority tiers → flattened to single duty set per type
- `get_eligible_duties()`, `get_promotion_duty()`
- Composer promotion/demotion logic → simplified to creation/dissolution
- PM developmental trajectory (ADR-121 Phase 4)

### Capability gating
- `SKILL_ENABLED_ROLES` constant
- `_fetch_skill_docs()` all-or-nothing injection
- `RuntimeDispatch` tool (replaced by type-scoped `RenderAsset`)

### Format-builder skills (Phase 3)
- `render/skills/pptx/` — replaced by HTML presentation layout mode
- `render/skills/html/` — absorbed into compose engine
- `render/skills/data/` — absorbed into compose engine
- `render/skills/pdf/` — retained as export step only, not agent-facing
- `render/skills/xlsx/` — retained as export step only, not agent-facing

### What stays
- `render/skills/chart/` — asset renderer (compute primitive)
- `render/skills/mermaid/` — asset renderer (compute primitive)
- `render/skills/image/` — asset renderer (compute primitive)
- Compose engine (`render/compose.py`, `POST /compose`)
- Output folder conventions (ADR-119) — unchanged
- Workspace conventions — unchanged
- Delivery pipeline — unchanged (reads from output folder)
- Agent pulse (ADR-126) — simplified (no Tier 2 seniority self-assessment needed)
- Feedback distillation (ADR-117 Phase 1) — agents still learn from user edits

---

## What gets preserved from the developmental model

**User authorization for consequential actions.** Write-backs to external platforms are gated by explicit user authorization per agent, not earned seniority. "This agent can post to #general" is a user setting.

**Feedback as learning signal.** User edits and approvals feed into `memory/preferences.md` via feedback distillation. Agents improve through accumulated preferences, not capability unlocking.

**Knowledge accumulation.** Agents develop domain expertise through workspace memory, observations, and thesis refinement. The developmental trajectory is knowledge depth, not capability breadth.

**Coherence protocol.** Self-assessments (ADR-128) continue — agents reflect on their mandate fitness and output quality. This drives knowledge refinement, not capability progression.

---

## Impact on existing systems

### Agent framework (`agent_framework.py`)
- `SKILL_ENABLED_ROLES` → deleted
- `ROLE_PORTFOLIOS` → flattened (single duty set per type, no seniority tiers)
- `classify_seniority()` → deleted
- `ROLE_PULSE_CADENCE` → absorbed into `AGENT_TYPES`
- New: `AGENT_TYPES`, `CAPABILITIES`, `RUNTIMES` registries
- New: `get_type_capabilities(agent_type)` → returns capability set
- New: `get_type_tools(agent_type)` → returns scoped tool definitions
- New: `get_type_skill_docs(agent_type)` → returns relevant SKILL.md content

### Agent creation (`agent_creation.py`)
- AGENT.md seeded with type and fixed capability set
- No capability progression references

### Agent execution (`agent_execution.py`)
- `_fetch_skill_docs()` → `_fetch_capability_docs(capabilities)` — scoped
- `RuntimeDispatch` → `RenderAsset` — scoped to agent's asset capabilities
- System prompt: only injects docs for capabilities the agent type has
- Tool set: only provides tools matching agent's capabilities
- Post-generation: calls compose engine for types with `compose_html`

### Agent pipeline (`agent_pipeline.py`)
- Role prompts: reference agent's known capability set
- Assembly prompt: PM composes structured markdown, specifies layout mode

### Render service (`render/main.py`)
- `/render` → retained for asset rendering (chart, mermaid, image)
- `/compose` → integrated into post-generation pipeline step
- Future `/export` → HTML → PDF, data → XLSX (on-demand)

### Delivery (`delivery.py`)
- `deliver_from_output_folder()` → sends composed HTML as email body

### Frontend
- Outputs tab → renders composed HTML inline
- Meeting room → rich output cards
- Export buttons → on-demand format conversion

---

## Phases

### Phase 1: Registry + type-scoped execution
- Define `AGENT_TYPES`, `CAPABILITIES`, `RUNTIMES` in `agent_framework.py`
- Replace `SKILL_ENABLED_ROLES` with type-based capability lookup
- Replace `_fetch_skill_docs()` with `_fetch_capability_docs(capabilities)`
- Delete seniority: `classify_seniority()`, `ROLE_PORTFOLIOS` tiers, promotion logic
- Scope tools in `generate_draft_inline()` to agent type's capabilities
- `RenderAsset` replaces `RuntimeDispatch` (same mechanics, scoped by type)
- AGENT.md seeded with type and fixed capabilities at creation
- Flatten `ROLE_PORTFOLIOS` to single duty set per type

### Phase 2: Compose integration
- Post-generation step calls `/compose` for types with `compose_html`
- Output folder stores composed HTML alongside output.md
- Email delivery sends composed HTML
- Frontend renders composed HTML in output tab / meeting room

### Phase 3: Dissolve format-builder skills + multi-runtime
- Remove pptx, html, data skills from render service
- Retain pdf/xlsx as export steps (not agent-facing)
- Runtime registry enables routing to different services
- New agent types addable without framework changes
- Platform write-back skills addable as external runtime capabilities

---

## Trade-offs

### Accepted

1. **No capability progression** — Agent types have fixed capability sets. Development is knowledge depth, not capability breadth. Trades narrative appeal for deterministic, debuggable behavior.

2. **Custom type deferred** — Users choose from pre-defined types, customize via instructions. Custom composition is Phase 2+ after architectural hardening.

3. **Legacy export fidelity** — Exports from HTML are viewing-quality. Native PPTX/XLSX editing fidelity is lower or deferred. Accepted because agent output is viewed, not edited in desktop apps.

### Rejected

1. **Seniority-gated capabilities** — Rejected: cold-start problems, subjective LLM judgment, pipeline complexity, uncertainty.

2. **Single universal runtime** — Rejected: video needs Node.js, platform write-backs need OAuth, marketplace skills have their own runtimes.

3. **Dual approach during migration** — Rejected: violates singular implementation. Replace completely in Phase 1.

---

## Axiom Alignment

| Foundation | Alignment |
|---|---|
| **Axiom 1 (Two Layers)** | Agent types are domain-cognitive with fixed capabilities. TP/Composer creates agents of known types. No third-layer capability management. |
| **Axiom 2 (Recursive Perception)** | Structured content is agent-readable. Downstream agents consume `output.md`. Compose engine produces human-readable HTML from the same source. |
| **Axiom 3 (Developing Entities)** | Development is knowledge depth: memory, preferences, domain thesis. Not capability breadth. Pulse sophistication scales with accumulated workspace state. |
| **Axiom 4 (Accumulated Attention)** | Value compounds through domain knowledge. A tenured agent produces better output because it knows more, not because it has more tools. |
| **Axiom 6 (Autonomy)** | End-to-end autonomous flow. User authorization for consequential actions is explicit, not earned. |
| **Derived Principle 7 (Singular)** | Three registries, one resolution path. No parallel format-specific paths. |
