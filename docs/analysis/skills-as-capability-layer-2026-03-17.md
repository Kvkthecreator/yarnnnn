# Skills as the Capability Layer: From Text Substrate to General-Purpose Agent Execution

> **Status**: ADR-118 formalized. All three phases (A+B+C) implemented.
> **Date**: 2026-03-17
> **Authors**: KVK, Claude
> **Context**: Observation that Claude Code's skill pattern (Remotion for video, pptx/xlsx/docx for documents) proves that structured instructions + filesystem = indefinitely expandable agent capabilities. What does this mean for yarnnn?

---

## The Observation

Claude Code demonstrated a pattern: install a skill (structured markdown instructions + code examples), and the agent gains a new capability domain. Remotion proves this for video creation. The pptx/xlsx/docx skills prove it for document generation. The pattern is general:

```
Skill definition (instructions + examples + constraints)
  + Filesystem (a place to write outputs)
  + Runtime (a way to execute/render)
  = New capability
```

This is not theoretical. It's shipping. A single Claude Code instance can generate React apps, render videos, build spreadsheets, write legal documents, and produce data visualizations — all from the same agent, differentiated only by which skill is loaded.

**The question for yarnnn**: if this pattern works for a local IDE agent, can it work for a cloud-hosted autonomous agent platform? And if so, what architectural gaps need to be closed?

---

## What Yarnnn Already Has

The conceptual bones are present:

| Claude Code Concept | Yarnnn Equivalent | Status |
|---|---|---|
| SKILL.md | AGENT.md (workspace) | Implemented (ADR-106) |
| Filesystem | workspace_files (Postgres) | Implemented (ADR-106) |
| Skill loading | Agent instructions + workspace context injection | Implemented |
| Skill taxonomy | Scope × Skill × Trigger (ADR-109) | Docs complete, code migration pending |
| Capability progression | Intentions + capability gating (FOUNDATIONS.md Axiom 3) | Conceptual, not implemented |

The parallels are real. A yarnnn agent's `AGENT.md` is functionally identical to a Claude Code `SKILL.md` — both are structured instructions that shape how the LLM reasons before acting. The workspace filesystem (ADR-106) provides path-based file operations over Postgres, which is architecturally equivalent to a local filesystem for writing outputs.

**What this means**: yarnnn agents can already, in principle, produce any text-based artifact. A "reporting" skill could produce structured markdown reports. A "research" skill could produce annotated bibliographies. An "analysis" skill could produce comparative frameworks. The skill pattern already works for the text substrate.

---

## The Gap: Execution Substrate

The divergence is in what happens after the agent writes something.

### Claude Code's execution model

```
Agent writes file → local runtime executes it → output materialized
                     ↑
                     Node.js, Python, Chrome, ffmpeg, Lambda, etc.
```

The agent has access to an entire compute environment. It can write a Remotion composition and then run `npx remotion render` to produce an MP4. It can write Python and execute it. It can install packages. The skill only needs to teach the agent *what to write* — the environment handles *what to do with it*.

### Yarnnn's current execution model

```
Agent writes to workspace_files → stored in Postgres → delivered as text
```

The agent's output boundary is text. It can produce remarkably sophisticated text — structured documents, analyses, knowledge artifacts — but it cannot execute code, render media, or invoke external tools beyond what the primitive set offers (RefreshPlatformContent, QueryKnowledge, WebSearch, etc.).

### The missing primitive: Runtime Dispatch

The gap is not the skill pattern. The gap is a **runtime layer** — the ability for an agent to declare what should happen to its output beyond storage.

```
Current:    Agent → writes artifact → workspace (done)
Proposed:   Agent → writes artifact + manifest → runtime dispatch → materialized output
```

A runtime dispatch primitive would let a skill declare its execution requirements:

```yaml
# In a hypothetical video skill's AGENT.md
runtime:
  type: remotion-lambda
  entry: compositions/WeeklyRecap.tsx
  output_format: mp4
  output_path: /agents/video-producer/outputs/weekly-recap.mp4
```

Or for document generation:

```yaml
runtime:
  type: docx-converter
  input: /agents/report-writer/drafts/q1-analysis.md
  template: /templates/yarnnn-report.docx
  output_path: /agents/report-writer/outputs/q1-analysis.docx
```

The platform would route the artifact to the appropriate execution environment — Lambda for rendering, a lightweight service for document conversion, an API call for external integrations.

---

## Architectural Layers for General-Purpose Agent Execution

Extending yarnnn from text-substrate to general-purpose execution requires thinking in layers:

### Layer 1: Skill Definitions (have this)

Structured instructions that teach an agent how to reason about a domain and what artifacts to produce. This is AGENT.md, workspace context, and the instructions injection pipeline.

**Current state**: Working. The skill/scope taxonomy (ADR-109) provides the framework. Making skills richer and more composable is an iteration on what exists.

### Layer 2: Workspace / Filesystem (have this)

A storage-agnostic abstraction where agents read and write files. Currently Postgres-backed via `workspace_files`, designed to be swappable (ADR-106).

**Current state**: Working. The abstraction is clean. The gap isn't storage — it's that writing a file is currently the terminal action.

### Layer 3: Runtime Registry (don't have this)

A registry of execution environments that the platform can dispatch to. Each runtime has:
- A type identifier (e.g., `remotion-lambda`, `docx-converter`, `python-sandbox`, `api-call`)
- Input/output contracts (what files it reads, what it produces)
- Resource constraints (timeout, memory, cost)
- Authentication requirements (API keys, service accounts)

**This is the primary architectural gap.**

### Layer 4: Dispatch Primitive (don't have this)

An agent primitive — `ExecuteRuntime` or similar — that takes an artifact + runtime type and dispatches it. This sits alongside existing primitives (WriteWorkspace, QueryKnowledge, WebSearch) as a new category of action.

**Design considerations**:
- Should the agent explicitly invoke the runtime, or should the skill manifest auto-trigger it?
- How does the output re-enter the workspace? (Rendered MP4 → stored where? Delivered how?)
- What's the feedback loop? (Agent can't "see" the rendered video the way a human can in Remotion Studio)

### Layer 5: Output Delivery (partially have this)

How materialized outputs reach the user. Text outputs are already delivered through the dashboard / agent run history. Non-text outputs would need:
- File storage (S3 or equivalent) for binary artifacts
- Delivery UI (links, previews, embedded players)
- Integration with existing output formats (agent run content field supports markdown; does it support file references?)

---

## What This Enables: The Infinite Skills Thesis

If layers 3-5 are built, the capability expansion becomes additive and unbounded:

| Skill | What Agent Produces | Runtime | Output |
|---|---|---|---|
| Digest | Markdown summary | None (text) | Dashboard text |
| Report | Structured document | docx-converter | .docx file |
| Video recap | Remotion composition | remotion-lambda | .mp4 file |
| Data analysis | Python script + data | python-sandbox | Charts, CSVs |
| Presentation | Slide content + layout | pptx-generator | .pptx file |
| Email draft | Formatted email body | email-api | Sent email (with approval) |
| Social post | Platform-specific copy | social-api | Published post (with approval) |

Each new skill is just: new instructions + (optionally) a new runtime adapter. The agent architecture doesn't change. The workspace doesn't change. The feedback loop doesn't change. The only new code is the runtime adapter itself.

**This is the same insight that made Claude Code extensible**: the LLM is the general reasoner, the skill teaches it domain knowledge, and the runtime handles materialization. Yarnnn's version just needs the runtime layer to be cloud-native rather than local.

---

## Bottleneck Assessment

Kevin asked: "Since we're not local and not an IDE, is that the biggest bottleneck?"

### Not the biggest — but a real one

The local/IDE constraint manifests as:

1. **No interactive preview** — Claude Code users see Remotion Studio, tweak, re-render in seconds. Yarnnn agents operate headlessly. The feedback loop is: generate → deliver → user reviews → feedback → next run. This is slower but acceptable for recurring agents (the whole point is they improve over tenure).

2. **No local compute** — Rendering, code execution, etc. need to be dispatched to cloud runtimes. This adds latency and infrastructure cost, but is architecturally clean (Lambda, Cloud Run, etc.).

3. **No real-time iteration** — A Claude Code user can say "make the text bigger" and see the change. A yarnnn agent would need to re-execute a full run. This is a product constraint, not an architectural one.

### The bigger bottleneck: the feedback loop for non-text outputs

For text, the feedback loop works: user reads the output, edits it, agent learns from edits (ADR-117). For non-text outputs (video, documents), the feedback signal is weaker:
- User can't "edit" a video the way they edit text
- The agent can't "see" its own rendered output to self-correct
- Quality assessment requires the user to download and review binary files

This suggests that non-text skills should start in **template mode** — the agent parameterizes a pre-built template rather than generating from scratch. The 8 ad variants already in `/video/` are exactly this pattern: fixed structure, variable content. The agent's job is choosing the right copy, timing, and parameters — not architecting a new composition from zero.

### The actual biggest bottleneck: runtime infrastructure investment

Each new runtime adapter requires:
- A cloud service (Lambda function, Cloud Run container, or equivalent)
- Input/output contracts
- Error handling and retry logic
- Cost tracking
- Security boundaries (agents running arbitrary code is a trust question)

This is real engineering work per runtime. The question is whether to build it incrementally (one runtime at a time, starting with the highest-value use case) or to build a general dispatch framework first.

**Recommendation**: Incremental. Start with document generation (markdown → docx/pdf) because it's closest to the current text substrate, has clear user value, and is technically simple (a single Lambda with pandoc or a document library). Video rendering is higher-impact but also higher-complexity — save it for when the dispatch pattern is proven.

---

## Relationship to Existing Architecture

### FOUNDATIONS.md

- **Axiom 3 (Agents as Developing Entities)**: Skills expand what "developing" means. An agent doesn't just develop deeper domain knowledge — it can develop new output modalities as capabilities are earned. A mature digest agent might progress from text summaries to formatted reports to automated presentations.

- **Axiom 3, Capabilities dimension**: The current progression (Read → Analyze → Write-back → Act) maps cleanly. "Write-back" to a platform could include rendering a video and posting it. "Act" could include dispatching to an execution runtime. The capability gating mechanism (feedback-earned trust) applies regardless of the output modality.

- **Open Question 1 (Intention model)**: Skills could be modeled as intention-capabilities. An agent with the "video" skill has the *intention* to produce visual content and the *capability* to invoke the Remotion runtime. The intention exists independent of whether the runtime is available — the platform just needs to know whether to enable it.

### ADR-106 (Workspace Architecture)

The workspace abstraction is well-positioned for this. The storage-agnostic design means binary outputs could be stored in S3 while maintaining the same path-based interface. A rendered video at `/agents/video-producer/outputs/recap.mp4` would have a workspace_files row pointing to an S3 URL rather than inline content.

### ADR-109 (Agent Framework)

The Skill axis (digest, prepare, monitor, research, synthesize, orchestrate, act) would expand to include output-modality skills. "Synthesize" might produce text, a document, or a presentation depending on which skill files are loaded. The taxonomy doesn't need to change — the skill axis already separates "what it does" from "what it knows."

### ADR-111 (Composer)

The Composer's assessment logic would need to be runtime-aware. When assessing whether to scaffold an agent, TP should know which runtimes are available. "This user would benefit from a weekly video recap" is only actionable if the Remotion runtime is configured.

---

## Runtime Implementation: Three Paths Considered

The question isn't whether agents need a runtime layer — they do. The question is *who operates it*. Three paths were considered:

### Path A: Self-Hosted Lambdas (Rejected for now)

Build and deploy AWS Lambda functions for each runtime type. Yarnnn owns the compute, the deployment, the scaling.

**Pros**: Full control, no per-call API costs (just Lambda pricing), can optimize heavily.
**Cons**: Yarnnn becomes an infrastructure company. Each runtime is a deployment artifact to maintain. Scaling, cold starts, monitoring, error handling — all owned by a 1-person team. This is the path that OpenClaw and Claude Code take, but they're local-first developer tools with the user's machine as the compute substrate. Yarnnn doesn't have that luxury.

**Verdict**: Architecturally correct but operationally premature. Revisit if a specific runtime has enough volume to justify dedicated infrastructure.

### Path B: Third-Party API Orchestration (Recommended near-term)

The "runtime" is an API call to a service that already exists:

| Output Type | Service | API Pattern |
|---|---|---|
| Video rendering | Remotion Cloud Run / Remotion Lambda (hosted) | POST composition + params → poll → MP4 URL |
| Document conversion | CloudConvert, Docmosis, or pandoc on a minimal Cloud Run | POST markdown + template → .docx/.pdf URL |
| Image generation | Replicate, Together, or Claude vision | POST prompt + constraints → image URL |
| Presentation | python-pptx on a minimal Cloud Run | POST slide spec → .pptx URL |
| Charts/visualization | QuickChart.io or a minimal matplotlib service | POST data + chart spec → PNG URL |

**The critical reframe**: this is the same architectural pattern as yarnnn's existing platform sync. Slack sync calls the Slack API. Gmail sync calls the Google API. A document runtime calls the CloudConvert API. The agent pipeline already knows how to make authenticated API calls, handle async responses, and store results. Adding a "render" step is not fundamentally different from adding a "sync" step.

**Pros**: No infrastructure to host. Pay-per-use aligns with yarnnn's cost structure. Each integration is a thin adapter (50-100 lines), not a deployed service. Battle-tested rendering by companies whose entire business is rendering.
**Cons**: Per-call costs (typically $0.01-0.10 per render). Dependency on third-party uptime. Less control over output quality.

**Verdict**: Right approach for proving the pattern. The dispatch primitive is the same regardless of whether the backend is a Lambda or a third-party API — if volume justifies self-hosting later, swap the adapter without changing the agent interface.

### Path C: Agent-to-Agent Delegation via A2A/MCP (Too early)

In a mature A2A ecosystem, yarnnn agents would delegate to specialized external agents: "Remotion agent, render this composition" or "Document agent, format this report." The runtime is someone else's agent.

**Pros**: No infrastructure, no API integration code, ecosystem-native, composable.
**Cons**: The A2A ecosystem doesn't exist in a reliable way yet. Google's A2A protocol is months old. MCP tool-use is closer but still requires discovering and trusting external tool providers. Yarnnn would be waiting on external standards and hoping the right services appear.

**Verdict**: Architecturally elegant, practically premature. The dispatch primitive should be designed to accommodate this path — if the adapter interface is clean, swapping "call CloudConvert API" for "delegate to document-agent via A2A" is a configuration change, not a rewrite.

### Decision: Hybrid (Path A for lightweight + Path B for heavy), designed for Path C later

The dispatch primitive should be adapter-based:

```python
# Pseudocode — the runtime adapter interface
class RuntimeAdapter:
    async def execute(self, spec: dict) -> RuntimeResult:
        """Takes an agent-authored spec, returns a URL to the output."""
        ...

class RemotionCloudAdapter(RuntimeAdapter):
    """Calls Remotion's hosted rendering service."""
    ...

class CloudConvertAdapter(RuntimeAdapter):
    """Calls CloudConvert for document conversion."""
    ...

# Future: swap in without changing agent code
class A2ADocumentAdapter(RuntimeAdapter):
    """Delegates to an A2A document agent."""
    ...
```

The agent never knows or cares which adapter runs. It writes a spec + manifest. The platform routes.

---

## First-Principles Derivation: What the Axioms Dictate

The FOUNDATIONS.md axioms aren't just philosophical framing — they're constraints that narrow the implementation space. Applied to the runtime question, they converge on a specific approach.

### Axiom 1 → Runtime is an agent capability, not a platform feature

TP owns attention allocation. Agents own domain execution. Runtime dispatch is execution — it belongs to agents. This means:

- The `RuntimeDispatch` primitive is an agent-side tool, invoked during agent runs, not a system-wide post-processing step.
- TP/Composer decides whether to scaffold an agent with runtime capabilities. The agent decides when and how to invoke them during execution.
- The dispatch primitive sits in the same capability set as `WriteWorkspace`, `QueryKnowledge`, `WebSearch` — it's another tool an agent can use, gated by earned trust.

**What this rules out**: a "rendering service" that sits outside the agent pipeline and transforms all outputs. That would violate the two-layer separation — it's the agent's job to decide what form its output takes, informed by its domain expertise.

### Axiom 2 → The output must re-enter the perception substrate

A rendered document or video is not a terminal artifact. It's a new piece of the knowledge layer. Other agents should be able to perceive it. TP should be able to reason about it. The user's feedback on it should feed back into the recursive loop.

This means:

- Every runtime output gets a `workspace_files` row, regardless of where the binary lives (S3, CDN, etc.). The row carries metadata: what skill produced it, what parameters, what template, when, what feedback the user gave.
- The metadata is more architecturally important than the binary. The binary is a delivery artifact. The metadata is the accumulation artifact.
- A `content_url` column on `workspace_files` (pointing to S3) is the minimal schema change. The path-based interface stays the same — `/agents/report-writer/outputs/q1-report.docx` resolves to an S3 URL instead of inline Postgres content.

**What this rules out**: storing rendered outputs only in S3 with no workspace representation. That would make them invisible to the perception substrate — dead artifacts that don't participate in the recursive loop.

### Axiom 3 → Runtime access is earned, not default

Agents develop through phases: Creation → Early Tenure → Developing → Mature → Evolved. Capabilities are gated by demonstrated quality. Runtime dispatch is a capability that follows the same progression:

```
Text output (default) → Template parameterization (early) → Runtime dispatch (developing+)
```

Concretely:

- **Creation**: Agent produces text-only outputs. No runtime dispatch available.
- **Early Tenure**: Agent can parameterize pre-built templates (e.g., fill in a report template). The template constrains the output — the agent chooses content, the template guarantees form.
- **Developing**: Agent earns `RuntimeDispatch` access after demonstrating consistent quality (approval rate, low edit distance). Can now invoke runtime adapters to produce non-text artifacts.
- **Mature**: Agent can select which template or runtime to use based on context. May produce different output types for different situations (text digest on quiet days, formatted PDF report on active weeks).

**What this rules out**: giving every new agent runtime access from day one. That would skip the feedback accumulation that makes the output worth rendering. A formatted PDF of a bad digest is worse than a good markdown digest.

**What this implies for implementation**: template parameterization comes before runtime dispatch. Phase 0 (richer text skills) and Phase 1 (first runtime adapter) are actually the same developmental progression — the agent learns to produce good text, then learns to parameterize templates, then earns the ability to render.

### Axiom 4 → Feedback loop depth over runtime breadth

The value isn't in how many output formats you support. It's in how well the agent learns from feedback on each format. One runtime with 10 runs of accumulated feedback produces better output than 5 runtimes with 2 runs each.

This dictates implementation priority:

1. **First**: Get the feedback mechanism working for non-text outputs. How does a user "edit" a PDF report? Options: annotate, reject with comments, approve with notes, or provide a text-level edit that the agent translates to the next render. This is the hard UX problem — solve it before adding runtimes.
2. **Second**: Build one runtime adapter end-to-end, including the full feedback loop.
3. **Third**: Only then generalize the adapter pattern to additional runtimes.

**What this rules out**: building the adapter registry before the feedback mechanism. The registry is the easy part (a config mapping types to classes). The feedback loop is the hard part and the value driver.

### Axiom 6 → Zero-configuration for the user

The Composer should auto-scaffold agents with appropriate runtime capabilities based on what's available and what the user's substrate suggests. A user who connects Slack and has a brand kit uploaded should see a branded PDF digest appear — not be asked to "configure document rendering."

This means:

- Runtime availability is a Composer input. When Composer assesses "what sustained attention is warranted," available runtimes expand the set of agent archetypes it can scaffold.
- Template discovery is automatic. If brand templates exist in the workspace, Composer knows about them when scaffolding.
- The user's first encounter with runtime dispatch should be receiving a rendered output, not configuring one.

### The Derived Approach

Combining all five constraints:

**Runtime dispatch is an agent capability (not a platform service) that is earned through feedback-gated progression (not default), where the rendered output re-enters the perception substrate as metadata-rich knowledge (not dead artifacts), implementation prioritizes feedback loop depth over runtime breadth (one adapter done well before many), and the user never configures it (Composer handles scaffolding).**

This is more specific than "Path B with templates." It's a developmental model for runtime:

```
Phase 0: Text substrate excellence
  └─ Skills make text outputs better (prompt engineering, structured rules)
  └─ Feedback loop for text is already working (ADR-117)
  └─ No new infrastructure

Phase 1: Template parameterization
  └─ Templates stored in workspace (brand kit, report templates, slide layouts)
  └─ Agent skill files teach template selection heuristics
  └─ Agent output = template ID + parameters (still text, just structured)
  └─ Composer aware of available templates when scaffolding
  └─ No runtime adapter yet — the "rendering" is client-side or deferred

Phase 2: Render service + first capability + feedback loop
  └─ Deploy yarnnn-render on Render (one service, fat Docker image)
  └─ First local handler: pandoc (markdown+template → .docx/.pdf)
  └─ workspace_files extended with content_url (S3-backed)
  └─ Feedback mechanism for non-text outputs designed and built
  └─ Capability gating: agents earn RuntimeDispatch via approval history
  └─ Full recursive loop: render → deliver → user feedback → agent learns → better render

Phase 3: Capability expansion
  └─ Additional local handlers (python-pptx, matplotlib, pillow)
  └─ First delegated adapter (Remotion Cloud for video)
  └─ Capability registry formalized (config-driven)
  └─ Cost tracking per-capability per-agent
  └─ Only after Phase 2's feedback loop is proven

Phase 4: Ecosystem (monitor, don't build yet)
  └─ A2A/MCP delegation when ecosystem matures
  └─ Adapter interface already accommodates this — swap, don't rewrite
```

The key shift from the previous phasing: **Phase 1 is now about templates as a first-class concept, not about building a runtime adapter.** The adapter comes in Phase 2, after templates prove that structured non-text output works and the feedback mechanism is designed. This is the axioms talking — Axiom 3 says "earn it," Axiom 4 says "feedback loop first."

### What This Means for Yarnnn's Evolution

Kevin identified the trajectory: yarnnn is evolving toward something like a web-based Claude Code for knowledge workers. The axioms say: **that's fine, as long as the evolution follows the developmental model, not the capability-explosion model.**

Claude Code gains capabilities by installing skills. Yarnnn gains capabilities by agents *earning* skills through tenure. The skill file might be identical — but the pathway to using it is fundamentally different. Claude Code is stateless capability expansion. Yarnnn is accumulated capability development.

This is the self-awareness the evolution requires. Yarnnn can have indefinitely many capabilities — but each agent earns its capabilities individually, through demonstrated quality, accumulated feedback, and graduated trust. The platform doesn't "get video" — a specific agent earns the ability to render video after proving it understands the domain well enough for that output to be worth rendering.

This is the moat. It's not the runtime adapter (anyone can call an API). It's the judgment about when a rendered output is warranted, accumulated over every previous run's feedback.

---

## Decision Validation: Stress-Testing the Derived Approach

Before hardening this into an implementation plan, each axiom-derived constraint was challenged with its strongest counter-argument.

### Challenge 1: "Earned runtime" creates a worse first-run experience

**Counter**: If rendering capabilities exist, why force a new agent through 5 runs of plain markdown before it can produce a PDF? The user's first impression is ugly text, not a polished document. That's a worse product.

**Resolution**: Template parameterization (Phase 1) is available from day one. Composer can scaffold a bootstrap agent that uses a pre-built template immediately — choosing the right template + filling parameters is not a capability that needs to be earned. What's earned is *generative* runtime dispatch (Phase 2+) — producing novel output structures without template guardrails. The distinction: templated rendering = supervised mode (no gate). Generative rendering = autonomous mode (gated). This means the user's first digest can arrive as a branded PDF if a template exists. The gate only applies to unconstrained rendering.

**Verdict**: Constraint holds, but the documentation must be explicit that templates are ungated. Updated in phasing.

### Challenge 2: Metadata-as-accumulation is over-engineering

**Counter**: Most users just want the PDF. Is the workspace row + metadata framing adding real value or philosophical overhead?

**Resolution**: Without the metadata, the agent has no record of what it produced, what parameters it used, or what feedback it received. It literally cannot improve on the next run. And cross-agent perception (ADR-116) already requires workspace rows for inter-agent reads. This isn't new infrastructure — it's using what exists. The metadata is also small (one row per output, not a new table), and the schema change is minimal (`content_url` column on `workspace_files`).

**Verdict**: Not over-engineering. It's the mechanism that makes the feedback loop possible. **Strong hold.**

### Challenge 3: Capability gating adds premature complexity

**Counter**: For a 1-person team, automated capability gating (tracking approval rates, defining thresholds) is premature. Just ship rendering for all agents and gate later.

**Resolution**: The gating doesn't need to be automated in Phase 2. It starts as a Composer heuristic — a conditional in Composer's scaffolding prompt: "If the agent has a template and 3+ approved runs, include RuntimeDispatch in its primitive set." That's a prompt change, not a system. Automated gating (threshold tracking, auto-promotion) comes in Phase 3+ if the pattern warrants it.

**Verdict**: Constraint holds with simplified implementation. Gating = Composer prompt heuristic, not an automated system.

### Challenge 4: "Depth over breadth" loses the positioning battle

**Counter**: If a competitor ships video + documents + images + social and yarnnn only has documents, does "one adapter done well" lose the market?

**Resolution**: The target audience (knowledge workers) already has Canva, Google Docs, Figma, etc. for format variety. What they don't have is an agent that produces a better report each week because it learned from their feedback. The value proposition is "your agent improves with tenure" — not "your agent supports 5 formats." For spray-and-pray marketing tools, breadth matters. For accumulated-quality autonomous agents, depth is the differentiator. If the audience shifts toward content-creator personas, revisit — but the current ICP validates depth.

**Verdict**: Holds for current audience. Flag as a monitoring point if ICP evolves.

### Challenge 5: Zero-config limits power users

**Counter**: Some users want to choose adapters, set quality parameters, configure rendering options. Zero-config as a hard constraint limits the product ceiling.

**Resolution**: Zero-config is the default, not the ceiling. The same pattern as source selection (ADR-113): auto-discovered by default, manually refinable through chat surface (ADR-105) or context pages. Power users modify agent instructions, swap templates, adjust output parameters. Zero-config means the first experience is effortless, not that configuration is impossible.

**Verdict**: Holds. Zero-config default + optional refinement.

### Infrastructure Model: Hybrid Render Service

The infrastructure decision was re-evaluated from first principles against code maintenance, scalability, cost, and stability. The result: a **hybrid render service** — one self-hosted Render web service for lightweight transformations, with delegation to third-party APIs for heavy compute.

#### The service

One new Render web service (`yarnnn-render`). Fat Docker image (~800MB-1GB) bundling lightweight Python/CLI tools. Single `POST /render` endpoint that routes internally by capability type. For capabilities that exceed what the service can handle (video, AI images), the same endpoint delegates to third-party APIs. The agent never knows which path runs.

#### Capability classification

**Local handlers** (bundled in Docker image, fixed cost, no external dependencies):

| Capability | Tool | Render time | RAM | Docker footprint |
|---|---|---|---|---|
| Documents (md → docx/pdf) | pandoc | 100-500ms | <128MB | ~200MB |
| Presentations (spec → pptx) | python-pptx | 200-800ms | <128MB | ~50MB |
| Spreadsheets (spec → xlsx) | openpyxl | 100-300ms | <128MB | ~30MB |
| Charts/visualizations | matplotlib + plotly | 200-1000ms | <256MB | ~300MB |
| Simple images (template → png/svg) | pillow + cairosvg | 100-500ms | <128MB | ~150MB |
| Email templates | jinja2 + mjml | <100ms | <64MB | ~20MB |
| Data exports (csv, json) | stdlib | <50ms | <64MB | 0 |

All handlers: CPU-fast (<1s), low-memory (<256MB), stateless. This covers the vast majority of knowledge-worker output types.

**Delegated to third-party APIs** (per-call cost, heavy compute):

| Capability | Service | Why not local | Cost/call | Phase |
|---|---|---|---|---|
| Video rendering | Remotion Cloud / Shotstack | 2-4GB RAM, 30-120s, headless Chrome | $0.05-0.50 | Phase 3 |
| AI image generation | Replicate / Together / OpenAI | Needs GPU | $0.01-0.10 | Phase 3 |
| Audio generation | ElevenLabs / future | Specialized model | $0.01-0.05 | Phase 4+ |

**Routing heuristic**: if a capability fits in <256MB RAM and <5s render time → local. Otherwise → delegated. This boundary is stable as capabilities grow.

#### Why hybrid beats the alternatives

| Dimension | Pure third-party (CloudConvert) | Pure self-hosted (Lambda) | Hybrid render service |
|---|---|---|---|
| **Code maintenance** | Low code, but API versioning + vendor monitoring | High — AWS IAM, CloudWatch, per-function deploys | Medium — one Dockerfile, pinned deps, quarterly updates |
| **Scalability** | Their problem, but rate limits yours | Your problem, full control | Fixed cost for 80%, delegated for 20% |
| **Cost at 1K agents/wk** | ~$40/mo | ~$7/mo + AWS overhead | ~$7/mo (local) + ~$0 (no delegated yet) |
| **Cost at 10K agents/wk** | ~$400/mo | ~$14/mo + AWS overhead | ~$14/mo + ~$200/mo (delegated) |
| **Stability** | Third-party uptime for ALL renders | Your uptime for ALL renders | Your uptime for core 80%, third-party for heavy 20% |
| **Ops overhead** | API keys, webhooks, polling, vendor monitoring | AWS account, IAM, CloudWatch, cold starts | One Render service (same as existing 4) |

### Cost Model (Hybrid)

| Scale | Local renders (fixed) | Delegated renders (variable) | Total render | Claude API (reference) | Render as % of API |
|---|---|---|---|---|---|
| 50 agents/week | $7/mo | $0 | $7/mo | $100-250/mo | 3-7% |
| 200 agents/week | $7/mo | ~$5/mo | $12/mo | $400-1,000/mo | 1-3% |
| 1,000 agents/week | $7/mo | ~$25/mo | $32/mo | $2,000-5,000/mo | 0.6-1.6% |
| 5,000 agents/week | $14/mo (2 instances) | ~$100/mo | $114/mo | $10,000-25,000/mo | 0.5-1.1% |
| 10,000 agents/week | $14/mo | ~$200/mo | $214/mo | $20,000-50,000/mo | 0.4-1.1% |

**Key insight**: render cost stays under 3% of Claude API cost at every scale. The local portion is fixed. The variable portion only kicks in for heavy capabilities (Phase 3+). Cost model does not change business fundamentals.

**Comparison to pure third-party at scale**:

| Scale | CloudConvert (all renders) | Hybrid | Annual savings |
|---|---|---|---|
| 1,000 agents/week | ~$40/mo | $7/mo | $396/yr |
| 10,000 agents/week | ~$400/mo | $14/mo (local only) | $4,632/yr |

### Scalability Assessment

The bottleneck at scale is not the render service:

- **Agent pipeline** (Claude API calls): Already the scaling constraint. Runtime dispatch adds one local function call (~100-500ms) — faster than an external API call.
- **Render service**: Stateless. Each render is independent. A single $7/mo Render instance handles hundreds of renders per hour. Horizontal scaling (2-3 instances) handles thousands.
- **S3 storage**: Scales indefinitely. Only needed for binary outputs (PDFs are small; video is Phase 3+).
- **Feedback metadata**: One `workspace_files` row per output. Postgres handles millions trivially.
- **Indefinite capabilities**: Adding a new local handler doesn't change the scaling profile. The service handles N types at the same throughput because each render is independent and fast. The Docker image can hold 15-20 capability types before reaching ~2-3GB (well within Render's limits).

### Stability Assessment

**Local handlers**: no external API calls during rendering. If Render is up (and your other 4 services already depend on this), rendering is up. Pandoc, python-pptx, matplotlib — among the most stable libraries in the Python ecosystem. No rate limits. No third-party deprecation. No pricing surprises.

**Delegated handlers**: third-party uptime, but blast radius is contained. If Remotion Cloud is down, only video agents are affected. Text, document, presentation, chart agents all continue on the local path. This is a strict improvement over pure third-party (where CloudConvert downtime affects ALL rendering).

**Operational overhead for a 1-person team**: one Dockerfile to maintain (quarterly dependency updates, CI-tested). One Render service to monitor (same dashboard as existing 4). No API keys for local handlers (only for delegated ones when added in Phase 3+). Less operational surface than a CloudConvert integration (no webhook handlers, no polling, no vendor monitoring for the core path).

### Future-Proofing Assessment

The adapter interface (`execute(spec) → RuntimeResult`) accommodates all foreseeable execution models:

| Future scenario | Change required | Agent-facing change |
|---|---|---|
| New local capability (e.g., audio waveform) | Add handler function + pip dependency | None |
| Promote delegated → local (e.g., self-host video) | Move handler from external adapter to local | None |
| A2A ecosystem matures | New delegated adapter class | None |
| Desktop/local component | New adapter routing to user's machine | None |
| Docker image too large (15+ capabilities) | Split into "light" and "heavy" services | None |

The service architecture allows capability migration in both directions (local ↔ delegated) without changing the agent-facing contract. The cost of being wrong on any individual capability classification is one code change.

### Validation Summary

All five axiom-derived constraints hold under stress testing. The main refinements:

1. **Templates are ungated** — only generative runtime dispatch is earned. Bootstrap agents can use templates from day one.
2. **Capability gating starts as a Composer prompt heuristic**, not an automated system. Automated gating deferred to Phase 3+.
3. **Cost is negligible** relative to existing Claude API spend (<10% marginal increase).
4. **Depth-over-breadth holds for current ICP** (knowledge workers). Monitor if audience shifts.
5. **Adapter interface is future-proof** because the abstraction is at the right layer and the cost of being wrong is low.

**Decision confidence: High.** No counter-argument undermined the core approach. The refinements are implementation details, not directional changes.

---

## Terminology & Capability Model

### The SKILL.md vs AGENT.md Question

Claude Code uses SKILL.md to teach an agent *how* to do something (render video, build spreadsheets). Yarnnn uses AGENT.md to define *who* the agent is (identity, directives, memory references). These are different concerns:

- **AGENT.md** = identity + behavioral directives (WHO the agent is)
- **SKILL.md** (Claude Code) = capability instructions (HOW to use a tool/runtime)

In Claude Code, these conflate because sessions are stateless — the skill IS the agent for that session. In yarnnn, agents persist across runs with accumulated memory. An agent's identity is independent of any single capability.

### Why SKILL.md Doesn't Port to Yarnnn

Claude Code's skills are unbounded because the local machine is the runtime — any skill file can teach the agent to invoke any local tool. In yarnnn, capabilities are bounded by what the platform has adapters for. You can't install a "video rendering skill" if there's no video adapter. **The adapter defines the capability boundary, not the instruction file.**

This means the skill concept is absorbed by the runtime registry. There's no separate "skill installation" step. The platform has an explicit set of capabilities (defined by adapters), and AGENT.md references which capabilities an agent is authorized to use.

### The Capability Model

| Concept | What it is | Where it lives | Who creates it |
|---|---|---|---|
| **Capability** | A runtime adapter the platform can dispatch to | Runtime registry (config) | Engineering (deliberate addition) |
| **AGENT.md** | Agent identity, directives, capability authorizations | Agent workspace | Composer (scaffolding) + user (refinement) |
| **Capability guide** | Shared reference: how to use a specific capability | `/capabilities/{name}/guide.md` in workspace | Engineering (per-adapter documentation) |
| **Template** | Pre-built output structure an agent parameterizes | `/templates/{name}/` in workspace | Engineering + user uploads (brand kits) |

### Explicit vs. Buffet

The capability set is **explicit and curated**, not an open-ended buffet. Each capability requires:

1. **An adapter** (engineering investment: 50-100 lines + error handling)
2. **A cost model** (per-call pricing, tier gating rules)
3. **A feedback mechanism** (how users provide input on this output type)
4. **A capability guide** (shared instructions agents reference)

This is a deliberate addition per capability, not a user-installable skill. The set grows with engineering investment and validation, not with user demand alone.

**Why this is a feature, not a limitation**: it gives capability gating clear boundaries (Axiom 3), cost control (Axiom 4), quality assurance, and clear Composer inputs ("here are the N things agents can produce beyond text"). The Composer can only scaffold what it knows about — an explicit registry makes this deterministic.

### Glossary Update

For consistency across the codebase and documentation:

| Term | Definition | Replaces |
|---|---|---|
| **Capability** | A registered, platform-level runtime adapter with defined I/O contracts | "skill" (in runtime context) |
| **AGENT.md** | Per-agent identity file: directives, memory refs, capability authorizations | Unchanged from ADR-106 |
| **Capability guide** | Shared documentation teaching agents how to use a specific capability | "skill file" (in yarnnn context) |
| **Template** | Pre-built output structure parameterized by agents | New concept |
| **Runtime adapter** | Code that dispatches a spec to an execution service and returns a result | New concept |
| **Runtime registry** | Config mapping capability types to adapter classes | New concept |
| **Capability gating** | The feedback-earned progression from text → template → generative rendering | Extension of Axiom 3 |

**Note**: "Skill" remains valid in the ADR-109 Scope × Skill × Trigger taxonomy (where it means "what the agent does" — digest, prepare, monitor, etc.). The term is NOT used for runtime capabilities to avoid confusion with Claude Code's SKILL.md pattern.

---

## Macro Positioning: What Is Yarnnn Becoming?

### The observation

This skills + runtime architecture pushes yarnnn toward something like a **cloud-native, knowledge-worker-facing Claude Code** — an agent platform where capabilities are infinitely extensible via skills, and outputs are materialized via runtime dispatch.

The comparison points:

| | Claude Code | OpenClaw | Yarnnn (with runtime layer) |
|---|---|---|---|
| **Substrate** | Local machine | Local machine | Cloud (Supabase + S3 + API adapters) |
| **User** | Developers | Developers | Knowledge workers |
| **Skill loading** | SKILL.md in repo | Skills in workspace | AGENT.md in workspace_files |
| **Execution** | Local Node/Python/etc | Local compute | Third-party APIs / future Lambdas |
| **Feedback loop** | Real-time (see output, tweak) | Real-time | Async (run → review → feedback → next run) |
| **Autonomy** | User-directed | User-directed | Autonomous + user-supervised |
| **Persistence** | Session-scoped | Session-scoped | Persistent (agents accumulate across runs) |

### What differentiates yarnnn

The last two rows are the moat. Claude Code is powerful but stateless — each session starts fresh (session compaction aside). Yarnnn agents are persistent entities that develop over time (Axiom 3). A Claude Code user must re-prompt for every video. A yarnnn agent produces weekly video recaps that improve with each iteration because it remembers what the user edited last time.

The autonomy dimension is equally distinctive. Claude Code waits for instructions. Yarnnn agents act on schedule, react to events, and proactively identify needs. Adding rich output modalities to autonomous agents creates a category that doesn't exist yet: **an autonomous creative production pipeline that learns from feedback**.

### The strategic question this raises

If yarnnn can produce documents, videos, images, and social posts autonomously — improving over tenure — it's no longer just a "knowledge work" platform. It's an **autonomous creative production pipeline**. The current wave of AI marketing agents (autonomous CMOs, content schedulers) takes a spray-and-pray approach — generate volume, hope something sticks. Yarnnn's architecture points to the opposite: accumulated understanding → high-quality outputs across modalities, where each run is informed by every previous run's feedback.

This is a thought branch, not a decision. Documenting it to revisit.

---

## Implementation Phases (Axiom-Derived)

*Previous phasing (v2) put runtime adapters before templates. The first-principles derivation reverses this: templates are how agents earn runtime access, and the feedback loop must precede adapter scaling.*

### Phase 0: Text Substrate Excellence (Now — no infrastructure change)

Make the existing text substrate more powerful before adding new output modalities:
- Skill files with structured rules (like the Remotion best-practices skill, but for writing, analysis, research)
- Per-skill prompt engineering guidelines
- Skill composition (an agent can load multiple skills for a single run)
- This is pure prompt/workspace work — no new services, no new infra
- **Why first**: Axiom 4 — the feedback loop for text already works (ADR-117). Improving text output quality compounds immediately through existing infrastructure.

### Phase 1: Template Parameterization (Near-term — minimal infrastructure)

Templates as a first-class concept, before any rendering:
- Template files stored in workspace (`/templates/` path convention — report templates, brand kits, slide layouts)
- Agent skill files teach template selection heuristics ("use the executive template for C-suite, the detailed template for engineering")
- Agent output = structured spec: template ID + parameters + content (still text/JSON, just structured)
- Composer aware of available templates when scaffolding agents
- User can upload brand kits / templates
- **Why before runtime**: Axiom 3 — template parameterization is the "supervised" mode of runtime. The agent learns to produce structured specs before earning the ability to render them. If the spec is bad, rendering just makes a bad output look polished.
- **Success metric**: agents produce structured output specs that are coherent and well-parameterized, even before rendering exists

### Phase 2: Render Service + First Capability + Feedback Loop (Near-term+)

Deploy the hybrid render service, prove the pattern with one capability, build the feedback loop:
- Deploy `yarnnn-render` on Render (5th service — Dockerfile + single endpoint)
- `RuntimeDispatch` primitive added to agent pipeline (~200 lines)
- First local handler: document conversion (markdown + template → .docx/.pdf) via pandoc
- `workspace_files` extended with `content_url` column (S3-backed binary references)
- **Critical design work**: feedback mechanism for non-text outputs — how does a user "edit" a PDF? Options: annotate, reject with comments, approve with notes, provide text-level edits the agent translates to next render
- Capability gating: agents earn `RuntimeDispatch` access via approval history (Axiom 3)
- Dashboard UI: download link + inline preview
- **Why the feedback loop is the hard part**: Axiom 4 — a rendered output without feedback is a dead artifact. The adapter is 50 lines. The feedback mechanism is the design problem that makes this valuable.
- **Success metric**: an agent produces a formatted .docx weekly report, user provides feedback on it, next week's report is measurably better

### Phase 3: Capability Expansion (Medium-term — only after Phase 2 feedback loop is proven)

Expand the render service with additional local handlers + first delegated capability:
- Add local handlers: presentations (python-pptx), charts (matplotlib), simple images (pillow)
- First delegated adapter: Remotion Cloud rendering for video (single-frame images or full video)
- Capability registry formalized as config (JSON/YAML mapping types to local handlers or external adapters)
- Cost tracking per-capability per-agent (for tier gating)
- Feedback mechanism generalized across output types (some modalities may need different feedback patterns)
- **Gate**: Phase 2's feedback loop must be working and producing measurable improvement before investing in additional capabilities
- **Success metric**: an agent produces branded social graphics that improve with user feedback across iterations

### Phase 4: Ecosystem Delegation (Future — monitor, don't build)

If the A2A/MCP ecosystem matures:
- A2A-based adapters alongside API-based adapters
- Agent can delegate to external specialized agents for rendering
- Yarnnn becomes a consumer in the agent ecosystem, not just a provider
- **Trigger**: when at least 2-3 reliable rendering agents exist with stable APIs
- The adapter interface already accommodates this — swap, don't rewrite

---

## Open Questions (Remaining)

*Questions 1, 4, and 5 from v2 were resolved by the Terminology & Capability Model section (capabilities are explicit/curated, not a marketplace; templates precede generative rendering as a developmental stage; capability guides are engineering-authored, not user-installed).*

1. **Runtime cost model**: Tier-gated rendering? Per-call costs are low ($0.01/conversion) but at scale could be material. Should Pro tier include unlimited rendering while Free tier limits to N renders/month? Does the agent need to "budget" its runtime invocations?

2. **Self-assessment for non-text outputs**: How does an agent evaluate whether its document/video/presentation is good before delivering? Options: invoke a review step (e.g., screenshot first page, analyze via vision), compare against template expectations, or rely entirely on user feedback post-delivery. This is relevant for Phase 2 feedback loop design.

3. **Cross-agent capability awareness**: Can one agent read another's rendered outputs and metadata? Already possible via ReadAgentContext (ADR-116 Phase 3), but the question is whether capability metadata (what template was used, what parameters, what feedback) should be exposed cross-agent or kept private.

4. **Template authoring UX**: Users can upload brand kits / templates (Phase 1). What's the UX? File upload via chat? Dashboard page? Can TP help the user create a template from examples? This is a product design question, not an architecture question.

---

## Decision Branches

### Resolved

**Branch 2 (Template-first vs. generative-first)**: **Resolved — template-first.** The first-principles derivation (Axiom 3) makes this a developmental sequence, not a choice: templates are the supervised mode of runtime, generative rendering is the autonomous mode earned through feedback. Not a branch anymore — it's the phasing.

**Branch 1 (Build vs. Buy for first adapter)**: **Resolved — hybrid render service.** Self-hosted Render service for lightweight capabilities (documents, presentations, charts, images, spreadsheets — covering 80%+ of knowledge-worker output types). Third-party API delegation for heavy compute (video, AI images — Phase 3+). Re-assessment against code maintenance, scalability, cost projections, and stability all favor the hybrid model over pure third-party. See Infrastructure Model section for full analysis.

### Active

### Branch 3: When to expose this to users

**Option A**: Build as internal infrastructure, expose gradually
**Option B**: Ship as a visible feature

**Leaning**: Option A. Prove the pipeline works end-to-end before marketing it. But note: if Composer auto-scaffolds agents with template capabilities (Axiom 6 — zero-config), users encounter it organically without a feature launch. The "exposure" may be implicit.

### Branch 4: Autonomous creative production pipeline

The runtime layer + existing content strategy + autonomous agents = a system that could produce blog posts, cross-posts, social graphics, video clips, and email sequences autonomously, improving with tenure. The differentiator from existing AI content tools is quality through accumulated understanding, not volume through generation.

**Not deciding this now.** Documenting the trajectory. This is a product positioning decision, not a technical one. The architecture supports it without additional conceptual work.

---

## Summary

Skills are the indefinitely expandable capability layer. The pattern already works for yarnnn's text substrate. The gaps are in execution (runtime dispatch) and delivery (binary output handling), not in the skill model itself.

**Infrastructure approach**: Hybrid render service. One new Render web service (`yarnnn-render`) with a fat Docker image bundling lightweight tools (pandoc, python-pptx, matplotlib, pillow, openpyxl). Single `POST /render` endpoint, routes internally by capability type. Heavy compute (video, AI images) delegated to third-party APIs via the same endpoint. Local handlers cover 80%+ of knowledge-worker output types at fixed cost ($7-14/mo). Render cost stays under 3% of Claude API spend at every scale. The adapter interface (`execute(spec) → RuntimeResult`) accommodates capability migration in both directions (local ↔ delegated) without agent-facing changes.

**Capability model**: Capabilities are explicit and curated (not a buffet). Each requires an adapter, cost model, feedback mechanism, and capability guide. SKILL.md (Claude Code's pattern) does not port — capabilities are bounded by the adapter registry, not by instruction files. AGENT.md absorbs capability authorizations. The "skill" term in ADR-109 (digest, monitor, etc.) remains distinct from runtime capabilities.

**Developmental model**: Runtime access follows the same earned-progression as other capabilities (Axiom 3). Templates are ungated (available from day one via Composer scaffolding). Generative runtime dispatch is earned through demonstrated quality. Capability gating starts as a Composer prompt heuristic, not an automated system.

**Implementation priority**: Feedback loop depth over runtime breadth (Axiom 4). One adapter with a working feedback mechanism is more valuable than five adapters with static output. The feedback mechanism for non-text outputs (how users "edit" a PDF) is the hardest and most valuable design problem.

**Phasing**: Text substrate excellence → template parameterization → render service + first capability + feedback loop → capability expansion → ecosystem delegation.

**Decision confidence**: High. All five axiom-derived constraints held under stress testing. Counter-arguments produced refinements (templates ungated, gating as heuristic, monitor ICP shifts) but no directional changes.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-17 | v1 — Initial analysis: skills as capability layer, execution substrate gap, implementation phases |
| 2026-03-17 | v2 — Added runtime implementation paths (self-hosted Lambda vs. third-party API vs. A2A), macro positioning analysis, decision branches, revised implementation phases to reflect API-first approach |
| 2026-03-17 | v3 — First-principles derivation from FOUNDATIONS.md axioms. Each axiom constrains the implementation space: runtime as agent capability (Ax1), output re-enters perception substrate (Ax2), runtime access earned through progression (Ax3), feedback loop depth over runtime breadth (Ax4), zero-config via Composer (Ax6). Revised phasing: templates precede runtime adapters. Upgraded interim decision to high confidence. Removed standalone competitor comparison, folded strategic insight into macro positioning. |
| 2026-03-17 | v4 — Decision validation: stress-tested all five axiom-derived constraints against strongest counter-arguments. Added cost & operational model (runtime <10% marginal cost). Added scalability assessment (no new bottlenecks). Added future-proofing assessment (adapter interface accommodates all foreseeable models). Added Terminology & Capability Model section: resolved SKILL.md vs AGENT.md question (capabilities absorbed by runtime registry, explicit/curated set, SKILL.md doesn't port), glossary alignment. Key refinement: templates are ungated (bootstrap agents use from day one), only generative runtime dispatch is earned. Decision confidence: high. |
| 2026-03-17 | v5 — Infrastructure model revised: hybrid render service replaces pure third-party API orchestration. One self-hosted Render service (`yarnnn-render`) for lightweight capabilities (pandoc, python-pptx, matplotlib, pillow, openpyxl — 80%+ of knowledge-worker outputs), third-party API delegation for heavy compute (video, AI images — Phase 3+). Full re-assessment against code maintenance (one Dockerfile < N API integrations), scalability (stateless, embarrassingly parallel, handles 15-20 capability types), cost projections (fixed $7-14/mo local + variable delegated, <3% of Claude API at all scales, saves $4.6K/yr vs CloudConvert at 10K agents), stability (no external dependencies for core path, blast radius contained for delegated). Branch 1 resolved. Capability classification table added (local vs. delegated with routing heuristic). Phasing updated: Phase 2 deploys render service, Phase 3 expands local handlers + adds first delegated adapter. |
