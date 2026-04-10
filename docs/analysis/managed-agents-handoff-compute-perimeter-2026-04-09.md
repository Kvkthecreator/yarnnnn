# Claude Managed Agents — Handoff, Compute Perimeter, and HTML-Native Outputs

**Date:** 2026-04-09
**Status:** Discourse analysis — not a decision, inputs to a future ADR
**Triggering event:** Anthropic shipped [Claude Managed Agents](https://platform.claude.com/docs/en/managed-agents/overview) — a pre-built, configurable agent harness that runs in Anthropic-managed infrastructure.

---

## 1. What Managed Agents actually is

A hosted agent harness. Four concepts: **Agent** (static config: model + prompt + tools + skills + MCP), **Environment** (container template), **Session** (running instance), **Events** (streamed I/O with interrupt/steer). Built-in tools: Bash, file ops, web search/fetch, MCP. Targeted at long-running async work. Beta-gated (`managed-agents-2026-04-01` header). Skills follow Claude Code `SKILL.md` conventions.

## 2. The honest strategic read

This is a **horizontal land grab by Anthropic into the territory solo founders building "agent platforms" have been occupying**. Agent config, environments, sessions, tool execution, SSE streaming, interrupts, persistent FS, MCP, skills, prompt caching, compaction — all the scaffolding a founder spent nights building is now a POST request. Anyone whose core value prop was "we run the agent loop for you + a nice UI" is in the blast radius.

**But the 1:1 vocabulary convergence is also the strongest external validation YARNNN's architecture has received.** Anthropic's engineers independently drew the same lines:

| YARNNN (ADR-138/140) | Managed Agents |
|---|---|
| Agent (AGENT.md, identity + memory) | Agent (prompt + tools + skills) |
| Workspace / `/tasks/{slug}/` | Environment + Session filesystem |
| Task (TASK.md, mode, cadence) | Session (one task instance) |
| `task_pipeline.execute_task()` loop | Managed harness |
| `agent_runs` audit | Server-side event history |

The model isn't invalidated — it's load-bearing enough that two teams arrived at it independently. What's commoditized is the *harness*. What remains uniquely YARNNN's is the **persistent cross-task, cross-agent accumulating workspace intelligence** (ADR-072 → ADR-151) — something Managed Agents structurally does not provide because Environments are per-session.

The pitch cannot be "we build agents" anymore. The pitch has to be **"we are the accumulating knowledge substrate that makes agents get better with tenure — the harness is commodity, the memory is the product."** Managed Agents' existence makes that contrast *legible*, not harder to tell.

## 3. The handoff question, narrowed

The question that matters is not "should we port YARNNN to Managed Agents." The question is: **"can the reasoning loop move to Managed Agents while the compute loop stays in `yarnnn-render`?"**

### 3a. Cost structure of a handoff

Token costs are roughly a wash (same Anthropic pricing either way, possibly slight gains from their built-in caching + compaction). The real savings are in:

- **Infrastructure bills:** Potentially eliminating `yarnnn-render` and thinning `yarnnn-unified-scheduler` to a dispatch-only service.
- **Engineering time:** `task_pipeline.execute_task()`, `agent_execution.py`, scheduler dispatch logic, skill runners, output gateway auth — chunks of these become thin wrappers over Sessions calls.

**The thing that gets worse:** per-session container metering. Every task run spins up container time Anthropic bills. For a workspace running 10 tasks/day, that's ~300 session-hours/month of container billing YARNNN does not have today. Crossover vs. Render Docker depends on pricing not yet public.

### 3b. "Dedicated agents" — not a thing

A Managed **Agent** is static config, not a running process. Mapping:

- **YARNNN's persistent agent identity (AGENT.md, memory, accumulated context)** stays in YARNNN's workspace substrate.
- **~8 global Managed Agent configs** correspond to YARNNN's ADR-140 roster types (competitive_intelligence, market_research, etc.), shared across all users.
- **Per-task Sessions** are ephemeral workers that spin up, read what they need via MCP, do the job, write results back, tear down.

No per-user agent provisioning. What YARNNN builds is a **Session lifecycle manager** (~200 lines replacing most of `task_pipeline.execute_task()`): open Session, stream events, handle interrupts, write output to `workspace_files`, close Session, record to `agent_runs`.

### 3c. Data mapping — clean with two sharp edges

Clean parts:

| YARNNN concept | Managed Agents equivalent |
|---|---|
| TASK.md (objective, mode, output spec) | Session initial user message + system prompt |
| AGENT.md (identity, domain) | Managed Agent system prompt + per-Session prefix |
| `/workspace/context/{domain}/` reads | MCP `ReadFile` / `SearchEntities` tools |
| Agent output (markdown + assets) | Session final output event → written to `workspace_files` |
| Feedback loop (ADR-117/149) | Next Session reads prior `feedback.md` via MCP |

**Sharp edge 1 — context-window economics.** Today `gather_task_context()` runs in Python with surgical control over what's injected. Under Sessions, the LLM makes gathering decisions via MCP tool calls, which means more round-trips and more tokens. ADR-159 (filesystem-as-memory, compact index + on-demand reads) was designed for exactly this model, so YARNNN is architecturally ready — but watch for cost regression from chatty sessions doing 8 MCP reads where Python did 1 bulk inject. Tunable but real work.

**Sharp edge 2 — post-generation Python logic.** ADR-149 mode-specific behavior (recurring auto-delivers, goal evaluates→steers→completes), ADR-162 inference-meta comment injection — these are today Python branches after generation. Under Sessions they have to live either in the lifecycle manager (post-Session Python, fine) or as prompt instructions (less reliable). Not a blocker, just work that gets explicit.

### 3d. Skills handoff — depends on Environment flexibility

Unknown until Managed Agents' Environment customization docs are read. Three scenarios:

1. **Environments support arbitrary pre-installed deps.** Port skills verbatim, `yarnnn-render` can die.
2. **Constrained skill format** (limited languages, no custom envs in beta). Heavy skills (pandoc, XLSX formulas, Remotion) stay in `yarnnn-render` as an MCP service; light skills (mermaid, basic charts) move to Managed Agents.
3. **Semantic mismatch** despite shared `SKILL.md` naming. Keep `yarnnn-render` entirely.

**Do not commit to a handoff architecture before answering this. It's a 1-hour docs read that determines whether `yarnnn-render` survives.**

## 4. Compute perimeter — the core framing

The sharpest lens on this whole discussion: **`render/skills/` is internalized compute.** `yarnnn-render` is a private VM YARNNN owns, pre-loaded with pandoc + python-pptx + openpyxl + matplotlib + pillow, exposing bounded verbs (the 8 `SKILL.md` folders) as callable capabilities. The capability *contract* is portable (Claude Code conventions) but the *runtime* is YARNNN's.

Managed Agents' Environment is the structurally identical shape from the opposite direction — internalized compute from Anthropic's perspective, which becomes **rented compute perimeter** if YARNNN adopts it. Same capability surface; different ownership of the perimeter.

### Why internal compute wins for this workload, even at scale

The conventional wisdom ("managed is cheaper until you're huge") is **wrong for artifact rendering** specifically. Three reasons:

**1. Amortization shape.** `yarnnn-render` is warm, multi-tenant, sublinear. One container, one pandoc install, one loaded Python interpreter serving every call across every user. Marginal cost of the 1,000th call ≈ 0. Scales with *peak concurrency*, not total volume. A Managed Agents Environment is per-Session, linear — every Session pays for container lifecycle (cold start, image pull, FS init, network attach). For short, frequent calls like artifact rendering, the curves cross *fast* — possibly at the tens-of-users level, not the tens-of-thousands.

**2. Locality.** `yarnnn-render` lives next to Supabase, storage, and MCP inside Render's network. A render call is three fast local hops. A remote Session calling back to YARNNN's MCP crosses the public internet twice with TLS handshakes and potential auth round-trips. At recurring-knowledge-work baseline load, latency *and* egress costs differ meaningfully.

**3. Determinism.** YARNNN controls pandoc version, fonts, template directory, package versions. Bit-identical output for bit-identical input. Anthropic updating their Environment image on their schedule could silently change output — new pandoc version, new font fallback, new matplotlib palette. For deterministic artifact production (IR decks compared quarter-over-quarter), that's a real cost even off-line-item.

**The one case where managed wins:** bursty, low-baseline workloads. If YARNNN had 100 users each rendering twice a month, idle `yarnnn-render` capacity would dominate. But recurring knowledge work is compounding baseline load — amortization works in YARNNN's favor from day one.

**Conclusion: The bet on `yarnnn-render` as internalized compute was correct. Managed Agents does not change the calculus — it *validates* it by showing what the outsourced version would cost in control, determinism, and round-trips.**

### The resulting architecture

**Anthropic runs the brain; YARNNN runs the hands.**

- **Reasoning loop** → potentially portable to Managed Agents Sessions (mount YARNNN's MCP; Session reads context, generates, writes results back).
- **Compute loop** → stays in `yarnnn-render`, exposed as MCP tools (`render_pdf`, `render_xlsx`, `render_pptx`, etc.) that Sessions call when they need artifact production.

`yarnnn-render` is already behind `RuntimeDispatch` with shared-secret auth (ADR-118 D.2) — wrapping it as an MCP tool surface is straightforward. This preserves the two things YARNNN cares most about (accumulation substrate + deterministic artifact compute) on YARNNN's side of the perimeter, while offloading the part that's genuinely commoditized (the agent loop).

## 5. The downstream consideration — HTML-native task outputs

A separate but related architectural move: **what if the output of a task isn't a document, but a page?**

Modern investor reports, IR decks, analyst dashboards aren't really PDFs anymore. The PDF is the *export*; the artifact is a living page with embedded charts, layout-aware images, diagrams, possibly video, possibly interactive filters. Reverse-engineering an existing IR deck forces this framing: you can't faithfully reproduce that artifact as a markdown document and export it. You have to reproduce it as a page.

ADR-130's HTML-native bet was already gesturing at this. The framing extends: **HTML isn't just a composition format, it's the delivery surface.** The task output *is* a page in YARNNN's web app. The document (PDF/DOCX export) is a *flattening* of that page into a static container when someone needs to download or email it.

### Implications if YARNNN takes this seriously

**1. The compute perimeter for HTML-native outputs is different.** PDF/XLSX/PPTX rendering needs heavy, deterministic offline compute (pandoc, LaTeX, font rasterization, page layout) — that's `yarnnn-render`. HTML rendering is basically free — it's React components with data, running on the main web service that already renders every other page. For HTML-native outputs, the task writes a structured data payload (markdown + chart specs + image URLs + diagram sources + embed refs) into `workspace_files`, and the web app reads that payload and renders it as a page. `yarnnn-render` only engages when the user clicks "Export as PDF."

**2. Task output schema becomes richer.** Today an agent output is a markdown file + manifest (ADR-119). HTML-native outputs need a structured page spec — sections with types (`hero`, `chart`, `narrative`, `comparison_grid`, `timeline`, `embed`), each with a typed data shape, composable in a layout tree. The "file" becomes a JSON manifest the web app interprets. This is an evolution of ADR-130's compose engine hint — but the implication is bigger than that ADR currently spells out.

**3. Task types gain a new `output_kind`.** ADR-166 established four output kinds (`accumulates_context`, `produces_deliverable`, `external_action`, `system_maintenance`). HTML-native outputs are a fifth shape — call it `rich_page` — or an extension of `produces_deliverable` with a `page_spec` sub-shape. Requires a registry update and probably new task types (`ir-deck-clone`, `investor-dashboard`, `competitive-page`).

**4. New input pipelines.** Reverse-engineering an IR deck involves: vision (reading the source), decomposition (identifying components), regeneration (producing equivalent components from YARNNN's context domains), layout synthesis. Not outside current capability — but a different pipeline shape than "read context, write prose."

**5. The web app becomes part of the compute perimeter.** Today the web app is a *viewer*. For HTML-native outputs, it becomes a *renderer* — final composition happens at view time, not task execution time. Cost win (render once per view against cached data). New coupling between task output format and web component library. Contract versioning required so old outputs still render when components update.

**6. The export story is where it gets hard.** Flattening a page with interactive charts, embedded videos, and responsive layout into a static PDF is genuinely harder than pandoc rendering. Interactive charts → static images (which library, what size, what legend?). Videos → thumbnails or placeholder frames. Responsive → fixed-width. Probably requires a new `yarnnn-render` skill (`page_to_pdf`) based on headless Chromium, not pandoc. This is the place where "HTML-native with derivative exports" stops being a clean slogan and becomes a pile of edge cases.

### Two distinct moves worth separating

**Move A — Compute perimeter decision (near-term, confirmatory).**
Keep `yarnnn-render` as internalized compute for document-shaped outputs. Do not hand this off to Managed Agents. Already-made decision being re-validated. Action: confirm explicitly, then re-read Managed Agents Environment docs to see if the reasoning loop can move to Sessions while `yarnnn-render` stays put as an MCP-exposed service.

**Move B — HTML-native output substrate (larger, strategic).**
Introduce HTML-native task outputs as a first-class output kind, rendered by the main web app rather than a render service. Render service narrows to *exports*. This is a new architectural move, probably an ADR, and it expands what YARNNN can produce into page-shaped artifacts (dashboards, IR decks, living reports). **This is closer to the moat story** — accumulating intelligence → outputs that compound, with pages that update as underlying context domains accumulate, and PDFs as downloadable snapshots. A document is a point-in-time snapshot; a page is a window onto the substrate.

### 5a. What the recent commits suggest the real "render HTML" discussion is

Recent commits make the repo's actual discussion much clearer:

- **The backend is already committed to `output.html` as a first-class artifact.** `task_pipeline.py` now composes HTML in both single-step and multi-step paths after generation, copies `output.html` into the task workspace, and uses task-type `layout_mode` to choose the composition strategy. That's the ADR-130/148 line made real in code.
- **The frontend still treats composed HTML as the primary deliverable surface.** `DeliverableMiddle.tsx` renders `latest.html_content` in a sandboxed `iframe` and only falls back to markdown when HTML is missing.
- **The newest UI commits are not reopening the HTML bet.** The `7704fdf` and `f7cc99b` ADR-167 amendments are about *containment and hierarchy*: the rendered output often has its own internal `<h1>`, so the surface chrome cannot also behave like a competing title. Hence PageHeader becomes pure breadcrumb chrome, SurfaceIdentityHeader becomes the real page title, and the HTML output gets framed as a nested document.

So the live question is not "should YARNNN render HTML?" That's already answered. The live question is **"what kind of thing is that HTML inside the surface?"** The recent answer is: a task-produced document embedded inside a higher-order application surface.

### 5b. The useful distinction: compose-time HTML vs. view-time page rendering

There are actually **two different ideas** getting conflated under "render HTML":

**1. Compose-time HTML (current system).** Agent writes `output.md` + assets. YARNNN composes that into `output.html` in `yarnnn-render`. The web app displays that finished artifact in an iframe. This is the current document-shaped pipeline.

**2. View-time page rendering (future rich-page idea).** Task writes a typed page spec or structured payload. The web app renders React components directly at view time. HTML is no longer a stored finished document; it's the browser result of the web app interpreting structured task output.

This distinction matters because Managed Agents only threatens the first half of the flow differently than the second:

- For **compose-time HTML**, the handoff seam is clean: Managed Agent can generate the structured source, while YARNNN keeps post-generation compose + export.
- For **view-time page rendering**, the main web app is itself part of the compute perimeter. That is even less portable to Anthropic-managed infrastructure, because the contract now lives in YARNNN's component library and routing/UI model, not just in a render container.

### 5c. One repo tension worth naming explicitly

The docs currently describe a stronger "singular rendering path" than the code quite enforces.

- ADR-148 and `SERVICE-MODEL.md` say the app "always" shows `output.html` and that markdown fallback is gone.
- The actual surface implementation still has a markdown fallback when `output.html` is absent.

That means the current truth is **HTML-primary, not HTML-exclusive**. That's probably the correct operational stance today, but it's worth naming because any future ADR about Managed Agents or `rich_page` outputs should not assume the stricter invariant has already been fully enforced.

## 6. Discourse conclusions (2026-04-10)

### Move B resolved into ADR-170: Compose Substrate

The extended discourse on Move B reached a foundational conclusion: the compose substrate is **axiomatic** — it is the layer that makes the accumulation thesis (FOUNDATIONS Axiom 2) manifest in output. It warrants its own architectural domain within the service model, comparable to how the render service or the task pipeline are distinct domains.

Key insights that emerged through discourse:

**The filesystem is relational and accumulating.** Directories are scoped context. Each producer run adds deposits. The net direction is growth. Synthesizer agents compose against progressively richer substrate. Assets created or scraped in one cycle are discoverable in the next. The compose substrate is the layer that queries this accumulating structure and projects it into deliverable sections.

**The compose playbook (`sys_compose.md`) replaces the JSON page spec.** Following YARNNN's existing playbook conventions (task process, agent playbooks), the structural knowledge is expressed as markdown — human-readable, editable, consistent. Created from task type templates, refinable by TP or user.

**Output is a folder, not a file.** The deliverable is a directory: `index.html` + section partials + assets + data + manifest. This makes revision structurally targetable: swap an asset, regenerate a section partial, recompose the index — without regenerating the whole output. The folder structure can in theory be served as its own standalone page or even app.

**Two kinds of assets: root and derivative.** Root assets (logos, screenshots) are durable and change rarely. Derivative assets (charts, diagrams) are generated from source data. Both can be refreshed without regenerating prose. The distinction also enables the static→live spectrum (compose-time render vs view-time render).

**Evaluation is a separate concern.** The compose substrate binds structure; it does not judge quality. Quality evaluation stays in ADR-149. The compose substrate consumes evaluation signals as revision inputs.

**Four revision types, not one.** Presentation (recompose index), section (regenerate partial), asset (re-render/re-fetch), root context (route upstream to domain re-sync). Only section revision costs LLM tokens.

**`sys_` naming convention** for system-managed compose artifacts distinguishes them from user-authored and agent-authored files.

### Documentation produced

- **ADR-170** (`docs/adr/ADR-170-compose-substrate.md`) — governing decision record
- **Architecture doc** (`docs/architecture/compose-substrate.md`) — canonical reference
- **FOUNDATIONS.md** — Axiom 2 extended with "Composition Is Projection of Accumulation" corollary
- **SERVICE-MODEL.md** — execution flow updated with SCAFFOLD + ASSEMBLE steps
- **output-substrate.md** — pipeline diagram updated with compose substrate phases

### Remaining next steps

1. **Confirm Move A explicitly.** Document in an ADR that `yarnnn-render` stays internalized for the reasons in §4. This is cheap and closes an open question.
2. **Read Managed Agents Environment + Tools docs.** 1-hour research task. Determines whether the reasoning loop can move while `yarnnn-render` stays, and which skills (if any) can port.
3. **Begin ADR-170 Phase 2 implementation.** Create `api/services/compose/` package, implement playbook parsing, scaffold 2-3 task types with `page_structure`.
4. **Update workspace-conventions.md.** Add `sys_` naming convention, output-as-folder structure, root vs derivative asset conventions.
5. **Tighten doc/code alignment on the rendering contract.** Either fully enforce `output.html` as mandatory for deliverable tasks, or update the prose to state the real invariant: HTML-primary with markdown fallback.
6. **Rewrite the positioning.** The pitch is "we are the accumulating knowledge substrate that makes agents get better with tenure." Managed Agents' existence makes this *easier* to tell.

## 7. Related ADRs

- **ADR-072**: Unified Content Layer — accumulation moat thesis (the thing Managed Agents structurally lacks)
- **ADR-118**: Skills as Capability Layer — internalized compute architecture, SKILL.md conventions
- **ADR-130**: HTML-Native Output Substrate — compose engine, asset producers, export pipeline (evolved by ADR-170)
- **ADR-138**: Agents as Work Units — identity/work separation that mirrors Managed Agents' Agent/Session split
- **ADR-140**: Agent Workforce Model — the ~8 global roster types that would map to global Managed Agent configs
- **ADR-141**: Unified Execution Architecture — mechanical scheduling + LLM generation separation (the seam where a handoff would cut)
- **ADR-148**: Output Architecture — pipeline extended by ADR-170 compose substrate
- **ADR-151/152**: Shared Context Domains / Unified Directory Registry — the accumulating workspace that is YARNNN's moat; scope declarations that drive compose assembly
- **ADR-157**: Fetch-Asset Skill — asset discovery absorbed into compose substrate
- **ADR-159**: Filesystem-as-Memory — already the right shape for chatty MCP-driven context gathering
- **ADR-166**: Registry Coherence Pass — output_kind taxonomy drives compose revision routing
- **ADR-170**: Compose Substrate — the foundational ADR produced by this discourse
