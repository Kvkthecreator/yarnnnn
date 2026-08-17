# Session handoff — 2026-08-17: the MCP connector audit, and what it produced

`origin/main` at `ec58956`. The audit asked: **does the connector show user
information and let you select a workspace — in the OAuth flow, and in the app?**
Four items shipped; one was **deliberately dropped after measurement**, and that
is the most reusable finding here.

> The prior handoff (ADR-572 D8, `dbccbd1`) is **ABSORBED**. Two of its owed
> items are now CLOSED by this session — the stranded-row backfill (audited, not
> needed) and "a connector cannot NAME a workspace" (ADR-573). Its remaining
> item, the Print/PDF click-pass, is carried forward below.

## ⭐⭐⭐ The correction that opened this session — carry it

The audit's first finding was **WRONG**. I reported that MCP requests fall
through to a per-principal default with `workspace_id` unset — a real defect,
**fixed at `e0fa233` five hours before this session started**. I read the
*fixed* file and did not notice the D6 block inside it.

**A file read mid-session is evidence of that moment only.** A peer lane was
committing into the same working tree throughout. Before auditing anything, run
`git log --oneline -10` for work that landed after your context was built.

The paired lesson, from the parallel lane: **a ratified ADR is evidence of a
decision, never of an implementation.** D6 was ratified, cross-referenced,
written in the tense of intent — and never built.

## What shipped

### 1. ADR-373 D6's stranded-row backfill — AUDITED, not needed (`4b550bc`)

The prior handoff warned pre-fix connector rows were stranded and needed a
backfill. **Counted against production: they aren't.** 53 MCP-authored versions
across 4 workspaces; exactly **2 sit in a workspace their author doesn't own**,
and both are `Documents/d6-probe-2.md` — the D6 probe itself, caught by the bug
it was probing. **Zero NULL-`workspace_id` rows** on either substrate table.

⭐ **The published remediation query could never have run**: it selected
`authored_by FROM workspace_files`, and that column lives on
`workspace_file_versions`. **A query that errors on contact is worse than no
query — it reads as a discharged obligation.** Replaced with a runnable form
that also answers what the original couldn't: *does each row's workspace belong
to its author?*

No bulk UPDATE run, none warranted. Deleting the two probe rows would rewrite an
attributed revision chain (ADR-209) to tidy test files.

### 2. ADR-563 consent screen — who, where, what (`52b6538`)

The screen named the client and redirect host, then printed a **fixed sentence
wrong twice over**: *"read and write your memory"* — `memory` is pre-ADR-512
vocabulary (the unit of interop is the FILE), and a legacy `read` token can also
**DELETE** files and mint share links granting **MEMBER** access. Neither was
mentioned. ADR-563 made the tiers *enforced*; the consent surface never showed
them.

It also never said **which account** the bind would use (identity comes from the
JWT — on a shared browser, that is approving as someone else), nor **which
workspace**.

⭐ Tier definitions moved to **`api/services/mcp_scopes.py`**: the API serves the
consent screen and **cannot import `mcp_server.auth`** (py3.9 venv + py3.11-only
`mcp` SDK — the same constraint that put `delete_tokens_for_client` in
`services/principal_grants.py`). `auth.py` re-exports them. A route-side copy
would have rebuilt the pre-563 defect at the surface: a label free to disagree
with the check.

### 3. Members pane — the connection's verb tier (`3803c5b`)

The pane showed only the **path** axis (ADR-532 read/write regions). Production
carries **both** `read` (legacy full) and `files:read` tokens today, and they
rendered identically. Now its own line — merging it into the zone chips would
imply one narrows the other, and it doesn't: a connector scoped to `Documents`
can still hold a token that deletes and shares within it.

### 4. ADR-573 — the connector is bound to a workspace at consent (`ec58956`)

⭐⭐⭐ **The demand was measured, not assumed.** Exactly one production principal
reaches two workspaces: owns `My Workspace`, holds an active member grant into
the shared `yarnnn workspace`. **All three of their connector writes landed in
the owner workspace** — the commons their membership exists FOR was
*unaddressable* from the connector.

The operator now picks at consent; stamped on the code, carried to **both**
tokens, read per request.

- **A stamp NARROWS, never grants** — routed through the same
  `resolve_workspace_for_principal` the JWT door uses, and
  `principal_reaches_workspace` is uncached, so a member revoked *after* their
  token was minted loses reach on their next call.
- **NULL is not a missing value; it is "the principal's default."** All **421**
  live pre-573 tokens carry it. **No backfill** — stamping them would *freeze* a
  default that may legitimately move. Nothing repointed on deploy day.
- The binding **rides the refresh token**, or silent rotation un-binds every live
  connector with nobody acting (the ADR-386 D1.a shape).

## ⭐⭐⭐ The item I DROPPED — and why it matters more than the ones I built

I had recommended threading `workspace_id` into `AgentWorkspace`: it re-derives
on every call, while `AuthenticatedClient`'s own docstring says to derive once
and thread. It **reads** like an un-swept second path. Measured before "fixing":

- the owner branch is `lru_cache`d — a repeat call is a dict lookup, not a query;
- the uncached branch needs a principal with an active grant and **no owned
  workspace** — **production count: 0**.

~90 construction sites, zero behaviour change, zero queries saved. **Dropped**,
with the rationale and the reversing condition recorded *in
`api/services/workspace.py`* so it is not re-proposed from the shape alone.

**Measure the exposure before paying for the cleanup.** A pattern that looks
wrong is not the same as a pattern that costs anything.

## Gate craft this session paid for

- ⭐⭐⭐ **A falsifier FAILED and exposed a worthless check.** My FE grants check
  grepped `"grants"` and `".map("` independently; replacing `info.grants.map(…)`
  with `[].map(…)` left both tokens present, so **a screen rendering nothing read
  green**. Now matches the iteration over the payload. *A co-occurrence check
  cannot defend a specific site.*
- ⭐⭐ **Moving a definition can blind a gate.** ADR-563's AST loader keeps only
  `Assign` nodes, so an `import` re-export is invisible to it. It errored
  honestly — the dangerous version passes on a stale copy. It now follows the
  definitions to their new home, and calls the **shipped** `satisfied_by` rather
  than re-deriving containment (a gate that re-implements a rule can only prove
  the rule agrees with itself).
- ⭐⭐ **`bound_workspace_id` initialized inside the `try`** would raise
  `UnboundLocalError` on the stdio/static-bearer path, which takes the *except*
  branch. Caught while writing; now gated by AST.
- ⭐ **A comment can satisfy a check about behaviour.** My own explanatory comment
  quoting the banned copy failed the "copy is deleted" check. The gate was right.

## Verification that must stay green

```
cd api && /tmp/mcpenv/bin/python3.11 test_adr573_connector_workspace_binding.py  # 18/18
cd api && python3 test_adr563_consent_discloses.py                              # 23/23
cd api && /tmp/mcpenv/bin/python3.11 test_adr563_mcp_scope_enforcement.py       # 16/16
cd api && /tmp/mcpenv/bin/python3.11 test_adr373_rekey.py                       # 20/20
cd api && python3 test_adr373_sweep_spine.py                                    # 26/26
cd api && python3 test_security_2026_08_01_fixes.py                             # ALL PASS
cd web && node_modules/.bin/next build                                          # 171/171
```

⭐ Anything importing `mcp_server/*` needs **py3.11** (`/tmp/mcpenv`); the API
venv is 3.9 and dies at import on a `str | None` default annotation.
⭐ `test_adr404_member_invites.py` has **1 PRE-EXISTING failure** — verified by
stashing this work and re-running, not assumed.
⭐ Migrations run through `scripts/db/run-migration.sh` (`--dry-run` first); the
runner's exit code is **not** verification — read the live object back.

## Still OWED

1. **ADR-573 operator click-pass** — re-authorize a connector, pick the *second*
   workspace, prove the write lands there. The one principal who can drive it is
   `2be30ac5…` (owns `My Workspace`, member of `yarnnn workspace`).
2. **ADR-563 consent click-pass** — read the new screen on a real re-authorize:
   account, workspace, real tier, legacy-full warning.
3. **Print/PDF click-pass** (carried from ADR-572) — a native modal the harness
   cannot dismiss. Two minutes of operator time: Text → Export → Print/PDF →
   confirm the A4 page reads as a document.
4. **The connector is still not TOLD which workspace it is in.** ADR-533 D6
   refuses to export workspace *intent* into a third-party context window;
   whether the workspace **name** — as distinct from its mandate — should cross
   that line is **unaddressed**. Note the instructions string is composed at
   **import time**, so per-connection identity would have to be a **resource**,
   never the instructions.

## Deferred, deliberately — named so it is not re-discovered as novel

- **A per-verb `workspace` argument** was considered and rejected in ADR-573 §2:
  nine signatures change, the **model** becomes the chooser (a wrong guess writes
  to the wrong commons with full attribution), and ADR-512 D5's
  `yarnnn://workspace/…` grammar has no workspace slot.
- **`context-brief`** (carried from ADR-572) — in
  `api/services/derive_recipes.py`, targets markdown, resident `scout`, **zero FE
  consumers**. Text is its natural home; it needs its own decision about where a
  derived brief lands.
