# ADR-434 — The Powerbox: the read+write, arbitrary-depth, two-axis scope gate

> **Status**: **Accepted** (2026-07-10, operator-directed and Implemented). The full powerbox — not the deferred "Half B" of the scoping audit — shipped in one pass: **two independent axes** (read_scopes + write_scopes), **object-granularity at arbitrary path depth**, and a **three-state polarity** per axis. It is `access(2)`'s read check for `principal_grants`: the write-only, top-level-root, one-axis grant stub from ADR-373 is now a read+write, arbitrary-depth, two-axis permission model. **Permissions, not runtime** — yarnnn runs no foreign code (ADR-417/420); this ADR is purely the authorization gate.
>
> **⚡ MIGRATIONS 211 + 212 APPLIED. GATE + MATCHER LIVE.** DB pre-check @ 2026-07-10: **all 15 live grants NULL-scoped on both axes** → class-default fall-through → **byte-identical**. The powerbox is a silent, no-migration-of-behavior flip; it bites only a *future* narrowing. Landed: migration 211 (`read_scopes`/`write_scopes` path-prefix arrays + backfill from legacy `scopes`, mirror kept), migration 212 (`p_allowed_prefixes` on both search RPCs so LIMIT applies after scoping), the one longest-prefix matcher (`path_under_scopes`), the two-axis consult (`_lookup_grant_axes`/`_grant_axis`), the write lock (`_is_path_locked_for_principal`) and read gate (`_is_path_readable_for_principal`), the `ReadFile` wholesale-deny in `resolve_permission`, the `ListFiles`/`SearchFiles`/`QueryKnowledge` result filters, `narrow_grant` (two-axis), and the `/narrow` endpoint + `/members` two-axis `read_state`/`write_state`/`access_state`. Gate: `api/test_powerbox_read_gate.py` (24/24, two-axis) + `api/test_powerbox_blob_gate.py` (9/9, the out-of-band blob read gate). **Supersedes the Half-A/Half-B split** of `docs/analysis/the-powerbox-scope-audit-implementation-fe-2026-07-10.md`: the operator directed the full scope be built now — future-proof, not backwards-looking.

**Date**: 2026-07-10
**Dimension**: Identity (Axiom 2 — *who* may see and touch *what*) + Substrate (Axiom 1 — the commons object the authority is scoped over) + Channel (Axiom 6 — the narrowed principal's smaller view)

**Extends**:
- **ADR-373** — the multi-principal re-key; the grant is "the agent OS's `access(2)`". ADR-373 D2/D3 shipped the *install fact* (`principal_grants` exists, per-principal write-region roots). This ADR completes the *open fact* (per-object, per-principal, read+write scoping). The consult it added (`_is_path_locked_for_principal`) is here lifted to two axes.
- **ADR-386** — the grant lifecycle (`narrow`/`revoke`). `narrow_grant` was write-only, root-granular; it is now two-axis, arbitrary-depth.
- **ADR-431** — the connecting-member grant key. The two-axis consult threads `connected_by` (member-first, provider-wide fallback) unchanged.
- **ADR-307** — the one gate above all primitives (`resolve_permission`). The read gate lives at that same layer (a `ReadFile` branch parallel to the two write branches), never re-scattered into handlers.
- **ADR-320** — path topology; `CALLER_WRITE_POLICY` lists LOCKED prefixes (the class ceiling). A grant axis is the complementary ALLOW-list below that ceiling.

**Companion analysis** (the *why* + the audit; no ADR previously rode either):
- `docs/analysis/the-commons-is-the-os-2026-07-09.md` §5 — the thesis: the commons is the OS, the powerbox is its `access(2)`; the open-fact gap named for seven live foreign-LLM principals.
- `docs/analysis/the-powerbox-scope-audit-implementation-fe-2026-07-10.md` — the three-finding audit + FE surfacing. This ADR **supersedes its Half-A/Half-B seam** (object-scoping + the two-axis model, held there for "Half B", are built here).

**Preserves**:
- **Byte-identity for every live grant.** All 15 live grants are NULL-scoped → the consult falls through to `_is_path_locked` (write) / read-all (read) = the exact pre-powerbox behavior. Nothing an owner or an unconfigured principal does changes.
- **Single-writer-per-path (ADR-286) + no merge/CRDT (ADR-378).** The powerbox is authorization only; conflict reconciliation is unchanged.
- **The gate lives at `execute_primitive` (ADR-307).** No handler self-gates; the read gate is one new branch at the consolidated site.

**Deferred (named, not built)**:
- **The ADR-427 D4 MINTED capability** — a cryptographic, TTL'd, per-request blob capability minted from `(blob_sha, principal, active grant)`, coupled to ADR-427 Phase 3 (out-of-band blob serving URLs). That is a *serving-layer* mechanism, distinct from this *authorization gate*. The blob read gate in THIS work is a plain gate check (`_is_path_readable_for_principal`), not a minted capability. When ADR-427 Phase 3 serves blobs out-of-band, the minted capability derives its scope from the same two axes this ADR establishes.
- **Dropping the legacy `scopes` column.** Kept as a deprecated transition mirror (= `write_scopes`) for a deploy-window; a follow-up migration drops it once no reader remains.

---

## 1. The problem — a grant that promised to restrict, and half-lied

ADR-373 shipped a multi-principal commons: humans, their agents, other humans, platforms, and foreign/local LLMs all attribute into one workspace, each authorized by a `principal_grants` row. ADR-386 shipped `narrow` — the verb that *promises* to restrict a principal to part of the substrate. On the read axis, that promise was **false**, and the write axis had two defects. The scoping audit (`the-powerbox-scope-audit-implementation-fe-2026-07-10.md` §1) verified three findings @ `adf735e`:

1. **No read gate.** The grant consult (`_is_path_locked_for_principal`) was called from exactly two sites, both inside write-verb branches of `permission.py`. **A principal with *any* active grant read the entire commons.** Narrowing a member's ChatGPT to `marketing/` confined its writes and left its reads over the whole workspace.
2. **`scopes: []` failed OPEN.** The lookup used `if raw:` — and `[]` is falsy in Python, so an empty allow-list collapsed into the same branch as `NULL` and resolved to the class default (which permits `operation/`, `agents/`, `working/`, `uploads/` for an agent-class caller). **"This principal touches nothing" was unrepresentable — it silently meant "everything the class allows."**
3. **Object-scoping mechanically impossible.** Every scope was normalized to a top-level root (`rstrip("/") + "/"`) and matched by `startswith`. A scope of `operation/reports/q3.md` became `operation/reports/q3.md/`, which never prefix-matched the file itself. **You could grant a root; you could not grant a folder-below-a-root or a single file.**

A read-only auditor, a scoped contractor, an external AI that sees much but changes little — none were representable. The three findings are the gap `the-commons-is-the-os-2026-07-09.md` §5 named: the grant model held the *install fact* but not the *open fact*.

---

## 2. The decision — build the full model, now

The audit split the work into "Half A" (the read gate + the polarity fix, root-granular, one write-region list reused for reads) and "Half B" (object-scoping + a separate read axis + the minted capability), recommending Half A now and Half B "held for the use-case session."

**The operator directed the full scope be built now — future-proof, not backwards-looking.** The demand driver is explicit: there is waiting demand at **>10× current scale** requiring multi-principal read scoping (a shared commons where members, contractors, and external AIs each see and touch only their slice — teams share folders and files, not kernel roots). Building the gate to a root-only, one-axis model and then re-cutting it for real object-scoped use cases would be the dual-implementation the codebase forbids. So the powerbox ships as the **two-axis, arbitrary-depth** model in one pass. The Half-A/Half-B seam in the audit doc is superseded by this ADR.

The five decisions below are the model.

### D1 — Two independent axes: `read_scopes` + `write_scopes`

A grant carries **two** scope lists, one per axis (migration 211). A read-only auditor (`read: operation/`, `write: []`), a contractor who reads broadly but writes one folder, an external AI that sees much but changes little — all representable. **read ⊇ write is the BACKFILL DEFAULT, not a constraint**: the migration mirrors the legacy `scopes` into both axes, and `narrow_grant`'s `read_scopes` defaults to `_UNSET` → mirrors `write_scopes` (`principal_grants.py:388`). An owner can move the read axis independently at any time (`read` broader than `write`). One list could not express a principal that sees more than it changes; two can.

### D2 — Object-granularity via path prefixes at arbitrary depth

Each element of each axis is a **path prefix at arbitrary depth** — `operation/`, `operation/marketing/`, `operation/reports/q3.md` — matched by ONE longest-prefix matcher (`path_under_scopes`, `workspace.py:2013`). A directory scope (trailing slash) matches itself and everything beneath it; a file scope (no trailing slash) matches that exact path; depths nest correctly. This is the **macOS security-scoped-bookmark granularity**: the OS hands an app *this file*, not *the disk*. Teams share folders and files, not kernel roots — so the finest grain is a file, and the coarsest a root, in one uniform prefix model. The old root-only `_grant_root_set` (`rstrip+startswith`) is **deleted** (Singular Implementation — verified: no reader remains).

### D3 — Three-state polarity per axis: NULL ≠ [] ≠ [..]

Each axis has three distinct states (`_axis_state`, `routes/workspace.py:872`):

| State | Meaning | Gate behavior |
|---|---|---|
| **NULL** | axis unconfigured | fall through to the class default (`_is_path_locked` for write; read-all for read) — **today's exact behavior** |
| **`[]`** | explicit deny-all (an empty allow-list) | nothing matches → locked/unreadable everywhere |
| **`[..]`** | allow-list | matches iff the path is under a granted prefix (longest-prefix) |

`NULL ≠ []` is the polarity fix. Finding 2's silent bug was `bool(scopes)` collapsing `[]` into `NULL`; `path_under_scopes(path, [])` now returns `False` for every path (nothing matches an empty allow-list), while `path_under_scopes(path, None)` returns the no-op `True` (not narrowing — caller uses the class default). "This principal touches nothing" is finally representable and honest.

### D4 — The read gate: `ReadFile` DENIES, set-returning reads FILTER

A single-object read and a set-returning read have different correct shapes, and conflating them leaks existence:

- **`ReadFile`** is a single object → a **wholesale DENY** is correct (`resolve_permission`, `permission.py:231-237` — a `ReadFile` branch parallel to the two write branches, at the ADR-307 consolidated gate, never in the handler). Out of read scope → `DENY, "read_scope_denied:{target}"`.
- **`ListFiles` / `SearchFiles` / `QueryKnowledge`** are result sets → they **FILTER**, not deny (`filter_results_by_read_scope` + the `ListFiles` in-handler filter at `workspace.py:1609`). A wholesale deny on a set-returning read would leak an out-of-scope file's *existence* (an error naming a path the principal may not see); silent filtering does not. **The reported count is the filtered count** — no "3 results hidden" tally that reveals out-of-scope volume.

**Search filtering is pushed INTO the DB RPCs** (migration 212 — `p_allowed_prefixes` on `search_workspace` + `search_workspace_semantic`). This is a correctness bug otherwise: filtering in Python *after* the RPC's `LIMIT` starves a narrowed principal's page (the DB caps to 20 rows, then the app drops the out-of-scope ones, so in-scope matches past the limit vanish). With the prefix filter in the RPC, the `LIMIT` applies to in-scope rows only — the page is full and correct at scale. `read_scope_db_prefixes` converts the workspace-relative gate scopes (`operation/`) to the absolute `/workspace/...` form the RPC matches.

### D5 — Safety invariant: a silent, byte-identical flip that bites only future narrowings

The DB pre-check (the §5 gate of the audit) came back clean @ 2026-07-10: **all 15 live grants NULL-scoped on both axes.** Every live caller therefore hits the fall-through — `_is_path_locked` (write) / read-all (read) — which is byte-identical to the pre-powerbox gate. The powerbox is a **silent flip with no behavior migration**: the grant-honored branch (deny/filter) is exercised only once a narrowing grant row exists. It bites a *future* member/foreign-LLM narrowing, which is the whole point. Migration 211 backfills NULL→NULL for all 15 rows (a no-op write it skips); `[]` and `[..]` (none live yet) are copied faithfully.

---

## 3. What shipped — the implementation

| Concern | File · symbol |
|---|---|
| Two axes on the grant | `supabase/migrations/211_powerbox_read_write_scopes.sql` — `read_scopes` + `write_scopes` (`text[]`, arbitrary-depth path prefixes); backfill `scopes → both axes` (read ⊇ write); `scopes` kept as deprecated mirror |
| Search scoping in the DB | `supabase/migrations/212_powerbox_search_scope.sql` — `p_allowed_prefixes` on `search_workspace` + `search_workspace_semantic` (drop-then-recreate for the 5th param; `NULL` = unscoped byte-identical; `{}` = deny-all; `{..}` = allow-list); LIMIT applies after scoping |
| The ONE matcher | `services/primitives/workspace.py::path_under_scopes` (`:2013`) — longest-prefix, arbitrary depth, three-state polarity (`None`→no-op `True`, `[]`→deny-all `False`, `[..]`→prefix match). Normalizers `_normalize_scope_candidate`/`_normalize_scope_prefix` (`:1989`/`:1999`) canonicalize dir-vs-file intent |
| The two-axis consult | `_lookup_grant_axes` (`:2079`) — resolves `{read, write}` for a principal in one memoized lookup; reads `read_scopes`/`write_scopes`, falls back to legacy `scopes` for pre-migration rows; threads ADR-431 `connected_by` (member-first, provider-wide fallback); fail-safe → class default. `_grant_axis` (`:2162`) picks an axis |
| Write lock | `_is_path_locked_for_principal` (`:2171`) — write axis `None`→`_is_path_locked` class default; else locked iff not under a granted prefix |
| Read gate (single object) | `_is_path_readable_for_principal` (`:2187`) — read axis `None`→read-all; `[]`→nothing; `[..]`→readable iff under a granted prefix. Called from `resolve_permission` (`permission.py:231`) as the `ReadFile` wholesale DENY |
| Read filters (set-returning) | `grant_read_scopes` (`:2199`), `filter_results_by_read_scope` (`:2227`), `read_scope_db_prefixes` (`:2206`); wired at `ListFiles` (`:1609`), `SearchFiles`/`QueryKnowledge` (`:1237`, `:1258`, `:1363`, `:1456`) |
| Two-axis narrow | `services/principal_grants.py::narrow_grant` (`:355`) — `write_scopes` + optional `read_scopes` (default `_UNSET`→mirror write); writes both axes + the deprecated `scopes` mirror; rejects the owner grant |
| Narrow endpoint + roster | `routes/workspace.py` — `POST /workspace/members/{id}/narrow` (`:1305`) accepts `write_scopes` + optional `read_scopes` (legacy `scopes` fallback); `_axis_state` (`:872`) three-way; `/members` returns per-principal `read_state`/`write_state`/`access_state` (the wider of the two, the operator glance) |
| Gate | `api/test_powerbox_read_gate.py` — 24/24 two-axis + `api/test_powerbox_blob_gate.py` — 9/9 (the blob serving read gate on `/documents/blob` + `/documents/{path}/download`); (NULL read-all, no-grant read-all, `[]` deny-all read + write, narrowed single/multi-root, absolute+workspace prefix normalization, `ReadFile` APPLY/DENY/null/agent-scope, read-gate-path resolver skips agent scope, filter drops/passes/empties, pure predicate, read-is-inverse-polarity-of-write). The ADR-373 empty-scopes test was amended — it had pinned the pre-fix open-polarity |

---

## 4. Why this is the OS's `access(2)`, and why apps are downstream (not this ADR)

`the-commons-is-the-os-2026-07-09.md` established that yarnnn holds three of the four macOS OS primitives (type system via `resolveViewerApplication`, write path via `write_revision`, install fact via `principal_grants`) and lacked the fourth — the **open fact** (per-object, per-principal, scoped authority; the security-scoped bookmark; `access(2)`'s read check). **This ADR is the fourth primitive.** With it, a principal is handed *this folder / this file, to read and/or write*, exactly as macOS hands an app a file rather than the disk.

The commons needs this **now**, for principals it already ships — not for a future app. Seven `foreign-llm` principals held grants that, before the read gate, read the whole commons even when narrowed; a multi-member workspace (invites already shipped) exposed member A's files to member B's connected AI. The powerbox closes that live exposure. Third-party apps — deferred (ADR-380 §5) — inherit this gate for free when they arrive; they are a *byproduct* of the commons primitive, not the reason it was built. This ADR does **not** open the app-principal question, the minted capability (deferred above), or a public ABI.

---

## 5. Consequences

- **`narrow` is honest on both axes.** A narrowed member/foreign-LLM now reads and writes only its granted prefixes — the promise ADR-386 made is finally true on read.
- **"Touches nothing" is representable.** `read: []` / `write: []` denies everything explicitly, distinct from an unconfigured NULL grant. FE must render the two differently ("no access" vs "not yet configured") or the operator cannot tell locked-down from wide-open (the audit §6.1 affordance).
- **Object-scoped sharing exists.** A grant can name `operation/marketing/` or `operation/reports/q3.md`, not just `operation/`. The finest grain is a file; the coarsest a root; one matcher spans both.
- **Search is correct at scale.** The DB scopes before its LIMIT, so a narrowed principal's page is never starved by a pre-scope cap.
- **Deploy-window safe.** `scopes` remains a mirror of `write_scopes`; old code reading `scopes` still works until the follow-up drop migration.
- **The minted capability has a home.** When ADR-427 Phase 3 serves blobs out-of-band, its per-request TTL'd capability derives scope from these two axes — the gate is the durable authority; the mint is the transient serving token over it.

---

## 6. Receipts / citations

| Claim | Receipt |
|---|---|
| Migrations 211 + 212 applied; all 15 live grants NULL-scoped → byte-identical | `supabase/migrations/211_powerbox_read_write_scopes.sql` (backfill + verification block) · DB pre-check 2026-07-10 |
| Two axes on the grant (read ⊇ write is a default) | `211_*.sql:40-53` — `read_scopes` + `write_scopes` cols + comments |
| Object-granularity via arbitrary-depth path prefixes; ONE longest-prefix matcher | `services/primitives/workspace.py::path_under_scopes:2013` · normalizers `:1989`,`:1999` |
| Three-state polarity per axis (NULL ≠ [] ≠ [..]) | `path_under_scopes:2028-2044` (`None`→`True` no-op; `[]`→`False`; `[..]`→match) · `_axis_state` `routes/workspace.py:872` |
| Two-axis consult, one memoized lookup, ADR-431 `connected_by` threaded | `_lookup_grant_axes:2079` · `_grant_axis:2162` |
| Write lock (class-default fall-through when axis NULL) | `_is_path_locked_for_principal:2171-2184` |
| Read gate = `ReadFile` wholesale DENY at the ADR-307 site | `services/primitives/permission.py:231-237` (`resolve_permission`) · `_is_path_readable_for_principal:2187` |
| Set-returning reads FILTER (existence never leaks) | `filter_results_by_read_scope:2227` · `ListFiles` filter `:1609` · `SearchFiles`/`QueryKnowledge` `:1237`,`:1456` |
| Search scoping in the DB so LIMIT applies after scoping | `212_*.sql` — `p_allowed_prefixes` on both RPCs · `read_scope_db_prefixes:2206` |
| Old root-only matcher deleted (Singular Implementation) | grep: no `_grant_root_set` / `_lookup_grant_scopes` reader remains |
| Two-axis narrow (`read_scopes` defaults to mirror write) | `services/principal_grants.py::narrow_grant:355-405` (`effective_read`, `:388`) |
| `/narrow` endpoint + `/members` two-axis state | `routes/workspace.py::narrow_member:1305` · `_axis_state:872` · `read_state`/`write_state`/`access_state` `:1181-1247` |
| Deprecated `scopes` mirror kept for deploy window | `211_*.sql:55-58` (COMMENT) · `narrow_grant:396` (`"scopes": write_scopes`) |
| Gate 24/24 + blob 9/9 | `api/test_powerbox_read_gate.py` · `api/test_powerbox_blob_gate.py` |
| The thesis: commons is the OS, powerbox is its `access(2)`; §5 gap for 7 live foreign-LLM principals | `docs/analysis/the-commons-is-the-os-2026-07-09.md` §5 |
| The audit (three findings) + Half-A/Half-B seam this ADR supersedes | `docs/analysis/the-powerbox-scope-audit-implementation-fe-2026-07-10.md` §1, §2 |
| Minted capability (deferred; ADR-427 Phase 3 serving-layer) | ADR-427 D4 |
| Grant = the agent OS's `access(2)`; the consult site | ADR-373 D2/D3 · ADR-307 (gate at `execute_primitive`) |
