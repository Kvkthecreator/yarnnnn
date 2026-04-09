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

## 6. Recommended next steps

1. **Confirm Move A explicitly.** Document in an ADR that `yarnnn-render` stays internalized for the reasons in §4. This is cheap and closes an open question.
2. **Read Managed Agents Environment + Tools docs.** 1-hour research task. Determines whether the reasoning loop can move while `yarnnn-render` stays, and which skills (if any) can port.
3. **Decide on Move B framing.** Is YARNNN's long-term output substrate document-shaped or page-shaped? This is a product question as much as an architecture question. If page-shaped, draft an ADR for `rich_page` output_kind + page spec format + web app rendering contract + export flattening strategy.
4. **Rewrite the positioning.** Independent of architecture: the pitch is no longer "we build agents." It is "we are the accumulating knowledge substrate that makes agents get better with tenure." Managed Agents' existence makes this *easier* to tell by providing the named contrast case.

## 7. Related ADRs

- **ADR-072**: Unified Content Layer — accumulation moat thesis (the thing Managed Agents structurally lacks)
- **ADR-118**: Skills as Capability Layer — internalized compute architecture, SKILL.md conventions
- **ADR-130**: HTML-Native Output Substrate — compose engine, asset producers, export pipeline (seed for Move B)
- **ADR-138**: Agents as Work Units — identity/work separation that mirrors Managed Agents' Agent/Session split
- **ADR-140**: Agent Workforce Model — the ~8 global roster types that would map to global Managed Agent configs
- **ADR-141**: Unified Execution Architecture — mechanical scheduling + LLM generation separation (the seam where a handoff would cut)
- **ADR-151/152**: Shared Context Domains / Unified Directory Registry — the accumulating workspace that is YARNNN's moat
- **ADR-159**: Filesystem-as-Memory — already the right shape for chatty MCP-driven context gathering
- **ADR-166**: Registry Coherence Pass — current output_kind taxonomy that `rich_page` would extend
