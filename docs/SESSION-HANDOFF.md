# Session handoff — 2026-08-20

Delete this file in the commit that absorbs it.

---

## What shipped

| Commit | What |
|---|---|
| `91fe2f6` | docs: authored-substrate — replay invariant measured, taxonomy re-synced, the no-compiler argument |
| `3751783` | blog: "Knowledge Work Has No Compiler" + **remark-gfm wired** (tables rendered as raw `\|---\|` on the live site; 4 posts) |
| `c6e9fcc` | feat: the export gets a door — Download Workspace card + purge confirm names the remedy |
| `7cc83a6` | fix: 168/1,613 export commits dated 1970 (py3.9 `fromisoformat`) |
| `d2c1281` | refactor: danger-zone condense — User Settings' dead L1/L2 plumbing deleted (net −81) |
| `5e76e3d` | fix: purge acts on the workspace it was asked about, and fails CLOSED |
| `99f5d51` | chore: api + web lanes validated |

## Measured facts (production, 2026-08-20)

- **Replay is clean**: 391/391 live files byte-identical to their head blob;
  0 dangling parents, 0 forked chains, 0 unattributed of 1,928 revisions.
  `workspace_files.content` is a genuine cache, not a second source of truth.
- **Concurrency is a real CAS** — migration 197's partial UNIQUE on
  `parent_version_id`. Not the read-then-insert it looks like.
- Attribution residue: 8 free-text `authored_by` rows, 2026-07-07→07-16, door
  since closed by `is_valid_author`. **They stay** — rewriting history to tidy
  the census trades the invariant for its appearance.
- Author census: operator 986 · system 769 · member 67 · yarnnn 56 · freddie 31.
  Machinery authors ~40% and touches more distinct paths (201) than the
  operator (141).
- 160 revision chains have no live file (the L1 orphan condition, below).

## OWED — needs a DECISION, not a patch

**1. Destructive paths bypass `delete_live_file` (unattributed destruction).**
The obvious fix is wrong: L2 deletes `workspace_file_versions` AND
`activity_log` in the same act, so any in-workspace record of the destruction is
destroyed by it. Needs a durable **out-of-workspace audit sink** first. For a
product whose invariant is "every change is signed by whoever made it", the one
unsigned path being the most destructive one is worth an ADR.

**2. L1 orphans revision chains.** `workspace_file_versions` has no FK to
`workspace_files` (keyed `(user_id, path)`), so L1's file deletes cascade
nothing — 160 chains already live. Arguably correct for a light L1, but
undocumented and the copy implies otherwise.

**3. `execution_events` (cost ledger) is destroyed by purge** — forced by a
`NO ACTION` FK, but in tension with ADR-291's "financial history preserved,
L4 only". Decision, not a patch.

## OWED — click-passes (mechanism verified, browser path not)

- **Download Workspace**: engine driven against the real 299-file workspace
  (1,613 commits, `git fsck --strict` clean, `git shortlog` names every
  principal). NOT clicked in a browser — the route streams a zip, and a
  `Content-Disposition`/CORS detail behaves differently there than in curl.
- Danger-zone condense (both doors after the cleanup).
- Everything in MEMORY.md still marked OWED from prior arcs.

## Gate notes

- `test_adr476_purge_scope` D3 pinned `?pane=danger` — a spelling the app has
  never used. RED since written. Re-anchored + falsified.
- `test_adr501_read_path_binding` pinned `resolve_purge_workspace(user_id)` in
  the `clear_integrations` window and read the fail-closed hardening as a
  regression. Re-anchored to accept either spelling.
- New: `api/test_purge_scope_and_failclosed.py` 8/8, each fix falsified against
  the real pre-fix code.
