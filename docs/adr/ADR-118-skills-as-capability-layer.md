# ADR-118: Skills as Capability Layer

> **Status**: Phase A+B+C implemented. Phase D (skills alignment + two-filesystem model + unified output) proposed.
> **Date**: 2026-03-17
> **Authors**: KVK, Claude
> **Supersedes**: None
> **Related**: ADR-106 (Workspace), ADR-109 (Agent Framework — `skill` column renamed to `role`, see Resolved Decision #4), ADR-117 (Feedback Substrate), ADR-119 (Workspace Filesystem Architecture), ADR-066 (Delivery-First), ADR-028 (Exporters), ADR-111 (Composer)

## Context

Claude Code demonstrated that structured instructions (SKILL.md) + a local filesystem + a local compute environment = indefinitely expandable agent capabilities. Yarnnn already has the instructions (AGENT.md) and the filesystem (workspace_files). The missing primitive is the compute environment.

**The key insight**: yarnnn's compute layer is not a "render service" that converts files. It is an **output gateway** — the cloud equivalent of Claude Code's local machine. It is the execution environment where agent-authored specs become materialized artifacts. Just as Claude Code's local machine has pandoc, Node.js, Python, and Remotion installed, yarnnn's output gateway has these tools in a Docker image. Just as Claude Code skills teach the agent how to use those tools, yarnnn's skills teach agents how to construct specs AND teach the output gateway how to process them.

**This makes yarnnn "Claude Code online"**: same capabilities model, but persistent (agents accumulate across runs), autonomous (agents act without prompting), and cloud-native (execution environment is a managed service, not the user's laptop).

## Decision

Extend yarnnn agents from text-only outputs to general-purpose artifact production via an output gateway and a two-filesystem architecture. Adopt Claude Code's naming conventions (skills, SKILL.md) directly — no yarnnn-specific terminology where Claude conventions exist.

### Core Principles

1. **The output gateway is the execution environment** — a fat Docker image with tools installed (pandoc, python-pptx, pillow, matplotlib, Remotion, mermaid-cli, etc.). Skills teach it how to process each type. Adding a skill = adding a skill folder + installing the tool. Same pattern as Claude Code.
2. **Skills are explicit and curated** — each requires a SKILL.md, scripts, cost model, and feedback mechanism. Not a marketplace or buffet. The skill registry IS the capability library.
3. **Two skill types, same interface** — local skills run tools in the container (fixed cost). Delegated skills call external APIs/MCPs (per-call cost). The agent never knows which path runs. Spec in → result out.
4. **Two filesystems, deliberately separated** — the capability filesystem (skills, tools, runtime) lives on the output gateway. The content filesystem (agent work, outputs, knowledge, assets) lives in workspace_files. Same interface pattern, different services, different lifecycles.
5. **Agents read SKILL.md** — when an agent has authorized skills, the execution pipeline injects the relevant SKILL.md content into the agent's context. The agent learns how to construct high-quality specs from the skill instructions, not just from a tool definition schema. This makes the Claude Code analogy structural, not aspirational.
6. **All outputs flow through the output gateway** — text AND binary. The current dual-path (text via agent_runs, binary via RuntimeDispatch) is migrated to a single unified path through workspace_files output folders (ADR-119). The output gateway handles all delivery (email, Slack, Notion).
7. **Dual output: text + binary** — agents always produce a text version (the spec, narrative, structured content) AND the rendered binary. The text version is the feedback surface. Users edit text; feedback distillation runs on text edits; the next run's binary improves because the text improved. This preserves the existing feedback pipeline for all output types.
8. **Runtime dispatch is an agent primitive** (Axiom 1) — invoked during agent runs, not system-wide post-processing. Sits alongside WriteWorkspace, QueryKnowledge, WebSearch.
9. **Feedback loop depth over runtime breadth** (Axiom 4) — one skill with working feedback > five without. But: format skills are table-stakes for non-technical users (not optional amplifiers), AND recursive cross-agent composition requires rich formats to realize full value.
10. **Zero-config via Composer** (Axiom 6) — users never configure skills. Composer scaffolds agents with appropriate ones.
11. **Outputs re-enter the perception substrate** (Axiom 2) — every output gets a workspace_files row with metadata, regardless of where the binary lives.

### Naming Alignment with Claude Ecosystem

yarnnn adopts Claude Code's naming conventions directly. No yarnnn-specific terminology where Claude conventions exist:

| Claude Code term | yarnnn equivalent | Notes |
|---|---|---|
| **Skill** | **Skill** | ~~Handler~~, ~~Capability~~ — use "skill" everywhere |
| **SKILL.md** | **SKILL.md** | ~~Capability guide~~ — same file, same format, same frontmatter |
| **Skill folder** | **Skill folder** | `render/skills/{name}/` — same structure as Claude Code |
| **Scripts** | **Scripts** | `render/skills/{name}/scripts/` — executable code |
| **AGENT.md** | **AGENT.md** | Agent-level identity (analogous to CLAUDE.md at project level) |
| **CLAUDE.md** | **CLAUDE.md** | Project-level instructions (yarnnn repo already has this) |

**What remains yarnnn-specific** (no Claude equivalent):
- **Output gateway** — the execution service itself (Claude Code doesn't have a separate service; it IS the local machine)
- **Skill registry** — the `SKILLS` dict in the gateway that routes dispatch to skill entry points
- **RuntimeDispatch** — the agent primitive that invokes skills (Claude Code agents just run bash)

**ADR-109 `role` column** (was: `skill`): The `role` column on the `agents` table (digest, monitor, synthesize, act) describes what an agent DOES — its behavioral role. Output gateway skills describe what an agent can PRODUCE. Renaming the ADR-109 axis from `skill` to `role` eliminates the naming overload. See Resolved Decision #4. Note: `orchestrate` was removed from the role taxonomy — orchestration is performed by TP (chat) and Composer (cron service), not by agents.

### Two-Filesystem Architecture

The deliberate separation between capabilities and content is the structural decision that allows yarnnn to participate in the Claude ecosystem while maintaining its own persistence model.

#### Capability Filesystem (Output Gateway)

Lives on the `yarnnn-render` Docker service. Contains everything needed to execute skills. Engineering-managed, version-controlled, deployed with the image. Does NOT change per user or per agent — it's the platform's capability surface.

```
render/
  skills/                                    ← skill library (was: handlers/)
    pptx/                                    ← one folder per skill
      SKILL.md                               ← frontmatter + instructions (agent reads this)
      scripts/                               ← executable code
        render.py                            ← entry point
      requirements.txt                       ← Python dependencies (if any beyond base)
    pdf/
      SKILL.md
      scripts/
        render.py
    xlsx/
      SKILL.md
      scripts/
        render.py
    chart/
      SKILL.md
      scripts/
        render.py
    diagram/                                 ← future
      SKILL.md
      scripts/
        render.py
    video/                                   ← future
      SKILL.md
      scripts/
        render.py
    email/                                   ← delegated skill (Resend API)
      SKILL.md
      scripts/
        deliver.py
    ai_image/                                ← delegated skill (Replicate/OpenAI)
      SKILL.md
      scripts/
        generate.py
  main.py                                    ← FastAPI app, skill registry, POST /render
  Dockerfile                                 ← tools installed here (pandoc, Node.js, etc.)
```

**SKILL.md format** — follows Claude Code conventions:

```yaml
---
name: pptx
description: "Create presentations from slide specs. Produces .pptx files from structured JSON input describing slides, layouts, content, and styling."
type: local                                  # local | delegated
tools: ["python-pptx"]                       # what's installed in the Docker image
input_format: "JSON slide spec"
output_formats: [".pptx"]
---

# PPTX Skill

## Input Spec
The input is a JSON object with...

## Examples
...

## Constraints
- Maximum 50 slides per presentation
- Images must be referenced by URL or workspace path
...
```

**SKILL.md serves dual purpose**: (1) the agent reads it during execution to learn how to construct high-quality specs (injected into context by the execution pipeline), and (2) the gateway uses the frontmatter for routing metadata. This is the same model as Claude Code — the LLM reads the skill, then acts on it.

**Skill registry** — replaces `HANDLERS` dict in `main.py`:

```python
# render/main.py
SKILLS = {
    "pptx": "skills.pptx.scripts.render:render_pptx",
    "pdf": "skills.pdf.scripts.render:render_pdf",
    "xlsx": "skills.xlsx.scripts.render:render_xlsx",
    "chart": "skills.chart.scripts.render:render_chart",
    # delegated
    "email": "skills.email.scripts.deliver:deliver_email",
    "ai_image": "skills.ai_image.scripts.generate:generate_image",
}
```

**Expansion pattern** — same as adding a Claude Code skill:
1. Create skill folder: `render/skills/{name}/`
2. Write `SKILL.md` with frontmatter + instructions
3. Add scripts: `render/skills/{name}/scripts/render.py`
4. Install tool in Dockerfile if needed (`apt-get`, `pip`, `npm`)
5. Register in `SKILLS` dict
6. Update `RuntimeDispatch` tool definition with new type

**Why this matters for ecosystem participation**: A Claude Code skill that teaches "how to make a presentation with python-pptx" follows the same folder structure, same SKILL.md format, same script conventions. Adapting it for yarnnn = adjusting the execution wrapper (entry point signature), not rewriting instructions or scripts. Conversely, a yarnnn skill can be extracted and used in Claude Code by pointing it at a local runtime. The **skill artifact is the shared interface** between local and cloud execution.

#### Content Filesystem (Workspace)

Lives in Postgres (`workspace_files`) + S3 (Supabase Storage). Contains everything agents produce and consume. User-scoped, agent-scoped, accumulates over time. Changes every run. Defined fully by ADR-106 + ADR-119.

```
/                                            ← workspace root (per user)
├── /agents/{slug}/                          ← agent workspace (ADR-106)
│   ├── AGENT.md                             ← identity + skill authorizations
│   ├── thesis.md                            ← evolving domain understanding
│   ├── /memory/                             ← accumulated state
│   ├── /working/                            ← ephemeral scratch (ADR-119)
│   └── /outputs/{date}/                     ← run outputs with manifest (ADR-119)
│       ├── manifest.json
│       ├── report.md                        ← text version (feedback surface)
│       └── report.pdf                       ← binary version (delivery artifact)
├── /knowledge/                              ← shared knowledge substrate
├── /projects/{slug}/                        ← cross-agent collaboration (ADR-119)
├── /assets/                                 ← shared creative resources
│   ├── /brand/                              ← logos, colors, fonts
│   ├── /images/                             ← reusable images
│   └── /templates/                          ← output templates by skill type
│       ├── /pptx/                           ← slide templates
│       ├── /pdf/                            ← document layouts
│       └── /video/                          ← Remotion compositions
└── /memory/                                 ← user-level memory
```

**Storage model**:
- Text content → Postgres (`workspace_files.content`)
- Binary outputs → S3/Supabase Storage (`workspace_files.content_url`)
- Creative assets → S3/Supabase Storage (user-uploaded, referenced by path)
- Metadata → Postgres (`workspace_files.metadata` JSONB)

### The Separation

| Aspect | Capability filesystem | Content filesystem |
|---|---|---|
| **What** | Skills, tools, runtime, scripts | Agent work, outputs, knowledge, assets |
| **Where** | Docker image (`yarnnn-render`) | Postgres + S3 (`workspace_files`) |
| **Lifecycle** | Deployed with service, version-controlled | Accumulates per user, per agent, per run |
| **Scope** | Platform-wide (all users, all agents) | User-scoped (per user, optionally per agent) |
| **Managed by** | Engineering | Agents + users + Composer |
| **Changes when** | New skill added, tool updated, deploy | Every agent run, every user edit |
| **Analogy** | Claude Code's installed packages + SKILL.md files | Claude Code's local filesystem (repo, project files) |

**Why separate**: In Claude Code, capabilities and content share a filesystem because it's one user, one machine, one session. In yarnnn, capabilities are platform-level (shared across all users) and content is instance-level (per user). Mixing them would mean either: (a) every user's workspace includes skill code (wasteful, security risk), or (b) skill code lives in Postgres alongside content (wrong abstraction, can't version-control with git). The separation is the natural consequence of being web-based rather than local.

**Same interface**: Despite living on different services, both filesystems present the same read/write/list interface to agents. An agent reads a skill's instructions the same way it reads a knowledge file — by path. The fact that one resolves to a Docker volume and the other to a Postgres row is invisible.

### Delivery-First Principle

Before building rich output rendering, agents must deliver to where users already are. Bootstrap and Composer-created agents default to email delivery (Resend). The user's first experience is receiving an output, not configuring delivery.

## The "Claude Code Online" Model

Yarnnn replicates the Claude Code capabilities model in the cloud:

| Claude Code (local) | Yarnnn (cloud) |
|---|---|
| User's local filesystem | Content filesystem (workspace_files + S3) |
| Installed tools (pandoc, node, python) | Output gateway Docker image |
| SKILL.md files in `.skills/skills/` | SKILL.md files in `render/skills/` |
| Agent reads SKILL.md, learns how to use tool | Agent reads SKILL.md (injected), learns how to construct spec |
| `scripts/` in skill folder | `scripts/` in skill folder |
| Agent runs bash to execute scripts | Agent calls RuntimeDispatch → gateway runs scripts |
| CLAUDE.md (project instructions) | CLAUDE.md (repo instructions) |
| Brand assets in local repo | `/assets/` in content filesystem |
| Session-scoped (starts fresh) | Persistent (agents accumulate across runs) |
| User-directed (waits for prompt) | Autonomous (acts on schedule, reacts to events) |
| Real-time feedback (see output, tweak) | Async feedback (run → review → feedback → next run) |

**What's the same**: the skill model. SKILL.md files with the same format and frontmatter conventions. Skill folders with the same structure (SKILL.md + scripts/ + supporting docs). The agent reads SKILL.md to learn the skill. Adding skills = adding folders + installing tools. The skill artifact is portable between Claude Code and yarnnn.

**What's different (the moat)**: persistence and autonomy. Claude Code users re-prompt every time. Yarnnn agents produce weekly reports that improve because they remember what the user edited last time. The skill set is the same — the operating model is fundamentally different.

**Ecosystem participation**: Because yarnnn skills follow the same format as Claude Code skills, the ecosystem's skill production feeds yarnnn's expansion. A new Claude Code skill for diagram generation can be adapted (not rewritten) for yarnnn. A yarnnn skill can be extracted for local Claude Code use. MCP tool registries, A2A agent cards, and skill marketplaces all interoperate because the underlying format is shared.

## Implementation Phases

### Phase A: Delivery by Default ✓
- Bootstrap agents set email destination automatically
- Composer-created agents include destination
- Skill prompts adapted for email delivery context
- No new infrastructure

### Phase B: Output Gateway + First Skills ✓
- `content_url` column on workspace_files for binary references
- Supabase Storage for binary file storage
- `yarnnn-render` web service (5th Render service) with initial skills
- Initial skills: document (pandoc), presentation (python-pptx), spreadsheet (openpyxl), chart (matplotlib)
- `RuntimeDispatch` primitive for headless agents
- Email delivery extended with rendered attachments/links

### Phase C: Composer + Frontend Awareness ✓
- Composer awareness of available skills
- Agent creation with skill hints in AGENT.md
- Frontend rendered output display (download buttons, type badges)

### Phase D.1: Skills Alignment + SKILL.md Injection (Proposed — low risk, can ship now)
- Rename `render/handlers/` → `render/skills/`
- Restructure each skill into folder format: `render/skills/{name}/SKILL.md` + `render/skills/{name}/scripts/render.py`
- Rename `HANDLERS` dict → `SKILLS` dict in `main.py`
- Write SKILL.md for each existing skill (pptx, pdf, xlsx, chart) following Claude Code frontmatter conventions
- **SKILL.md injection**: during `load_context()` in execution strategies, when an agent has authorized skills in AGENT.md, inject relevant SKILL.md content into agent context. Gateway serves SKILL.md content via `GET /skills/{name}/SKILL.md` endpoint.
- Update `RuntimeDispatch` tool description to use "skill" terminology
- Update all documentation references (handler → skill, capability → skill)
- ADR-109 `skill` → `role` column rename (see Resolved Decision #4)

### Phase D.2: Render Service Hardening (Implemented)
- ✅ Service-to-service auth via `RENDER_SERVICE_SECRET` env var + `X-Render-Secret` header on POST /render
- ✅ Request size limits: 5MB max payload (Content-Length check)
- ✅ User-scoped storage paths: `{user_id}/{date}/{filename}.{ext}`
- ✅ In-memory rate limiting: 60 requests/minute sliding window per caller
- ✅ Workspace write fatal (done in D.1, Resolved Decision #3)
- ✅ Render call counting via `render_usage` table (migration 115) + `get_monthly_render_count()` RPC
- ✅ Tier-based render limits: free=10/month, pro=100/month (`monthly_renders` in PlatformLimits)
- ✅ Hard rejection in RuntimeDispatch via `check_render_limit()` before dispatch
- ✅ Env var `RENDER_SERVICE_SECRET` set on API + Unified Scheduler + Render services

### Phase D.3: Unified Output Substrate (Implemented)
- ✅ Agent outputs written to workspace_files output folders BEFORE delivery (output folder is the single delivery source)
- ✅ **Dual output**: RuntimeDispatch renders accumulate as `pending_renders` during headless generation, passed to `save_output()` → manifest.json `files[]` includes text + binary
- ✅ Email delivery reads from output folder manifest (text from `output.md`, rendered attachments from `manifest.files[]`) instead of agent_runs
- ✅ `deliver_from_output_folder()` — workspace-based delivery with manifest-sourced attachments
- ✅ agent_runs retains content (dual-write for backward compat) but delivery reads from output folder
- ✅ Non-email destinations (Slack, Notion) fall through to existing exporters with text from output folder
- ✅ Fallback: if output folder write fails, legacy agent_runs delivery path activates
- ✅ Manifest updated with delivery status after send
- ✅ Notifications (ADR-040) and export logging via standalone helpers
- ⏳ Move email skill to output gateway (deferred — Resend stays on API)
- ⏳ Add Slack/Notion delivery skills to gateway (deferred to D.4+)

### Phase D.4: Expand Skill Library (Proposed — after D.2 + D.3)
- Image skill (pillow + cairosvg) — local
- Diagram skill (mermaid-cli / graphviz) — local
- Video skill (Remotion / Node.js) — local
- AI image skill (Replicate / OpenAI) — delegated (requires D.2 cost enforcement)
- Audio skill (ElevenLabs) — delegated (requires D.2 cost enforcement)

### Phase D.5: Assets Layer (Deferred — until user demand)
- Establish `/assets/` path conventions in content filesystem
- User upload path for brand assets (dashboard or TP chat)
- Template storage in `/assets/templates/{skill-name}/`
- Install expanded tool set in Docker image for new skills

### Deferred
- Automated skill gating (threshold tracking, auto-promotion)
- A2A/MCP ecosystem skill discovery + delegation
- Skill marketplace (community-contributed skills)
- Docker image splitting if size exceeds Render limits

## Glossary

| Term | Definition |
|---|---|
| **Skill** | A folder in the output gateway containing SKILL.md + scripts that produce a specific output type. Same format as Claude Code skills. Replaces "handler" and "capability" in prior terminology. |
| **SKILL.md** | Frontmatter + instructions for a skill. Same format and conventions as Claude Code SKILL.md files. Dual purpose: agent reads it to learn spec construction; gateway uses frontmatter for routing metadata. |
| **Skill folder** | The directory containing a skill's SKILL.md, scripts/, and supporting docs. Located at `render/skills/{name}/`. |
| **Local skill** | Skill that runs tools installed in the Docker image. Fixed cost. |
| **Delegated skill** | Skill that calls an external API/MCP. Per-call cost. |
| **Skill registry** | The `SKILLS` dict in `render/main.py` that routes dispatch to skill entry points. |
| **Output gateway** | The execution service for skills. Docker service with tools installed + skill registry. yarnnn-specific (no Claude Code equivalent — it IS the local machine in Claude Code). |
| **RuntimeDispatch** | Agent primitive that invokes a skill on the output gateway. yarnnn-specific (Claude Code agents just run bash). |
| **Capability filesystem** | The skill library on the output gateway. Platform-wide, engineering-managed, deployed with Docker image. |
| **Content filesystem** | The workspace (workspace_files + S3). User-scoped, agent-scoped, accumulating. Where all agent work and outputs live. |
| **Skill gating** | Feedback-earned progression from text → template parameterization → generative dispatch. |
| **Creative assets** | Shared brand resources in `/assets/` accessible to all agents. Part of the content filesystem. |
| **Template** | Pre-built output structure in `/assets/templates/{skill-name}/` that agents parameterize. |
| **Role** | What an agent does — its behavioral function (digest, prepare, monitor, research, synthesize, act). Column on `agents` table. Was: `skill` in ADR-109, renamed to eliminate overload with output gateway skills. `orchestrate` removed — orchestration is TP/Composer, not an agent role. |

## Resolved Decisions

1. **Agents read SKILL.md (making the Claude Code analogy structural).** When an agent's AGENT.md authorizes a skill, the execution pipeline injects the relevant SKILL.md content into the agent's context during `load_context()`. The agent learns how to construct high-quality specs from skill instructions, not just from a tool definition schema. The gateway serves SKILL.md content via a GET endpoint. This makes the "Claude Code online" model real — agents read skills, then act on them — not aspirational.

2. **All outputs flow through workspace_files (unified substrate).** The current dual-path (text via `agent_runs` → email, binary via RuntimeDispatch → dashboard) is eliminated. Both text and binary outputs are written to workspace_files output folders (ADR-119). The output gateway handles all delivery — email, Slack, Notion — reading from workspace_files. `agent_runs` becomes pure audit trail. This means rendered PDFs get emailed (the disconnect is fixed).

3. **Workspace write is fatal.** If the workspace_files row creation fails after a render, the RuntimeDispatch call fails entirely. The agent gets an error and can retry or fall back to text. An orphaned binary in Supabase Storage with no workspace metadata is worse than a failed render call.

4. **ADR-109 `skill` column renamed to `role`.** The `skill` column on the `agents` table (digest, monitor, synthesize, etc.) is renamed to `role`. This eliminates the naming overload — "role" describes what an agent does (behavioral), "skill" describes what an agent can produce (output). The dual naming was not acceptable for downstream clarity. This is a migration: update column name, update all code references, update ADR-109 documentation. Scoped into Phase D.1.

5. **Render service hardened with auth + rate limits + user-scoped storage.** POST /render requires service-to-service auth (shared secret). Storage paths include user_id for scoping. Request size limits and rate limiting enforced. This is a prerequisite for production use and must land before skill library expansion.

6. **Tier-gated render limits (cost enforcement).** Free tier gets N renders/month, pro gets higher/unlimited. Render call counting per user per month with hard rejection in RuntimeDispatch when exceeded. This is a prerequisite for delegated skills (AI image, audio) which have real per-call API costs. Resolves Open Question 1.

7. **Dual output: text + binary (non-text feedback solved).** Agents always produce a text version alongside any rendered binary. The text version lives in the output folder as the feedback surface. Users edit or comment on the text; feedback distillation operates on text edits; the next run's binary improves because the text improved. This preserves the existing feedback pipeline for all output types and matches how Claude Code works — the user sees and edits the code (text), the rendered output is a derivative. Resolves Open Question 2.

8. **Phase D split into independent phases.** D.1 (naming + SKILL.md injection, low risk) → D.2 (hardening, prerequisite) → D.3 (unified output, depends on ADR-119) → D.4 (expand skills, after D.2+D.3) → D.5 (assets, deferred). Each phase has its own risk profile, dependencies, and can be shipped independently.

## Open Questions

1. **Template authoring UX**: File upload via chat? Dashboard? TP-assisted creation? Deferred to Phase D.5.
2. **Docker image size management**: As tools accumulate, image grows. At what point split into light + heavy services? Monitor after D.4.
3. **Creative asset upload flow**: How do users get brand assets into `/assets/`? Deferred to Phase D.5.
4. **agent_runs migration**: When workspace_files becomes the output substrate (D.3), does agent_runs get slimmed (drop content columns) or kept as-is for backward compatibility? Decide during D.3 implementation.
5. **Skill format divergence risk**: If Claude Code's SKILL.md format evolves, how do we track and adapt? Monitor Anthropic's skill-creator skill + documentation.
6. **Workspace quotas + pricing model**: Storage accumulates with output folders, version history, project contributions, and S3 binaries. Requires separate economics and pricing model analysis. Per-agent pricing may conflict with multi-agent project value. See ADR-119 Resolved Decision #8.

## Analysis Reference

Full analysis with axiom derivation, stress testing, cost model, and scalability assessment: `docs/analysis/skills-as-capability-layer-2026-03-17.md`
