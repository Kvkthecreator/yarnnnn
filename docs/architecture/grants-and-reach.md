# Grants & Reach — the workspace authorization model

**The singular reference for who-may-reach-what** (ADR-517; FOUNDATIONS Derived Principle 36;
GLOSSARY §Reach & Sharing). Consult this before touching share, invite, grant, viewer, or
membership code — do not re-derive the model from the ADR trail. The lineage: ADR-373 (the
grant is the authorization fact) → ADR-386 (lifecycle) → ADR-431 (MCP grants) → ADR-437/465
(share transport + shapes) → ADR-513 (public view) → **ADR-517** (mint authority + role-honest
enforcement — the current ruling set).

**Disambiguation first**: this document is about the **reach grant** (`principal_grants` — who
may reach the workspace). The **autonomy grant** (`governance/` — how far an *agent's
decisions* bind, ADR-366) shares nothing but the word.

---

## 1. The model in one paragraph

Governance is **workspace-level** (ADR-378: nothing above the workspace). The **grant is the
single authorization fact** — one `principal_grants` row per (principal, workspace), carrying a
`role` and two path-prefix axes (`read_scopes` / `write_scopes`, the powerbox, migration 211).
Principals are **species-blind** (ADR-405): humans, viewers, and connected AIs hold the same
kind of row; technical handling differs (`CALLER_WRITE_POLICY` locks MCP callers out of
governance regions), authorization kind never does. **Mutating grants is governance**
(`routes/workspace.py::_require_owner_workspace`: "anything that mutates WHO may act") — so
mint, narrow, revoke, and invite all sit behind governance gates. **Share is the reflexive verb
of governance**: the one act that writes to the grant table itself. There is deliberately **no
separate share policy system**. **Export is outside the model entirely** — see §7.

## 2. The roles

| Role | What it is | Write reach | Seat? | Minted by |
|---|---|---|---|---|
| `owner` | The constitutional author (ADR-386 D4) | everything | yes | genesis |
| `member` | A human collaborator | class default (`operation/` + `agents/`), narrowable per-grant | yes | share accept · invite accept |
| `viewer` | Read-only reach, scoped to the shared artifact (ADR-517 D1) | **none — DB-enforced** | **no** | viewer-share accept |
| `foreign-llm` | A connected AI (ADR-431; owned by `connected_by`) | `operation/` only (`CALLER_WRITE_POLICY`) | no | OAuth connect |
| `own-agent` | A hired program agent (ADR-414 D5) | per hire | no | program activation |
| `platform` / `a2a` | Reserved (no creation path) | — | no | — |

**Viewer specifics**: `role='viewer'` with `write_scopes=[]`, `read_scopes=[artifact]`.
Renders in the roster (an invisible principal is an ungovernable one), enters the workspace
switcher, is excluded from `is_workspace_member` (no co-member roster read) and from
`HUMAN_SEAT_ROLES` (view-only reach never bills). **Widening a viewer is a re-grant** — an
owner role-change, never an axes edit; RLS would silently deny a viewer-role grant with write
axes, so the primitive layer must refuse the combination instead.

## 3. The enforcement contract (ADR-517 R1 — read this before writing substrate queries)

Two layers, each guaranteeing a different thing:

| Layer | Guarantees | Where |
|---|---|---|
| **RLS** (Postgres) | Membership + the **role-binary**: any active grant reads; a `viewer`-role grant cannot INSERT/UPDATE/DELETE `workspace_files` / insert `workspace_file_versions` (migration 234; migration 235 dropped the pre-ADR-373 legacy `user_id` policies that OR'd around both predicates — found live by the 2026-08-04 click-pass) | migrations 189/198/221/234/235 |
| **Primitive layer** (Python) | **Path-prefix narrowing** on both axes | `grant_read_scopes` / `path_under_scopes` / `read_scope_db_prefixes` in `services/primitives/workspace.py` |

> **The contract**: any code path that reads or writes substrate on the user-scoped client
> without routing through the primitive filters gets **membership-truth, not scope-truth** —
> a narrowed member's prefixes are NOT enforced by the database. Such a path must either route
> through the filters or state at the call site why membership-truth suffices. Full prefix-RLS
> was deliberately deferred (ADR-517 R1); revisit only with evidence this contract is breached
> in practice.

## 4. Mint / revoke authority (ADR-517 D3/D4)

One gate — `services/workspace_shares.py::assert_may_mint_share` — called by **both** origins
(cockpit `POST /api/workspace/shares` + the MCP `share` verb; species-blind):

| Act | Who may |
|---|---|
| Mint a share link | Owner always. Otherwise: non-viewer role AND not write-deny-all, subject to the dial. |
| The dial (`workspaces.share_mint_policy`) | `write-holders` (default) \| `owner-only` |
| Revoke a share link | Owner (any link) · the minter (their own) |
| Invite / narrow / revoke a grant / set caps | Owner only (`_require_owner_workspace`) |

The closed doors this replaced: any grant holder (including viewers, including a viewer's
laundered third party) could mint bare workspace-wide `member` links (ADR-515 §6.1); the MCP
verb skipped even the reach check; any member could revoke anyone's link.

## 5. The two doors

| | **Share** (`workspace_shares`) | **Invite** (`workspace_invites`) |
|---|---|---|
| Recipient | anyone with the link | one email, matched at accept |
| Scope | workspace or one artifact (`artifact_path`, **absolute spelling**, normalized at `create_share`) | workspace only — no artifact column |
| Grant shape | `member` (broad) or `viewer` (birth-narrowed) | `member` only |
| Minted by | write-holders (dial-gated) | owner only |
| Public preview | `/s/{token}` — anonymous, capped content + attribution walk, `no-store` + `noindex` on every status (ADR-513) | none |

They never merged because invites carry no artifact scope — a missing capability, not
vocabulary drift (ADR-515 §4). Extending invites to artifact scope is a real migration, owned
by no current ADR.

## 6. Standing-state surfaces (what answers "who can reach this?")

- **`WorkspaceMembersCard`** (Settings → Access, both mounts): the roster of principals —
  humans + AI as peers — with invite/narrow/revoke/cap. Shows reach as workspace *regions*.
- **Get Info / `NodeDetailsPanel`** (ADR-512 D6): per-file reach (`FileReach`) + this file's
  live links with revoke (`FileShares`).
- **Known half-view (owed, named by ADR-515 D6)**: the rail is per-principal-never-per-file;
  Get Info is per-file-never-per-principal. The direction of resolution (ADR-517 discourse):
  render live share links as **principal-class rows in the roster** ("Anyone with link ·
  view-only · path · Revoke") — publicness becomes legible by reading one surface.
- **Publicness is derivable, never stored**: a file is public iff a live link covers it. A
  per-file visibility attribute is the DP36 diagnostic for reintroducing a second
  authorization system.

## 7. Export — the contrast, not a sibling

Share changes *who can reach* the file: in-system, attributed, revocable — an authorization
act. Export changes *where the bytes are*: out-of-system, attribution stripped, irreversible —
past read access, prevention is impossible (print, copy, screenshot), so export is governed by
**honesty**: the declared-omissions manifest (`EXPORT-MANIFEST.md`, ADR-510 D4) and copy that
states what leaves. Export never appears inside a share surface (ADR-515 D5). The export lane's
own canon (FE door, ADR-328 Phase-1 package, stale PDF/PPTX doc repairs) is a separate arc
(ADR-517 R3).

## 8. Owed (tracked, not silently open)

- **FE convergence** (ADR-515 phases 2–5 + the rail pass): the Share modal, the
  `Copy AI reference` verb move, the precondition seam, links-as-roster-rows, the
  `share_mint_policy` dial UI, viewer-promotion affordance. Click-pass lane.
- **FE retirement of `shareKey()`** (`NodeDetailsPanel.tsx`) once no pre-234 client writes
  relative paths.
- **Stale user docs**: gitbook expiry claim (false — no UI passes `ttl_days`), always-member
  claim (false since ADR-465 Phase D), view-only undocumented; AUTHORING.md Share placement.
- **Invite-with-artifact-scope**: named, unowned (§5).
