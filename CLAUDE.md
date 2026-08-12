# CLAUDE.md - Development Guidelines for YARNNN

This file provides context and guidelines for Claude Code when working on this codebase.

## Project Overview

YARNNN is an **autonomous agent platform for recurring knowledge work**. Persistent AI agents connect to work platforms (Slack, Notion), run on schedule, learn from feedback, and produce outputs that improve with tenure.

**Architecture**: Next.js frontend → FastAPI backend → Supabase (Postgres) → Claude API. Agents (identity) + Tasks (work units) as core model.

> **OS framing note (as of 2026-04-27, ADR-222 + FOUNDATIONS Principle 16)**: YARNNN is canonized as an **agent-native operating system**. The substrate (filesystem + primitives + axioms + privileged daemons) is the **kernel**; the primitive matrix is the **syscall ABI**; the chat agent is the **shell**; workspaces are **userspaces**; programs (alpha-trader, etc.) are **applications** running in userspace; their bundle (`docs/programs/{program}/`) is an `.app`-equivalent (manifest + reference workspace + composition manifest); a **compositor** layer (forthcoming) reads program-shipped composition manifests against substrate to render the cockpit. The kernel boundary is sacred — programs do not modify the kernel; the shell is application code; the compositor reads but never authors. Workspaces don't have "types" — they run programs; the program declaration is the implicit type; specialization happens at the compositor, not the kernel. See [ADR-222](docs/adr/ADR-222-agent-native-operating-system-framing.md) + [FOUNDATIONS Principle 16](docs/architecture/FOUNDATIONS.md) + [GLOSSARY "Operating System Framing"](docs/architecture/GLOSSARY.md) + [docs/programs/](docs/programs/README.md) + [implementation roadmap](docs/architecture/os-framing-implementation-roadmap.md).

> **Surface model note**: the authenticated workspace is an OS desktop of windowed surfaces driven by one
> window manager (`useSurfacePreferences`), with content parsers in `web/lib/content-shapes/` and structured
> affordances in `web/components/library/` (ADR-245's three-layer rendering). **The surface roster churns fast** —
> Home and Channels were both deleted (ADR-435, ADR-415) after long stints in this file. Do not trust a surface
> list written here; read [compositor.md](docs/architecture/compositor.md) and the FE `SurfaceRegistry` for the
> live set. Redirect stubs are pure server transport (`redirect()`, ADR-308) — never `'use client'` + `useEffect`.

> **Vocabulary note (as of 2026-04-24, ADR-216 reframe)**: "Agent" in YARNNN canon means a **persona-bearing judgment entity** — Reviewer and user-authored domain Agents. YARNNN is the **orchestration chat surface**, not an Agent (reclassified by ADR-216 from ADR-212 D1). Production machinery (task pipeline, production roles like Researcher/Writer/etc., platform integrations, YARNNN chat surface) is **Orchestration**, not persona-bearing. See [docs/architecture/LAYER-MAPPING.md](docs/architecture/LAYER-MAPPING.md) + [ADR-216](docs/adr/ADR-216-orchestration-surface-vs-judgment-persona.md) for the authoritative taxonomy. Historical ADR summaries below may use pre-flip vocabulary ("Specialist" / "Platform Bot" as entity terms, or YARNNN-as-Agent); those are historical artifacts preserved verbatim — for current framing read the Key terminology section below.

**Key terminology**

> **[docs/architecture/GLOSSARY.md](docs/architecture/GLOSSARY.md) is authoritative for vocabulary, and it moves.**
> Terms here have been renamed or dissolved repeatedly (Task dissolved by ADR-231; Reviewer relabeled Freddie by
> ADR-381; the YARNNN-vs-Agent split collapsed to one system agent by ADR-414 D3). Check GLOSSARY before using a
> term in code, canon, or operator-facing strings. Deep taxonomy: [LAYER-MAPPING.md](docs/architecture/LAYER-MAPPING.md).

The few that are load-bearing every session:

- **Workspace** — the substrate's binding unit and the outermost scope (ADR-373, ADR-378). One multi-principal
  attributed commons. Not federated to anything above it.
- **Principal** — anyone who attributes into the workspace: the operator, other humans, their AI connections,
  agents. Permission is a **grant** (`principal_grants`), never a species rule (ADR-405).
- **Substrate** — the authored filesystem (`workspace_files` + `workspace_file_versions`). Every mutation is
  attributed and parent-pointered (ADR-209). `write_revision()` is the single write path.
- **Freddie** — the system agent; one per workspace; the rail is its voice (ADR-381, ADR-414 D3). The
  reviewer→freddie rename is **full, in code and data** (ADR-381 D1 as amended — `freddie_agent.py`,
  `invoke_freddie`, the `freddie:` attribution prefix). The *review seat* machinery is NOT renamed
  (`review_rotation.py`, the "review" verb, `ReturnVerdict`) — ADR-315's seat≠occupant boundary holds.
  **"Reviewer" is banned from operator-facing strings** (ADR-410 D4).
- **Mandate** — an agent's declared purpose. Per-agent since ADR-414 D6, not a single workspace-level file.

## The Two Hats: System Editor vs External Developer of the System

YARNNN is an Agent OS. Real operators of YARNNN interact via the cockpit + chat surface; the system runs Reviewer + System Agent + Orchestration + substrate + governance on their behalf. **All of that — every file under `api/`, `web/`, every ADR, every architecture doc, every bundle reference-workspace — is INSIDE the system.** That's the world FOUNDATIONS describes.

There is a separate surface — the **external developer surface** — that exists only because we are still iterating on YARNNN. It comprises the operator-proxy capability (ADR-294), scripted scenarios + evaluations (`docs/evaluations/`, renamed from `docs/observations/` 2026-05-26 per criterion-declaration discipline — see `docs/evaluations/README.md` §"Why 'evaluations' and not 'observations'"), ADR drafts before they ratify, the human developer (KVK), and Claude as a collaborator. **None of this ships to real operators.** It is the toolchain through which YARNNN's canon evolves.

**Two hats. Don't conflate them.**

### Hat A — System Editor

When working in any of these locations, you are editing the system real operators will inherit:
- `api/services/`, `api/agents/`, `api/routes/`, `api/services/primitives/`, `api/scripts/alpha_ops/` (yes — alpha-ops orchestrates real persona workspaces)
- `web/` (frontend cockpit)
- `docs/adr/`, `docs/architecture/`, `docs/programs/{program}/` (canon + bundles)
- `api/prompts/CHANGELOG.md` (LLM-facing behavior)
- Any bundle reference-workspace file (`docs/programs/{program}/reference-workspace/**`)

System-hat discipline:
- Speak in system vocabulary (Reviewer, operator, substrate, gating). Do NOT introduce "developer," "Claude," "observation" as system actors.
- Singular implementation, doc-first ADR amendments, full Render parity check.
- The change ships through git → Render deploy → real operator workspaces.

### Hat B — External Developer of the System

When working in these locations, you are operating the developer toolchain that probes + iterates on the system:
- `api/services/operator_proxy/`, `api/scripts/operator/` (the harness)
- `docs/evaluations/` (scenarios + captures + findings)
- Pre-ratification ADR drafts (after ratification they're system canon)

Developer-hat discipline:
- Speak in evaluation vocabulary (scenarios, expected vs observed, hypotheses, findings).
- A finding here recommends system-side changes; it does not make them. The *fix* lands in Hat A territory.
- Don't introduce concepts that only make sense to developers into the system's vocabulary. If a recommendation requires a new primitive / axiom / ADR, that primitive/axiom/ADR lives in Hat A docs after ratification.

### Crossing hats inside one session

The hat distinction is directional, not ceremonial. The discipline that matters is **substrate-receipts under every load-bearing claim** — revision_ids, execution_event ids, wake_queue ids, reproducible queries. A claim without a receipt is narrative, not evidence; that's the drift the discipline exists to prevent.

When the same session both surfaces a finding and lands the fix: use whichever commit shape produces honest commits. Small + obvious + named in-canon precedent → cross-over in a single commit is fine. Anything that benefits from operator sign-off, multi-module changes, or design discussion → separate commits. The goal is not single-author optimism (same author finds the bug and validates the fix as one indivisible motion); the goal is not commit-counting ceremony either.

### Why the hats matter for autonomy

The Agent-OS aspiration is full autonomy: the Reviewer can take capital actions AND meta-aware-edit every operator-canon file (principles, mandate, risk envelope, ground-truth) on its own initiative, under in-system discipline + audit trail + revertibility. The current ADR-293 lock-set on three governance files (`AUTONOMY.md` + `_autonomy.yaml` + `_token_budget.yaml`) is **current dev-trust state**, not permanent architecture. As we harden the Reviewer's self-amendment discipline through Hat-A edits (validated *via* Hat-B evaluation runs), the lock-set should shrink toward zero.

**Wake architecture (ADR-296 v2, fully Implemented 2026-05-20).** The Reviewer is event-fired, not continuously-running. Five wake sources (`cron_tick | addressed | proposal_arrival | substrate_event | manual_fire`) contribute proposals to one evaluation funnel (`services/wake_evaluation.py`); the Reviewer fires only on escalation. The Reviewer's authority is over **cadence preference** (Schedule) + **standing intent** (WriteFile to `/workspace/review/standing_intent.md`) + **substrate-event hooks** (ManageHook) — NOT over invoking itself. **FireInvocation removed from `REVIEWER_PRIMITIVES` per D3**; FireInvocation remains in `CHAT_PRIMITIVES` for operator-initiated manual fire. Singular invocation gateway: `services/wake.py::submit_wake_proposal(source, payload)` (and `stream_addressed_wake(...)` for the SSE-streaming addressed path). Source-side modules at `services/wake_sources/{cron_tick, addressed, proposal_arrival, substrate_event, manual_fire}.py` are the only sites that wake the Reviewer. Substrate-event hooks at `/workspace/_hooks.yaml` (sibling of `_recurrences.yaml`) — operator/Reviewer declare interest in substrate transitions; scheduler walks recent `workspace_file_versions` against declared hooks at every tick. Telemetry: `execution_events.wake_source` + `funnel_decision` (migration 177) populate at every Reviewer-wake call site. Bundle migrations: alpha-trader `trade-proposal` recurrence dissolved into `signal-evaluation` inline ProposeAction; alpha-author `pre-ship-audit` migrated from `schedule: null` recurrence to `_hooks.yaml` substrate-event hook. **Canon rewrite Implemented (2026-05-20)**: FOUNDATIONS Axiom 2 + Axiom 4 amendments + new Derived Principle 20 (wake-as-irreducible-unit) + GLOSSARY new entries (Wake / Wake source / Wake proposal / Wake evaluation funnel / Hook / ManageHook) + amendments to Recurrence + Pulse + Reviewer + Loop entries + `invocation-and-narrative.md` §2 rewrite (Pulse aligned to wake sources) + `primitives-matrix.md` (ManageHook row + REVIEWER_PRIMITIVES update + mode totals) + SERVICE-MODEL Execution Flow rewrite + 8 ADR status banners (ADR-253/256/260/261/263/274/275/276). See [ADR-296](docs/adr/ADR-296-continuous-judgment-cycle.md) + [implementation scope](docs/architecture/adr296-implementation-scope.md).

**Hat-B is the feedback loop. Hat-A is where the system actually changes.**

If a session is unclear which hat applies, the test is: *would a real operator on a stable YARNNN release see this change?* If yes, Hat A. If no, Hat B. The system's own runtime never references Hat-B artifacts; FOUNDATIONS doesn't mention them; ADRs treat them as out-of-canon. They exist purely as our scaffolding while we build.

## Core Execution Disciplines

### 0. Before Proposing Architectural Changes

**ALWAYS check existing ADRs first** before suggesting new patterns or comparing against external systems:

```bash
# Search for existing decisions on a topic
ls docs/adr/ | grep -i "<topic>"
# Or search ADR content
grep -r "<keyword>" docs/adr/
```

**The per-ADR history lives in [docs/architecture/ADR-LEDGER.md](docs/architecture/ADR-LEDGER.md)** — 139 ADR entries with philosophy notes and supersession chains. It is reference material, read on demand, not loaded every session. Search it before proposing an architectural change.

The load-bearing live canon, if you read nothing else:

- [FOUNDATIONS.md](docs/architecture/FOUNDATIONS.md) — the axioms + derived principles (the spine).
- [GLOSSARY.md](docs/architecture/GLOSSARY.md) — current vocabulary. Terms drift; this is authoritative.
- [ESSENCE.md](docs/ESSENCE.md) — what the product is.
- [ADR-414](docs/adr/ADR-414-the-pure-workspace-genesis-system-agent-program-as-hire.md) — the live frontier umbrella. Read first when touching workspace genesis, agents, or program activation.

If an external system (Claude Code, ChatGPT, etc.) does something differently, check whether YARNNN has an ADR explaining why we chose a different approach.

### 1. Documentation Alongside Code

When refactoring or implementing features:
- Update relevant ADRs with implementation status
- Update `docs/database/ACCESS.md` if schema changes
- Keep inline docstrings current with behavior

### 2. Singular Implementation (No Dual Approaches)

- **Delete legacy code** when replacing with new implementation
- **No backwards-compatibility shims** unless explicitly required for migration
- **One way to do things** - avoid parallel implementations that cause confusion
- If old code is superseded, remove it entirely

### 3. Database Operations

- **SQL execution**: Refer to `docs/database/ACCESS.md` for connection strings
- **Migrations**: Run via psql with the connection string in ACCESS.md
- **Schema verification**: Always verify table/column names match current schema
- **PostgREST cache**: After schema changes, may need Supabase dashboard refresh

### 4. Code Quality Checks

Before completing work:
- **Double-check endpoints**: Verify API routes match frontend calls
- **Column name mismatches**: Ensure code uses current schema (e.g., `platform` not `provider`)
- **Import paths**: Verify all imports resolve correctly

### 5. Render Service Parity

YARNNN runs on **3 Render services** (ADR-083: worker + Redis removed; ADR-153: platform sync removed; ADR-417: output gateway / render service removed). When changing environment variables, secrets, or architectural patterns, check ALL services:

| Service | Type | Render ID |
|---------|------|-----------|
| yarnnn-api | Web Service | `srv-d5sqotcr85hc73dpkqdg` |
| yarnnn-unified-scheduler | Cron Job | `crn-d604uqili9vc73ankvag` |
| yarnnn-mcp-server | Web Service | `srv-d6f4vg1drdic739nli4g` |

All execution is inline — no background worker, no Redis. **ADR-417: the yarnnn-render output gateway (`srv-d6sirjffte5s73f90pfg`, Docker) is decommissioned** — generation is rented, not owned; yarnnn hosts no generation/rendering engine. Asset generation (chart/mermaid/image/video) and file export (PDF/XLSX) are retired; compose (section→HTML) moved in-API as a pure-Python library (`api/services/compose/engine.py`).

**Critical shared env vars** (must be on API + Unified Scheduler):
- `INTEGRATION_ENCRYPTION_KEY` — Fernet key for OAuth token decryption. Scheduler needs it for task execution with platform APIs.
- `NOTION_CLIENT_ID` / `NOTION_CLIENT_SECRET` — needed by Scheduler for task execution with Notion API

**API-only env vars** (not needed on schedulers):
- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` — ADR-147: only needed for OAuth initiation on API. Schedulers use encrypted tokens from DB for sync.

**MCP Server env vars** (separate from above — MCP server uses service key, not user JWTs):
- `SUPABASE_SERVICE_KEY` — Service key for RLS bypass (same as Schedulers)
- `MCP_USER_ID` — User UUID for data scoping (auto-approve OAuth + static bearer fallback)
- `MCP_BEARER_TOKEN` — Static bearer token for Claude Desktop/Code
- `MCP_SERVER_URL` — OAuth issuer URL (defaults to `https://yarnnn-mcp-server.onrender.com`)

**MCP Auth model** (ADR-075): OAuth 2.1 for Claude.ai/ChatGPT (auto-approve, tokens stored in `mcp_oauth_*` tables). Static bearer token fallback for Claude Desktop/Code. See `api/mcp_server/oauth_provider.py`.

**Render service env vars** (ADR-417 — RETIRED): `RENDER_SERVICE_URL` / `RENDER_SERVICE_SECRET` are gone. Nothing reads them; strip from the API + Scheduler dashboards when decommissioning the `srv-d6sirjffte5s73f90pfg` deployment.

**Common mistake**: Adding an env var to the API service but forgetting the Scheduler. The API handles OAuth and stores tokens; Scheduler decrypts and uses them for task execution with platform APIs.

**Impact triggers** — if you change any of these, check the affected services:
| If you change... | Also check... |
|-----------------|--------------|
| Env vars (any) | All 3 services — use Render MCP `update_environment_variables` |
| OAuth flow / token handling | Unified Scheduler (decrypts & uses tokens for task execution) |
| Supabase schema (RPC, tables, RLS) | Unified Scheduler + MCP Server (both use service key) |
| Agent execution / pipeline logic | Unified Scheduler (triggers agent runs via cron) |
| MCP tool definitions / auth | MCP Server (separate service, separate deploy) |

**Note**: Both platforms (Slack, Notion) use Direct API clients — no gateway service needed (ADR-076).

### 6. Git Workflow

- **Commit when appropriate**: Can commit and push when changes are complete and tested
- **Meaningful commits**: Use conventional commit style with ADR references where applicable
- **No force pushes** to main unless explicitly requested

### 7. Progress Tracking

- **Use TodoWrite tool** for multi-step tasks to track progress
- **Share progress** to keep context visible across conversation turns
- **Mark todos complete immediately** after finishing each step

### 8. Hooks (Automated Reminders)

One hook auto-injects context that git can load but a static file cannot.

- **Config**: `.claude/settings.json` (committed, shared)
- **Hook files**: `.claude/hooks/` directory

| Hook | Event | Matcher | Purpose |
|------|-------|---------|---------|
| `session-reorient.sh` | `SessionStart` | `startup\|compact` | Recent git log, uncommitted work, branch, and any active `docs/SESSION-HANDOFF.md` — new sessions and post-compaction |

- **To edit**: update the `.sh` file — no need to touch hook config.
- **Hooks carry dynamic state only.** Static doctrine belongs in this file, which is already loaded; a hook that re-echoes it just costs tokens. Add a per-message hook only for a *repeated* observed failure, not a speculative one.

### 9. File Format Discipline (ADR-254)

Every workspace file has exactly one primary consumer. Format follows the consumer:

| Format | Primary consumer | Rule |
|--------|-----------------|------|
| `.md` (UPPERCASE) | Operator / LLM | Prose docs — `MANDATE.md`, `IDENTITY.md`, `AUTONOMY.md`. Never machine-parsed. |
| `.md` (lowercase) | LLM / append-only | Accumulated narrative — `principles.md`, `decisions.md`, `_performance.md`. Never machine-parsed. |
| `_.yaml` (underscore prefix) | Python code | Machine config/state — `_autonomy.yaml`, `_universe.yaml`, `_principles.yaml`. Always `yaml.safe_load()`. |
| `_.yaml` (recurrence declarations) | Scheduler | `/workspace/_recurrences.yaml` (single flat list per ADR-261 D2) + `/workspace/_hooks.yaml`. The per-shape files (`_spec.yaml`, `_action.yaml`, `_recurring.yaml`, `back-office.yaml`) are DELETED. |
| `.json` | Machine only | Manifests — `sys_manifest.json`. No comments needed. |
| `.html` | Render surface | Composed output artifacts. System-produced. |

**Rules:**
- **No new YAML-frontmatter `.md` files.** `_performance.md` and `OCCUPANT.md` are grandfathered exceptions (machine-written body + LLM reads full content). No new mixed-format files.
- **No hand-rolled frontmatter parsers.** Use `load_workspace_yaml()` from `services.review_policy` for `.yaml` bodies, or `re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)` + `yaml.safe_load()` for frontmatter extraction. No regex line-splitting.
- **Underscore prefix = machine-parsed.** All `_*.yaml` files are machine-parsed config or state. Human edits these to configure; Python reads them at runtime.
- **Integer fields in `.yaml` are ints, not strings.** `ceiling_cents: 20000` not `ceiling_cents: "20000"`. `load_autonomy()` and `load_principles()` now coerce and log on mismatch.

### 10. MCP Servers (Local Setup)

Project-scoped MCP servers wired in `.mcp.json` at the repo root. The file itself contains no secrets — tokens flow in via `${VAR}` shell-env interpolation, so the file is safe to commit.

| Server | Transport | Required env var (parent shell) | Scopes |
|--------|-----------|---------------------------------|--------|
| `sentry` | stdio (`npx @sentry/mcp-server`) | `SENTRY_AUTH_TOKEN` | `org:read`, `project:read`, `event:read`, `team:read` |

- **Token setup**: mint at https://sentry.io/settings/account/api/auth-tokens/, `export SENTRY_AUTH_TOKEN=...` in `~/.zshrc`, `source` it, restart Claude Code.
- **Never paste the token into chat, JSON, or git.** If it leaks, revoke immediately and mint a fresh one — Sentry tokens are shown once at creation.
- **Restart required**: `.mcp.json` changes are read at Claude Code startup, not hot-reloaded.

---

## Prompt Change Protocol

Applies to `api/agents/freddie_agent.py` (the system-authored prompt layer), `api/agents/freddie_agent_sections.py`, and `api/services/primitives/*.py` (tool definitions).

You MUST:
1. Update `api/prompts/CHANGELOG.md` with the change.
2. Note the expected behavior change.
3. Run the size ratchets — `api/test_adr383_trigger_framing_recarved.py` and `api/test_adr323_frame_collapse_finished.py`.

**The prompt layer is ablated, not accreted** (ADR-306, FOUNDATIONS DP22). It went ~36K → ~10K and is held there by CI ceilings. Before adding an instruction:

- **Adding is the last resort.** Rules of judgment belong in `principles.md`; substrate semantics in `_workspace_guide.md`; anything a code gate already enforces needs no prose at all. `docs/architecture/agent-composition.md` §3.2.1 is the singular home for that partition — consult it, don't re-derive it.
- **Only for a repeated, observed failure**, not a speculative one. Say which failure in the CHANGELOG entry.
- **Raising a ceiling requires the same evidence as adding an instruction.** ADR-323's 11.5K→12K bump cites a measured readability win in its own assertion message. A silently raised ceiling is not a ceiling.

### Changelog Format

```markdown
## [YYYY.MM.DD.N] - Description

### Changed
- file.py: What changed and why
- Expected behavior: How this affects YARNNN/tool behavior
```

---

## Key Architecture References

### Reviewer seat — substrate canon + partition-discipline canon

**Canonical homes; do not re-derive, look them up first.** If a session would benefit from understanding what `principles.md` is for, what `IDENTITY.md` carries, what the persona-frame owns, what the seat's six files are, or where the content boundaries live — these are the singular references. Per ADR-315 (2026-06-04) the Reviewer technical canon is split along the seat≠occupant line:

- **[`docs/architecture/reviewer-substrate.md`](docs/architecture/reviewer-substrate.md)** — one-screen index routing to the three docs below. Start here if unsure which to read.
- **[`docs/architecture/reviewer-seat-substrate.md`](docs/architecture/reviewer-seat-substrate.md)** — the **kernel/seat** canon. Six seat files, occupant rotation protocol, calibration trail semantics, delegation vocabulary, prospective-attribution contract with chat surfaces. The seat is substrate. Referenced from ADR-194, 195, 211, 212, 253, 280, 282, 284, 285 + FOUNDATIONS Derived Principle 14.
- **[`docs/architecture/reviewer-occupant.md`](docs/architecture/reviewer-occupant.md)** — the **occupant** canon. The AI agent (`freddie_agent.py`) that fills the seat: occupant classes, `invoke_freddie`, model-by-trigger, persona-frame discipline, how the occupant consumes the contract.
- **[`docs/architecture/reviewer-occupant-contract.md`](docs/architecture/reviewer-occupant-contract.md)** — the **published ABI** (ADR-315). `FreddieContext` / `FreddieOutput` / `FREDDIE_MODEL_IDENTITY` / `invoke_freddie` / the kernel-side envelope assembler (the 2026-06-29 full rename; the doc's ADR-414 banner carries the live names). Defined in `api/agents/occupant_contract.py` (pure data — no LLM runtime; the kernel depends on the contract, never on the occupant impl).
- **[`docs/architecture/agent-composition.md`](docs/architecture/agent-composition.md) §3.2.1** — **the singular enforcement home for the partition between `principles.md` (the rule-set the persona applies) and the persona-frame `_compute_*` sections in `api/agents/freddie_agent.py` (the reasoning posture).** Names the four-field rule shape, the bright-line list of content that does NOT belong in `principles.md` (self-amendment discipline, anti-patterns, fiduciary principle, posture taxonomy, standing-intent contract, cadence-trifecta, wake-context discipline, write authority, voice/narration — all in persona-frame), the conflict-resolution rule (PRECEDENT > principles; persona-frame > principles for reasoning-posture; AUTONOMY ceiling > principles for delegation widening), and a diagnostic test for uncertain content.

**When to consult §3.2.1**: before editing any `docs/programs/{slug}/reference-workspace/review/principles.md` (bundle template); before drafting an ADR that prescribes principles.md content; before adding a `_compute_*` section to `api/agents/freddie_agent.py`; when auditing whether a workspace's `principles.md` has drifted to multi-purpose. Future ADRs that reshape principles.md content **must update §3.2.1 in the same commit** — the partition discipline is enforced at the canon layer, not by re-derivation.

The one-line statement (canonized at `agent-composition.md` §4.2 + §3.2.1): **persona is *how to reason*; mandate is *why we exist*; autonomy is *how far decisions bind*; principles is *what the rules of judgment are*.**

### ADR-064: Unified Memory Service (updated by ADR-156, post-ADR-235)

**Memory is in-session** — YARNNN writes facts proactively via `WriteFile(scope="workspace", path="memory/notes.md", content="...", mode="append")` during conversation. Follows the Claude Code model: memory happens in the moment of learning, not as a batch job. (Pre-ADR-235 used `UpdateContext(target="memory")`.)

- ADR-156: Nightly cron extraction REMOVED. YARNNN writes facts in-session.
- Session summaries: generated inline at session close (chat.py), not by nightly cron.
- Session continuity: YARNNN writes shift notes to AWARENESS.md.
- User can still edit memories directly via Context page.
- Working memory injected into YARNNN prompt is unchanged.

**Key files**:
- `api/services/memory.py` — retained for bulk import only (nightly cron removed)
- `api/services/working_memory.py` — formats memory for prompt injection
- Memory-write guidance now lives in the system agent's frame (`api/agents/freddie_agent.py`); the `agents/prompts/` profile registry is DELETED.
- `docs/features/memory.md` — user-facing docs

### Schema (tables + columns)

**Per-table detail lives in [docs/database/SCHEMA-NOTES.md](docs/database/SCHEMA-NOTES.md)** — current table names, deprecated columns, and the ADR history behind each. Read it on demand; `supabase/migrations/` is authoritative for actual DDL.

The rule that matters every session: **use current names.** `agents` not `deliverables`, `agent_runs` not `deliverable_versions`, `platform_connections` not `user_integrations`. Verify against the live schema before writing a query.

### ADR-077: Platform Sync Overhaul — **SUPERSEDED by ADR-153**

**ADR-153 sunset**: `platform_content` table, `platform_worker.py`, `platform_sync_scheduler.py` all deleted. Platform data now flows through tasks into workspace context domains. Agents call platform APIs live during task execution.

**Preserved infrastructure**: `platform_connections` (OAuth tokens), API clients (`slack_client.py`, `notion_client.py`, `github_client.py`), `sync_registry` (observability), `landscape.py` (source discovery).

### ADR-106: Agent Workspace Architecture

**Virtual filesystem over Postgres** — agents interact with workspace via path-based operations (`read`, `write`, `list`, `search`). Storage-agnostic abstraction layer.

- **Schema**: `workspace_files` table with `path`, `content`, `embedding`, `tags`
- **Path conventions**: `/agents/{slug}/AGENT.md` (like CLAUDE.md), `/agents/{slug}/thesis.md`, `/agents/{slug}/memory/*.md` (topic-scoped), `/knowledge/slack/{channel}/{date}.md`
- **Agent archetypes**: Reporter (platform dump, unchanged), Analyst (workspace-driven search), Researcher (workspace + WebSearch), Operator (future)
- **Key change**: Reasoning agents drive own context gathering from workspace. No pre-gathered platform dump.
- **Replaces**: `agent_memory` JSONB blob, `user_memory` KV pairs (phased migration)
- **Abstraction**: `AgentWorkspace` class — swap backing store without changing agent code

**Key files**:
- `api/services/workspace.py` — AgentWorkspace + KnowledgeBase abstraction
- `api/services/primitives/workspace.py` — ReadWorkspace, WriteWorkspace, SearchWorkspace, QueryKnowledge

### ADR-057: Streamlined Onboarding (updated by ADR-113)

- OAuth callback auto-discovers landscape + auto-selects sources + kicks off sync (ADR-113)
- Redirects to `/orchestrator?provider=X&status=connected`
- Source curation on context pages is optional refinement, not prerequisite
- Tier-gated source limits enforced by `compute_smart_defaults()` max_sources

### ADR-056: Per-Source Sync

- Sync operates per-source (channel, label, page) not per-platform
- `integration_import_jobs` — DEPRECATED (ADR-153 + ADR-156: import jobs sunset, platform data flows through task execution)

---

## File Locations

| Concern | Location |
|---------|----------|
| System agent (prompt + loop) | `api/agents/freddie_agent.py` — the single system agent per ADR-414 D3. `_compute_minimal_frame()` is the whole system-authored prompt layer (size-ratcheted; see `api/test_adr383_trigger_framing_recarved.py`). Sections in `freddie_agent_sections.py`; published ABI in `occupant_contract.py`. The old YARNNN/orchestration split, `agents/prompts/` profile registry, and `routes/chat.py` resolver are all DELETED. |
| Tool Primitives (code) | `api/services/primitives/*.py` — canonical registry in `registry.py` |
| Tool Primitives (canonical doc) | `docs/architecture/primitives-matrix.md` (ADR-168) — substrate × mode × capability matrix, rename protocol, deleted primitives ledger |
| Memory Service | `api/services/memory.py` |
| Working Memory | `api/services/working_memory.py` |
| Chat/Streaming | `api/services/anthropic.py` |
| OAuth Flow | `api/integrations/core/oauth.py` |
| **Workspace (canonical doc)** | `docs/architecture/WORKSPACE.md` — layers, filesystem inventory, 5-phase bootstrap, autonomy threshold. Paired with `docs/design/WORKSPACE.md` (per-tab surface contracts). **Start here for anything substrate/init/onboarding/bootstrap/autonomy-threshold.** |
| Workspace Initialization | `api/services/workspace_init.py` — `initialize_workspace()` (5 phases: YARNNN row → skeletons → narrative session → balance audit → optional fork). Called by `GET /api/workspace/state` (lazy scaffold), `DELETE /account/workspace` (L2), `DELETE /account/reset` (L4). |
| Workspace Path Constants | `api/services/workspace_paths.py` — `SHARED_CONTEXT_FILES` (kernel-seeded set: MANDATE, IDENTITY, BRAND, AUTONOMY, PRECEDENT). `SHARED_CONVENTIONS_PATH` kept as a constant but **not in `SHARED_CONTEXT_FILES`** — CONVENTIONS is program-scoped. |
| Workspace Utilities | `api/services/workspace_utils.py` — `is_skeleton_content()` + `classify_file_state()`. Single source of truth for skeleton detection (used by init, workspace state surface, and activation state classifier). |
| Program Lifecycle (fork) | `api/services/programs.py` — `fork_reference_workspace()`, `_strip_tier_frontmatter()`, `parse_active_program_slug()`, `strip_program_marker_from_mandate()`. Bundle fork logic is here, not in workspace_init. |
| Back-Office Lifecycle | `materialize_back_office_task()` lives in `api/services/workspace_init.py`; the `services/back_office/` package is DELETED (ADR-260/261). |
| Agent Workspace | `api/services/workspace.py` (ADR-106) |
| Workspace Primitives | `api/services/primitives/workspace.py` (ADR-106) |
| Authored Substrate (ADR-209) | `api/services/authored_substrate.py` — `write_revision()` is the single write path for every `workspace_files` content-layer mutation. Also `list_revisions()`, `read_revision()`, `count_revisions()`, `is_valid_author()`. **Phase 5 (2026-04-23) — ADR CLOSED**: Migration 159 dropped `workspace_files.version`, tightened lifecycle constraint (`archived` enum value removed), deleted residual `/history/` artifact row. `workspace_files.content` denormalization retained after measurement (FTS + embedding indexes require it). Permanent CI regression guard `api/test_adr209_no_filename_versioning.py` (12 banned-pattern checks with allowlist). Branches + distributed replication explicitly out of scope per D10 + authored-substrate.md §7. **Phase 4 (2026-04-23)** adds HTTP revision endpoints, optional `message` field on `PATCH /api/workspace/file`, new `web/components/workspace/RevisionHistoryPanel.tsx` wired into BrandSection / TaskContentView / AgentContentView. `_append_inference_meta` schema simplified (dropped `inferred_at`). `save_identity` / `save_brand` routes now pass explicit `authored_by="operator"`. **Phase 3 (2026-04-23)** adds read-side primitives at `api/services/primitives/revisions.py`: `ListRevisions` / `ReadRevision` / `DiffRevisions` (chat + headless; NOT MCP — ADR-169 intent-shape). `ListFiles` extended with `authored_by`/`since`/`until` filters. `working_memory._get_recent_authorship_sync()` + one-line activity summary in compact index. "Revision-Aware Reading" posture in `yarnnn_prompts/tools_core.py` (dir since DELETED — ADR-414 D3). **Phases 1–2 (2026-04-23, caller list is that date's snapshot — several callers since deleted)**: every caller in `services/workspace.py`, `services/task_workspace.py`, `services/reviewer_audit.py`, `services/primitives/workspace.py`, `services/primitives/runtime_dispatch.py`, `services/outcomes/ledger.py`, and `routes/{documents,chat,workspace,integrations}.py` routes through `write_revision`. `/history/` subfolder convention, `_archive_to_history`, `_cap_history`, `_is_evolving_file`, `list_history`, ADR-176 Phase 4 entity-profile `v{N}.md` archive all DELETED. Permitted direct-mutation exceptions (2): `authored_substrate._upsert_workspace_file` (the write target) and `primitives/workspace._embed_workspace_file` (metadata-only embedding update). Test gates: Phase 1 (11/11) + Phase 2 (14/14) + Phase 3 (15/15) + Phase 4 (13/13) + Phase 5 (12/12) = **65/65**. |
| Agent Framework (canonical) | [docs/architecture/orchestration.md](docs/architecture/orchestration.md) + [agent-composition.md](docs/architecture/agent-composition.md) |
| Directory Registry | `api/services/directory_registry.py` (ADR-152: WORKSPACE_DIRECTORIES — context domains, uploads, output categories) |
| Agent Framework (code) | `api/services/orchestration.py` (ADR-140 + ADR-166: workforce roster, AGENT_TEMPLATES, DEFAULT_ROSTER, capabilities, runtimes, PLAYBOOK_METADATA, TASK_OUTPUT_PLAYBOOK_ROUTING) |
| Agent Playbook Framework | `docs/features/agent-playbook-framework.md` (playbook loading, selective injection, governing axioms) |
| Agent Creation (shared) | `api/services/agent_creation.py` (ADR-111 Phase 1) |
| YARNNN Composer / Heartbeat | DELETED (ADR-156 — Composer sunset, single intelligence layer) |
| Agent Pulse Engine | DELETED (ADR-141: dissolved into scheduler SQL + task pipeline) |
| Invocation Dispatcher | DELETED (ADR-260/261 + ADR-296). Wakes route through `api/services/wake.py` → `wake_drainer.py`. |
| Dispatch Helpers | DELETED (ADR-260/261). Sub-LLM calls go through `api/services/primitives/dispatch_specialist.py`. |
| Recurrence Module | `api/services/recurrence.py` (ADR-231 walker, re-cut by ADR-261: every recurrence lives in `/workspace/_recurrences.yaml`, flat list; paths slug-templated by `conventions.py`. `recurrence_paths.py`, the per-shape declaration files, and `RecurrenceShape` are all DELETED.) |
| Scheduling | `api/services/scheduling.py` (`compute_next_run_at`, `materialize_scheduling_index`, `get_due_recurrences`, `claim_task_run` CAS claim) |
| Recurrence Lifecycle Primitive | `api/services/primitives/schedule.py` (`Schedule(action=...)` for create/update/pause/resume/archive — renamed from ManageRecurrence) + `services/primitives/fire_invocation.py` (`FireInvocation`, operator-initiated manual fire; CHAT_PRIMITIVES only per ADR-296 D3). **Replaces** deleted `UpdateContext(target='recurrence')` and `ManageTask` primitives. |
| Inference Primitives | DELETED — `InferContext` (ADR-324) and `InferWorkspace` (ADR-314 D4) both dissolved; identity/brand authoring flows through ordinary substrate writes. (They had replaced `UpdateContext` per ADR-235 D1.a.) |
| Substrate Write Primitive (ADR-235 D1.b + Option A) | `api/services/primitives/workspace.py::handle_write_file` with `scope='workspace'`. Reaches operator-shared substrate (`context/_shared/*`, `memory/*`, `reports/*/feedback.md`, etc.) via workspace-relative path. Recognized canonical paths emit activity-log events automatically. |
| Feedback Formatters (ADR-235 D1.b) | `api/services/feedback_formatters.py` — pure-Python helpers for memory/agent/task feedback formatting; called server-side from chat dispatch when feedback is being routed. |
| Agent Execution (deleted) | DELETED (ADR-271 dead-headless-path sweep, 2026-05-14). Pre-ADR-261 task pipeline `execute_agent_generation` + `generate_draft_inline` + `_build_headless_system_prompt` had no live caller after ADR-141 + ADR-261. Live execution paths today: scheduler walkers → `wake_queue` → `wake_drainer` → `invoke_freddie` (Path 1) and chat → `invoke_freddie(trigger='addressed')` (Path 2). Sub-LLM calls go through `dispatch_specialist.py` (headless tool surface). |
| Delivery Service | `api/services/delivery.py` (ADR-118 D.3: `deliver_from_output_folder()`) |
| Feedback Distillation | `api/services/feedback_distillation.py` (ADR-117: edits → style.md; ADR-231: writes to natural-home `_feedback.md`) |
| Feedback Engine | `api/services/feedback_engine.py` (edit metrics computation) |
| Agent Pipeline | DELETED (ADR-260/261 — the headless task pipeline dissolved into the real-time loop). |
| Agent Routes | `api/routes/agents.py` |
| Task Deliverable Inference | DELETED (ADR-231 — the task abstraction sunset). |
| Recurrences Routes | `api/routes/recurrences.py` (ADR-231 Phase 3.8: renamed from `routes/tasks.py`; URL `/api/recurrences/*`) |
| **DELETED (ADR-231 Phase 3.7)** | `api/services/task_pipeline.py` (4,204 LOC), `api/services/task_workspace.py` (319), `api/services/task_types.py` (1,836), `api/services/task_derivation.py` (334), `api/services/primitives/manage_task.py` (1,498) — all replaced by `invocation_dispatcher` + `dispatch_helpers` + recurrence-walker substrate. |
| Dashboard Summary | DELETED (2026-03-22) — collapsed into Agents page |
| Platform Sync Worker | DELETED (ADR-153 — platform_content sunset) |
| Platform Sync Scheduler | DELETED (ADR-153 — platform_content sunset) |
| Platform API Clients | `api/integrations/core/{slack,notion,github}_client.py` |
| Landscape Discovery | `api/services/landscape.py` |
| Tier Limits | `api/services/platform_limits.py` |
| Agent Scheduler | `api/jobs/unified_scheduler.py` (ADR-231 Phase 3.3: walks recurrence YAML declarations via `services.scheduling.get_due_declarations`; thin `tasks` index gates due-row queries). **ADR-298 Phase 3 cutover (2026-05-22):** walkers enqueue to `wake_queue` via `submit_wake_proposal`; the scheduler tick calls `wake_drainer.drain_all_users_with_pending(client)` after the walker block (preceded by `wake_queue.reclaim_stale_locks` for crash recovery per Scenario J). Reviewer is NOT invoked inline by `submit_wake_proposal` post-cutover; execution happens in the drainer with single-in-flight + pace-aware drain. |
| Wake Queue (ADR-298) | `api/services/wake_queue.py` — single-lane Reviewer execution per workspace, two-lane drain (paced/live), cross-source dedup at insert time. Transient compute per Axiom 1 (migration 179, Phase 1 Implemented 2026-05-22). Service helpers: `enqueue`, `get_next_pending`, `try_lock`, `has_in_flight`, `mark_completed`/`mark_failed`/`mark_dropped`, `reclaim_stale_locks`, `gc_completed`, `queue_depth`. |
| Wake Drainer (ADR-298 Phase 3) | `api/services/wake_drainer.py` — drainer pulls pending wakes, respects paced-lane pace cap + single-in-flight constraint, dispatches to source-specific Reviewer-invocation body. `drain_next_for_user`, `drain_user_until_empty`, `drain_all_users_with_pending`, `drain_can_acquire_for_user`, `paced_lane_eligible_to_drain`. Called from scheduler tick after walker block. Phase 3 Implemented 2026-05-22. |
| **Which model runs (ADR-556 + ADR-557 D3)** | **FOUR determinants — never merge them.** (1) **Machinery** → `api/services/system_calls.py`, keyed by CALL TYPE (`resolve_system_call` / `system_call_model`), env `YARNNN_SYSCALL_{CALL_TYPE}`. (2) **An APP** (Studio · Docs · IMAGES · radar — all user-facing) → **its RESIDENT**: `web/lib/apps/authoring.ts` + `KERNEL_AGENTS` (+ `radar.resolve_radar_resident`). An app's engine follows its resident, NEVER a caller-supplied model id — the rule that made Designer exist instead of `models[0]`. (3) **The open surface** (chat) → the member picks the COLLEAGUE; the engine rides behind the name (ADR-460); no default (ADR-467 D2). (4) **The steward** → `services/model_selection.py`, keyed by trigger shape, Anthropic-direct for prompt caching (ADR-463 D3; `freddie_agent.py` must never import `model_router`). Every row is `provider/model`-prefixed and must have a `_BILLING_RATES` row. Gates: `test_adr556_system_calls.py`, `test_adr557_router_hardening.py`. |
| **Engine registry (ADR-559)** | `LANE_MODELS` is the **turn-time whitelist**, not just the chooser — **deleting a row breaks every lane pinned to it** (at the 2026-08-12 refresh all 65 live lanes pinned `claude-sonnet-4-6`). Superseded engines carry `retired: True`: still routable, gone from the door. `offered_lane_models()` is the chooser's view; the loops gate on the full dict. Retired rows KEEP their `_BILLING_RATES` row (`unpriced_lane_model` gates every turn). **Availability has three reasons** — `no_provider_key` + `unpriced` (computed) and `upstream_refused` (OBSERVED via `note_upstream_refusal`, healed by any success; narrow — a timeout or rate-limit must NOT darken an engine). Unavailable engines are **served greyed with a reason, never filtered** — hiding reads as a bug. `create_lane` refuses at the door, before the lane row exists. Gate: `api/test_adr559_engine_registry.py`. ⚠️ Sonnet 5 is priced at STANDARD $3/$15 while Anthropic runs an intro $2/$10 through 2026-08-31 — the rate mirror reads x1.50 on that row **by decision**, not by defect. |
| **Router flags (ADR-557)** | **TWO flags, two questions.** `MODEL_ROUTER_ENABLED` = *is multi-provider TRANSPORT available* (infra). `lanes_enabled()` = *are member LANES GA* (product); `LANES_ENABLED` unset defers to transport, so the split ships inert. **A product flag may never grant more than the infra it rides on.** The transport ENFORCES its own flag (`_assert_router_enabled` → `RouterDisabled`) before the lazy litellm import — it is not a convention call sites may forget (radar forgot, and a flag-off sweep reached the provider over the network). Machinery callers read the transport flag; only lane paths read `lanes_enabled()`. |
| Pace / cadence | No `services/pace.py` — DELETED. Pace state reads via `api/services/wake.py` + `budget.py`; the substrate path constant is in `services/workspace_paths.py`. Cost governance is `governance/_budget.yaml` (ADR-327). |
| Bundle minimum_pace gate (ADR-298 Phase 4) | **DELETED by ADR-327** — `minimum_pace` removed from all bundle manifests, `bundle_reader.get_minimum_pace` deleted (tombstone at `bundle_reader.py:66`), the activation pace gate + D8 default-pace seed removed from `fork_reference_workspace` (tombstone `programs.py:597`). Cost governance is `governance/_budget.yaml` only. This row is retained as a tombstone so stale references are caught. |
| Workspace Export (ADR-328 D4 / ADR-510) | `api/services/export/git_export.py` — Category 1 → a plain git repo (pure-Python loose objects) + `EXPORT-MANIFEST.md` declaring omissions; served by `GET /api/workspace/export`. Binary substrate has ONE lane: `write_revision(content_bytes=…)` → the ADR-427 CAS seam (ADR-510 deleted the design-system import's bucket lane). |
| MCP Server | `api/mcp_server/` (ADR-075 infra + ADR-543/545 file-native tool surface: `open` / `list` / `search` / `save` / `edit` / `delete` / `move` / `history` / `share` — each a binding of a kernel verb per ADR-512 D3 + ADR-337; caller of `execute_primitive()` per ADR-164; roster is `_INTEROP_VERBS`) |
| MCP Composition | `api/services/mcp_composition.py` (ADR-543/545: `compose_{open,list,search,save,edit,delete,move,history}`, `parse_file_reference` / `format_file_reference` (the ADR-512 D5 handle grammar), `derive_client_name_from_token`; principal display via `services/principal_display.py`; the memory-verb machinery is DELETED) |
| MCP Feature Docs | `docs/features/mcp/` — `README.md` (entry), `tool-contracts.md`, `workflows.md`, `architecture.md` (ADR-169 canonical product framing) |
| Output Gateway (yarnnn-render) | **DELETED (ADR-417)** — generation is rented, not owned; yarnnn hosts no generation/rendering engine. The `render/` tree + the Docker deployment (`srv-d6sirjffte5s73f90pfg`) are decommissioned. |
| RuntimeDispatch Primitive | **DELETED (ADR-417)** — the asset-generation primitive (chart/mermaid/image/video via the render service) is retired. The `designer` production role collapses to compose-only; `has_asset_capabilities()` returns `False` universally. |
| Compose Engine (in-API) | `api/services/compose/engine.py` (ADR-417) — pure-Python section→styled-HTML templating, ported in-API from the retired render service. The two matplotlib chart kinds did NOT port (they degrade to native data-tables). Callers: `delivery.py`, `compose/task_html.py`, `primitives/compose.py`, `primitives/repurpose.py`. |
| Frontend API Client | `web/lib/api/client.ts` |
| Sync Error Categorization | `web/lib/sync-errors.ts` (ADR-086) |
| Onboarding / First-run UI | `web/app/auth/callback/page.tsx` (redirect gate). Per ADR-414 D4 genesis is pure — no skeleton seeding; `web/components/onboarding/` and the Settings WorkspaceSection are DELETED. |
| **Chat vs Agents (ADR-558)** | **Two surfaces, two questions — do not re-merge them.** **Chat** (`web/components/chat-surface/`) is the ENGINE surface: starting a conversation picks an engine (sticky last-used), and `create_lane` **422s on `agent` for an unbound lane**. **Agents** (`web/components/agents/`) owns personas — `KERNEL_AGENTS`/`KERNEL_POSTURES` + the member's `_agent.yaml`. Who REPLIES is the **cast** (`conversation_cast`, ADR-495), joined from inside a conversation — never chosen at the door. `lane_meta["agent"]` survives for **bound** lanes only (Studio·Docs·IMAGES pin a resident, ADR-467 D1). Gate: `api/test_adr558_chat_is_engines.py`. |
| Agents Page (Home) | `web/app/(authenticated)/agents/page.tsx` |
| Chat Page | `web/app/(authenticated)/chat/page.tsx` |
| Route Constants | `web/lib/routes.ts` (HOME_ROUTE = "/chat" per ADR-205 F1) |
| Workspace Surface Contracts | `docs/design/WORKSPACE.md` (renamed from SURFACE-CONTRACTS.md 2026-05-12; ADR-215: per-tab contracts + 4-shape CRUD matrix for Chat · Work · Agents · Files; paired with `docs/architecture/WORKSPACE.md`) |
| Invocation & Narrative (canonical) | `docs/architecture/invocation-and-narrative.md` (FOUNDATIONS Axiom 9: atom = one cycle of the six dimensions; narrative = single chat-shaped log of every invocation; task = nameplate + pulse + contract legibility wrapper; `/work` is narrative filtered by task slug) |

---

## Common Pitfalls

1. **Schema mismatch**: Code referencing old table/column names — use `agents` not `deliverables`, `agent_runs` not `deliverable_versions`, `agent_id` not `deliverable_id`
2. **Tool loop exhaustion**: YARNNN hits `max_tool_rounds=5` without text response if tools return empty
3. **PGRST205 errors**: PostgREST schema cache needs refresh after table changes
4. **Render env var drift**: Worker/Scheduler missing env vars that API has — Worker silently fails to decrypt tokens, reports `success=True` with 0 items. Always check all services.
5. **Backend/frontend field name mismatch**: Backend returns one shape (e.g., `selected_sources`), frontend expects another (e.g., `sources`). Verify API response matches frontend consumer.

---

## Quick Commands

```bash
# Run API locally
cd api && uvicorn main:app --reload --port 8000

# Run frontend locally
cd web && pnpm dev

# Run SQL migration
psql "${SUPABASE_DB_URL}" -f supabase/migrations/XXX_name.sql

# Check recent commits
git log --oneline -20
```
