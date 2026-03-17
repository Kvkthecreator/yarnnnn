# Skills as the Capability Layer: From Text Substrate to General-Purpose Agent Execution

> **Status**: Analysis / Discourse
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

### Decision: Path B now, designed for Path C later

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

Phase 2: First runtime adapter + feedback loop
  └─ One adapter (document conversion: markdown+template → .docx/.pdf)
  └─ workspace_files extended with content_url (S3-backed)
  └─ Feedback mechanism for non-text outputs designed and built
  └─ Capability gating: agents earn RuntimeDispatch via approval history
  └─ Full recursive loop: render → deliver → user feedback → agent learns → better render

Phase 3: Adapter generalization
  └─ Second adapter (image or video rendering)
  └─ Adapter registry formalized (config-driven)
  └─ Cost tracking per-adapter per-agent
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

### Phase 2: First Runtime Adapter + Feedback Loop (Near-term+)

One adapter, end-to-end, with the full feedback mechanism:
- `RuntimeDispatch` primitive added to agent pipeline (adapter-based, ~200 lines)
- First adapter: document conversion (markdown + template → .docx/.pdf) via CloudConvert or minimal Cloud Run
- `workspace_files` extended with `content_url` column (S3-backed binary references)
- **Critical design work**: feedback mechanism for non-text outputs — how does a user "edit" a PDF? Options: annotate, reject with comments, approve with notes, provide text-level edits the agent translates to next render
- Capability gating: agents earn `RuntimeDispatch` access via approval history (Axiom 3)
- Dashboard UI: download link + inline preview
- **Why the feedback loop is the hard part**: Axiom 4 — a rendered output without feedback is a dead artifact. The adapter is 50 lines. The feedback mechanism is the design problem that makes this valuable.
- **Success metric**: an agent produces a formatted .docx weekly report, user provides feedback on it, next week's report is measurably better

### Phase 3: Adapter Generalization (Medium-term — only after Phase 2 feedback loop is proven)

Expand to additional output modalities:
- Second adapter: Remotion Cloud rendering (single-frame images or full video)
- Adapter registry formalized as config (JSON/YAML mapping runtime types to adapter classes)
- Cost tracking per-adapter per-agent (for tier gating)
- Feedback mechanism generalized across output types (some modalities may need different feedback patterns)
- **Gate**: Phase 2's feedback loop must be working and producing measurable improvement before investing in additional adapters
- **Success metric**: an agent produces branded social graphics that improve with user feedback across iterations

### Phase 4: Ecosystem Delegation (Future — monitor, don't build)

If the A2A/MCP ecosystem matures:
- A2A-based adapters alongside API-based adapters
- Agent can delegate to external specialized agents for rendering
- Yarnnn becomes a consumer in the agent ecosystem, not just a provider
- **Trigger**: when at least 2-3 reliable rendering agents exist with stable APIs
- The adapter interface already accommodates this — swap, don't rewrite

---

## Open Questions for Continued Discourse

1. **Skill marketplace**: If skills are infinitely composable, does yarnnn eventually have a skill marketplace? Users (or TP) install skills to expand agent capabilities, analogous to Claude Code's skill ecosystem.

2. **Runtime cost model**: Who pays for Lambda renders? Is this a tier-gated feature? Does the agent need to "budget" its runtime invocations?

3. **Self-assessment for non-text outputs**: How does an agent evaluate whether its video/document/presentation is good? Can it invoke a review runtime (e.g., screenshot the first frame and analyze it) before delivering?

4. **Template vs. generative**: Should agents primarily parameterize templates (safer, more predictable) or generate from scratch (more flexible, less predictable)? Is this a per-skill decision or a platform-wide stance?

5. **Skill authoring**: Who writes skills? If users can author skills (like Claude Code users can write SKILL.md files), the platform becomes extensible by users, not just by engineering. This maps to the "workspace IS identity" thesis from ADR-116.

6. **Cross-agent skill sharing**: Can one agent's skill be readable by another? A "video" agent could read a "brand" agent's workspace to understand visual guidelines. This is already possible via ReadAgentContext (ADR-116 Phase 3) but the skill-awareness dimension is new.

---

## Decision Branches (Active)

Documenting the thought branches that remain open. These should be revisited as implementation progresses.

### Branch 1: Build vs. Buy for first runtime

**Option A**: Minimal Cloud Run service with pandoc (self-hosted, ~$5/mo on Render)
- Pro: No third-party dependency, full control, no per-call cost
- Con: Another service to maintain, deploy, monitor

**Option B**: CloudConvert API ($0.01/conversion, hosted)
- Pro: Zero maintenance, battle-tested, supports 200+ formats
- Con: Per-call cost, external dependency

**Leaning**: Option B for speed of proof, with the understanding that the adapter interface makes swapping trivial. Don't over-invest in infrastructure before validating that users want formatted outputs.

### Branch 2: Template-first vs. generative-first

**Option A**: Agents parameterize pre-built templates (safer, more brand-consistent)
**Option B**: Agents generate artifacts from scratch (more flexible, less predictable)

**Leaning**: Template-first. The Remotion video templates and the brand design system already exist. Agents choosing the right template + filling parameters is a higher-confidence path than agents writing React from scratch. Generative can be layered on for advanced/mature agents.

### Branch 3: When to expose this to users

**Option A**: Build runtime dispatch as internal infrastructure, expose gradually
**Option B**: Ship it as a visible feature ("your agents can now produce documents/videos")

**Leaning**: Option A first. Prove the pipeline works end-to-end with one agent type (e.g., weekly report as .docx). Once reliable, surface it as a capability users can see and request.

### Branch 4: Autonomous creative production pipeline

The runtime layer + existing content strategy + autonomous agents = a system that could produce blog posts, cross-posts, social graphics, video clips, and email sequences autonomously, improving with tenure. The differentiator from existing AI content tools is quality through accumulated understanding, not volume through generation.

**Not deciding this now.** Documenting the trajectory. The skills + runtime architecture makes this possible without additional conceptual work — it's a product positioning decision, not a technical one.

---

## Summary

The insight is correct: skills are the indefinitely expandable capability layer, and the pattern already works for yarnnn's text substrate. The gaps are in execution (runtime dispatch) and delivery (binary output handling), not in the skill model itself.

**Key reframe from discourse**: the runtime layer does not require self-hosted infrastructure. Third-party APIs provide the same execution substrate via API calls — the same pattern yarnnn already uses for platform sync. The dispatch primitive is an adapter interface that can swap implementations without changing the agent-facing contract.

**Key derivation from first principles**: the axioms converge on a specific approach that is more constrained than "just add API adapters." Runtime dispatch is an agent capability earned through feedback-gated progression, not a platform-wide feature. The implementation priority is feedback loop depth over runtime breadth. Templates precede rendering. The user never configures runtimes — Composer scaffolds agents with appropriate capabilities.

**Macro positioning**: yarnnn evolves toward a cloud-native agent platform with indefinitely expandable output modalities. The differentiator from Claude Code/OpenClaw is that capability expansion follows a developmental model (agents earn capabilities through tenure) rather than a stateless model (install skill, use immediately). The differentiator from AI content generators is quality through accumulated understanding rather than volume through generation.

**Interim decision (high confidence)**: Proceed with the axiom-derived phasing — text substrate excellence → template parameterization → first runtime adapter with full feedback loop → adapter generalization → ecosystem delegation. Path B (third-party API orchestration) for adapters when they arrive. The feedback mechanism for non-text outputs is the hardest and most valuable design problem; solve it before scaling runtimes.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-17 | v1 — Initial analysis: skills as capability layer, execution substrate gap, implementation phases |
| 2026-03-17 | v2 — Added runtime implementation paths (self-hosted Lambda vs. third-party API vs. A2A), macro positioning analysis, decision branches, revised implementation phases to reflect API-first approach |
| 2026-03-17 | v3 — First-principles derivation from FOUNDATIONS.md axioms. Each axiom constrains the implementation space: runtime as agent capability (Ax1), output re-enters perception substrate (Ax2), runtime access earned through progression (Ax3), feedback loop depth over runtime breadth (Ax4), zero-config via Composer (Ax6). Revised phasing: templates precede runtime adapters. Upgraded interim decision to high confidence. Removed standalone competitor comparison, folded strategic insight into macro positioning. |
