# ADR-208: Workspace Git Backend for Operator-Authored Files

> **Status**: Proposed
> **Date**: 2026-04-22
> **Authors**: KVK, Claude
> **Triggered by**: ADR-207 v1.2 deferral. Operator-authored configuration files (MANDATE.md, IDENTITY.md, BRAND.md, CONVENTIONS.md, domain `_operator_profile.md` + `_risk.md`, `review/principles.md`) are the workspace's CLAUDE.md equivalent. They deserve git-native semantics — version history, branch-based experimentation, diff/revert, push/pull portability — not a middle-ground in-DB versioning substrate that would churn against a real-git migration.
> **Extends**: ADR-106 (Agent Workspace Architecture — filesystem-over-Postgres substrate). Doesn't replace it for accumulated/output files; adds a git backing path for a specific class of authored files.
> **Amends**: ADR-119 (`/history/` subfolder convention). The subfolder convention stays for per-agent memory history on accumulation-style files; git backend handles the workspace-authored configuration set.
> **Reaffirms**: FOUNDATIONS Axiom 1 (filesystem as persistence layer — git repos are still filesystem, just with commit history as a first-class property).

---

## Context

### What this ADR is about

The operator authors a small, high-value set of files that codify how their operation runs:

- `/workspace/context/_shared/MANDATE.md` — the workspace's north star (ADR-207 D2)
- `/workspace/context/_shared/IDENTITY.md` — who the operator is
- `/workspace/context/_shared/BRAND.md` — output voice and style
- `/workspace/context/_shared/CONVENTIONS.md` — workspace filesystem rules
- `/workspace/context/{domain}/_operator_profile.md` — domain-scoped operator spec
- `/workspace/context/{domain}/_risk.md` — domain-scoped hard limits
- `/workspace/review/principles.md` — Reviewer's capital-EV calibration framework

These files share four properties that distinguish them from everything else in `workspace_files`:

1. **Operator-authored, operator-owned.** Unlike accumulated context (domain entities, `_tracker.md`) or task outputs (`_performance.md`, briefings), these are *declarations*. The operator writes them; YARNNN assists via inference but doesn't self-update them.
2. **Configuration-shaped.** They calibrate downstream behavior. A change to `_risk.md` changes what the Reviewer permits; a change to MANDATE.md changes what the workspace is for. They're like `package.json` or `CLAUDE.md` — configuration, not data.
3. **Revision-sensitive.** Operators experiment ("what if I loosen this risk limit?", "what if I add a new Signal?"). Experiments need diff, revert, and optionally branching.
4. **Portable candidates.** An operator should be able to clone their workspace configuration, inspect it locally, share it with a collaborator, push it to a private GitHub repo for backup.

These four properties match exactly what git was designed for. Everything else in `workspace_files` (accumulated domain context, task outputs, platform observations, ephemeral trackers) does *not* have these properties — those are data accumulations, not authored artifacts, and Postgres row storage is correct for them.

### Why not in-DB versioning (the deferred ADR-207 Level 1)

A naive first instinct is a `workspace_file_versions` append-only table. Solves diff + revert + history. But:

- **Can't push/pull.** Operators can't `git clone` an append-only Postgres table into their editor for diffs-at-scale.
- **No branches.** An operator who wants to A/B two rule sets has no substrate for it in append-only DB versioning.
- **No collaborator workflow.** Can't share configuration with a consultant, co-founder, or audit reviewer in a form they can inspect natively.
- **Forces a migration later.** If git is the right answer eventually, building `workspace_file_versions` first means migrating operator history twice — into the DB, then out into real git — with lossy fidelity both times.

**Singular-implementation discipline says: ship git now, skip the middle-ground.**

### Why git as the *backing store*, not just an export format

An export-only approach (dump workspace as a git bundle on request) doesn't give the operator living git state. Every edit in YARNNN creates no commit; every external edit must be re-imported with manual merge. It's portability without versioning.

A backing-store approach (git IS where these files live at rest) means every `UpdateContext` write is a commit. The operator gets commit history for free. Branches are first-class. Push to a remote is a `git push`. Working locally is `git clone + git commit + git push` round-trip.

This is the approach ADR-208 commits to.

---

## Decision

### D1 — Git backend for the operator-authored file set

Per workspace, YARNNN maintains a bare git repository hosting the operator-authored file set. The set is fixed (not operator-configurable):

```
/.yarnnn-authored.git      ← bare repo, per workspace
  HEAD = refs/heads/main
  tracked paths:
    context/_shared/MANDATE.md
    context/_shared/IDENTITY.md
    context/_shared/BRAND.md
    context/_shared/CONVENTIONS.md
    context/{domain}/_operator_profile.md
    context/{domain}/_risk.md
    review/principles.md
```

Every operator-authored write to these paths creates a commit. Everything outside the set stays in `workspace_files` as-is (Postgres row storage; no git involvement).

### D2 — Where the repo lives

Primary storage: **S3-compatible object store** (Supabase Storage or equivalent), one bare repo per workspace at `yarnnn-workspaces/{workspace_id}/authored.git/`. YARNNN's API processes pull the repo, operate on it via `libgit2` (or `pygit2` / `dulwich`), and push changes back.

Why S3 not Postgres: git's object store is already a content-addressed store designed for S3-shaped backends. Putting it in Postgres fights the grain. Supabase Storage (which YARNNN already uses for render assets per ADR-118) is the right home.

`workspace_files` rows for the seven file paths continue to exist but become a **cache + query index** over the git working tree. Reads hit the cache; writes invalidate the cache and commit to git. Source of truth = git; cache = Postgres.

### D3 — Write path: every UpdateContext is a commit

`UpdateContext(target="mandate" | "identity" | "brand" | "conventions" | "operator_profile" | "risk" | "review_principles")`:

1. Compute the new file content (inference, operator direct edit, etc.)
2. Fetch the workspace's `authored.git` (cached locally in the API process; TTL'd).
3. Write the new content to the working tree path.
4. Commit with message = operator-supplied summary, or YARNNN-inferred summary if absent.
5. Push to the S3-backed remote.
6. Update the `workspace_files` cache row for that path.

Commit message format (convention, not schema): `{target}: {summary}\n\nauthored-by: {operator|yarnnn|claude|reviewer}`. Operator and author-of-record both captured.

Atomicity: the write is considered complete when the commit exists locally + remote is pushed. If push fails (network, conflict), the local commit stays queued; next write attempts a rebase + push.

### D4 — Read path: cache-first, repo on miss

`UserMemory.read()` for a tracked path:

1. Check `workspace_files` cache row. If fresh, return.
2. Cache stale / missing → fetch latest commit of the path from git, update cache, return.

Cache freshness is bounded by the last commit SHA — invalidated on every write. Reads are fast; writes are slower (git commit + push).

### D5 — Branches for operator experimentation

Default branch: `main`. YARNNN always reads and writes `main` unless directed otherwise.

Operators can create named branches via a new primitive `ManageBranch(action="create", name, from="main")`. Branches are real git refs. Operators can:

- Ask YARNNN to try a rule change on `experiment/looser-risk` — YARNNN commits to that branch, never touches `main`
- Compare branches via `DiffBranches(a, b)` — returns operator-readable diff
- Merge experiment to main via `ManageBranch(action="merge", from="experiment/looser-risk", to="main")` — YARNNN performs the merge, operator confirms

Under Knowledge-mode (ADR-207 D6), branching still works — it's purely authored-file revision, no execution change.

### D6 — Portability: clone, fork, push

Each workspace exposes a git remote URL:

```
GET /api/workspace/git-url
  → { "remote": "https://git.yarnnn.com/{workspace_id}/authored.git",
      "access": "read-write",
      "auth": "<short-lived-token>" }
```

Operator runs `git clone <url>`. Edits locally. `git push` round-trips back to YARNNN. Incoming push validates against the authored-file set (commits touching non-tracked paths rejected).

Backup / external-collaborator workflows: operator can configure a secondary remote (their own GitHub private repo) — YARNNN mirrors commits on every write if configured. Opt-in.

### D7 — Commit attribution: `authored-by` tag

Each commit records who wrote it via a trailer:

```
identity: short summary of edit

authored-by: operator
# or
authored-by: yarnnn:claude-sonnet-4-6
# or
authored-by: reviewer:ai-sonnet
```

No separate audit table. Commit history IS the audit trail. Matches how git-controlled codebases attribute edits (git blame + commit metadata). Aligns with ADR-194 Reviewer decision attribution pattern.

### D8 — What stays in Postgres (out of scope for git)

- All `workspace_files` rows for paths NOT in the authored set — stay Postgres-only, no versioning
- `_performance.md` per domain — Postgres-only (high write rate, append-style, reconciler-owned — not operator-authored)
- Accumulated domain entities (competitor profiles, SKU trackers, etc.) — Postgres-only
- Per-task `TASK.md` / `DELIVERABLE.md` / `awareness.md` / `feedback.md` — Postgres-only (churn rate too high for git backend to be useful)
- `/workspace/memory/*.md` (YARNNN's internal memory) — Postgres-only
- `/agents/{slug}/*.md` — Postgres-only (agent authorship is domain-cognition-accumulated, not operator-configuration)

**Test for inclusion**: *"Does an operator who wants to audit, revert, or share this file benefit from git semantics?"* If yes, include. If no, Postgres.

---

## What changes (implementation phases)

### Phase 1 — ADR ratification + prototype (this ADR + small follow-up)

This ADR proposes the architecture. Small follow-up commit prototypes the read path against a single file (MANDATE.md) to validate the S3+libgit2 stack choice before full implementation.

### Phase 2 — Git backend for MANDATE.md only

- Schema: Supabase Storage bucket `yarnnn-workspaces/{workspace_id}/authored.git/`
- `api/services/git_backend.py` — wrapper around libgit2 (or pygit2) with read/write/commit/push/clone helpers
- `workspace_init.py` Phase 2 addendum: initialize empty `authored.git` at signup with a seed commit (all skeletons)
- `UpdateContext(target="mandate")` routes writes through git backend; cache row updates on success
- `UserMemory.read()` for MANDATE.md reads cache, falls back to git on miss
- Migration 158: initialize `authored.git` repos for existing workspaces (backfill from current `workspace_files` content)

### Phase 3 — Expand backing to full authored set

- Extend D1's tracked paths to include all seven file classes
- `UpdateContext(target="identity" | "brand" | "conventions" | "operator_profile" | "risk" | "review_principles")` route through git
- Migration 159: backfill existing workspace content into git

### Phase 4 — Remote URL + clone/push

- `/api/workspace/git-url` endpoint
- Token-authenticated HTTPS git (likely via a reverse-proxy + libgit2-smart-http)
- Operator-facing docs: *"To work on your workspace configuration locally, `git clone <url>`..."*

### Phase 5 — Branches + diff/merge primitives

- `ManageBranch(action="create"|"delete"|"list"|"merge", ...)`
- `DiffBranches(a, b, path?)`
- `DiffCommits(sha_a, sha_b, path?)`
- YARNNN prompt guidance on branch-aware reasoning ("operator wants to experiment — create a branch first")

### Phase 6 — External remote mirroring (opt-in)

- `/api/workspace/remote/configure` accepts operator's external remote URL + credentials
- On every local commit, push to external remote if configured
- Backup + collaborator workflow unlocked

---

## Supersedes / amends summary

| ADR | Relationship | Notes |
|---|---|---|
| ADR-106 | **Extended** | Filesystem-over-Postgres substrate preserved for accumulated/output files; git-over-S3 substrate added for operator-authored files. No conflict. |
| ADR-119 | **Amended** | `/history/{filename}-v{N}.md` subfolder convention continues for per-agent-memory versioning. Not used for operator-authored files — git backend supersedes that use-case. |
| ADR-205 / ADR-206 / ADR-207 | **No change** | Substrate conventions preserved; git is just how the authored-file subset is stored at rest. |

---

## What doesn't change

- **FOUNDATIONS v6.0 axioms.** Git repos are filesystem with commit history. Axiom 1 holds.
- **Primitive surface for most primitives.** `UpdateContext` signature unchanged (operator and caller don't know git is under the hood). `ReadFile`, `ListFiles`, `SearchFiles` unchanged for the authored set — cache-first reads keep performance identical to Postgres-only.
- **Reviewer / Money-truth substrates.** `_performance.md` and `decisions.md` continue as Postgres-only accumulation files. Not git-backed.
- **Task / agent substrates.** TASK.md, DELIVERABLE.md, AGENT.md stay Postgres-only.

---

## Consequences

### Positive

- **Operators get CLAUDE.md-like versioning for their configuration.** Matches the mental model of developers using Claude Code: CLAUDE.md is git-versioned; git-blame shows who changed what when; git-log shows evolution over time.
- **Branching enables systematic experimentation.** "Try a looser risk profile for a month" becomes a real branch, not an irreversible edit. Rollback is `git checkout main -- _risk.md`.
- **Portability + audit trail for free.** Compliance asks "show me the history of your Reviewer principles" — answer is `git log review/principles.md`. No custom audit infrastructure.
- **Collaborator workflow.** Co-founder or consultant can `git clone`, propose changes via PR/push, operator reviews in git-native tooling.
- **External backup is trivial.** Operator configures a GitHub private repo as secondary remote; YARNNN mirrors on every commit. Workspace configuration is never lost.
- **Matches real-operator expectations.** Systematic operators (alpha-trader persona) already think in terms of rule changes having a revision history. Git gives them that natively.
- **Avoids a half-built interim substrate.** The ADR-207 Level 1 (in-DB `workspace_file_versions`) would have shipped weeks of implementation for a methodology that gets replaced in months. Skip it.

### Costs

- **Non-trivial implementation**: S3 + libgit2 wrapper + cache-invalidation + remote-auth + reverse-proxy for HTTPS git are real engineering. 6-phase roadmap is genuinely 6 phases, not notional.
- **Two substrate types (Postgres + git) to reason about.** Engineering team must know which files are git-backed vs Postgres-only, and which primitives route through which path. Discipline cost: the authored-file set must be exhaustively enumerated and maintained.
- **Write latency**: commit + push is slower than a Postgres UPDATE. For operator-authored files this is acceptable (writes are rare; reads are frequent and cached). But we must measure in Phase 2 prototype.
- **Merge semantics**: if the operator pushes changes from their local clone at the same time YARNNN makes a change via chat, we have a conflict. Phase 5 branching + merge design must handle this — probably via automatic rebase on push with conflict-surfaced to operator if non-trivial.
- **Storage cost**: every commit adds git objects. A busy workspace with many rule tweaks could accumulate objects. Git's own gc/compaction handles this but needs scheduled runs.
- **Operator UX for git-naive operators**: not every alpha operator is a developer. The "clone your workspace" affordance must degrade gracefully — if the operator never clones, the git backend is invisible (they just see diff + revert in the cockpit).

### Deferred

- **Merge-conflict resolution UX.** Phase 5 will need a thoughtful design. Deferred until we have real operator signal on how often conflicts arise.
- **Per-branch Reviewer calibration.** Does Reviewer read principles.md from `main` or from the current branch? Defaults to `main`; branch-scoped reviewer calibration can ship in a Phase 5.5 if experimentation scales.
- **Git push webhooks**: respond to external pushes (operator pushed from local clone) by re-reading their changes into the cache. Needs Phase 4+.
- **CI-like automation**: "run Reviewer dry-run against this branch before merging to main." Nice-to-have; defer.

---

## Dimensional classification (FOUNDATIONS v6.0)

Primary: **Substrate** (Axiom 1) — git repositories are filesystem with history as a first-class property. Extends the substrate commitment rather than violating it.

Secondary:
- **Identity** (Axiom 2) — commit `authored-by` trailer captures which layer wrote each commit (operator / YARNNN / Reviewer / etc.).
- **Purpose** (Axiom 3) — authored files are operator Intent declarations; git history IS the Purpose-layer's audit trail.
- **Channel** (Axiom 6) — git remote is a new Channel affordance (operator clones, external repo mirroring).
- **Recursion** (Axiom 7) — commit history compounds over time; branching enables systematic experimentation within the Recursion pattern.

---

## Open questions

1. **Monorepo vs. per-workspace repos.** One S3 bucket with per-workspace bare repos is the default. Alternative: one monorepo with per-workspace subdirectories. Per-workspace wins on isolation + simpler auth; monorepo wins on cross-workspace references (if operator ever runs multiple Mandates). Default: per-workspace. Revisit if multi-mandate UX emerges.
2. **Commit author identity for YARNNN.** When YARNNN writes via UpdateContext, commit author is `yarnnn-bot <bot@yarnnn.com>` or similar. What about Reviewer? `reviewer-ai <reviewer@yarnnn.com>`? Naming is bikeshed; load-bearing decision is whether each Identity layer (Axiom 2) gets its own committer email. My default: yes.
3. **Git hosting scale**: Supabase Storage as the S3-compatible backend works for alpha. At scale, does YARNNN run its own git server (Gitea, Gogs) for better smart-http performance? Defer until scale justifies.
4. **Operator-initiated `git push` with dirty YARNNN local**: if YARNNN has uncommitted changes queued when operator pushes from a clone, how is that reconciled? Queued changes become commits that rebase onto the incoming push — or operator is notified "YARNNN has pending edits; rebase or force-push?" Phase 4+ design concern.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-22 | v1 — Initial proposal. Git-backed substrate for the seven operator-authored configuration files (MANDATE, IDENTITY, BRAND, CONVENTIONS, operator_profile per domain, risk per domain, review/principles). S3-backed bare repo per workspace. Every `UpdateContext` write to these paths becomes a commit. Branches + clone + push/pull as operator-facing git-native semantics. Six-phase implementation roadmap. Supersedes ADR-207 Level-1 in-DB versioning that was considered and explicitly deferred to this ADR. Extends ADR-106 substrate commitment to include a git-over-S3 backing path for this authored-file subset. |
