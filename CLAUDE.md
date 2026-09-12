# CLAUDE.md — working in YARNNN

Instruction only. Reference material lives in the canon this file points at. `api/test_claude_md_ratchet.py`
holds this file under a size ceiling that only ratchets down and checks every path cited here exists.
Do not regrow it: a per-ADR ruling belongs in the ADR and the ADR-LEDGER, a schema fact in SCHEMA-NOTES,
craft in a skill, and anything a gate enforces needs no prose at all.

## What YARNNN is

An autonomous agent platform for recurring knowledge work: persistent agents connect to work platforms,
run on schedule, learn from feedback, and produce outputs that improve with tenure. Next.js → FastAPI →
Supabase (Postgres) → Claude API, deployed as three Render services plus Vercel.

Framing (ADR-222): YARNNN is an **agent-native operating system**. The substrate (filesystem + primitives
+ gates) is the **kernel**; the chat lane is the **shell**; workspaces are **userspaces**; apps are
**applications**. The kernel boundary is sacred: apps never modify the kernel, and specialization happens
at the compositor, not the kernel. Workspaces have no types.

## Read the canon before deciding anything

| Question | Read |
|---|---|
| What the product is | [ESSENCE.md](docs/ESSENCE.md) |
| The axioms and derived principles | [FOUNDATIONS.md](docs/architecture/FOUNDATIONS.md) |
| What a word means — terms move, this is authoritative | [GLOSSARY.md](docs/architecture/GLOSSARY.md) · [LAYER-MAPPING.md](docs/architecture/LAYER-MAPPING.md) |
| Whether a decision already exists, and its history | [ADR-LEDGER.md](docs/architecture/ADR-LEDGER.md) (per-ADR notes + supersession chains), then `docs/adr/` |
| The live frontier umbrella: genesis, agents, apps | [ADR-414](docs/adr/ADR-414-the-pure-workspace-genesis-system-agent-program-as-hire.md) |
| Tables, columns, what was dropped | [SCHEMA-NOTES.md](docs/database/SCHEMA-NOTES.md); DDL in `supabase/migrations/`; connection in [ACCESS.md](docs/database/ACCESS.md) |
| The substrate, bootstrap, workspace layers | [architecture/WORKSPACE.md](docs/architecture/WORKSPACE.md) + [design/WORKSPACE.md](docs/design/WORKSPACE.md) |
| Surfaces, windows, the desktop | [compositor.md](docs/architecture/compositor.md) + `web/components/shell/SurfaceRegistry.tsx` — the roster churns; never trust a list written elsewhere |
| What an agent's prompt is made of, and where prose goes | [lane-frame.md](docs/architecture/lane-frame.md) + [agent-composition.md](docs/architecture/agent-composition.md) §3.2.1 |
| Tool primitives | [primitives-matrix.md](docs/architecture/primitives-matrix.md); code registry `api/services/primitives/registry.py` |
| How outside content reaches the commons | [intake-pipeline.md](docs/architecture/intake-pipeline.md) · [connectors.md](docs/architecture/connectors.md) |
| The MCP connector | [docs/features/mcp/](docs/features/mcp/) |
| Orchestration machinery | [orchestration.md](docs/architecture/orchestration.md) |

**Before proposing an architectural change**: `ls docs/adr/ | grep -i <topic>`, then search the ledger. If an
external system does something differently, check whether an ADR already explains why we chose otherwise.

## Load-bearing vocabulary

- **Workspace** — the substrate's binding unit and outermost scope; one multi-principal attributed commons (ADR-373/378).
- **Principal** — anyone who attributes into a workspace: the operator, other humans, their AI connections, agents.
  Permission is a **grant** (`principal_grants`), never a species rule (ADR-405). Reach is a grant, never an ownership
  column: a workspace is not minted until its owner's grant row exists (`ensure_owner_workspace` in `api/services/supabase.py`).
- **Substrate** — the authored filesystem (`workspace_files` + `workspace_file_versions`). Every mutation is attributed
  and parent-pointered; **`write_revision()` in `api/services/authored_substrate.py` is the single write path** (ADR-209).
  No filename versioning. Folders are derived from paths; an empty folder is a trailing-slash marker row (ADR-588).
- **Agent** — identity ⊕ character ⊕ engine and nothing else (ADR-596). Authority, clock, purpose and judgment live on
  grants, declarations and gates, never on the agent; an agent carries no record of its own work (ADR-640). One register:
  `AGENTS` in `api/services/agents_registry.py`. Its home `agents/{slug}/` holds only `memory/` and two locked grant sidecars (ADR-624).
- **Two execution paths, both lanes** — attended: a member's message → `run_lane_turn` in `api/services/lane_runner.py`;
  unattended: a standing declaration → `run_bounded_derive_turn` in `api/services/derive_turn.py`, toolless,
  contract-checked, receipted (ADR-603/618/639). Nothing wakes on its own initiative.
- **Standing work** — a kernel lane, not an app: `{folder}/_standing.yaml` + `CONTRACT.md`
  (`api/services/standing_work.py`), drained by the ONE loop in `api/services/scheduling.py`.
- **Reach** — the boundary's door, a primary kernel surface (ADR-642). One reach structure,
  `api/services/reach_status.py`; a reach sentence anywhere else is a defect (ADR-644). Reach follows the acting
  member: a credential is a human's, keyed by `user_id`, and an agent caller is refused
  (`api/services/platform_credentials.py`, ADR-577). Credential adoption and mirroring are CLOSED (ADR-645 D1).
- **Retired — do not reintroduce**: the steward / Reviewer / Freddie seat with its prompt layer, wake sources, queue
  and drainer (ADR-632); recurrences and their dispatch (ADR-603 D5); the pre-ADR-596 agent model and its eight tables
  (mig 248); the strings app and Supervisor (ADR-639); the output gateway and asset generation (ADR-417); platform sync
  workers (ADR-153). The ledger of deletions and their gates is in ADR-LEDGER. `freddie:` survives only as a
  display-resolved attribution prefix on historical revisions.

## The two hats

Everything under `api/`, `web/`, `docs/adr/`, `docs/architecture/`, `docs/programs/` and every bundle
reference-workspace is **inside the system** real operators inherit — **Hat A, system editor**. Speak system
vocabulary (operator, member, substrate, grant, gate); never introduce "developer", "Claude" or "observation" as
system actors. Singular implementation, doc-first ADR amendments, Render parity.

`api/services/operator_proxy/`, `api/scripts/operator/`, `docs/evaluations/` and pre-ratification ADR drafts are
the **developer toolchain** that probes the system — **Hat B**. Speak evaluation vocabulary (scenario, expected vs
observed, finding). A finding recommends; the fix lands under Hat A.

The test: *would a real operator on a stable release see this change?* Yes → Hat A. What binds both hats:
**a substrate receipt under every load-bearing claim** — revision ids, event ids, reproducible queries. A claim
without a receipt is narrative.

## Execution disciplines

1. **Docs alongside code.** Update the ADR's implementation status, SCHEMA-NOTES and ACCESS on a schema change, and docstrings.
2. **Singular implementation.** Delete legacy code when replacing it; no compatibility shims unless a migration
   explicitly needs one; one way to do a thing.
3. **Database.** Migrations run via `scripts/db/run-migration.sh --dry-run supabase/migrations/NNN.sql`, then for
   real; verify the LIVE object — the runner's exit code is not verification. Use current table names
   (SCHEMA-NOTES) and check the live schema before writing a query. PostgREST may need a cache refresh after DDL.
4. **Before finishing.** Routes match frontend calls; column names match the current schema; imports resolve;
   `cd web && pnpm build` for a frontend change (tsc alone is not verification); a UI change gets a browser click-pass.
5. **Gates.** Every ADR names its gate, `api/test_adr{N}_*.py`; run the one the ADR you touched names. A gate is
   proven RED before its green is trusted; a script-shaped gate reports a count, not an exit code; a gate that
   crashes reports nothing. Driving the path (a click-pass, a real run) finds what reading it cannot.
6. **Git.** Conventional commits with ADR references. Other sessions commit concurrently: commit with
   `git commit --only <paths>`, never `add` then a bare `commit`. No force-push to main.
7. **Render parity.** Three services: `yarnnn-api` (web, `srv-d5sqotcr85hc73dpkqdg`), `yarnnn-unified-scheduler`
   (cron, `crn-d604uqili9vc73ankvag`), `yarnnn-mcp-server` (web, `srv-d6f4vg1drdic739nli4g`). All execution is
   inline: no worker, no Redis. An env var, OAuth or schema change is checked on every service that reads it.
   `INTEGRATION_ENCRYPTION_KEY` and the Notion client pair must be on API **and** scheduler (the scheduler decrypts
   tokens and uses them); the GitHub and WordPress OAuth pairs are API-only; the MCP server uses
   `SUPABASE_SERVICE_KEY` + `MCP_USER_ID` + `MCP_BEARER_TOKEN` + `MCP_SERVER_URL`. The scheduler's lanes: the skills
   mirror, capture (`CAPTURE_LANE_ENABLED`), the standing-work drain.

## File format (ADR-254)

One primary consumer per file; format follows it. `UPPERCASE.md` — operator/LLM prose, never machine-parsed.
`lowercase.md` — append-only narrative. `_name.yaml` — machine-parsed config or state (`yaml.safe_load`; ints are
ints). `.json` — manifests. `.html` — composed artifacts. No new YAML-frontmatter `.md` files; no hand-rolled
frontmatter parsers — `load_workspace_yaml` in `api/services/review_policy.py`, or the one `re.match` + `safe_load` idiom.

## Prompt change protocol

The live frame is `build_lane_conventions` in `api/services/lane_runner.py` (with the standing frame there and
`_STANDING_JOB` in `api/services/standing_work.py`), the app postures in `api/services/authoring.py` and
`api/services/apps/*.py`, the participant constants in `api/services/workspace_paths.py`, the skills in
`api/services/skills/*/SKILL.md`, and the tool definitions in `api/services/primitives/*.py`. Changing any of them:

1. Prepend an entry (newest first) to `api/prompts/CHANGELOG.md` naming the **repeated, observed** failure it
   fixes and the expected behavior change. The file holds the newest two months; older months are frozen in
   `api/prompts/archive/`, held by `api/test_prompt_changelog_discipline.py`.
2. Run the size ratchets: `api/test_adr632_the_seat_retires.py` §5 and `api/test_adr630_skills.py`.
3. Adding is the last resort (ADR-306, FOUNDATIONS DP22). Rules of judgment → `principles.md`; substrate semantics →
   the workspace guide; craft with a contract → a skill; anything a gate enforces → no prose. agent-composition.md
   §3.2.1 is the partition — consult it, don't re-derive it. Raising a ceiling needs the same evidence as adding an
   instruction, named in the raising commit.
4. A skill earns its bytes only for a shape the model has no prior for. Its failure is silent, so **never prune a
   skill on a quality score**; the index roster is argued on reach, never on byte count.
5. How an agent speaks is `PARTICIPANT_REGISTER` (ADR-638): structure rules, A/B-validated. Softening them re-runs the falsified arm.

```markdown
## [YYYY.MM.DD.N] - Description
### Changed
- file.py: what changed and why
- Expected behavior: how this affects behavior
### Why
The repeated, observed failure, with its receipt.
### Gate
The ratchets run and the ADR's gate.
```

## Where things live

| Concern | Path |
|---|---|
| Lane frame, turn loop, engine whitelist `LANE_MODELS` | `api/services/lane_runner.py` |
| Unattended derive turn | `api/services/derive_turn.py` |
| Which engine runs — three determinants, never merged (ADR-556/557/562) | machinery → `api/services/system_calls.py`; an app → its resident via `register_app` in `api/services/authoring.py`; chat → the member's pick, no default |
| Multi-provider transport and the ONLY caching site | `api/services/model_router.py` — `MODEL_ROUTER_ENABLED` is infra, `lanes_enabled()` is product; product never grants more than infra |
| Context budget — one home per rule (ADR-648) | read cap `_clip_read` in `api/services/primitives/workspace.py`; history ceiling `_clamp_history_chars` in `api/routes/lanes.py`, oldest-first; summarisation refused |
| Workspace filesystem over Postgres | `api/services/workspace.py` + `api/services/primitives/workspace.py`; told-names resolve through `HOME_ALIASES` at `parse_file_reference` in `api/services/mcp_composition.py` |
| Genesis and programs | `ensure_owner_workspace` in `api/services/supabase.py` (called from `get_user_client`); `api/services/workspace_init.py`; `api/services/programs.py`; bundles in `docs/programs/{program}/` |
| Skills (ADR-630) | `api/services/skills/{slug}/SKILL.md`, mirrored into every workspace at `system/skills/`; the index is bounded in bytes |
| Scheduling — the one drain loop | `api/services/scheduling.py`; cron entry `api/jobs/unified_scheduler.py` |
| Connectors, attached MCP connectors, credentials | `api/services/connectors.py` · `api/services/attached_connectors.py` · `api/services/platform_credentials.py` · clients in `api/integrations/core/` |
| MCP server — OAuth 2.1 + bearer fallback, scopes, workspace binding | `api/mcp_server/` (`resolve_request_client(verb=…)` is the one auth chokepoint); tiers in `api/services/mcp_scopes.py`; verbs composed in `api/services/mcp_composition.py` |
| Artifact types — the server scopes (ADR-473/646) | `kinds_for_app` in `api/services/authoring.py`; an unowned type opens in the generic viewer, never a default app |
| Export | `api/services/export/git_export.py` → `GET /api/workspace/export` |
| Compose, section → HTML, in-API | `api/services/compose/engine.py` |
| Mentions and attention (ADR-605/637) | `api/services/mentions.py` — one cursor; visiting advances it |
| App exposure stage (ADR-592) | `api/services/app_stage.py`; a slug leaving the roster leaves `web/middleware.ts` with it |
| Client app registry — one `AppDescriptor` per app, never authority-shaped fields (ADR-636) | `web/lib/apps/registry.ts`; icons and accents in `web/lib/shell/surface-icons.tsx` (ADR-641) |
| Routes, window manager, rendering layers | `web/lib/routes.ts` (`HOME_ROUTE` is `/desktop`); `web/lib/shell/surface-preferences.ts`; `web/lib/content-shapes/` + `web/components/library/` |
| Redirect stubs | pure server `redirect()` (ADR-308), never `'use client'` + `useEffect` |
| Memory — in-session, no batch extraction | `api/services/memory.py`; guidance rides the lane frame's commons contract |
| Alpha-ops harness — orchestrates real persona workspaces, so Hat A | `api/scripts/alpha_ops/` |

## Hooks and the verification radar

`.claude/settings.json` wires two `SessionStart` hooks (startup + compact). Hooks carry dynamic state only;
doctrine lives here or in the docs they point at.

| Hook | Purpose |
|---|---|
| `.claude/hooks/session-reorient.sh` | recent commits, branch, uncommitted work, and the open-items file below |
| `.claude/hooks/verification-radar.sh` | which lanes have changes since their last-validated SHA in `.claude/validation-ledger.json`; criteria per lane in [VERIFICATION.md](docs/evaluations/VERIFICATION.md) |
| `.claude/hooks/mark-validated.sh <lane>` | records a lane validated at HEAD — only after its exit criteria are actually met; commit the ledger with the validation |

**`docs/SESSION-HANDOFF.md` holds OPEN items only** — the debt one session leaves the next. Delete an item in the
commit that closes it; narrative goes to the ADR, the evaluation record, or memory. It is not a journal.

## MCP servers (local)

`.mcp.json` wires `sentry` over stdio; the token arrives as `${SENTRY_AUTH_TOKEN}` from the parent shell
(`org:read`, `project:read`, `event:read`, `team:read`). Never paste a token into chat, JSON or git; revoke and
re-mint if it leaks. `.mcp.json` is read at startup, not hot-reloaded.

## Common pitfalls

- Code referencing dropped tables: `agents` and `agent_runs` are gone (mig 248); `platform_connections`, not `user_integrations`.
- An env var added to the API but not the scheduler: the scheduler fails to decrypt and reports success with zero items.
- Backend/frontend field-name drift (`selected_sources` vs `sources`): verify the served shape against its consumer.
- PGRST205: the PostgREST schema cache needs a refresh after table changes.
- A gate green on read and wrong in production: drive the path before believing it.

## Quick commands

```bash
cd api && uvicorn main:app --reload --port 8000                    # API
cd web && pnpm dev                                                  # frontend
scripts/db/run-migration.sh --dry-run supabase/migrations/NNN.sql   # migration, dry first
cd api && python3 -m pytest test_adrNNN_*.py -q                     # an ADR's gate
```
