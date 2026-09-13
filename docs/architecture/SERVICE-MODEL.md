# YARNNN Service Model

> **Status**: Canonical
> **Version**: v3.0 (2026-09-12 — the post-steward recut, ADR-596/603/632/639/642; v2.1 archived verbatim at [previous_versions/SERVICE-MODEL-v2.1-2026-09-12.md](previous_versions/SERVICE-MODEL-v2.1-2026-09-12.md))
> **Scope**: End-to-end — how the system works, from a member's intent to the work that lands in the commons and the work that leaves it.
> **Rule**: This is the single document that describes the complete system. Deep-dive docs are linked, not duplicated.

> **Recut (2026-09-12).** v2.1 still described the steward era end to end — five wake sources through a funnel into a Reviewer's Loop, recurrences and hooks, back-office tasks, the five-destination cockpit, production roles. All of it is deleted (ADR-603 D5, ADR-632). The framing that survives — the six dimensions, the filesystem as the substrate, the OS layering, the acts over a commons — is restated below on the live system.

---

## What YARNNN is

YARNNN is **the system of record where human and AI work settles** ([ESSENCE](../ESSENCE.md)). A workspace is a multi-principal commons — the owner, invited members, their AI connections over the interop face, and the agents they work with — where every contribution lands as an attributed, parent-pointered revision on one ledger. Engines are fungible; the accumulated, attributed memory is not.

The felt product is **a desk of acts over a commons that remembers** (FOUNDATIONS DP29; ADR-507). The acts are media, each hosting apps, and neither list is closed:

- **Think** — dialogue: **Chat**, the member's lanes (ADR-411/558) — workspace-scoped, grounded, multi-engine.
- **Make** — the artifact: **Text · Slides · Images · Blogger** (ADR-571/599/633/627), each a pane over one artifact type with its resident agent beside the canvas.
- **Perceive** — the world arriving: **Reach** (ADR-642), the boundary's door, and the captures that land observations in the commons (ADR-582).

*Words for exploring, hands for shaping, attention for what arrives.* There is no pipeline between them; the commons is the shared medium. **Files** is the record's mirror, **Notifications** carries attention (ADR-605/639), **Settings** is the management plane — real, but not acts. **Nothing acts on its own initiative**: an agent works in a member's lane or on a member's standing declaration, and that is the whole of unattended work (ADR-632/603).

**The two layers, kept distinct** (ESSENCE v16): the record is the moat; the desk is the product. The ledger is felt at staged moments — *trace* (why is this here) · *correct once, everything inherits* · *leave with everything* (the git export, ADR-328 D4) — never as the ambient experience.

**The product thesis**: work here is cumulative. Every correction, every authored file, every thought that lands as a file raises the floor the next act starts from. An agent is a colleague met through a lane — identity, character, engine, and nothing else (ADR-596); authority is a grant, never a property of the agent.

---

## Architectural preamble

### Frame 1 — the six dimensions (Axiom 0)

Every mechanic occupies a cell in six orthogonal dimensions — **Substrate** (what persists) · **Identity** (who acts) · **Purpose** (why) · **Trigger** (when) · **Mechanism** (how — deterministic code to judgment) · **Channel** (where output goes). A mechanic that spans dimensions without justification is a design error ([FOUNDATIONS Axiom 0](FOUNDATIONS.md)).

### Frame 2 — the filesystem is the substrate (Axiom 1)

The filesystem holds all semantic state; every other layer is stateless computation over it. A lane turn, a standing run, a capture, the mirrors, the compose engine — each reads the filesystem, acts, writes the filesystem, terminates. Accumulation happens in files, revision over revision.

The database is permitted for a few row kinds only:

1. **Grants** — who may reach what (`principal_grants`, the one authorization table; ADR-373/517).
2. **Scheduling index** — when standing work and captures are due (`tasks` survives as the drain's due-time index until dropped — ADR-632 §3; `platform_connections` carries a capture's schedule).
3. **Audit ledgers** — what happened, for billing and legibility (`execution_events`, `token_usage`, `activity_log`). No semantic content.
4. **Credentials** — encrypted secrets the filesystem cannot hold (`platform_connections`, `mcp_oauth_*`; keyed by the human, ADR-577).
5. **Queues** — items awaiting a member's decision (`action_proposals`, ADR-307).
6. **Member experience** — one member's private operating state (`chat_sessions` · `session_messages` · `member_state`; never consulted for authorization, never holding authored content — ADR-407).

Anything else belongs in the filesystem ([FOUNDATIONS Axiom 1](FOUNDATIONS.md); [WORKSPACE.md](WORKSPACE.md)).

### Frame 3 — the desktop (ADR-297)

The member works inside YARNNN on a windowed desktop: surfaces are windows over substrate, one window manager, `HOME_ROUTE = /desktop`, Chat the default landing (ADR-435). The live roster is `KERNEL_SURFACES`; the contracts are in [docs/design/WORKSPACE.md](../design/WORKSPACE.md). External channels are derivative: what leaves the workspace leaves on the member's click, receipted (ADR-628).

### Frame 4 — invocation as the atom; two trigger shapes (Axioms 4 and 9)

One cycle of the six dimensions is an **invocation**. There are exactly two trigger shapes (FOUNDATIONS Axiom 4 v10): an **attended** turn — a member's message in a lane — and an **unattended** run — a member's standing declaration coming due. Every invocation lands on one timeline, attributed by Identity (Notifications → Activity); a standing declaration's runs are that timeline filtered to its kept file, never a second log.

### Frame 5 — the agent-native operating system (ADR-222, DP16)

| OS layer | YARNNN equivalent | Status |
|---|---|---|
| **Kernel** | the filesystem over Postgres, the primitives, the gates, the one drain loop, the mirrors it writes into `system/` | shipped |
| **Filesystem** | `workspace_files` + the authored substrate (ADR-209); binary through the CAS seam (ADR-427) | shipped |
| **Syscall ABI** | the primitive matrix ([primitives-matrix.md](primitives-matrix.md)) | shipped |
| **Shell** | the lane frame (`build_lane_conventions`, [lane-frame.md](lane-frame.md)) — application code over the kernel | shipped |
| **Init** | genesis: `ensure_owner_workspace` mints the row and the owner grant; nothing is seeded (ADR-414 D4/465) | shipped |
| **Applications** | the apps (`register_app`, one `AppDescriptor` each on the client — ADR-562/636) and programs (`docs/programs/{slug}/`, a post-genesis hire — ADR-414 D5) | shipped |
| **Compositor / window manager** | the shell ([compositor.md](compositor.md)) — reads the registries, authors nothing | shipped |
| **Userspace** | a workspace — one multi-principal commons (ADR-373/378) | shipped |
| **Daemons** | the scheduler's three lanes: the kernel skills mirror (ADR-630), capture (ADR-582/591), the standing-work drain (ADR-639) — none gated on a steward flag | shipped |
| **Interop face** | the MCP server — the file-native verbs as a connected LLM's syscalls (ADR-543/545) | shipped |
| **System component library** | `web/components/library/` (ADR-245 L3) | shipped |

Workspaces have no types; they run apps and, optionally, programs. Specialization happens at the app row and the compositor, never in the kernel.

---

## Entity model

| Entity | What it is | Home | Canon |
|---|---|---|---|
| **Workspace** | the binding unit and outermost scope; one attributed commons | `workspaces` + the filesystem | ADR-373/378 |
| **Member** | a human principal with a grant | `principal_grants` | ADR-405/517 |
| **Connected principal** | an LLM acting as the member over the interop face, under a token stamped with scopes and a workspace | `mcp_oauth_*` | ADR-563/573/584 |
| **Agent** | identity ⊕ character ⊕ engine; one register; a home of `memory/` + two locked grant sidecars | `AGENTS` (`agents_registry.py`); `agents/{slug}/` | ADR-596/600/624 |
| **App** | an artifact type + its resident + its posture + its stage | `register_app`; `web/lib/apps/registry.ts` | ADR-562/592/636/646 |
| **File / revision** | the substrate; every write an attributed, parent-pointered revision; folders derived | `workspace_files` + `workspace_file_versions` | ADR-209/588 |
| **Lane** | a member's conversation with one agent under the member's grant | `chat_sessions` (member experience) | ADR-411/558 |
| **Standing declaration** | a kept file + a contract + a schedule + sources + the app | `{folder}/_standing.yaml` + `CONTRACT.md` | ADR-603/639 |
| **Connection** | consent + credential + aperture; the member's, keyed `user_id` | `platform_connections` | ADR-577/582/645 |
| **Proposal** | a consequential act awaiting the member's verdict | `action_proposals` | ADR-307/405 |

---

## Execution

### The attended turn

```
member's message in a lane
  → run_lane_turn (api/services/lane_runner.py)
  → the frame: build_lane_conventions (agent-composition.md §3.1) — the cached prefix (ADR-634/647)
  → the tool loop over lane_tool_names(...): the file + folder verbs, the uniform reads,
    the member's turn reach (ADR-615), attached connectors (ADR-635)
  → every write an attributed revision, member:{user_id} via {model} (ADR-209)
  → the timeline; the artifact card; the reply in the member's register (ADR-638)
```

Bounded by the member's grant (one decider, ADR-643), the balance, the read cap and the history ceiling (ADR-648). A binary read of an image lets the lane see (ADR-623).

### The unattended run

```
a standing declaration comes due
  → the ONE drain loop: claim_run · record_run · drain_due (api/services/scheduling.py, ADR-639 D3)
  → build_standing_frame + _STANDING_JOB (agent-composition.md §3.2)
  → run_bounded_derive_turn (api/services/derive_turn.py): toolless, bounded by the pool (ADR-618)
  → the contract check (CONTRACT.md) → a revision attributed system:standing, or an honest no-op
  → a receipt on the timeline; Run now / Pause in Notifications → Standing work
```

A standing run has no outbound reach by design: it is refused a member's credential (ADR-577/645).

### Intake — how the world reaches the commons

`retain → distil → signal → read` ([intake-pipeline.md](intake-pipeline.md)): a capture lands an attributed observation at the fixed intake lane (`inbound/{lane}/{selector}/{stamp}.{ext}`, `system:capture-{platform}`), a derive step distils it citing the raw, judgment reads the distillate. Three dispositions of platform reach, and a proposal declares which: **intake** (durable), **turn reach** (transient, ADR-615), **outbound** (ADR-628). Uploads take the same shape (a raw kept, a text projection derived — ADR-395).

### Outbound — how work leaves

The member's click on the artifact's own pane, through `services/publish.py` (WordPress · Slack, ADR-628): composition refused when it cannot land (D6), reachability recorded (D7), the receipt cites what was read back (D8). Reach → Leaving shows the boundary proposals; Reach → Crossed is the timeline's boundary lens (ADR-642).

### Consequential acts

An agent proposes (`ProposeAction`); the witness dial decides what surfaces before it binds (ADR-405); the member executes or rejects (Reach, Notifications → To do); the verdict is recorded (`judgment_log.py` — the verdict-giver is the member, ADR-632 D2). One gate, one queue (ADR-307).

### Interop

A connected LLM acts as the member through `whoami · open · list · search · save · edit · delete · move · request_upload · history · share` — each a server-side composition over the kernel verbs, under the token's scopes and workspace binding ([docs/features/mcp/README.md](../features/mcp/README.md)).

---

## How outputs are produced

An artifact declares its type in its own bytes (`data-template`); a layout row declares the owning app; the server scopes which types an app opens (`kinds_for_app`, ADR-473/646). The apps' residents author through the ordinary verbs at the artifact's grain (a judged act — ADR-612/613/620). The in-API **compose engine** (`services/compose/engine.py`, ADR-417) turns sections into styled HTML; **generation is rented, not owned** — there is no asset engine, `GenerateImage` calls a provider (ADR-568). What leaves is published on the member's click (above); the whole workspace leaves as a git repository with history and attribution (`GET /api/workspace/export`, ADR-328 D4/510).

---

## Deployed services

Three services on Render, each stateless over Supabase (Postgres); the frontend is Next.js on Vercel.

| Service | Type | What it does |
|---|---|---|
| **yarnnn-api** | web (FastAPI) | every member-facing operation: the lanes, the file routes, OAuth, publish, proposals, the compose engine |
| **yarnnn-unified-scheduler** | cron (`*/5`) | the three lanes: the kernel skills mirror (ADR-630) · capture (`CAPTURE_LANE_ENABLED`, ADR-582) · the standing-work drain (ADR-639, bounded by ADR-618); hourly a heartbeat row. No wake queue, no hook walker, no steward gate (ADR-632). |
| **yarnnn-mcp-server** | web (FastAPI) | the interop face — OAuth 2.1 + a static bearer fallback (ADR-075), scopes (ADR-563), workspace binding (ADR-573) |

Shared state and env-var parity are in CLAUDE.md § Render parity. Retired: the render service (ADR-417), the platform-sync service (ADR-153).

---

## Primitives

The verb-level reference is [primitives-matrix.md](primitives-matrix.md). In one line: a lane holds the file + folder verbs and four uniform reads, plus the member's own reach; interop holds the eleven composed verbs; a standing run holds nothing; the desktop calls the same handlers by click. Who holds a verb is a fact about the surface, never a roster on the primitive (ADR-467 D4).

---

## Perception

Reality enters only as an attributed observation (DP27/32): captures on a connection's schedule (ADR-582/591), uploads, and what a member pastes into a lane; the derive step cites the raw. A live read inside a turn (turn reach, ADR-615) is a convenience for the member's question, never the record (FOUNDATIONS Axiom 1, third clause). Attention is derived from the timeline per viewer and never stored (ADR-410/605); the boundary is one surface (Reach, ADR-642).

---

## Billing

One meter, pooled per workspace: seats and the pooled balance (ADR-445), two free seats and a PAYG margin over standing list price (ADR-490) — every engine row in `LANE_MODELS` carries a `_BILLING_RATES` row at list price, never promotional (ADR-559), metered per call into `execution_events`/`token_usage`. The balance is the gate for attended work; unattended spend is bounded by the pool (ADR-618). The prompt, not the engine price, was the cost (ADR-647): the frame is cached, history is clamped oldest-first (ADR-634/648). The content-commerce substrate (ADR-183, [commerce-substrate.md](commerce-substrate.md)) is not a live connector today.

---

## Key files

| Concern | File |
|---|---|
| the lane frame + turn loop | `api/services/lane_runner.py` |
| the unattended run | `api/services/derive_turn.py` · `api/services/standing_work.py` · `api/services/scheduling.py` |
| the substrate | `api/services/authored_substrate.py` · `api/services/workspace.py` · `api/services/primitives/workspace.py` |
| the participant contract | `api/services/workspace_paths.py` |
| the agents · the apps · the engines | `api/services/agents_registry.py` · `api/services/authoring.py` (`register_app`) + `api/services/apps/` · `LANE_MODELS` in `lane_runner.py` |
| reach · connections · credentials | `api/services/reach_status.py` · `api/services/connectors.py` · `api/services/attached_connectors.py` · `api/services/platform_credentials.py` |
| outbound · proposals | `api/services/publish.py` · `api/services/primitives/propose_action.py` + `api/routes/proposals.py` |
| interop | `api/mcp_server/` · `api/services/mcp_composition.py` · `api/services/mcp_scopes.py` |
| the scheduler | `api/jobs/unified_scheduler.py` |
| billing | `api/services/telemetry.py` (`_BILLING_RATES`) · `api/services/budget.py` |
| the client registry · the shell | `web/lib/apps/registry.ts` · `web/components/shell/` |

## Deep-dive references

| Topic | Document |
|---|---|
| First principles | [FOUNDATIONS.md](FOUNDATIONS.md) · [GLOSSARY.md](GLOSSARY.md) · [LAYER-MAPPING.md](LAYER-MAPPING.md) |
| The substrate · the surfaces | [WORKSPACE.md](WORKSPACE.md) · [docs/design/WORKSPACE.md](../design/WORKSPACE.md) · [authored-substrate.md](authored-substrate.md) |
| The frame · composition | [lane-frame.md](lane-frame.md) · [agent-composition.md](agent-composition.md) |
| The verbs | [primitives-matrix.md](primitives-matrix.md) |
| Intake · connectors · reach | [intake-pipeline.md](intake-pipeline.md) · [connectors.md](connectors.md) · [grants-and-reach.md](grants-and-reach.md) |
| The shell | [compositor.md](compositor.md) |
| Interop | [docs/features/mcp/README.md](../features/mcp/README.md) |
| Product | [ESSENCE.md](../ESSENCE.md) · [NARRATIVE.md](../NARRATIVE.md) · [docs/monetization/STRATEGY.md](../monetization/STRATEGY.md) |

---

## Revision history

| Date | Change |
|---|---|
| 2026-03-29 → 2026-07-30 | v1 → v2.1 — the record of the steward era's service model, archived verbatim at previous_versions/SERVICE-MODEL-v2.1-2026-09-12.md. |
| 2026-09-12 | v3.0 — **the post-steward recut (ADR-596/603/632/639/642).** The acts restated over the live apps; the DB row kinds restated (grants, the drain index, ledgers, credentials, queues, member experience); the OS layering table restated (daemons = the scheduler's three lanes; shell = the lane frame; init = genesis); the entity model on workspace · member · connected principal · agent · app · file · lane · standing declaration · connection · proposal; execution as the attended turn, the unattended run, intake, outbound, consequential acts and interop; outputs, services, perception and billing on the live model. The cockpit destinations, the wake/funnel/Loop, recurrences, hooks, back-office tasks, production roles, the ADR-198 surface architecture and the ADR-149 feedback model are in the archive. |
