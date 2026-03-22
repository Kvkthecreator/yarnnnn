# From Skills to Capabilities: Three-Registry Migration

> **Status**: Design Decision
> **Date**: 2026-03-22 (revised)
> **Implements**: ADR-130 (Agent Capability Substrate — Three-Registry Architecture)
> **Supersedes**: ADR-118's format-builder model, ADR-117's seniority-gated capability progression

---

## The Problem

The current system manages agent capabilities through three disconnected mechanisms that conflate type, capability, and runtime:

1. `SKILL_ENABLED_ROLES = frozenset({"synthesize", "research", "monitor", "custom"})` — binary capability gating by role name
2. `ROLE_PORTFOLIOS` — seniority-based duty expansion that never actually gates capabilities
3. `RuntimeDispatch` → single Python render service for all skill types, all-or-nothing SKILL.md injection

Additionally, the seniority system (`classify_seniority()`) creates cold-start problems, relies on subjective LLM-judged metrics, and adds complexity without proven quality benefit.

## The Reframe

**Agent types determine capabilities. Capabilities are deterministic. The platform renders output.**

Three registries replace all scattered gating:
- **Agent Type Registry** — what bundles of capabilities each type gets
- **Capability Registry** — what each capability enables, where it executes
- **Runtime Registry** — where compute happens (Python, Node.js, external APIs)

No earning. No progression. No seniority-gated capability tiers. Agent development is about knowledge depth (accumulated memory, preferences, domain expertise), not capability breadth.

---

## Current → New Mapping

### What gets replaced

| Current | New | Phase |
|---|---|---|
| `SKILL_ENABLED_ROLES` | `AGENT_TYPES[type].capabilities` | Phase 1 |
| `ROLE_PORTFOLIOS` (seniority tiers) | Flattened to single duty set per type | Phase 1 |
| `classify_seniority()` | Deleted | Phase 1 |
| `get_eligible_duties()` | Deleted | Phase 1 |
| `get_promotion_duty()` | Deleted | Phase 1 |
| `ROLE_PULSE_CADENCE` | `AGENT_TYPES[type].pulse_cadence` | Phase 1 |
| `_fetch_skill_docs()` (all-or-nothing) | `_fetch_capability_docs(capabilities)` (scoped) | Phase 1 |
| `RuntimeDispatch` (monolithic tool) | `RenderAsset` (scoped to type's asset capabilities) | Phase 1 |
| `render/skills/pptx/` | Deleted (HTML presentation mode) | Phase 3 |
| `render/skills/html/` | Absorbed into compose engine | Phase 3 |
| `render/skills/data/` | Absorbed into compose engine | Phase 3 |
| `render/skills/pdf/` | Retained as export step only | Phase 3 |
| `render/skills/xlsx/` | Retained as export step only | Phase 3 |

### What stays

- `render/skills/chart/` — asset renderer, compute primitive
- `render/skills/mermaid/` — asset renderer, compute primitive
- `render/skills/image/` — asset renderer, compute primitive
- Compose engine (`render/compose.py`, `POST /compose`) — preserved and integrated
- Output folder conventions (ADR-119) — unchanged
- Delivery pipeline (`deliver_from_output_folder()`) — unchanged
- Feedback distillation (ADR-117 Phase 1) — agents still learn from edits
- Agent pulse (ADR-126) — simplified, no Tier 2 seniority self-assessment
- SKILL.md convention — preserved for skill knowledge (Claude Code compatible)

---

## Current → New Wiring

### Current wiring (disconnected, scattered)

```
agent_framework.py
├── SKILL_ENABLED_ROLES (hardcoded frozen set by role name)
├── ROLE_PORTFOLIOS (seniority × duties, never gates capabilities)
├── ROLE_PULSE_CADENCE (separate registry by role)
├── classify_seniority() (feedback-based, gates duties only)
├── get_eligible_duties() (seniority-dependent)
└── get_promotion_duty() (seniority-dependent)

agent_execution.py
├── _fetch_skill_docs() (fetches ALL 8 SKILL.md if role matches)
├── _build_headless_system_prompt() (injects all skills if role matches)
└── generate_draft_inline() (checks SKILL_ENABLED_ROLES for injection)

agent_creation.py
├── create_agent_record() (seeds AGENT.md with capability ref if role matches)
└── Appends "Available Capabilities" section for skill-enabled roles
```

### New wiring (three registries, deterministic)

```
agent_framework.py
├── AGENT_TYPES (type → capability set + pulse cadence + prompt template)
├── CAPABILITIES (capability → runtime + tool + skill_docs + output_type)
├── RUNTIMES (runtime → endpoint + auth + timeout)
├── get_type_capabilities(type) → capability list
├── get_type_tools(type) → scoped tool definitions
└── get_type_skill_docs(type) → scoped SKILL.md content paths

agent_execution.py
├── _fetch_capability_docs(capabilities) (fetches only relevant SKILL.md)
├── _build_headless_system_prompt() (scoped to type's capabilities)
└── generate_draft_inline() (calls get_type_tools, scopes tools to type)
    └── Post-generation: compose step if type has compose_html

agent_creation.py
├── create_agent_record() (seeds AGENT.md with ## Type + ## Capabilities)
└── Fixed capability set from AGENT_TYPES[type]

agent_pipeline.py
├── build_role_prompt() (references agent's known capabilities)
└── ROLE_PROMPTS (keyed by type's prompt_template)
```

---

## Skill Knowledge: Built-in vs. Imported

The capability registry accommodates two sourcing modes for skill knowledge:

### Built-in capabilities (our own)

Internal compute primitives we own, version, and deploy:
- **Asset renderers**: chart, mermaid, image — SKILL.md + render scripts in `render/skills/`
- **Compose engine**: markdown + assets → styled HTML — `render/compose.py`
- **Export steps**: HTML → PDF, data → XLSX — `render/` service (future)

### Imported capabilities (marketplace / external)

Platform-specific skills where someone else owns the API:
- **Platform write-backs**: Slack write, Notion write, Linear create — SKILL.md format, copy/adapted from Claude Code skills marketplace
- **MCP tools**: External MCP servers providing capabilities — registered via the same capability schema
- **Future integrations**: Figma, GitHub, etc.

The distinction matters for evolution:
- Built-in capabilities evolve on our deploy cycle
- Imported capabilities evolve on external API changes
- Both use the same SKILL.md convention for LLM knowledge injection
- Both are registered identically in the capability registry

---

## Video: The Stress Test

Video rendering validates the three-registry architecture:

```
Agent Type Registry:
  "video": {
    capabilities: ["read_workspace", "video_render", "produce_markdown"],
    pulse_cadence: "schedule",
    prompt_template: "video",
  }

Capability Registry:
  "video_render": {
    runtime: "node_remotion",
    tool: "RenderAsset",
    skill_docs: "video/SKILL.md",
    output_type: "asset",
  }

Runtime Registry:
  "node_remotion": {
    endpoint: "https://yarnnn-video.onrender.com",
    protocol: "http_post",
    auth: "render_secret",
    timeout: 120,
  }
```

Adding video requires:
1. Add type entry to `AGENT_TYPES`
2. Add capability entry to `CAPABILITIES`
3. Add runtime entry to `RUNTIMES`
4. Deploy Node.js service with Remotion
5. Create `video/SKILL.md` for LLM knowledge

No changes to: agent framework, execution pipeline, delivery, workspace conventions, or frontend. The architecture accommodates new runtimes without structural changes.

---

## Example: Before and After

### Before (format-builder model + seniority gating)

A synthesize-role agent produces a quarterly report:
1. `SKILL_ENABLED_ROLES` check: "synthesize" → allowed
2. `_fetch_skill_docs()` fetches ALL 8 SKILL.md files (~8K tokens into prompt)
3. Agent calls `RuntimeDispatch(type="chart", input={data}, output_format="png")` → PNG
4. Agent calls `RuntimeDispatch(type="presentation", input={slides}, output_format="pptx")` → blank PPTX
5. PPTX delivered as email attachment
6. Downstream agents cannot read PPTX
7. Agent at "new" seniority — no visualization capability yet (cold-start)

### After (three registries, deterministic types)

A synthesize-type agent produces a quarterly report:
1. `AGENT_TYPES["synthesize"].capabilities` → includes chart, mermaid, compose_html
2. `_fetch_capability_docs(["chart", "mermaid"])` → only 2 relevant SKILL.md files
3. Agent calls `RenderAsset(type="chart", input={data})` → SVG in `assets/`
4. Agent references: `![Revenue Trend](assets/revenue-trend.svg)`
5. Post-generation: compose engine renders markdown + SVG → styled HTML (dashboard mode)
6. HTML delivered as email body
7. Downstream agents read `output.md` — structured, parseable, composable
8. User clicks "Download PDF" → platform exports HTML → PDF on demand
9. All capabilities available from first run — no cold-start
