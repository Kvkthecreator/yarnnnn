# CLAUDE.md - Development Guidelines for YARNNN

This file provides context and guidelines for Claude Code when working on this codebase.

## Project Overview

YARNNN is an **autonomous agent platform for recurring knowledge work**. Persistent AI agents connect to work platforms (Slack, Notion), run on schedule, learn from feedback, and produce outputs that improve with tenure.

**Architecture**: Next.js → FastAPI → Supabase (Postgres) → Claude API. Core model: the **workspace** over the **authored substrate**; staffed by **agents** (ADR-596; the one noun since ADR-631), not the pre-ADR-231/596 "Agents + Tasks".

> **OS framing note (ADR-222 + FOUNDATIONS Principle 16)**: YARNNN is an **agent-native operating system**. Substrate (filesystem + primitives + axioms + daemons) = **kernel**; primitive matrix = **syscall ABI**; chat agent = **shell**; workspaces = **userspaces**; programs = **applications**, shipped as an `.app`-equivalent bundle at `docs/programs/{program}/`. **The kernel boundary is sacred** — programs never modify the kernel; the shell is application code; the compositor reads but never authors. Workspaces have no "types": they run programs, and specialization happens at the compositor, not the kernel. See [ADR-222](docs/adr/ADR-222-agent-native-operating-system-framing.md) + FOUNDATIONS + GLOSSARY.

> **Surface model note**: the authenticated workspace is an OS desktop of windowed surfaces driven by one
> window manager (`useSurfacePreferences`), with content parsers in `web/lib/content-shapes/` and structured
> affordances in `web/components/library/` (ADR-245's three-layer rendering). **The surface roster churns fast** —
> Home and Channels were both deleted (ADR-435, ADR-415) after long stints in this file. Do not trust a surface
> list written here; read [compositor.md](docs/architecture/compositor.md) and the FE `SurfaceRegistry` for the
> live set. Redirect stubs are pure server transport (`redirect()`, ADR-308) — never `'use client'` + `useEffect`.

> **Vocabulary note**: ADR-216's "agent = persona-bearing judgment entity" is superseded by **ADR-596: an agent is identity ⊕ character ⊕ engine and nothing else** (see the Agents row; ADR-631 retired the transitional noun *being* and the surface noun *desk* → **pane**). Production machinery is **Orchestration**, never persona-bearing. Current taxonomy: [LAYER-MAPPING.md](docs/architecture/LAYER-MAPPING.md) + Key terminology below.

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
- **Steward / Freddie / Reviewer / seat** — **RETIRED (ADR-632, 2026-09-02).** The systemic agent, its prompt
  layer, model table, wake stack, review seat, kernel mirrors and chrome are DELETED. Nothing wakes on its own
  initiative: an attended turn is a member's message in a lane; an unattended run is a standing declaration's
  schedule (ADR-603). The `freddie:` attribution prefix survives on historical revisions, display-resolved. The
  billing **seat** (ADR-445) is a different word. Do not reintroduce a systemic agent, a wake source, or a
  per-shape model table. Gate: `test_adr632_the_seat_retires.py`.
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

The Agent-OS aspiration is full autonomy: an agent under a grant can take capital actions AND meta-aware-edit every operator-canon file (principles, mandate, risk envelope, ground-truth) on its own initiative, under in-system discipline + audit trail + revertibility. The current ADR-293 lock-set on three governance files (`AUTONOMY.md` + `_autonomy.yaml` + `_token_budget.yaml`) is **current dev-trust state**, not permanent architecture. As we harden the Reviewer's self-amendment discipline through Hat-A edits (validated *via* Hat-B evaluation runs), the lock-set should shrink toward zero.

**Wake architecture — DELETED (ADR-632).** There are no wake sources, no funnel, no queue, no drainer. The two live execution paths: chat → `run_lane_turn` (attended, the member's grant) and standing declarations → `run_bounded_derive_turn` (unattended, toolless, contract-checked, receipted — ADR-603/618).

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
- `WORDPRESS_CLIENT_ID` / `WORDPRESS_CLIENT_SECRET` — ADR-628: OAuth initiation + the member-clicked publish both run on the API; the scheduler never publishes (phase (b) unbuilt by design).

**MCP Server env vars** (separate from above — MCP server uses service key, not user JWTs):
- `SUPABASE_SERVICE_KEY` — Service key for RLS bypass (same as Schedulers)
- `MCP_USER_ID` — User UUID for data scoping (auto-approve OAuth + static bearer fallback)
- `MCP_BEARER_TOKEN` — Static bearer token for Claude Desktop/Code
- `MCP_SERVER_URL` — OAuth issuer URL (defaults to `https://yarnnn-mcp-server.onrender.com`)

**MCP Auth model** (ADR-075): OAuth 2.1 for Claude.ai/ChatGPT (auto-approve, tokens stored in `mcp_oauth_*` tables). Static bearer token fallback for Claude Desktop/Code. See `api/mcp_server/oauth_provider.py`.

**MCP authorization** (ADR-563): identity answers *who*; **scopes answer what they may do**. Additive tiers `files:read` ⊂ `files:write` ⊂ `files:share` (share is its own tier — granting REACH ≠ changing CONTENT). **`read` = LEGACY full access**: every pre-563 token carries it, so narrowing it breaks live connectors. Check is `assert_scope(verb)` from **`resolve_request_client(verb=…)`** — the chokepoint that already resolves identity, never per call site — and it **fails closed**. `required_scopes` stays EMPTY (enforcing at the transport 401s legacy tokens first). ⚠️ Pre-563 `valid_scopes=["read"]` was decorative — a token *labelled* read could `delete` and `share`. Gate: `api/test_adr563_mcp_scope_enforcement.py` (script-style). Tier definitions live in **`services/mcp_scopes.py`**, not `mcp_server/auth.py` — the API serves the consent screen and cannot import the MCP package (py3.9 venv, py3.11-only SDK); auth re-exports them, so label and check cannot drift.

**MCP workspace binding** (ADR-373 D6 + ADR-573): scopes answer *what*; **the binding answers where**. The operator picks a workspace at consent; it is stamped on the token and read by `resolve_mcp_workspace(user_id, bound)`, which routes through the SAME `resolve_workspace_for_principal` the JWT door uses — so a stamp **NARROWS, never grants**, and reach is re-checked every request. **NULL = the principal's default** (every pre-573 token; no backfill — stamping them would freeze a default that may legitimately move). The binding must ride the REFRESH token too, or silent rotation un-binds every live connector. Gate: `api/test_adr573_connector_workspace_binding.py` (py3.11).

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

Applies to the LIVE frame — `api/services/lane_runner.py` (`_CONVENTIONS_FRAME`, the composition site), the app postures (`api/services/authoring.py::_POSTURE_FRAME`, `api/services/apps/*.py`), the standing frame (`lane_runner._STANDING_FRAME` + `api/services/standing_work.py::_STANDING_JOB`, ADR-639), the kernel participant constants (`api/services/workspace_paths.py`), `api/services/skills/*/SKILL.md` (ADR-630), and `api/services/primitives/*.py` (tool definitions). The steward's prompt layer is DELETED (ADR-632).

You MUST:
1. Update `api/prompts/CHANGELOG.md` with the change.
2. Note the expected behavior change.
3. Run the size ratchets — `api/test_adr632_the_seat_retires.py` §5 (the conventions scaffold + the studio posture frame) and `api/test_adr630_skills.py` (the skills index ceiling).

**The prompt layer is ablated, not accreted** (ADR-306, FOUNDATIONS DP22). The steward's frame went ~36K → ~10K under CI ceilings and then retired; the same discipline holds the lane frame. Craft prose belongs in a skill, grammar stays derived from the app registries. Before adding an instruction:

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

### The seat canon — ARCHIVED (ADR-632)

The Reviewer/steward canon (`reviewer-substrate.md`, `reviewer-seat-substrate.md`, `reviewer-occupant.md`, `reviewer-occupant-contract.md`, `cadence-and-wakes.md`, `invocation-and-narrative.md`, `execution-loop.md`, `agent-execution-model.md`, `persona-reflection.md`, the `adr296-*` audits) lives under `docs/architecture/previous_versions/`. The live Altitude-2 canon is [lane-frame.md](docs/architecture/lane-frame.md); [agent-composition.md](docs/architecture/agent-composition.md) §3.2.1 still governs the partition between a program's `principles.md` and the posture frame.

### ADR-064: Unified Memory Service (updated by ADR-156, post-ADR-235)

**Memory is in-session** — YARNNN writes facts proactively via `WriteFile(scope="workspace", path="memory/notes.md", content="...", mode="append")` during conversation. Follows the Claude Code model: memory happens in the moment of learning, not as a batch job. **Nightly cron extraction is REMOVED** (ADR-156) — session summaries generate inline at session close (chat.py); shift notes go to AWARENESS.md; the user can still edit memories via the Context page.

**Key files**:
- `api/services/memory.py` — `process_conversation` / `get_for_prompt` / `extract_from_text_to_user_memory`
- Memory-write guidance lives in the lane frame's commons contract (`api/services/workspace_paths.py`); the steward's frame and the `agents/prompts/` profile registry are DELETED.
- `docs/features/memory.md` — user-facing docs

### Schema (tables + columns)

**Per-table detail lives in [docs/database/SCHEMA-NOTES.md](docs/database/SCHEMA-NOTES.md)** — current table names, deprecated columns, and the ADR history behind each. Read it on demand; `supabase/migrations/` is authoritative for actual DDL.

The rule that matters every session: **use current names**, and note `agents`/`agent_runs` are DROPPED (mig 248). `platform_connections` not `user_integrations`. Verify against the live schema before writing a query.

### Platform sync + agent workspace (ADR-056/057/077/106, post-ADR-153)

**There is no platform-content store.** `platform_content`, `platform_worker.py`, and `platform_sync_scheduler.py` are DELETED (ADR-153); agents call platform APIs **live** during execution. Preserved: `platform_connections` (OAuth tokens), the API clients, `sync_registry`, `landscape.py`.

**The workspace is a virtual filesystem over Postgres** (ADR-106) — path-based `read`/`write`/`list`/`search` over `workspace_files` (`path`, `content`, `embedding`, `tags`), behind the storage-agnostic `AgentWorkspace` class (`api/services/workspace.py`; primitives in `api/services/primitives/workspace.py`). Reasoning agents gather their own context from the workspace — never a pre-gathered platform dump. History: [ADR-LEDGER](docs/architecture/ADR-LEDGER.md).

---

## File Locations

| Concern | Location |
|---------|----------|
| System agent (prompt + loop) | **DELETED (ADR-632)** — `api/agents/` is gone with the wake stack. The live frame is `api/services/lane_runner.py::build_lane_conventions` (lane-frame.md). |
| Tool Primitives (code) | `api/services/primitives/*.py` — canonical registry in `registry.py` |
| Tool Primitives (canonical doc) | `docs/architecture/primitives-matrix.md` (ADR-168) — substrate × mode × capability matrix, rename protocol, deleted primitives ledger |
| Memory Service | `api/services/memory.py` |
| Chat/Streaming | `api/services/anthropic.py` |
| OAuth Flow | `api/integrations/core/oauth.py` |
| **Workspace (canonical doc)** | `docs/architecture/WORKSPACE.md` — layers, filesystem inventory, 5-phase bootstrap, autonomy threshold. Paired with `docs/design/WORKSPACE.md` (per-tab surface contracts). **Start here for anything substrate/init/onboarding/bootstrap/autonomy-threshold.** |
| Workspace Initialization | `api/services/workspace_init.py` — `initialize_workspace()` (5 phases: YARNNN row → skeletons → narrative session → balance audit → optional fork). Called by `GET /api/workspace/state` (lazy scaffold), `DELETE /account/workspace` (L2), `DELETE /account/reset` (L4). |
| Workspace Path Constants | `api/services/workspace_paths.py` — `SHARED_CONTEXT_FILES` (kernel-seeded set: MANDATE, IDENTITY, BRAND, AUTONOMY, PRECEDENT). `SHARED_CONVENTIONS_PATH` kept as a constant but **not in `SHARED_CONTEXT_FILES`** — CONVENTIONS is program-scoped. |
| **An agent's home (ADR-624)** | `agents/{slug}/` is a **PRINCIPAL home, not a semantic root**, holding **exactly two things**: `memory/` (what the agent KNOWS — freely writable by it, ordinary substrate) and the **grant sidecars** `_autonomy.yaml`+`_budget.yaml` (LOCKED). ⭐⭐⭐**The ADR-414 twelve-file set is DELETED, not dormant** — ten of those put authority/clock/purpose/per-app judgment on an agent, which ADR-596 D1 forbids and ADR-601 many-to-one breaks. Do not reintroduce them. Confinement rides `_is_path_locked` (fails closed). Gate: `test_adr624_the_being_has_a_home.py`; rationale in the ADR-LEDGER. |
| **Folders + told-names (ADR-588)** | **Folders do not exist in the substrate** — one exists iff a file exists under its prefix; the tree is DERIVED. An EMPTY folder is a MARKER row (trailing-slash path + `content_type='inode/directory'`, written via `write_revision`, NOT `WriteFile`). ⭐**The trailing slash is load-bearing.** Filter every listing/search/export on `is_folder_marker` (hide at PRESENTATION, never at authorization). ⭐⭐⭐`PARTICIPANT_FILESYSTEM_MODEL` TELLS every LLM "Documents"/"Downloads" while the kernel has `operation/`/`inbound/` — `HOME_ALIASES` resolves at `parse_file_reference`, the ONE chokepoint. RESOLVE, never refuse. Detail: ADR-LEDGER. Gate: `test_adr588_folder_markers_and_home_aliases.py`. |
| Workspace Utilities | `api/services/workspace_utils.py` — `is_skeleton_content()` + `classify_file_state()`. Single source of truth for skeleton detection (used by init, workspace state surface, and activation state classifier). |
| Program Lifecycle (fork) | `api/services/programs.py` — `fork_reference_workspace()`, `_strip_tier_frontmatter()`, `parse_active_program_slug()`, `strip_program_marker_from_mandate()`. Bundle fork logic is here, not in workspace_init. |
| Back-Office Lifecycle | `materialize_back_office_task()` lives in `api/services/workspace_init.py`; the `services/back_office/` package is DELETED (ADR-260/261). |
| **Platform credentials (ADR-577)** | `api/services/platform_credentials.py` — the ONE path. **A human's account credential, keyed `user_id`. There is NO workspace credential store** — ADR-566's second store is withdrawn (unfillable, mis-filled by migration 201's owner-fill trigger, unreadable under `user_id` RLS). **An AGENT caller is REFUSED and logged**, never falling through to the owner's token — the guard ADR-566 specified but keyed on an `own-agent` role that ZERO rows hold, behind a `workspace_id` `HeadlessAuth` never carried. `platform_connections.workspace_id` = **routing**, never ownership. Re-entry needs a DRIVEN TRACE (ADR-577 §7). Gate: `test_adr577_credential_claim.py`. |
| Authored Substrate (ADR-209) | `services/authored_substrate.py` — **`write_revision()` is the single write path** for every `workspace_files` content-layer mutation. ADR CLOSED (Phase 5, 2026-04-23). **Permitted direct-mutation exceptions (2 only)**: `_upsert_workspace_file` (the write target) and `primitives/workspace._embed_workspace_file` (metadata-only). `content` denormalization is retained deliberately (FTS + embedding indexes). The `/history/` convention, `_archive_to_history`, `_cap_history`, `list_history` and the ADR-176 `v{N}.md` archive are DELETED — do not reintroduce filename versioning. Guard: `test_adr209_no_filename_versioning.py`. |
| Agent Framework (canonical) | [docs/architecture/orchestration.md](docs/architecture/orchestration.md) + [agent-composition.md](docs/architecture/agent-composition.md) |
| Directory Registry | `api/services/directory_registry.py` — `WORKSPACE_DIRECTORIES` (context domains, uploads, output categories) |
| Agent Framework (code) | `api/services/orchestration.py` — mostly kernel default-content constants (`DEFAULT_*_MD`, `KERNEL_VERSION`, steward defaults) + role/capability resolution (`resolve_role`, `has_capability`, `ALL_ROLES`). ⚠️ `AGENT_TEMPLATES` + `AGENT_TYPES` are **DELETED** (ADR-269) — do not reintroduce. (The gate that held this went with the pre-ADR-596 agent model; `test_agent_model_is_retired.py` is the nearest live guard.) |
| DELETED — do not reintroduce | Composer/Heartbeat (ADR-156) · Pulse Engine (ADR-141) · Invocation Dispatcher (ADR-260/261) · the headless task pipeline (ADR-231) · Platform Sync Worker + Scheduler (ADR-153) · Dashboard Summary · `InferContext`/`InferWorkspace` · `web/components/onboarding/` · **the pre-ADR-596 agent model** and its **8 TABLES** (mig 248, all empty) — ⭐NO successor verb: authority over an agent is unrepresentable (ADR-460 D3.a) · **the wake stack** (ADR-632) · `services/derive_recipes.py` + the ADR-157 playbook family (ADR-630). Detail: ADR-LEDGER. Gates: `test_agent_model_is_retired.py` · `test_adr632_the_seat_retires.py`. |
| **Recurrences (RETIRED — ADR-603 D5, 2026-08-24)** | Concept + every member surface DELETED (production: 0 declarations — retire-clean): `routes/recurrences.py` + `routes/narrative.py`, the `recurrence`/`activity` surface rows, the whole FE chain. Run receipts = notifications Activity ledger. **Steward-side plumbing survives INERT** (`services/recurrence.py`, `Schedule`/`FireInvocation`, scheduler dispatch, bundle seeding) — dies with ADR-596 D3 phase (a); do not build on it. Standing work = the **standing declaration** (`services/standing_work.py` — ADR-639; the strings app is DELETED). |
| Scheduling | `api/services/scheduling.py` — `compute_next_run_at` + **the ONE drain loop** (`claim_run` · `record_run` · `drain_due`, ADR-639 D3) shared by standing work + capture; a third unattended kind is an adapter, never a twin |
| Substrate Write Primitive (ADR-235 D1.b + Option A) | `api/services/primitives/workspace.py::handle_write_file` with `scope='workspace'`. Reaches operator-shared substrate (`context/_shared/*`, `memory/*`, `reports/*/feedback.md`, etc.) via workspace-relative path. Recognized canonical paths emit activity-log events automatically. |
| Agent Execution | **Two live paths, both lanes**: chat → `run_lane_turn` (attended, `member:` grant, the uniform tool surface) and a standing declaration → `run_bounded_derive_turn` (unattended, toolless, contract-checked, receipted — ADR-603/618). The steward paths (`invoke_freddie`, the wake queue/drainer) are DELETED (ADR-632). |
| Platform API Clients | `api/integrations/core/{slack,notion,github}_client.py` |
| Landscape Discovery | `api/services/landscape.py` |
| Tier Limits | `api/services/platform_limits.py` |
| Agent Scheduler | `api/jobs/unified_scheduler.py` — three lanes, none steward-gated (ADR-632): the kernel skills mirror (ADR-630), the capture lane (own flag `CAPTURE_LANE_ENABLED`), the standing-work drain (`drain_due_standing_work`, ADR-618-bounded — ADR-639). No wake queue, no hook walker, no kernel mirrors. |
| **Which model runs (ADR-556/557 D3)** | **THREE determinants — never merge them.** (1) **Machinery** → `services/system_calls.py`, keyed by CALL TYPE. (2) **An APP** → **its RESIDENT**, declared in the app's own module, resolved SERVER-side via `register_app` → `resident_for_app()` (ADR-562); never a caller-supplied model id. (3) **Chat** → the member picks the COLLEAGUE; the engine rides behind the name (ADR-460); no default. Every row is `provider/model`-prefixed and needs a `_BILLING_RATES` row. Detail: ADR-LEDGER. Gates: `test_adr556_system_calls.py` · `test_adr557_router_hardening.py` · `test_adr562_app_owned_config.py`. |
| **Engine registry (ADR-559)** | `LANE_MODELS` is the **turn-time whitelist**, not just the chooser — deleting a row breaks every lane pinned to it. Superseded engines carry `retired: True` (routable, gone from the door) and KEEP their `_BILLING_RATES` row. Availability has three reasons — `no_provider_key` · `unpriced` (computed) · `upstream_refused` (OBSERVED, healed by any success). Unavailable engines are served **greyed with a reason, never filtered**. ⚠️Rates are STANDING list price, never promotional (ADR-559 D1.a). Detail: ADR-LEDGER. Gate: `test_adr559_engine_registry.py`. |
| **Router flags (ADR-557)** | **TWO flags, two questions.** `MODEL_ROUTER_ENABLED` = is multi-provider TRANSPORT available (infra). `lanes_enabled()` = are member LANES GA (product). **A product flag may never grant more than the infra it rides on.** The transport ENFORCES its own flag (`_assert_router_enabled`) before the lazy litellm import — not a convention call sites may forget. ⭐**ADR-634: the system prompt is CACHE-MARKED** (`_system_payload`, BOTH doors); LiteLLM keeps the marker for Anthropic, STRIPS it for OpenAI-compatible + Gemini. ⚠️A cache WRITE is 1.25x: 1-round turns cost +25%, ≥2 rounds win (~46% blended). Gates: `test_adr557_router_hardening.py` · `test_adr634_prompt_caching.py` (py3.9 venv). |
| Pace / cadence | No `services/pace.py` — DELETED; the ADR-327 `minimum_pace` bundle gate is deleted too. Pace state reads via `api/services/wake.py` + `budget.py`; the substrate path constant is in `services/workspace_paths.py`. Cost governance is `governance/_budget.yaml` (ADR-327). |
| Workspace Export (ADR-328 D4 / ADR-510) | `api/services/export/git_export.py` — Category 1 → a plain git repo (pure-Python loose objects) + `EXPORT-MANIFEST.md` declaring omissions; served by `GET /api/workspace/export`. Binary substrate has ONE lane: `write_revision(content_bytes=…)` → the ADR-427 CAS seam (ADR-510 deleted the design-system import's bucket lane). |
| MCP Server | `api/mcp_server/` (ADR-075 infra + ADR-543/545 file-native tool surface: `open`/`list`/`search`/`save`/`edit`/`delete`/`move`/`history`/`share` — each a binding of a kernel verb; roster is `_INTEROP_VERBS`). **ADR-584 adds `whoami`** (subject is the CONNECTION). **ADR-622 adds `request_upload`** (payload never crosses the wire). ⭐**ADR-621: a binary file is not an empty file.** ⭐A new verb needs a rendering story or `test_adr533_participant_contract.py` fails. ⭐Verb counts are DERIVED — never pin `== 9`. |
| **Connector workspace identity (ADR-584)** | **`whoami` answers *where am I standing*.** The workspace is otherwise invisible to a connected principal: a bare UUID on `AuthenticatedClient.workspace_id`, a query filter only, discarded before every response — **no `compose_*` file verb carries a workspace key, and that envelope shape is REJECTED, not merely absent**. ⭐⭐⭐`binding` is the point: ADR-573's degrade of an unreachable stamped workspace was *unobservable*. The workspace NAME is an **address, not intent**. Detail: ADR-LEDGER. Gate: `test_adr584_connector_names_its_workspace.py`. |
| MCP Composition | `api/services/mcp_composition.py` (ADR-543/545: `compose_{open,list,search,save,edit,delete,move,history}` + ADR-584 `compose_whoami`, `parse_file_reference` / `format_file_reference` (the ADR-512 D5 handle grammar), `derive_client_name_from_token`; principal display via `services/principal_display.py`; the memory-verb machinery is DELETED) |
| MCP Feature Docs | `docs/features/mcp/` — `README.md` (entry), `tool-contracts.md`, `workflows.md`, `architecture.md` (ADR-169 canonical product framing) |
| Output Gateway + RuntimeDispatch | **DELETED (ADR-417)** — generation is rented; the `render/` tree, its Docker deploy and the asset primitive are retired. `has_asset_capabilities()` is `False` universally. (Full rationale: §5 above.) |
| Compose Engine (in-API) | `api/services/compose/engine.py` (ADR-417) — pure-Python section→styled-HTML. The 2 matplotlib chart kinds did NOT port (degrade to data-tables). |
| **Lane vision (ADR-623)** | A lane agent SEES what it reads: a binary `ReadFile` on a viewable image appends the pixels as a `user` message's `image_url` part — never base64 in the tool result. ⭐⭐⭐**External must never be better than internal.** Both tool loops promote (twins). Detail: ADR-LEDGER. Gate: `test_adr623_the_lane_can_see.py`. |
| **Skills (ADR-630)** | `api/services/skills/{slug}/SKILL.md` (Agent Skills shape: `name` + `description`, the ADR-254 named exception), **mirrored** into every workspace at `system/skills/` as `system:kernel-skills` revisions. A workspace's own live at `skills/{name}/SKILL.md`. ⭐**Discovery is the description**: the frame carries an INDEX, the body loads on demand via ReadFile (DP22) — bounded in BYTES at composition by TWO budgets (`INDEX_CEILING` ratchets OURS, `MEMBER_INDEX_ALLOWANCE` members'). ⚠️A count cap is not a byte cap. **Scoped by app** — `metadata.apps` names the panes a skill is for; silence = everywhere; withheld ones are NAMED + ListFiles (presentation, never authorization). ⭐**A skill never names an agent.** Detail: ADR-LEDGER. Gate: `test_adr630_skills.py`. |
| **IMAGES chrome (ADR-633)** | **The kernel stays shared; the chrome does not.** APP-SCOPED: the left rail, the object noun, the artboard-grained inspector rows. ⭐⭐⭐**The rail is DECLARED** — `AuthoringApp.objectModel` (`flow`\|`pages`\|`layers`), REQUIRED on every row, never back-derived. ⚠️Kernel CSS changes MUST bump `STUDIO_KERNEL_CSS_VERSION`. ⭐⭐⭐**Chrome CONFIRMED on production; the 4 tokens are UNEXERCISED, not falsified** (§5a). 0 token uses in the landed markup read as a design defect and was WRONG — the body has 0 `opacity:`/`mix-blend-mode:` (all 8 in-file are OUR kernel CSS); the agent wrote 14 `rgba()`, every one a COLOUR. **Colour-alpha ≠ layer-opacity** (a gradient's stops carry their own alpha), so it picked right and never needed a whole-layer dim. ⚠️Do NOT re-shape `opacity` as a measure: the posture says measures are member-authored, *preserve exactly*, and never that an agent may SET one — that would make it unreachable. ⭐⭐**A zero is not a verdict** — read the bytes before re-shaping a grammar. Detail: ADR-LEDGER. Gate: `test_adr633_the_artboard_is_layers.py`. |
| **Lane frame / focus (ADR-522+606)** | `docs/architecture/lane-frame.md` (canonical) — the Altitude-2 pane frame: ONE composition site (`lane_runner`), app-declared postures (`register_app(posture=…)`), the focus declaration (object from SUBSTRATE, place from DECLARATION). Gate: `test_adr606_pane_sees_the_member.py`. |
| Onboarding / First-run UI | `web/app/auth/callback/page.tsx` (redirect gate). ADR-414 D4: genesis is pure. |
| **How an agent SPEAKS (ADR-638)** | **`PARTICIPANT_REGISTER`** (`services/workspace_paths.py`) — a participant clause (ADR-533 D1) composed into the lane frame as `## Talking to {member}`. Name the THING not its mechanism; lead with what changed; the member's nouns. ⭐⭐⭐**It governs the ADDRESS, never the WORK** — the agent still authors `data-block-id` (ADR-365 D5). ⭐⭐**STRUCTURE, not word-frequency**: ADR-365's vague "write plainly" was A/B-FALSIFIED (noise); softening these rules re-runs that arm. ⚠️LANES ONLY — the connector's host owns its own voice. Precedents that must stay standing: `toolLabels.ts` (verbs) + `PARTICIPANT_FILESYSTEM_MODEL` (Documents/Downloads). Validated: 0.00 vs 2.08 leaks/reply, 9/9 vs 1/9 clean. Gate: `test_adr638_register.py`. |
| **An app on the CLIENT (ADR-636)** | **`web/lib/apps/registry.ts` — ONE `AppDescriptor` per app**, the client mirror of `register_app`. Adding an app = a row HERE + its window component + (if it authors) its `AuthoringApp`. `APP_SURFACES`, `servesIndex` and the authoring rows are DERIVED from it; `SERVED_INDEX_APPS`, the hand-keyed `APP_SURFACES`, `AuthoringApp.icon` and its closed `slug` union are DELETED. ⭐⭐⭐**A client row may NEVER carry the resident/engine/stage/tier/pin or anything authority-shaped** — those are the server's and arrive on the roster (ADR-460 D3.a, enforced as a key whitelist). ⚠️Icons resolve via `resolveSurfaceIcon` off the surface row's `icon_key` (ADR-297) — never a second map. ⭐⭐**A NEGATIVE check ("no longer claims docs") catches a forgotten DELETION and never a forgotten ADDITION** — assert the relation, both directions. ⭐**A gate that pins a SPELLING pins the defect**: assert the fact, not the literal row text. Detail: ADR-LEDGER. Gate: `test_adr636_app_declaration_parity.py`. |
| **App exposure (ADR-592)** | **One `stage` per app row** (`internal\|search-only\|beta\|primary`, `services/app_stage.py`); `launcher_tier`+`default_pinned` are DERIVED. ⭐⭐⭐**`internal` REMOVES the row from the served roster** — nav is backend-driven, so that IS the hide. ⚠️**Obligation: route → redirect stub AND hand-listed in `middleware.ts`** (`SURFACE_PREFIXES` is roster-derived, so a slug leaving the roster leaves the auth gate with it). ⭐An app with a CLOCK is deleted, not staged. Detail: ADR-LEDGER. Gate: `test_adr592_app_stage.py`. |
| **Agents (ADR-596→604; ADR-631; ADR-640)** | An agent = identity ⊕ character ⊕ engine; **authority/clock/judgment live on grants, declarations and gates — never on the agent** (ADR-596 D1). ⭐**ONE noun** — *being* retired; *desk* → **pane** (surface) + **app** (row). ONE register: `agents_registry.AGENTS` (ADR-600/601). Capability lives at the APP, so many-to-one is free: Editor → slides·text · Designer → images · Blogger → blogger (**Supervisor → strings retired, ADR-639**). A **standing declaration** names the APP or derives it from the kept file's type; the agent derives (ADR-603 D2 / ADR-639 D3). The steward is RETIRED (ADR-632). ⭐⭐⭐**An agent carries NO RECORD of its own** (ADR-640): no surface, payload or derived view presents work/output/cost/history attributed to an agent — attribution names the member and the engine because an agent is a character the hands wear. ⚠️The one agent-shaped join (`execution_events.session_id` → a lane's `agent` stamp) is lossy AND **historically true in the way that makes present-tense totals false** (25 lanes truthfully say `text`/`designer` because ADR-602 moved Text to Editor *after* them). PERMITTED, read-only, derived: the **craft** (skills whose `metadata.apps` meet the agent's apps) and the **tending** (declarations whose `resolve_executor` is it) — never settable. *An agent is met, not audited.* Detail: ADR-LEDGER. Gates: `test_agent_registry.py` · `test_adr631_vocabulary.py` · `test_adr640_no_agent_record.py`. |
| **Mentions / attention (ADR-605+637)** | `services/mentions.py` — the stamp rides `write_narrative_entry` (every writer, species-blind); the To-do surface is DERIVED per viewer, no inbox table. ⭐⭐⭐**ONE cursor decides membership and VISITING advances it** (`GET /lanes/{id}/messages` → `_mark_visited` → `mark_read_up_to`). The **reply floor is DELETED** — a reply is a visit, and a second floor that can disagree with the first IS the defect (a live row outlived a week of the viewer working in that lane). `Dismiss` = clear-without-opening, never the only exit. ⚠️The `member_state` KEY stays `mention_resolutions` (renaming strands live cursors). ⚠️The lane read must SELECT `sequence_number` or every advance is a silent no-op. Detail: ADR-LEDGER. Gate: `test_adr605_mentions_attention.py`. |
| **Chat vs Agents (ADR-558)** | **Two surfaces, two questions — do not re-merge them.** **Chat** is the ENGINE surface (`create_lane` 422s on `agent` for an unbound lane). **Agents** shows AGENTS — the ONE register (ADR-600), sectioned by app with provenance served. Who REPLIES is the **cast** (`conversation_cast`, ADR-495) — joined from inside a conversation, never chosen at the door. Detail: ADR-LEDGER. Gate: `test_adr558_chat_is_engines.py`. |
| Route Constants | `web/lib/routes.ts` (HOME_ROUTE = "/chat" per ADR-205 F1) |
| Workspace Surface Contracts | `docs/design/WORKSPACE.md` (renamed from SURFACE-CONTRACTS.md 2026-05-12; ADR-215: per-tab contracts + 4-shape CRUD matrix for Chat · Work · Agents · Files; paired with `docs/architecture/WORKSPACE.md`) |
| **Intake pipeline (CANON)** | `docs/architecture/intake-pipeline.md` — how ANYTHING from outside reaches the commons: `retain → distil → signal → read`, path grammar **`inbound/{lane}/{selector}/{stamp}.{ext}`** (BINDING). ⭐⭐**THREE DISPOSITIONS of platform reach: INTAKE (durable) · TURN REACH (transient, ADR-615) · OUTBOUND (ADR-628). A reach proposal must declare which in its first paragraph.** ⭐The tenant roster is NOT part of the contract — never name a lane after its first consumer. |
| **Standing work (ADR-639)** | **A kernel lane, not an app.** `services/standing_work.py` (the maintained file: `{folder}/_standing.yaml` + `CONTRACT.md`; discovery · index · the run) rides the ONE drain loop in `scheduling.py`; its system prompt is `lane_runner.build_standing_frame` (the lane frame minus tools/reach/cast/focus/register/index, plus the kernel JOB + the `keeping-a-file-current` skill BODY). ⭐⭐⭐**The strings app, its pane, `routes/strings.py` and the Supervisor agent are DELETED** — declaring is the `declaring-standing-work` skill in every lane; the roster + Run now/Pause are Notifications → Standing work (`routes/standing_work.py`, `/api/standing`); `/strings` is a stub. ⭐**`app` derives from the target's TYPE** (prose → text → Editor); an agent slug in `app` is `app_invalid`. `kind='standing'`, `system:standing` (historical `system:strings` display-resolved), `funnel_decision='standing'` (mig 251 BEFORE the code). Detail: ADR-LEDGER. Gate: `test_adr639_standing_work.py`. |
| **Connectors (ADR-582/591/594)** | `docs/architecture/connectors.md` + `services/connectors.py`. **A connection is consent + credential + aperture; a capture is a CONSUMER's act**, landing attributed observations at the FIXED intake lane. ONE selection store (`landscape.selected_sources`); ⭐⭐⭐**NO per-connection settings** (ADR-594 D1 deleted the destination dial). Raw is addressed by MECHANISM (`system:capture-{platform}` + `observation`); meaning lives at the CONSUMER layer. ⭐⭐⭐**No clock** (ADR-591) — the seam's caller is a string's run. Detail: ADR-LEDGER. Gates: `test_adr591_no_pull_job.py` · `test_adr582_connectors.py`. **ADR-635 — attached connectors**: `services/attached_connectors.py` + `connector_directory.py`; a row keyed `mcp:{slug}`; the DIRECTORY is CONSUMED (the registry + a seed DERIVED by `scripts/refresh_connector_directory.py`), never authored; the APERTURE is per-tool consent on the CONNECTION (`direct`/`propose`/unlisted = DENY); a `propose` call is the queue's first producer. `TrackForeign` is DELETED. Gate: `test_adr635_attached_connectors.py`. |
| Invocation & Narrative (canonical) | `docs/architecture/invocation-and-narrative.md` (FOUNDATIONS Axiom 9: atom = one cycle of the six dimensions; narrative = single chat-shaped log of every invocation; task = nameplate + pulse + contract legibility wrapper; the `/work`→`/recurrence` view is DELETED (ADR-603 D5)) |

---

## Common Pitfalls

1. **Schema mismatch**: Code referencing dropped/renamed tables — `agents`/`agent_runs` no longer exist (mig 248); verify against the live schema
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
