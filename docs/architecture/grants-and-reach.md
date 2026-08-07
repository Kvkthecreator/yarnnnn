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

## 3a. The axis-state display contract (ADR-532)

The two axes are **three-state** (ADR-434 D3), and each state means something a
surface must render differently. Any pane that displays reach reads this table —
**do not re-derive it, and never compute a displayed reach from a different
function than the one that enforces it.**

| Axis value | Means | Enforced by | Displayed as |
|---|---|---|---|
| `NULL` | Not narrowed — falls through to the class default | write: `_is_path_locked_for_principal` (class policy) · read: `_is_path_readable_for_principal` → **True, read-all** | "Not narrowed". Read reach is **the whole substrate** (`READ_ALL_REGIONS`), NOT the write class default |
| `[]` | Deny-all on that axis | both gates deny | "nothing" |
| `[..]` | Exactly these prefixes, at any depth | `path_under_scopes` (longest-prefix) | the paths |

Three rules follow, each of which was violated in production before ADR-532:

1. **NULL is not a path list.** A surface must never seed, suggest, or default a
   NULL axis into a concrete prefix row. `NULL` tracks the class policy as it
   evolves; `['operation/']` pins a literal prefix. Collapsing them re-introduces
   the polarity loss ADR-434 D3 removed — and, if the row is editable, lets an
   operator narrow a principal merely by opening a dialog and pressing Apply.
2. **The read display reads the READ gate.** Reporting the *write* class default
   as read reach understates the kernel by the entire commons. (This was the
   ADR-501 D1 display/gate divergence recurring on the second axis.)
3. **The axes are independent in the KERNEL** (ADR-434 D1: `read ⊇ write` is the
   backfill default, never a constraint) — and the cockpit deliberately does not
   expose that. `narrow_grant` mirrors read from write by default and zero live
   grants move them apart, so a per-path read control would be UI carrying a
   distinction nothing sets. The read-only auditor stays representable in the
   grant and reachable over the API. **Surface the axes separately only when a
   real use case asks**; until then the cockpit sets both together.

**What the cockpit may express at all** (ADR-532 §3a): `narrow` is
**narrow-only** — `narrow_grant::_within` raises `ScopeEscalation` on any
widening — and the class ceiling is `operation/`. So a grant-editing surface can
offer exactly three states: the class default (`null`), a subset of the ceiling
(`[..]`), or nothing (`[]`). **Never offer a path outside the principal's current
reach**: the server refuses it, so the control is one that cannot be entered.
Widening is a different act and needs its own deliberate path.

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
| Public preview | `/s/{token}` — anonymous, capped content + attribution walk, `no-store` on every status (ADR-513). **Indexable since ADR-531** — `noindex` removed so ChatGPT's search-mediated retrieval can read it. | none |
| Machine read | `/s/{token}` negotiated on `Accept`, or the alias `/s/{token}.txt` — the file's **model-consumable projection** (DP34/ADR-530), `Link: rel="canonical"` home. Same token, same capability, same revocation. | none |

They never merged because invites carry no artifact scope — a missing capability, not
vocabulary drift (ADR-515 §4). Extending invites to artifact scope is a real migration, owned
by no current ADR.

## 5a. What a share link actually surrenders (ADR-531 — read before arguing "privacy")

A capability link collapses three different properties that get called "privacy". Separating them
is what makes any share decision arguable rather than vibes-based:

| Property | Controlled by | State once a link is minted |
|---|---|---|
| **Confidentiality** — may a holder read it | the token | **already surrendered, deliberately** (ADR-513 D1: *"the sharer already decided the world-with-the-link may see this"*) |
| **Discoverability** — may a non-holder find it | indexing | open since ADR-531 (indexable by searching; still not guessable — 192-bit token) |
| **Revocability** — may I take it back | `status='revoked'` + `no-store` | **authoritative at the origin, best-effort in the world** |

**The consequence to state plainly when anyone asks**: a revoked link goes dark at the origin
immediately; a copy already retained by a third-party index may outlive the revoke. That cost was
accepted knowingly for reach (ADR-531 §4), over a recorded objection — **not** discovered
afterwards. A future session finding an indexed-but-revoked share is looking at a ratified
trade-off, not a bug.

## 6. Standing-state surfaces (what answers "who can reach this?")

- **`WorkspaceMembersCard`** (Settings → Access, both mounts): the roster of principals —
  humans + AI as peers — with invite/narrow/revoke/cap. Shows reach as workspace *regions*.
- **Get Info / `NodeDetailsPanel`** (ADR-512 D6): per-file reach (`FileReach`).
- **`ShareDialog`** (ADR-529 D1) — the singular mint surface, raised from the `FileVerbs`
  bundle so every file surface opens the same act. It also carries **this file's live links
  with revoke**, which is where the operator manages what they minted. (The old `FileShares`
  block in `NodeDetailsPanel` is DELETED, ADR-529 D4 — do not reintroduce a second place to
  revoke a link.)
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

**Closed 2026-08-06 by [ADR-529](../adr/ADR-529-one-share-act-one-link-two-readers.md)**: the
Share modal (one `ShareDialog` on the `FileVerbs` bundle, replacing three divergent surfaces);
the `shareKey()` retirement (ADR-517 D5's named dead defence — paths have been
canonical-absolute at the write since migration 234); and the public link's legibility (the
page is server-rendered, so a machine handed the link can read it, and `Accept: text/markdown`
serves the same projection as prose — one URL, two representations).

**Closed 2026-08-06 by [ADR-530](../adr/ADR-530-the-projection-is-a-property-of-the-file.md)**: the
public boundary now serves the file's **model-consumable projection** (DP34) rather than its raw
container — closing a live defect where an `.html` share was readable only inside its locked
iframe, and a shared PDF/XLSX/ZIP had its raw bytes emitted into a `<pre>`. Formats with no
registered strategy are legibly marked, never dumped. The link gained a **machine address**
(`/s/{token}.txt`, an alias with `rel="canonical"`).

Still owed:

- **FE convergence remainder** (ADR-515 D3/D4/D6 + the rail pass): the `Copy AI reference` verb
  move, the internal-referral ADR, the precondition seam, links-as-roster-rows, the
  `share_mint_policy` dial UI, viewer-promotion affordance. Click-pass lane.
- **The click-pass for ADR-529 itself** — the dialog + the public view have not been driven in
  a browser (opaque-origin iframe defeats CDP for the Studio mount; the Files mount and `/s`
  are drivable).
- **Rate limiting on `/api/s/{token}`** — named owed by ADR-513 D5 and slightly more owed now
  that SSR makes the surface cheaper to scrape. The token's 192 bits still carry enumeration.
- **Stale user docs**: gitbook expiry claim (false — no UI passes `ttl_days`), always-member
  claim (false since ADR-465 Phase D), view-only undocumented; AUTHORING.md Share placement.
- **Invite-with-artifact-scope**: named, unowned (§5).
- **Stored projections** (ADR-530 D6): v1 derives on read behind one seam
  (`project_for_machine`). The conformant end state is a projection as a *cited substrate object*
  (`derived_from`, per DP32/ADR-395) computed at write — cacheable, attributable, and what makes
  ADR-512 D5's reserved `@{revision_id}` form reachable at this boundary.
- **Image delivery + sub-part addressing** (ADR-530 D7): `passthrough` kinds are honestly marked
  in v1; delivering the image itself, and addressing a figure *inside* a document, are named-
  deferred.
