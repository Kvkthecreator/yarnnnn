# The Powerbox — Audit, Implementation Scope, and FE Surfacing

*Finishing `access(2)`: the read axis, the empty-set fix, and object-scoping. Permissions, not runtime.*

> **Status**: Scoping analysis (2026-07-10). Doc-first, receipts-backed @ `adf735e`. **No ADR rides this yet** — this doc scopes the work so a powerbox ADR can be written against a real map. It is the implementation companion to `the-commons-is-the-os-2026-07-09.md` §5 (the *why*) and to the concepts carryover (the *runtime-vs-permissions* nuance, handled separately).
>
> **⚡ SUPERSEDED — THE FULL POWERBOX SHIPPED (2026-07-10). See ADR-434.** The Half-A/Half-B split below is superseded: the operator directed the **full scope** be built now (future-proof, not backwards-looking — waiting demand at >10× scale). Landed in one pass: **two independent axes** (`read_scopes` + `write_scopes`, migration 211), **object-granularity at arbitrary path depth** (one longest-prefix matcher `path_under_scopes`), **three-state polarity** per axis, **DB-side search scoping** (migration 212 — `p_allowed_prefixes` so LIMIT applies after scoping), the `ReadFile` wholesale read gate + set-returning filters, the **blob read gate** (`documents.py` — `test_powerbox_blob_gate.py` 9/9), `narrow_grant` two-axis, the `/narrow` + `/members` two-axis endpoints, and the FE picker (per-path No-access/Read/Read+Write + arbitrary-depth path input + deny-all). DB pre-check clean (all 15 live grants NULL-scoped → **byte-identical**). Gates: `test_powerbox_read_gate.py` (24/24) + `test_powerbox_blob_gate.py` (9/9); ADR-373/386 amended for the two-axis behavior; `tsc` clean. **The §2 Half-A/Half-B framing below is retained for the record but is no longer the plan — ADR-434 is authoritative.** Only the ADR-427 D4 *minted capability* (cryptographic TTL'd blob capability, a serving-layer mechanism) remains deferred — distinct from this authorization gate.
> **Authors**: KVK, Claude
> **Hat**: A (system canon). Vocabulary: principal, grant, scope, gate, powerbox, read-axis, object-scope, minted capability.
> **The one-sentence frame**: the powerbox is **permissions, not runtime** — completing the write-only, root-granular grant gate into a read+write, object-granular one. It is `chmod`/`access(2)` reads for `principal_grants`, which today only checks mode bits on writes.

---

## 0. Read this first — what the powerbox IS and IS NOT

- **IS**: a permission gate. Per-principal, per-object, scoped, expiring authority to *read* or *act on* a substrate object.
- **IS NOT**: a runtime, a sandbox, code execution, an app store. yarnnn runs no foreign code (ADR-417/420 — generation is rented; foreign actors reach in over MCP as principals). The runtime question is genuinely separate and is handled in the concepts session, not here.
- **The debt**: yarnnn shipped multi-principal + grants + a `narrow` verb that *promises* to restrict a principal. On the read axis, that promise is **currently false**. This doc scopes making it true.

---

## 1. The audit — three findings, verified @ `adf735e`

The app-layer doc's §10 line numbers had drifted; these are re-verified against live code. All three hold, and one is sharper than the doc stated.

### Finding 1 — there is no read gate. (CONFIRMED)

The grant consult `_is_path_locked_for_principal` is called from exactly **two** sites, both in `api/services/primitives/permission.py`, and **both are inside `_PATH_ADDRESSED_QUEUEABLE` (write-verb) branches**:

- `permission.py:270` — the **MCP (foreign-LLM) branch**: `if name in _PATH_ADDRESSED_QUEUEABLE:` → consult. `_PATH_ADDRESSED_QUEUEABLE` = WriteFile + the ADR-337 mutating verbs.
- `permission.py:364` — the **Reviewer/steward branch**: same `if name in _PATH_ADDRESSED_QUEUEABLE:` guard → consult.

The read primitives — `handle_read_file` (`workspace.py:522`), `handle_list_files` (`:1512`), `handle_search_files` (`:1195`), `handle_query_knowledge` (`:1287`) — **never call the consult, and there is no read branch in `permission.py` that does.** A principal with *any* active grant reads the entire commons.

> **Manifestation**: narrow a member's ChatGPT to `marketing/` → its *writes* are confined to `marketing/`, its *reads* still cover the whole workspace. The `narrow` verb is half-honest.

### Finding 2 — `scopes: []` fails OPEN. (CONFIRMED, sharper than the doc)

The polarity hinge is `_lookup_grant_scopes` in `workspace.py`. The code comment (`:2013`) *claims* "NULL scopes → None (class default). A non-empty list → allow-list." But the actual gate is `if raw:` (`workspace.py:2015`):

```python
raw = result.data[0].get("scopes")
if raw:                      # ← [] is falsy: empty list takes the SAME branch as NULL
    scopes = list(raw)
# scopes stays None otherwise → _is_path_locked_for_principal falls to class default
```

`[]` (empty list) is falsy in Python, so it collapses into the `NULL → None → class-default` path. **The empty scopes list — the only way to encode "this principal may write NOTHING" — resolves to the class default, which for an `agent`/`mcp`-class caller PERMITS `operation/`, `agents/`, `working/`, `uploads/`.**

> **Manifestation**: "give this principal a grant but scope it to nothing" is unrepresentable. `[]` means "everything the class allows," the exact opposite of intent. This is a one-line polarity bug with a security consequence.

### Finding 3 — object-scoping is mechanically impossible. (CONFIRMED)

`_grant_root_set` (`workspace.py:1946`) normalizes every scope to a **top-level root prefix**: `{s.rstrip("/") + "/" for s in scopes if s}`. And `_is_path_locked_for_principal` (`:2050`) matches `candidate.startswith(root)`. A scope of `operation/reports/q3.md` becomes `operation/reports/q3.md/`, which never prefix-matches the file `operation/reports/q3.md`. Scopes are **roots**, not paths. You cannot grant one object; only a top-level region.

> **Manifestation**: "let this app open THIS ONE file" is unrepresentable. The finest grain today is a top-level root (`operation/`, `agents/`, …).

---

## 2. The Half-A / Half-B seam — the governing decision

The three findings split cleanly into two halves with **different readiness**:

| | **Half A — debt repayment** | **Half B — new capability** |
|---|---|---|
| Findings | 1 (read gate) + 2 (polarity) | 3 (object-scoping) + minted capability |
| Correct behavior is… | **derivable** from what "grant"/"narrow" already claim | **shaped** by use-case answers |
| New use-case knowledge? | **none** | **required** (subtree vs object? read-only vs scoped-write? TTL?) |
| Blast radius | small, known | larger, undefined until scoped |
| Safe to build now? | **yes** | **no — wait for use-case hardening** |
| Ships as | a correctness fix (makes `narrow` honest) | a new grant shape + capability minting |

> **The recommendation**: build **Half A now**; hold **Half B** for the use-case session. This doc scopes Half A fully and sketches Half B enough to leave the right seams.

---

## 3. Half A — implementation scope (the part that's ready)

### A.1 — Fix the empty-set polarity (Finding 2). One-line-ish, do first.

The fix distinguishes `[]` (deny-all — an explicit empty allow-list) from `NULL` (fall to class default):

```python
raw = result.data[0].get("scopes")
if raw is not None:          # explicit list, INCLUDING [] → allow-list (empty = deny-all)
    scopes = list(raw)       # [] stays [] → _grant_root_set([]) = ∅ → nothing matches → locked
```

Verify the downstream honors it: `_grant_root_set([])` returns `∅`; `_is_path_locked_for_principal` then returns `not any(...)` over an empty set = `True` (locked) for every path. Correct: an empty allow-list locks everything. **Gate the change**: a test that `scopes=[]` → every write path locked, distinct from `scopes=NULL` → class default. This is a pure write-axis fix and is **byte-identical for every live grant** (all current grants are NULL-scoped, so none takes the `[]` branch).

### A.2 — Add the read gate (Finding 1). The core of Half A.

The read verbs must consult the same per-principal grant the write verbs do. Design decisions, each with a receipt-backed default:

1. **Where the consult lives.** The write consult is in `permission.py` at `execute_primitive` (ADR-307 — the gate moved UP; tools don't gate themselves, `workspace.py:775-782`). The read gate should live at the **same layer**, so `permission.py` gains a read branch parallel to the two write branches. Do NOT gate inside `handle_read_file` — that would re-scatter the gate ADR-307 consolidated.

2. **What "locked for read" means with today's write-shaped scopes.** The current `scopes` are *write-region* roots. The cleanest Half-A semantics: **a principal may READ any root it may WRITE, plus explicitly-granted read-only roots.** Read ⊇ write. This avoids inventing a separate read-scope model in Half A (that's Half B). Concretely: reuse `_is_path_locked_for_principal`; a read is locked iff the path's root is outside the principal's granted region. For NULL-scoped grants (all live ones) → class default → **byte-identical to today** (owner reads everything; this only bites narrowed principals).

3. **Which read verbs.** `ReadFile` (object), `ListFiles` (enumeration — must filter, not just deny), `SearchFiles` (must filter results), `QueryKnowledge` (must filter results). **The enumeration/search verbs are the subtle ones**: they can't just "deny or allow" — they must *filter their result set* to the principal's granted region, or they leak existence/content of out-of-scope files. Scope A.2's work honestly: `ReadFile` is a gate; `ListFiles`/`SearchFiles`/`QueryKnowledge` are *filters*. The filter is more work than the gate.

4. **The migration risk — THIS GATES A.2's SHIP.** Adding a read gate is a *behavior change for 7 live foreign-llm principals* that currently read broadly. Before shipping: run the DB pre-check (§5) — are any live principals actually narrowed AND relied upon for broad reads? If yes, it's a migration (announce + re-grant), not a silent flip. If no (likely — narrowing is post-launch-additive, ADR-373 D4), the flip is safe because every live grant is NULL-scoped → class-default → unchanged.

### A.3 — What A does NOT do

- No object-scoping (roots only — that's Half B).
- No separate read-scope model (read ⊇ write in Half A).
- No minted/expiring capability (Half B).
- No new grant UX beyond making `narrow` honest.

**Half A's deliverable**: `narrow` and `scopes:[]` become TRUE on both axes, at root granularity, for the principals the commons already has. That is the whole debt, paid.

---

## 4. Half B — the sketch (leave these seams; don't build yet)

Held for the use-case session. Named so Half A doesn't foreclose them:

- **Object-scoping** — `scopes` gains a path-granular form (not just roots). `_grant_root_set` becomes `_grant_scope_matcher` supporting both root-prefix and exact-object rules. **Seam to leave in A**: keep the scope-matching in ONE function (`_is_path_locked_for_principal` already centralizes it) so B extends the matcher, not the call sites.
- **Read-only vs scoped-write scopes** — today `scopes` is one write-region list. B may need `read_scopes` / `write_scopes` (or a per-scope mode). **Seam**: A's "read ⊇ write" is a clean default that B can specialize without rework.
- **The minted read capability (ADR-427 D4)** — per-request, per-principal, TTL'd, computed from `(blob_sha, principal, active grant)`; "a cached capability is a leaked capability." This is the app/blob-serving case, and it couples to ADR-427 Phase 3 (serving URLs). **Do not build in A** — A gates the *primitive* call; B mints a *capability* for out-of-band blob fetch. Different mechanisms.
- **The three use-case questions B needs answered** (the use-case session's job): subtree vs object granularity? read-only vs scoped-write? TTL semantics (session / task / standing)?

---

## 5. The DB pre-check — the empirical gate on A.2

Before A.2 ships, answer from the live DB (docs/database/ACCESS.md):

```sql
-- Are there live NON-owner, NON-NULL-scoped grants on multi-member workspaces?
-- (= principals that would CHANGE read behavior under the new gate)
select pg.workspace_id, pg.principal_id, pg.role, pg.scopes,
       (select count(*) from principal_grants g2
        where g2.workspace_id = pg.workspace_id and g2.status='active') as ws_principal_count
from principal_grants pg
where pg.status = 'active'
  and pg.role <> 'owner'
  and pg.scopes is not null;   -- narrowed principals: the only ones the read gate changes
```

- **Empty / all-NULL-scoped** → A.2 is a safe silent flip (byte-identical for live grants; the gate only bites future narrowings). Ship freely.
- **Non-empty** → each row is a principal whose reads will narrow. It's a migration: notify, re-grant read scope if intended, then flip.

This is also the §8 go/no-go input from the commons doc: it tells you whether the powerbox is *overdue* (real narrowed principals reading across members) or *pre-emptive* (N=1, no live exposure).

---

## 6. FE surfacing — what the operator/member actually sees

The powerbox is invisible as a concept; it manifests as **"share part, not all."** Three surfaces, mapped to existing homes (no new top-level surface — DP29 mirror-once discipline).

### 6.1 — The grant editor (where narrowing is authored)

Today: `WorkspaceMembersCard` (`web/components/workspace-concepts/WorkspaceMembersCard.tsx`) is a **read-only roster** with narrow/revoke verbs already wired (`POST …/members/{id}/{narrow,revoke}`, `routes/workspace.py`). Half A makes `narrow` finally mean something on reads. FE work:

- **The scope picker** — narrowing today is coarse (the verb exists; the UI to *choose* a scope may be minimal). Half A needs a **root-multiselect**: "this principal may access: ☐ operation ☐ agents ☐ uploads …". This is root-granular (matches A's model). Object-granular picking waits for Half B.
- **The `[]` = deny-all affordance** — "no access" must be an explicit, selectable state (empty allow-list), visually distinct from "not yet configured" (NULL → class default). The polarity fix (A.1) makes these two different; the UI must too, or the operator can't tell "locked down" from "wide open."
- **Honesty of the label** — anywhere the UI says "restricted to X," it must now be true on reads. Audit existing member-card copy for over-claims that were previously false.

### 6.2 — The principal's-eye view (what a narrowed member/AI sees)

When Half A lands, a narrowed member (or their connected AI) sees a **smaller Files tree** — only granted roots. FE work:

- The Files surface (`ContentViewer` / the explorer tree) already renders from `GET /workspace/roots`; once `ListFiles` filters by grant (A.2), the tree naturally shrinks for narrowed principals. **Verify the empty/partial-tree states are honest** ("you have access to marketing/ · 3 folders" not a blank screen that reads as broken).
- Search/recall results filtered by grant must not leak *existence* of out-of-scope files (no "3 results hidden" count that reveals volume). Silent filtering.

### 6.3 — The audit/legibility surface (who-can-see-what)

New need Half A surfaces: an operator must be able to **read the current access map** — "who can see which roots." This is a *mirror* (DP29), derived from `principal_grants`, not a new stored thing. Candidate home: extend the members roster with a per-principal "sees: operation, uploads" summary column, or a dedicated Access pane under Workspace Settings → Access (where the roster already lives). Keep it derived-never-stored.

### 6.4 — What the FE does NOT get in Half A

- No per-file sharing UI (object-scoping is Half B).
- No "share this one document with an app" (Half B + apps, deferred).
- No expiring-link UX (minted capability is Half B).

---

## 7. Sequencing summary

```
1. DB pre-check (§5)              ── gates whether A.2 is a flip or a migration
2. Half A.1  polarity fix         ── one-line, byte-identical for live grants, do first
3. Half A.2  read gate + filters  ── the core; ReadFile=gate, List/Search/Query=filters
4. Half A FE  (§6.1–6.3)          ── scope picker + honest narrowed-view + access map
5. → powerbox ADR (Half A ratified; Half B seams named)
   ── THEN the use-case session answers B's three questions
   ── THEN Half B (object-scope + minted capability), its own ADR
```

Half A is a **self-contained, shippable correctness fix** that makes an existing promise true. Half B is a **new capability** that should be use-case-shaped first. The powerbox ADR can be written after Half A with Half B's seams named — exactly the "build the debt now, design the capability against real use cases" split the operator proposed.

---

## 8. Receipts index

| Claim | Receipt |
|---|---|
| Consult called only in write branches | `permission.py:270` (MCP), `:364` (Reviewer) — both under `_PATH_ADDRESSED_QUEUEABLE` |
| Read verbs never consult | `workspace.py::handle_read_file:522`, `handle_list_files:1512`, `handle_search_files:1195`, `handle_query_knowledge:1287` — no consult call |
| `scopes:[]` fails open (polarity) | `workspace.py:2015` `if raw:` (`[]` falsy → NULL branch → class default) |
| Class default is write-capable | `_is_path_locked` + `CALLER_WRITE_POLICY` (`workspace.py:1865`, `workspace_paths.py`) |
| Object-scoping impossible (roots only) | `_grant_root_set:1946` (`rstrip("/")+"/"`), match at `:2050` (`startswith`) |
| The consult is centralized (one extension point) | `_is_path_locked_for_principal:2033` — single gate entry |
| Grant verbs already exist | `POST /api/workspace/members/{id}/{narrow,revoke}` · `principal_grants.py` |
| Roster is the FE home | `WorkspaceMembersCard.tsx` (Workspace Settings → Access) |
| Gate moved up (don't re-scatter) | ADR-307 · `workspace.py:775-782` |
| Minted capability spec (Half B) | ADR-427 D4 |
| 7 live foreign-llm principals | ADR-386 backfill 2026-06-30 · ADR-373 D2.a |
