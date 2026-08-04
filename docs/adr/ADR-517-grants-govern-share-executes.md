# ADR-517 — Grants govern, share executes: the workspace reach model made honest

**Status**: Accepted (2026-08-04, operator-ratified — the three rulings below were put to the
operator explicitly and each landed on the recommended option)
**Date**: 2026-08-04
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Identity (who may reach what) + Governance (who may change who may reach what)

**Amends**:
- **ADR-437 D4.3** ("ONE grant model — the role column stays `member`; the narrowing lives on
  the axes") — **overturned by D1**. The one-grant-model *intent* survives (one table, one
  authorization fact); the role-spelling does not: a viewer-born grant now stores `role='viewer'`,
  because a role the database cannot see is a role the database cannot enforce (§1.2).
- **ADR-437 D4 / ADR-408 D1** ("any principal with a grant may share — the free-for-all") —
  **narrowed by D3**. Minting a grant is governance; governance is never free-for-all.
- **ADR-465 D3** (share-as-view) — preserved; its viewer shape gains DB-level teeth.

**Ratifies**: **ADR-515 §6.1** (open question 1 — "can a viewer grant a share?"). Ruling: **no.**
This ADR is the floor ADR-515's phases stand on; ADR-515's surface work (the modal, the verb
move, the D6 seam) remains ADR-515's own. Its D8 (delete the dead `POST /api/share`) is executed
here (D7) because it belongs to the same deletion sweep.

**Preserves**: ADR-373 (the grant is the authorization fact) · ADR-378 (workspace outermost) ·
ADR-405 (species-blind: permission is a grant, never a species rule) · ADR-431 (the connecting
member owns the MCP grant) · ADR-386 (grant lifecycle) · ADR-513 (public view transport) ·
ADR-445/490 (seats — see D6: a viewer is not a seat).

---

## 1. Context — the audit and the convergence

A three-lane audit (2026-08-04, backend grants / export lane / FE surfaces + docs) confirmed the
operator's thesis that sharing was structurally under-authorized and under-documented. The two
load-bearing findings:

### 1.1 The escalation door (ADR-515 §6.1, confirmed live)

`POST /api/workspace/shares` gates only on `principal_reaches_workspace`, which is role-blind
(`supabase.py` selects `id` by principal + workspace + `status='active'`, never reading `role`
or the scope axes). The chain: a viewer accepts a single-file view link → holds an active grant
→ mints a **bare workspace-wide `member` link** (`artifact_path` is optional) → a third party
lands the broad class-default grant. A read-only holder of one file laundered full membership.
The MCP `share` verb was weaker still — it skipped even the reach check.

Meanwhile `routes/workspace.py::_require_owner_workspace` already states the rule the mint path
violates: *"Governance = anything that mutates WHO may act or HOW FAR they may act."* Minting a
grant mutates who may act. Share-mint was the one governance verb not behind a governance gate.

### 1.2 The enforcement divergence (worse, and previously unregistered)

The `viewer` shape existed **only in the application layer**. `accept_share` deliberately stored
`role='member'` (ADR-437 D4.3) with narrowing on the powerbox axes — and **zero RLS policies
read `read_scopes`/`write_scopes`**. Migration 198's write policies (its very name is
`member_write_scope`) are membership-binary: any active grant = full DB write reach on
`workspace_files` + `workspace_file_versions`. A viewer was a member at the database. Every
un-scoped query path — present or future — was a hole, even for a well-behaved viewer.

### 1.3 The converged model (operator-ratified framing)

> **Grants are the governance system; share is just one mechanism that executes against it** —
> the mechanism that mints new grants. Governance is workspace-level; narrowing is per-grant
> path scopes; principals are species-blind (technical handling may differ; authorization never
> keys on species). There is **no separate share policy** — share folds under the one
> governance model. **Export is a different kind of act entirely** (a read that escapes the
> system: bytes leave, attribution and revocability are lost) and is carved out to its own arc.

## 2. The three rulings (operator, 2026-08-04)

| # | Question | Ruling |
|---|---|---|
| R1 | Where is grant narrowing enforced? | **Role-honest RLS + app prefixes.** The grant row stores its true role; RLS excludes `viewer` from writes at the DB; path-prefix narrowing stays in the primitive layer under a written contract (D2). Full prefix-RLS deliberately deferred. |
| R2 | Who may mint share links? | **Write-holders mint; viewers never.** A workspace dial (`share_mint_policy`) lets the owner tighten to owner-only. Species-blind: the same gate binds the cockpit and the MCP verb. |
| R3 | Arc scope | **Share/governance arc now; export arc after**, as its own ADR. |

## 3. Decisions

### D1 — The role is honest: `viewer` is a first-class grant role

A viewer-born grant stores `role='viewer'` (CHECK constraint widened, migration 234).
`accept_share`'s viewer branch mints `role="viewer"` with the same birth-narrowed axes
(`write_scopes=[]`, `read_scopes=[artifact]`). Existing viewer-born grants are backfilled by
their birthmark (`granted_by LIKE 'share-view:%'` **and** `write_scopes = '{}'` — the axes
guard means a grant an owner has since widened is left alone).

Why the amendment to ADR-437 D4.3 is safe: nothing keyed on "viewer-ness" before, because
viewer-ness wasn't representable — the axes carried it, and the axes survive unchanged. What
changes is that the database can now *see* the shape it is asked to enforce.

**Promotion is a re-grant.** Widening a viewer to a writer is a role change, not an axes edit —
an owner act via the rail (affordance owed to the FE phase). RLS would silently deny a
`viewer`-role grant given write axes; the primitive layer refuses the combination instead.

### D2 — Enforcement boundary, canonized: RLS carries the role-binary, the primitive layer carries the prefixes

Migration 234 recreates the four substrate write policies (3× `workspace_files`, 1×
`workspace_file_versions` INSERT) with `role <> 'viewer'` in the grants subquery. Reads stay
grant-broad at the DB and artifact-narrowed in the primitive layer (`grant_read_scopes` /
`path_under_scopes`), as today.

**The written contract** (this is the part that was missing, not the code): the database
guarantees *membership and the write/read role-binary*; the primitive layer guarantees
*path-prefix narrowing*; *any code path that reads substrate on the user-scoped client without
routing through the primitive filters gets membership-truth, not scope-truth, and must say so at
the call site.* This contract lands in `docs/architecture/grants-and-reach.md` (D8) — the
singular home; do not re-derive it.

### D3 — Mint authority: write-holders mint, viewers never, and the dial can tighten

One gate, `assert_may_mint_share(user_id, workspace_id)` in `services/workspace_shares.py`,
called by **both** origins (cockpit route + MCP `share` verb — species-blind, per ADR-405):

1. The owner always may.
2. Otherwise the caller's grant is loaded: `role='viewer'` → refuse; explicit `write_scopes=[]`
   → refuse (a narrowed-to-nothing member is a viewer in fact).
3. The workspace dial `workspaces.share_mint_policy` (`'write-holders'` default |
   `'owner-only'`): on `'owner-only'`, non-owners are refused regardless of write reach.

The MCP verb additionally gains the `principal_reaches_workspace` check it always should have
had (gate parity with the cockpit origin).

### D4 — Revocation is governed by the same logic

`revoke_share` learns who is asking: the **owner revokes any link; the minter revokes their
own**. The prior rule (any grant holder revokes anyone's link) was the mint hole's mirror — a
denial door instead of an escalation door.

### D5 — One spelling for `artifact_path`, normalized at the write

The canonical spelling is **absolute** (`/workspace/…` — the substrate's own path identity).
`create_share` normalizes; migration 234 backfills existing rows. The two downstream
compensating normalizers (FE `shareKey()` in `NodeDetailsPanel.tsx`, the inline abs-conversion
in the `/s/{token}` preview) become dead defence — the preview's is removed now; the FE one
retires in the FE phase. Three origins, one column, one spelling: the 2026-08-03
unrevocable-live-link defect class ends at the write, not at each reader.

### D6 — A viewer is a principal, not a seat

Role-consumer sweep, decided per consumer rather than by accident:

| Consumer | Treatment of `viewer` |
|---|---|
| Workspace switcher (`.in_("role", ["member"])`) | **Included** — a viewer must be able to enter the workspace they can view. |
| Members roster (BE buckets + FE `HUMAN_ROLES`/`ROLE_META`) | **Included, labeled Viewer** — an invisible principal is an ungovernable one. |
| `HUMAN_SEAT_ROLES` (billing, ADR-445/490) | **Excluded — unchanged `("owner","member")`.** View-only reach does not bill a seat; the existing ratchet asserting the pair stays green and now guards this ruling too. |
| `is_workspace_member` (mig 221) | **Excluded** — viewers do not read the co-member grant roster. |
| `class_default_write_regions` | Returns `[]` for `viewer` — the class default IS deny-all, so even a hypothetical axes-less viewer grant inherits nothing. |

### D7 — Deletions (Singular Implementation)

- **`POST /api/share`** (`routes/documents.py::share_file_global`, ADR-127) — deleted. Zero FE
  callers (verified by sweep); it squatted the product's most load-bearing word writing to a
  `/user_shared/` staging area nothing reads. Executes ADR-515 D8.
- The `/s/{token}` preview's inline path re-normalization — deleted with D5.
- ADR-437 D4.3's role-spelling comment block in `accept_share` — rewritten to the honest model.

### D8 — The canon package (the documentation half of the thesis)

1. **FOUNDATIONS** gains the reach principle the ADR-373 lineage always leaned on but never
   canonized: *who may reach what is a grant — workspace-scoped, per-grant narrowed,
   species-blind; mutating grants is governance.* (ADR-515 cited "Axiom 2 — who may reach what";
   Axiom 2 is authorship. The missing principle lands as a Derived Principle, not a rewrite of
   Axiom 2.)
2. **GLOSSARY** gains entries: **Grant** (disambiguating the *reach* grant from the *autonomy*
   grant — two concepts, one word, previously undefined), **Share** (the mechanism), **Viewer**,
   **Invite** (email-locked, workspace-scoped, owner-only — vs the link-based share).
3. **`docs/architecture/grants-and-reach.md`** — the singular reference for the reach model:
   the grant table, the roles, the axes, the enforcement contract (D2), the mint/revoke
   authority table (D3/D4), the two doors (share/invite), and the standing-state surfaces.
4. Stale-doc repairs are **enumerated as owed** where not landed in this arc: STUDIO.md's Share
   placement (moved to the header 2026-07-24), gitbook's expiry claim (false — no UI passes
   `ttl_days`) and always-member claim (false since ADR-465 Phase D), view-only documented
   nowhere user-facing.

### D9 — Out of scope, deliberately

- **The FE convergence** — Share modal (ADR-515 D2), the verb move (D3), the D6 seam, share
  links rendered as principal-class rows in the rail, the `share_mint_policy` dial UI, viewer
  promotion affordance. FE surface work rides the browser click-pass lane and lands as ADR-515's
  own phases plus a rail pass. This arc gives those surfaces a floor that cannot over-grant.
- **The export arc** (R3) — FE export door, the stale PDF/PPTX canon (`output-substrate.md`,
  `registry-matrix.md`, GLOSSARY:167), ADR-328's Phase-1 canon package, ADR-510's LEDGER entry.
  Own ADR, next arc. The carve is semantic, not organizational: share changes *who can reach*
  (in-system, revocable — authorization); export changes *where the bytes are* (out-of-system,
  irreversible — honesty, not prevention).
- **Full prefix-RLS** — R1 defers it; revisit only with evidence the primitive-layer contract
  is being breached in practice.

## 4. Phases

1. **Migration 234** — role CHECK + backfill-by-birthmark + 4 write policies + dial column +
   path-spelling backfill. (This commit.)
2. **Backend** — D3 gate both origins, D4 revoke, D5 normalize-at-write, D6 sweep, D7
   deletions. (This commit.)
3. **Gates** — `api/test_adr517_grants_govern.py`: mint-authority refusals executed (not
   grepped), viewer-role mint on accept, canonical spelling, dead-endpoint absence, RLS
   migration shape. Existing ADR-465/513 suites stay green; the ADR-445 seat ratchet now guards
   D6. (This commit.)
4. **Canon** — D8 package. (Docs commit, same arc.)
5. **FE phase** — D9 first bullet, owed to ADR-515 execution + a rail pass, click-pass lane.

## 5. The one-line statement

**Grants govern reach inside the boundary; share is governance minting new reach; export is the
boundary being crossed — and now the database, the gate, and the canon all say the same thing.**
