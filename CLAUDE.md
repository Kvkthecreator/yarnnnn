# CLAUDE.md - Development Guidelines for YARNNN

This file provides context and guidelines for Claude Code when working on this codebase.

## Project Overview

YARNNN is an **autonomous agent platform for recurring knowledge work**. Persistent AI agents connect to work platforms (Slack, Notion), run on schedule, learn from feedback, and produce outputs that improve with tenure.

**Architecture**: Next.js frontend → FastAPI backend → Supabase (Postgres) → Claude API. Agents (identity) + Tasks (work units) as core model.

> **OS framing note (ADR-222 + FOUNDATIONS Principle 16)**: YARNNN is an **agent-native operating system**. Substrate (filesystem + primitives + axioms + daemons) = **kernel**; primitive matrix = **syscall ABI**; chat agent = **shell**; workspaces = **userspaces**; programs = **applications**, shipped as an `.app`-equivalent bundle at `docs/programs/{program}/`. **The kernel boundary is sacred** — programs never modify the kernel; the shell is application code; the compositor reads but never authors. Workspaces have no "types": they run programs, and specialization happens at the compositor, not the kernel. See [ADR-222](docs/adr/ADR-222-agent-native-operating-system-framing.md) + FOUNDATIONS + GLOSSARY.

> **Surface model note**: the authenticated workspace is an OS desktop of windowed surfaces driven by one
> window manager (`useSurfacePreferences`), with content parsers in `web/lib/content-shapes/` and structured
> affordances in `web/components/library/` (ADR-245's three-layer rendering). **The surface roster churns fast** —
> Home and Channels were both deleted (ADR-435, ADR-415) after long stints in this file. Do not trust a surface
> list written here; read [compositor.md](docs/architecture/compositor.md) and the FE `SurfaceRegistry` for the
> live set. Redirect stubs are pure server transport (`redirect()`, ADR-308) — never `'use client'` + `useEffect`.

> **Vocabulary note**: ADR-216's "agent = persona-bearing judgment entity" is superseded by **ADR-596: an agent is a BEING** (see the Agents-are-BEINGS row). Production machinery is **Orchestration**, never persona-bearing. Current taxonomy: [LAYER-MAPPING.md](docs/architecture/LAYER-MAPPING.md) + Key terminology below.

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

**Wake architecture (ADR-296 v2; steward-side, dissolving per ADR-596 D3).** The Reviewer is event-fired: wake sources → one funnel (`services/wake_evaluation.py`); **singular gateway `services/wake.py::submit_wake_proposal`**; only `services/wake_sources/*.py` may wake it; `FireInvocation` is `CHAT_PRIMITIVES`-only. The `cron_tick` (recurrence) source is INERT since ADR-603 D5. Detail: [ADR-LEDGER](docs/architecture/ADR-LEDGER.md) + [ADR-296](docs/adr/ADR-296-continuous-judgment-cycle.md).

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

**Canonical homes; do not re-derive, look them up first.** Per ADR-315 the Reviewer canon splits along the seat≠occupant line — start at [`reviewer-substrate.md`](docs/architecture/reviewer-substrate.md), a one-screen index routing to:

- [`reviewer-seat-substrate.md`](docs/architecture/reviewer-seat-substrate.md) — the **kernel/seat** canon (the seat is substrate): seat files, occupant rotation, calibration trail, delegation vocabulary, prospective-attribution contract.
- [`reviewer-occupant.md`](docs/architecture/reviewer-occupant.md) — the **occupant** canon: `freddie_agent.py`, occupant classes, model-by-trigger, persona-frame discipline.
- [`reviewer-occupant-contract.md`](docs/architecture/reviewer-occupant-contract.md) — the **published ABI**, defined in `api/agents/occupant_contract.py` (pure data, no LLM runtime — **the kernel depends on the contract, never on the occupant impl**).
- [`agent-composition.md`](docs/architecture/agent-composition.md) **§3.2.1** — **the singular enforcement home** for the partition between `principles.md` (the rule-set) and the persona-frame `_compute_*` sections (the reasoning posture): the rule shape, what must NOT go in `principles.md`, and the conflict-resolution order (PRECEDENT > principles; persona-frame > principles for posture; AUTONOMY ceiling > principles for delegation).

**When to consult §3.2.1**: before editing any bundle `principles.md`; before drafting an ADR that prescribes its content; before adding a `_compute_*` section to `freddie_agent.py`. Future ADRs reshaping principles.md content **must update §3.2.1 in the same commit**.

The one-line statement (canonized at `agent-composition.md` §4.2 + §3.2.1): **persona is *how to reason*; mandate is *why we exist*; autonomy is *how far decisions bind*; principles is *what the rules of judgment are*.**

### ADR-064: Unified Memory Service (updated by ADR-156, post-ADR-235)

**Memory is in-session** — YARNNN writes facts proactively via `WriteFile(scope="workspace", path="memory/notes.md", content="...", mode="append")` during conversation. Follows the Claude Code model: memory happens in the moment of learning, not as a batch job. **Nightly cron extraction is REMOVED** (ADR-156) — session summaries generate inline at session close (chat.py); shift notes go to AWARENESS.md; the user can still edit memories via the Context page.

**Key files**:
- `api/services/memory.py` — `process_conversation` / `get_for_prompt` / `extract_from_text_to_user_memory`
- `api/services/working_memory.py` — formats memory for prompt injection
- Memory-write guidance now lives in the system agent's frame (`api/agents/freddie_agent.py`); the `agents/prompts/` profile registry is DELETED.
- `docs/features/memory.md` — user-facing docs

### Schema (tables + columns)

**Per-table detail lives in [docs/database/SCHEMA-NOTES.md](docs/database/SCHEMA-NOTES.md)** — current table names, deprecated columns, and the ADR history behind each. Read it on demand; `supabase/migrations/` is authoritative for actual DDL.

The rule that matters every session: **use current names.** `agents` not `deliverables`, `agent_runs` not `deliverable_versions`, `platform_connections` not `user_integrations`. Verify against the live schema before writing a query.

### Platform sync + agent workspace (ADR-056/057/077/106, post-ADR-153)

**There is no platform-content store.** `platform_content`, `platform_worker.py`, and `platform_sync_scheduler.py` are DELETED (ADR-153); agents call platform APIs **live** during execution. Preserved: `platform_connections` (OAuth tokens), the API clients, `sync_registry`, `landscape.py`.

**The workspace is a virtual filesystem over Postgres** (ADR-106) — path-based `read`/`write`/`list`/`search` over `workspace_files` (`path`, `content`, `embedding`, `tags`), behind the storage-agnostic `AgentWorkspace` class (`api/services/workspace.py`; primitives in `api/services/primitives/workspace.py`). Reasoning agents gather their own context from the workspace — never a pre-gathered platform dump. History: [ADR-LEDGER](docs/architecture/ADR-LEDGER.md).

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
| **Folders + told-names (ADR-588)** | `api/services/workspace_paths.py`. **Folders do not exist in the substrate** — a folder exists iff a file exists under its prefix, the tree is DERIVED (`_build_tree`). An EMPTY folder is a MARKER row: trailing-slash path + `content_type='inode/directory'`, written via `write_revision` (NOT `WriteFile` — its empty-content guard correctly refuses a 0-byte write). ⭐**The trailing slash is load-bearing**: `git_export._repo_rel` already rejects it (a zero-byte blob named `acme` would collide with the tree entry `acme/`), and `…/acme` vs `…/acme/` are distinct unique-index keys. Filter every listing/search/export on `is_folder_marker` (the ADR-395 `is_upload_projection` precedent — hide at PRESENTATION, never at authorization). ⭐⭐⭐**`PARTICIPANT_FILESYSTEM_MODEL` TELLS every LLM "Documents"/"Downloads"; the kernel has `operation/`/`inbound/`** — `HOME_ALIASES` resolves the told-name at `parse_file_reference`, the ONE interop chokepoint (read AND write, so the round-trip holds). RESOLVE, never refuse: the participant used the vocabulary we handed it. Un-aliased, this minted a real `/workspace/Documents/` twin — the ADR-373 D6 incorrect-success class. Gate: `test_adr588_folder_markers_and_home_aliases.py`. |
| Workspace Utilities | `api/services/workspace_utils.py` — `is_skeleton_content()` + `classify_file_state()`. Single source of truth for skeleton detection (used by init, workspace state surface, and activation state classifier). |
| Program Lifecycle (fork) | `api/services/programs.py` — `fork_reference_workspace()`, `_strip_tier_frontmatter()`, `parse_active_program_slug()`, `strip_program_marker_from_mandate()`. Bundle fork logic is here, not in workspace_init. |
| Back-Office Lifecycle | `materialize_back_office_task()` lives in `api/services/workspace_init.py`; the `services/back_office/` package is DELETED (ADR-260/261). |
| **Platform credentials (ADR-577)** | `api/services/platform_credentials.py` — the ONE path. **A human's account credential, keyed `user_id`. There is NO workspace credential store** — ADR-566's second store is withdrawn (unfillable, mis-filled by migration 201's owner-fill trigger, unreadable under `user_id` RLS). **An AGENT caller is REFUSED and logged**, never falling through to the owner's token — the guard ADR-566 specified but keyed on an `own-agent` role that ZERO rows hold, behind a `workspace_id` `HeadlessAuth` never carried. `platform_connections.workspace_id` = **routing**, never ownership. Re-entry needs a DRIVEN TRACE (ADR-577 §7). Gate: `test_adr577_credential_claim.py`. |
| Agent Workspace | `api/services/workspace.py` |
| Workspace Primitives | `api/services/primitives/workspace.py` |
| Authored Substrate (ADR-209) | `api/services/authored_substrate.py` — **`write_revision()` is the single write path** for every `workspace_files` content-layer mutation (also `list_revisions` / `read_revision` / `count_revisions` / `is_valid_author`). ADR **CLOSED** (Phase 5, 2026-04-23). **Permitted direct-mutation exceptions (2 only)**: `authored_substrate._upsert_workspace_file` (the write target) and `primitives/workspace._embed_workspace_file` (metadata-only embedding update). `workspace_files.content` denormalization is retained deliberately (FTS + embedding indexes require it). The `/history/` subfolder convention, `_archive_to_history`, `_cap_history`, `_is_evolving_file`, `list_history` and the ADR-176 `v{N}.md` archive are all DELETED — do not reintroduce filename versioning. Guard: `api/test_adr209_no_filename_versioning.py`. Phase history + per-phase gate counts: [ADR-LEDGER](docs/architecture/ADR-LEDGER.md). |
| Agent Framework (canonical) | [docs/architecture/orchestration.md](docs/architecture/orchestration.md) + [agent-composition.md](docs/architecture/agent-composition.md) |
| Directory Registry | `api/services/directory_registry.py` — `WORKSPACE_DIRECTORIES` (context domains, uploads, output categories) |
| Agent Framework (code) | `api/services/orchestration.py` — mostly kernel default-content constants (`DEFAULT_*_MD`, `KERNEL_VERSION`, steward defaults) + role/capability resolution (`resolve_role`, `has_capability`, `ALL_ROLES`). ⚠️ `AGENT_TEMPLATES` + `AGENT_TYPES` are **DELETED** — a gate forbids reintroducing them (`test_adr269_capability_flow.py`). |
| Agent Playbook Framework | `docs/features/agent-playbook-framework.md` (playbook loading, selective injection, governing axioms) |
| Agent Creation (shared) | `api/services/agent_creation.py` |
| DELETED — do not reintroduce | Composer/Heartbeat (ADR-156), Pulse Engine (ADR-141), Invocation Dispatcher + Dispatch Helpers (ADR-260/261), the headless task pipeline (`task_pipeline.py`, `task_workspace.py`, `task_types.py`, `task_derivation.py`, `primitives/manage_task.py` — ADR-231), Platform Sync Worker + Scheduler (ADR-153), Task Deliverable Inference (ADR-231), Dashboard Summary. **Wakes route through `services/wake.py` → `wake_drainer.py`; sub-LLM calls through `primitives/dispatch_specialist.py`.** |
| **Recurrences (RETIRED — ADR-603 D5, 2026-08-24)** | Concept + every member surface DELETED (production: 0 declarations — retire-clean): `routes/recurrences.py` + `routes/narrative.py`, the `recurrence`/`activity` surface rows, the whole FE chain. Run receipts = notifications Activity ledger. **Steward-side plumbing survives INERT** (`services/recurrence.py`, `Schedule`/`FireInvocation`, scheduler dispatch, bundle seeding) — dies with ADR-596 D3 phase (a); do not build on it. Standing work = the **standing declaration** (`services/standing_declarations.py`; strings first instance). |
| Scheduling | `api/services/scheduling.py` — `compute_next_run_at` (shared by strings + capture); its recurrence slice is inert per ADR-603 D5 |
| Inference Primitives | DELETED — `InferContext` + `InferWorkspace` are dissolved; identity/brand authoring flows through ordinary substrate writes. |
| Substrate Write Primitive (ADR-235 D1.b + Option A) | `api/services/primitives/workspace.py::handle_write_file` with `scope='workspace'`. Reaches operator-shared substrate (`context/_shared/*`, `memory/*`, `reports/*/feedback.md`, etc.) via workspace-relative path. Recognized canonical paths emit activity-log events automatically. |
| Feedback Formatters (ADR-235 D1.b) | `api/services/feedback_formatters.py` — pure-Python helpers for memory/agent/task feedback formatting; called server-side from chat dispatch when feedback is being routed. |
| Agent Execution (deleted) | DELETED (ADR-271 dead-headless-path sweep) — `execute_agent_generation` / `generate_draft_inline` / `_build_headless_system_prompt` are gone. **Two live execution paths**: scheduler walkers → `wake_queue` → `wake_drainer` → `invoke_freddie`, and chat → `invoke_freddie(trigger='addressed')`. Sub-LLM calls go through `dispatch_specialist.py`. |
| Feedback Distillation | `api/services/feedback_distillation.py` — edits distil to the natural-home `_feedback.md`. |
| Feedback Engine | `api/services/feedback_engine.py` (edit metrics computation) |
| Agent Routes | `api/routes/agents.py` |
| Platform API Clients | `api/integrations/core/{slack,notion,github}_client.py` |
| Landscape Discovery | `api/services/landscape.py` |
| Tier Limits | `api/services/platform_limits.py` |
| Agent Scheduler | `api/jobs/unified_scheduler.py` — the recurrence walk is INERT since ADR-603 D5 (0 declarations; the dispatch stack dies with ADR-596 D3 phase (a)); the live lanes are the strings drain (`drain_due_string_runs`) + capture lane + wake-queue maintenance. Walkers **enqueue** to `wake_queue` via `submit_wake_proposal`; the tick then calls `wake_queue.reclaim_stale_locks` (crash recovery) + `wake_drainer.drain_all_users_with_pending(client)`. **`submit_wake_proposal` does NOT invoke the Reviewer inline** — execution happens in the drainer (ADR-298). |
| Wake Queue (ADR-298) | `api/services/wake_queue.py` — single-lane Reviewer execution per workspace, two-lane drain (paced/live), cross-source dedup at insert time. Transient compute per Axiom 1. |
| Wake Drainer (ADR-298) | `api/services/wake_drainer.py` — pulls pending wakes, respects paced-lane pace cap + single-in-flight, dispatches to the source-specific Reviewer-invocation body. Called from the scheduler tick after the walker block. |
| **Which model runs (ADR-556 + ADR-557 D3)** | **FOUR determinants — never merge them.** (1) **Machinery** → `api/services/system_calls.py`, keyed by CALL TYPE (`resolve_system_call` / `system_call_model`), env `YARNNN_SYSCALL_{CALL_TYPE}`. (2) **An APP** (Slides · Text · IMAGES · strings — the Docs app is DELETED in full per ADR-599 D5; radar DELETED) → **its RESIDENT**, declared in the app's OWN module and resolved SERVER-side (ADR-562): `services/authoring.py` (slides · text) + `services/apps/images/stage.py` + `services/apps/__init__.py` (strings), all through `register_app` → `resident_for_app()`; the being's engine comes from the ONE register `agents_registry.AGENTS` (ADR-600 — `KERNEL_AGENTS`/`KERNEL_POSTURES`/`APP_RESIDENTS` are deleted). `web/lib/apps/authoring.ts` is **DELETED** — the client names the APP, never a colleague; `CreateLaneRequest` is `extra="forbid"` so a stale `agent` is refused, not dropped. A canvas-less derive lane takes the RECIPE's resident (`DERIVE_RECIPES[…]["resident"]`). An app's engine follows its resident, NEVER a caller-supplied model id (residents: see the Agents-are-BEINGS row). Gate: `test_adr562_app_owned_config.py`. (3) **The open surface** (chat) → the member picks the COLLEAGUE; the engine rides behind the name (ADR-460); no default (ADR-467 D2). (4) **The steward** → `services/model_selection.py`, keyed by trigger shape, Anthropic-direct for prompt caching (ADR-463 D3; `freddie_agent.py` must never import `model_router`). Every row is `provider/model`-prefixed and must have a `_BILLING_RATES` row. Gates: `test_adr556_system_calls.py`, `test_adr557_router_hardening.py`. |
| **Engine registry (ADR-559)** | `LANE_MODELS` is the **turn-time whitelist**, not just the chooser — **deleting a row breaks every lane pinned to it** (at the 2026-08-12 refresh all 65 live lanes pinned `claude-sonnet-4-6`). Superseded engines carry `retired: True`: still routable, gone from the door. `offered_lane_models()` is the chooser's view; the loops gate on the full dict. Retired rows KEEP their `_BILLING_RATES` row (`unpriced_lane_model` gates every turn). **Availability has three reasons** — `no_provider_key` + `unpriced` (computed) and `upstream_refused` (OBSERVED via `note_upstream_refusal`, healed by any success; narrow — a timeout or rate-limit must NOT darken an engine). Unavailable engines are **served greyed with a reason, never filtered** — hiding reads as a bug. `create_lane` refuses at the door, before the lane row exists. Gate: `api/test_adr559_engine_registry.py`. ⚠️ **`_BILLING_RATES` carries STANDING list price — never an introductory or promotional rate, any engine, any provider** (ADR-559 D1.a). A promo rate must be un-entered on a date nobody watches, so it silently under-charges the day it lapses; a standing rate is wrong by a bounded amount and VISIBLE in the ADR-408 D4 rate mirror. Sonnet 5 reads x1.50 there today **by rule, not defect** — do not "fix" it. |
| **Router flags (ADR-557)** | **TWO flags, two questions.** `MODEL_ROUTER_ENABLED` = *is multi-provider TRANSPORT available* (infra). `lanes_enabled()` = *are member LANES GA* (product); `LANES_ENABLED` unset defers to transport, so the split ships inert. **A product flag may never grant more than the infra it rides on.** The transport ENFORCES its own flag (`_assert_router_enabled` → `RouterDisabled`) before the lazy litellm import — it is not a convention call sites may forget (one did, and a flag-off sweep reached the provider over the network). Machinery callers read the transport flag; only lane paths read `lanes_enabled()`. |
| Pace / cadence | No `services/pace.py` — DELETED; the ADR-327 `minimum_pace` bundle gate is deleted too. Pace state reads via `api/services/wake.py` + `budget.py`; the substrate path constant is in `services/workspace_paths.py`. Cost governance is `governance/_budget.yaml` (ADR-327). |
| Workspace Export (ADR-328 D4 / ADR-510) | `api/services/export/git_export.py` — Category 1 → a plain git repo (pure-Python loose objects) + `EXPORT-MANIFEST.md` declaring omissions; served by `GET /api/workspace/export`. Binary substrate has ONE lane: `write_revision(content_bytes=…)` → the ADR-427 CAS seam (ADR-510 deleted the design-system import's bucket lane). |
| MCP Server | `api/mcp_server/` (ADR-075 infra + ADR-543/545 file-native tool surface: `open` / `list` / `search` / `save` / `edit` / `delete` / `move` / `history` / `share` — each a binding of a kernel verb per ADR-512 D3 + ADR-337; caller of `execute_primitive()` per ADR-164; roster is `_INTEROP_VERBS`). **ADR-584 adds `whoami`** — the one verb whose subject is the CONNECTION, not a file. ⭐**A new verb needs a rendering story** (`presentation/affordances.py`: a widget or a written `TEXT_ONLY` reason) or `test_adr533_participant_contract.py` fails. ⭐Verb counts are DERIVED — never pin `== 9`; the roster grows and a hand-kept count reads growth as a violation. |
| **Connector workspace identity (ADR-584)** | **`whoami` answers *where am I standing*.** The workspace is otherwise invisible to a connected principal: it lives as a bare UUID on `AuthenticatedClient.workspace_id`, is a query filter only, and is discarded before every response — **no `compose_*` file verb carries a workspace key, and that envelope shape is REJECTED, not merely absent** (gated). ⭐⭐⭐**`binding` is the point**: ADR-573's degrade of an unreachable stamped workspace to the principal's default is deliberate and STAYS, but it was *unobservable* — the ADR-373 D6 incorrect-success class surviving in the branch D6 didn't cover. `resolve_mcp_workspace_detail()` returns `(workspace_id, binding)`; **`resolve_mcp_workspace()` keeps its exact signature/return for its ~90 callers.** The workspace NAME is an **address, not intent** — ADR-533 D6 (the MANDATE does not port) is unchanged and gated. Gate: `test_adr584_connector_names_its_workspace.py` (py3.11). |
| MCP Composition | `api/services/mcp_composition.py` (ADR-543/545: `compose_{open,list,search,save,edit,delete,move,history}` + ADR-584 `compose_whoami`, `parse_file_reference` / `format_file_reference` (the ADR-512 D5 handle grammar), `derive_client_name_from_token`; principal display via `services/principal_display.py`; the memory-verb machinery is DELETED) |
| MCP Feature Docs | `docs/features/mcp/` — `README.md` (entry), `tool-contracts.md`, `workflows.md`, `architecture.md` (ADR-169 canonical product framing) |
| Output Gateway + RuntimeDispatch | **DELETED (ADR-417)** — **generation is rented, not owned**; yarnnn hosts no generation/rendering engine. The `render/` tree, its Docker deployment, and the asset-generation primitive (chart/mermaid/image/video) are all retired; `designer` collapses to compose-only and `has_asset_capabilities()` returns `False` universally. |
| Compose Engine (in-API) | `api/services/compose/engine.py` (ADR-417) — pure-Python section→styled-HTML templating. The two matplotlib chart kinds did NOT port (they degrade to native data-tables). Callers: `compose/task_html.py`, `primitives/{compose,repurpose}.py`. |
| Frontend API Client | `web/lib/api/client.ts` |
| Onboarding / First-run UI | `web/app/auth/callback/page.tsx` (redirect gate). Per ADR-414 D4 genesis is pure — no skeleton seeding; `web/components/onboarding/` and the Settings WorkspaceSection are DELETED. |
| **App exposure (ADR-592)** | **One `stage` per app row** (`internal|search-only|beta|primary`, `services/app_stage.py`); `launcher_tier`+`default_pinned` are DERIVED. ⭐⭐⭐**`internal` REMOVES the row from the served roster** — nav is backend-driven, so that IS the hide, and it reaches a **curated Dock** where a `DEFAULT_KEPT_SURFACES` edit cannot (the reseed fires only on byte-equality — why ADR-574's Docs pause never landed). ⚠️**Obligation: route → redirect stub AND hand-listed in `middleware.ts`**; `SURFACE_PREFIXES` is roster-derived, so a slug leaving the roster leaves the **auth gate** with it. ⭐**An app with a CLOCK is deleted, not staged** (spend). Gate: `test_adr592_app_stage.py`. |
| **Agents are BEINGS (ADR-596→604)** | An agent = identity ⊕ character ⊕ engine; **authority/clock/judgment live on grants, declarations and gates — never on the being** (ADR-596 D1). ONE register: `agents_registry.AGENTS` + `offered` + `kernel` (ADR-600/601 — the three-register split is deleted). Capability lives at the APP, so many-to-one is free: Editor → slides·text · Designer → images · **Supervisor → strings voice / Keeper → strings standing executor** (ADR-604's split; the dedicated supervisor app is DELETED). `is_promoted` derives from app stage; `assert_editable` is the one edit chokepoint. A **standing declaration** names the APP, the agent derives (ADR-603 D2); Supervisor authors declarations, never commands beings. Freddie's dissolution is PHASED (ADR-596 D3). Gates: `test_agent_registry.py` · `test_adr597…` · `test_adr603…`. |
| **Chat vs Agents (ADR-558)** | **Two surfaces, two questions — do not re-merge them.** **Chat** (`web/components/chat-surface/`) is the ENGINE surface: starting a conversation picks an engine (sticky last-used), and `create_lane` **422s on `agent` for an unbound lane**. **Agents** (`web/components/agents/`) shows BEINGS — the ONE register (`AGENTS`, ADR-600), sectioned by desk with provenance served (`kernel`/`homes`, ADR-601 D4); the member-agent machinery (`_agent.yaml`, `based_on`) is DELETED (ADR-599 D2/D3). Who REPLIES is the **cast** (`conversation_cast`, ADR-495), joined from inside a conversation — never chosen at the door. `lane_meta["agent"]` survives for **bound** lanes only (the app registration pins the resident, derived at read time — ADR-467 D1/ADR-597 D1; ADR-602 D7: a bound lane belongs to an app, stamped or not). Gate: `api/test_adr558_chat_is_engines.py`. |
| Agents Page (Home) | `web/app/(authenticated)/agents/page.tsx` |
| Chat Page | `web/app/(authenticated)/chat/page.tsx` |
| Route Constants | `web/lib/routes.ts` (HOME_ROUTE = "/chat" per ADR-205 F1) |
| Workspace Surface Contracts | `docs/design/WORKSPACE.md` (renamed from SURFACE-CONTRACTS.md 2026-05-12; ADR-215: per-tab contracts + 4-shape CRUD matrix for Chat · Work · Agents · Files; paired with `docs/architecture/WORKSPACE.md`) |
| **Intake pipeline (CANON)** | `docs/architecture/intake-pipeline.md` — how ANYTHING from outside reaches the commons: `retain → distil → signal → read`, path grammar **`inbound/{lane}/{selector}/{stamp}.{ext}`** (BINDING; four live lanes already conform). ⭐⭐**TWO DISPOSITIONS of platform reach (§5, GLOSSARY): INTAKE (durable, this pipeline) vs TURN REACH (transient — conventional-MCP shape; NOT built, a named seam). A reach proposal must declare which in its first paragraph.** ⭐**The tenant roster is NOT part of the contract** — lanes and the apps above them churn; never name a lane after its first consumer. Raw = `system:{mechanism}` + `revision_kind='observation'`; DERIVED = **`system:derive-{lane} on behalf of {owner}`**, encoded `authored_by` + `author_identity_uuid=connected_by`, sentence composed at DISPLAY (ADR-580 D4; ADR-401 D1 intact, ADR-378 §7 stays closed). Derive is per-lane WITH A STATED REASON (`mcp` correctly does not; connector lanes derive via a Strings md string — ADR-594 D3 superseded the ADR-580 digest; D1 re-fixed the grammar as LAW). |
| **Connectors (ADR-582/591/594 — the connection is a RAIL)** | `docs/architecture/connectors.md` + `api/services/connectors.py`. **A connection is consent + credential + aperture; a capture is a CONSUMER's act, landing attributed observations at the FIXED intake lane; anything built from them cites them.** ONE selection store (`landscape.selected_sources`); ⭐⭐⭐**NO per-connection settings** — ADR-594 D1 deleted the destination dial; `settings["connector"]` is an unread fossil. Raw is addressed by MECHANISM (`system:capture-{platform}` + `observation`, never embedded); meaning lives at the CONSUMER layer. ⭐`connector_watch.py` + `CaptureConnector` + seed-at-select + `connector_derive.py` are DELETED — the digest is an md string with `connector:` sources (ADR-594 D3). ⭐⭐⭐**No clock** (ADR-591) — the seam's caller is **a string's run** (ADR-594 D2, "reach with a receipt"): `run_connector_capture(…, selectors=)` = ask ∩ aperture, freshness-floored (`strings._CONNECTOR_CAPTURE_MIN_INTERVAL_S`), owner's token via non-agent `system:connector-capture` (ADR-577 untouched). Retention dial = a PRICING axis (disposition owed). ADR-393's lane keeps its own `CAPTURE_LANE_ENABLED`. Gates: `test_adr591_no_pull_job.py` · `test_adr582_connectors.py` · `test_adr569_strings.py` §7. |
| Invocation & Narrative (canonical) | `docs/architecture/invocation-and-narrative.md` (FOUNDATIONS Axiom 9: atom = one cycle of the six dimensions; narrative = single chat-shaped log of every invocation; task = nameplate + pulse + contract legibility wrapper; the `/work`→`/recurrence` view is DELETED (ADR-603 D5)) |

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
