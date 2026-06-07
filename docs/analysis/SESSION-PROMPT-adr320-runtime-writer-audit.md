# Spin-off Session Prompt — ADR-320 Runtime-Writer Audit

> Copy everything below the line into a fresh Claude Code session in the `/Users/macbook/yarnnn` repo. It is context-complete; the new session has none of the migration context, so it front-loads what it needs.

---

You are auditing the YARNNN codebase after a large filesystem-topology migration (ADR-320). Your job is a **runtime-writer audit**: verify that **every code path + agent that WRITES a workspace file at runtime targets the correct new root**. This is Hat-A (system canon) work with Hat-B discipline (substrate receipts under every claim).

## Background you must load first (read these, in order)

1. `docs/adr/ADR-320-constitution-region-topological-cut.md` — the migration. Five roots replaced the old layout. Read the "Decision — five roots" + "Claim tiering" sections.
2. `docs/architecture/FOUNDATIONS.md` Derived Principle 25 (search "Derived Principle 25") — the canonical statement.
3. `api/services/workspace_paths.py` — the SINGLE source of path constants + `CALLER_WRITE_POLICY`. This is the authority; every writer should resolve paths from here.

## The mapping (old → new) that the migration applied

```
context/_shared/{AUTONOMY,_autonomy,_token_budget,_pace,_preferences}  → governance/
context/_shared/{MANDATE,PRECEDENT}                                     → constitution/
context/_shared/IDENTITY.md (operator posture) + review/IDENTITY.md     → persona/IDENTITY.md (COLLAPSED — one file)
review/{principles,_principles,judgment_log,OCCUPANT,handoffs,calibration,standing_intent}  → persona/
context/{domain}/  (trading, authored, portfolio, customers, revenue, audience, ...)        → operation/{domain}/
context/_shared/{BRAND,CONVENTIONS} + specs/ + reports/ + operations/   → operation/
memory/                                                                 → system/
```

## Why this audit exists (the failure pattern — read carefully)

The migration session's reader-inventory (path *references*) was thorough and grep-able. But the live system surprised us **twice** with **writers** the reader-audit missed:

1. **Scheduler world-mirror race**: the deployed old-code scheduler (`system:sync-platform-state`) kept re-writing `context/portfolio/_account.yaml` etc. at OLD paths every tick until the new code deployed. (Resolved — frozen pre-deploy, deleted.)
2. **Reviewer LLM dual-write**: the Reviewer agent (`reviewer:ai:reviewer-sonnet-v8`) kept writing `review/standing_intent.md` at the OLD path AFTER deploy — because it *chose the path in its WriteFile tool call* from a path-less wake-envelope header. The code constants were all correct; the **LLM-facing prompt** named a bare filename, so the model filled in the old directory from prior knowledge. (Fixed in commit `fc86f3b` — full-path headers; verification of the next wake still pending.)

**The lesson**: writers fail differently than readers. A writer can (a) use a stale literal, (b) use the right constant but a sibling site builds the path differently, or — uniquely for LLM writers — (c) the code is right but the *prompt* tells the model the wrong path. Your audit must catch all three classes.

## Your task

Produce an **exhaustive inventory of every runtime workspace-file writer**, and for each, verify it targets the correct new root. Cover these writer classes (find others if they exist):

- **Mechanical primitives / mirrors**: `mirror_schedule_index`, `mirror_recent_execution`, `sync-platform-state`, kernel mirrors, reconciler (`outcomes/ledger.py` → `persona/calibration.md` — the one cross-class write), back-office writers.
- **The fork**: `services/programs.py::fork_reference_workspace` (writes bundle templates to new roots; verify the three-way branch).
- **The Reviewer agent** (`api/agents/reviewer_agent.py`): BOTH the code-path writes (dispatcher silent-exit helper) AND the **prompt-driven writes** — audit every wake-envelope header + every "write X" instruction across ALL invocation paths (`addressed`, `reactive`-recurrence, `reactive`-proposal, `manual_fire`) for path-less filenames that the LLM could resolve to an old root. This is the class that bit us.
- **Inference primitives**: `infer_context.py` (identity → persona/IDENTITY.md, brand → operation/BRAND.md — verify the split), any `infer_workspace`.
- **WriteFile / the primitive layer**: `services/primitives/workspace.py` — does any default-path or path-resolution helper prepend an old root?
- **MCP caller** (`yarnnn:mcp`): trace a write through the gate — does `CALLER_WRITE_POLICY["mcp"]` correctly DENY governance/constitution/persona/system and APPLY operation/? (live trace if feasible)
- **workspace_init**: scaffolds kernel-universal paths — correct roots?
- **Specialists** (`dispatch_specialist.py` headless writes), domain agents (`agent:` writes), feedback writers.

For each writer, classify the path source: **constant** (safe — resolves from workspace_paths), **literal** (audit the string), or **LLM-chosen** (audit the prompt that tells the model the path).

## Discipline (non-negotiable)

- **Substrate receipts under every claim.** "Writer X targets the right root" is not a claim until you've shown the path source (constant/literal/prompt line) AND, where feasible, a live DB query proving recent writes land at the new root. DB connection string: `docs/database/ACCESS.md`. Useful query shape: `SELECT path, updated_at, (SELECT authored_by FROM workspace_file_versions v WHERE v.id=f.head_version_id) FROM workspace_files f WHERE <condition> ORDER BY updated_at DESC` — `authored_by` tells you WHICH writer wrote it.
- **Distinguish stale-pre-deploy from live-bug**: a row at an old path with `updated_at` BEFORE the relevant deploy is stale (delete-able); AFTER is a live writer bug (must fix the writer/prompt).
- **Singular implementation**: if you find a writer using a literal where a constant exists, the fix is to use the constant (delete the literal), not to add a second literal.
- **Prompt changes** require an `api/prompts/CHANGELOG.md` entry.
- **Two hats**: writer-code + prompts are Hat-A (system canon). Speak system vocabulary.

## Deliverable

1. A writer inventory table: writer → path-source-class → target root → verified? (receipt).
2. Any rogue-path writer found (the bug + the fix, landed in a commit referencing ADR-320).
3. Confirmation (with a live receipt) that the Reviewer's first post-`fc86f3b`-deploy wake wrote `persona/standing_intent.md` NOT `review/` — this closes the still-pending dual-write verification.
4. A short "writers fully accounted for" sign-off, OR a list of writers that remain unverified with why.

## Known state (so you don't re-investigate)

- ADR-320 shipped in 9 commits ending `fc86f3b` (all on `origin/main`). Live migration (migration 183) moved 295 files + 9289 versions; live DB has zero `context/`/`review/`/`memory/` rows as of the cleanup.
- Backend test gates green: `test_adr320_permission_topology.py` (15/15) + ~188 adjacent. `_is_path_locked(caller_class, path)` is the unified gate (replaced `_is_path_locked_for_reviewer` + `_is_path_locked_for_mcp`).
- KNOWN out-of-scope (do NOT fix here): `test_recent_commits.py` 10 failures (pre-existing ADR-231 rot); `_shared/` conflict-backups (pre-ADR-206 cruft).
