# ADR-534 — The share link is a standing address, and an honest one when it breaks

**Status**: **Accepted** (2026-08-07, operator-ratified across three turns). The operator
commissioned the audit — *"shouldn't the user experience be centered for view only to more
readily show and 'reuse oriented' that link? right now the inverse seems to be true from a UI UX
standpoint"* — ruled on the framing — *"this is different from a publish act… closer to
optimization and efficiency framing under the sharing architecture"* — and, when this ADR's first
draft proposed chasing paths through mutations, **overruled it**: *"i actually am leaning to
option C, an honest way, which i think existing home pages and URL handling does? which makes me
lean that is the actual more future proof scalable method."*
**Date**: 2026-08-07
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Channel (Axiom 6 — the doors a file travels through, and what the operator can see
of a door they already opened)

**Amends**:
- **ADR-529 D1** — the `ShareDialog`'s four contents are **preserved**; what changes is their
  ORDER OF AUTHORITY. D1 item 2 said "the minted URL, visible"; item 3 said "this file's active
  links". This ADR states that an *already-live* link is item 2's equal, not item 3's footnote —
  **the dialog opens on what exists**.
- **ADR-513 D2** (the public boundary) — touched in exactly one place, deliberately: the **token**
  joins the *authenticated* `list_shares` projection (D2). Named as a boundary move and argued on
  its own, NOT smuggled in under the representation argument that carries D1. The **public**
  projection is unchanged.

**Preserves**: ADR-373 (the grant is the authorization fact) · ADR-517 (grants govern, share
executes — mint/revoke authority untouched) · ADR-515 D5 (Export never appears in a share
surface) · ADR-531 D3 (**no publish act** — see §2.1) · ADR-529 D2/D3/D5 (one projection, SSR,
the re-weighted public view) · **ADR-448** (the reference edge is a historical fact, never a live
foreign key — this ADR applies that same ruling to the share row, see §3).

---

## 1. Context — two defects in one mechanism

### 1.1 The surface treats a link as valuable only while it is new

Read from `ShareDialog.tsx`, not from a summary of it. On open (lines 104–112) the dialog clears
`role`, clears `minted`, and *then* loads existing links. The consequences, as the operator meets
them:

| What the operator has | How the dialog renders it | Affordances offered |
|---|---|---|
| A link minted **10 seconds ago** | labeled field · monospace · selectable · Copy control · a consequence line (lines 225–252) | copy, re-copy, read |
| A link minted **last week, still live, still resolving the current file** | one row in a footer list: the words "View only" and a Revoke button (lines 263–280) | **revoke — and nothing else** |

These are the same object. One `workspace_shares` row, one token, one capability, identical
lifecycle. The only difference is which side of a page-load it was created on.

> **The finding**: the dialog is a *mint form* that happens to list its own history. The one
> durable, reusable thing it produces is rendered as a footnote whose sole affordance is
> destruction — and on a file that already has a live link, the primary button reads **"Create
> another"**. The path of least resistance is duplication.

### 1.2 Why this bites view-only hardest

The two shapes have genuinely different lifecycles, and the surface treats them identically:

| | **Full access** | **View only** |
|---|---|---|
| What accepting does | mints a broad `member` grant; stamps `accepted_principal_id` | mints a birth-narrowed `viewer` grant |
| After acceptance | the link has **done its job** — the person is a member now | the link **is** the ongoing artifact — nothing was converted |
| Natural cardinality | arguably one per recipient (revoke one without killing others) | **one per file**, reused indefinitely |
| Grants anything | yes — governance | **no reach a reader did not already get from the token** |

A View-only link converts nobody, never expires (`DEFAULT_SHARE_TTL_DAYS = None`,
`workspace_shares.py:36`), and resolves its `artifact_path` against `workspace_files` **live on
every request** (`routes/shares.py:373-379` — no snapshot, no stored projection, no pinned
revision). It is the closest thing yarnnn has to a **permalink for a document**. Handing that
shape a "Create link" button as its primary action is a category error.

### 1.3 The second defect: a moved file breaks its links SILENTLY

Neither `routes/documents.py::move_document` (line 897) nor `routes/studio.py::rename_artifact`
(line 667) reads or writes `workspace_shares` — verified by sweep: **zero** `share` references in
either handler or in `services/primitives/workspace.py`.

Worse, the break is structural rather than incidental. `handle_move_file`
(`primitives/workspace.py:1419`) is **write-new + delete-old**:

```
write_revision(abs_dst, content)   → a NEW workspace_files row, NEW uuid
delete_live_file(abs_src)          → tombstone + DELETE the old live row
```

So a moved file is a *different row with a different id*, related to its predecessor only by a
message string in the revision chain.

The consequence at the share boundary: the preview's lookup returns no rows
(`shares.py:374-379`) and the link renders **`200` with no artifact content** — not a 404, not a
410, not anything a reader or an operator can act on. A silent, healthy-looking empty page.

**That silence is the defect.** Not the breakage.

## 2. The axiom

> **A live share link is a standing address for a file: durable, reusable, resolving to the
> current content on every read. It names a path, not an identity — so when the path stops
> naming that file, the link says so out loud instead of rendering blank.**

### 2.1 Why this is NOT the publish act ADR-531 D3 refused

`grants-and-reach.md` §8 lists **"a publish act — deliberately NOT built (ADR-531 D3)"**, because
publishing is a **distribution** act (audience, reach, GTM) while sharing is an **interop** act (a
specific collaborator in a specific document) — and folding one into the other repeats the
ADR-515 one-button-three-jobs error.

**Operator ruling (2026-08-07)**: this ADR is not adjacent to that refusal, it is orthogonal to
it. Recorded so a future session cannot mistake it for precedent:

| | **Publish (refused)** | **This ADR** |
|---|---|---|
| Changes who may reach | **yes** — a new audience | **no** — the reach decision was made at mint |
| New transport / token class | yes | **none** |
| New boundary | yes | one narrow, named, separately argued (D2) |
| What it optimizes | distribution | **the operator's use of a decision already made** |

Publish asks *"who should see this?"* — a reach question. This asks *"where is the link I already
made, and is it still pointing at anything?"* — a lifecycle question.

## 3. The rejected alternative, recorded — path-chasing and file-identity

This ADR's first draft proposed a `repoint_shares` helper called by move/rename: chase the path,
rewrite the share row. **The operator overruled it**, and the reasoning is canon-worthy because
the rejected option is the one a future session will re-derive as an obvious improvement.

**Why not chase the path (option A).** A helper every relocation verb must remember to call is an
*obligation*, not a mechanism. Two verbs already forgot; `DuplicateFile` exists; a `MoveFolder`
would need it too. It scales by discipline, not by construction — and the failure mode is silent,
which is the same class of defect this ADR exists to remove.

**Why not bind to a file identity (option B).** The obvious chokepoint fix — store `file_id`, not
`artifact_path` — **is not available in this substrate**: `MoveFile` is write-new-delete-old, so
`workspace_files.id` does not survive a move. Making it survive means an identity-preserving
`UPDATE … SET path`, which contradicts the ADR-209 single-write-path model and imposes a standing
invariant (*the substrate may never again relocate a file in a way that loses row identity*) on a
write model built the other way. That is a substrate ADR, not a share ADR.

**Why honest-failure is the right answer, not merely the cheap one.** Three independent
arguments, and they converge:

1. **The operator's URL precedent.** The web has an identity mechanism (`301`) that nobody
   maintains at scale, and runs instead on: a URL names a resource by path, paths break, and a
   broken one says `404` — with `410 Gone` distinguishing *deliberately ended* from *never was*.
   That is not a compromise the web fell into; it is what let it scale without a global identity
   registry or referential integrity across a decentralized namespace.
2. **The substrate already ratified exactly this ruling.** ADR-448's reference edge
   (`authored_substrate.py:232`): *"The edge is a HISTORICAL FACT about the revision, not a live
   foreign key — a later move/rename of a source never rewrites the ledger."* A share row is the
   same shape of reference. Chasing paths in `workspace_shares` while refusing to chase them in
   the ledger would be two answers to one question.
3. **DP34's anti-silent-drop clause, one layer up.** ADR-530 established at *this same boundary*
   that a format with no strategy is *"a KNOWN GAP, said out loud"* — legibly marked, never
   dropped. A share whose file has moved is the same kind of gap; today it renders an empty 200,
   which is the silent-drop failure DP34 forbids.

**The measurement that sized this** (2026-08-07, by sweep): `derived_from` edges are **already**
honest-by-design (ADR-448, above). The ADR-514 launch-handler binding is **genuinely broken** —
it writes `workspace_files.metadata` and `handle_move_file` carries `content` only, so the
comment at `routes/documents.py:954` claiming a handler *"travels with it through move/rename"*
is **false**. That is a real defect in a different mechanism; it is **named as owed (§7)**, not
fixed here, and it does not change this ruling — one broken binding is a bug to fix honestly, not
evidence for a substrate-wide identity system.

## 4. Decisions

### D1 — The dialog opens on the link that exists

When a live link of a given shape already exists for this file, **that shape's card carries the
link**: URL visible, selectable, with a Copy control — the same weight a freshly minted URL gets
today. `role` seeds from what is live instead of `null`.

The reuse lookup keys on **(artifact_path, role)**, never path alone — a file with both shapes
live must surface the right one, and a path-only lookup would hand a View-only requester a
Full-access link. This is the load-bearing detail.

**Minting a second link of the same shape stays reachable and becomes deliberate** — a secondary
control, never the primary button. Multiple links to one file remain legitimate and are NOT
deprecated: the transport is link-based precisely so one recipient's link can be revoked without
killing the others. What ends is *accidental* duplication.

**Full access keeps that control prominent**, because per-recipient links are its genuine use
(§1.2). View-only demotes it, because one address per file matches the mechanism.

**Why not dedupe at the server** (an upsert in `create_share`): the duplicate is sometimes what
the operator wants, and a server silently returning an existing row would make "give this
contractor their own revocable link" unexpressible. The fix belongs at the surface that chooses,
not the write that executes — mirroring ADR-529 D1's own discipline that no default fires without
a click.

### D2 — `list_shares` returns the token (a boundary move, argued on its own)

D1 is impossible without it: `list_shares` (`workspace_shares.py:164-173`) selects
`id, artifact_path, label, role, status, created_at, expires_at, last_accepted_at` and **no
token**, so the FE cannot render an existing link's URL at all.

This is a real widening and it does **not** ride D1's presentation argument. Stated plainly: the
authenticated, workspace-scoped list endpoint begins returning live capability URLs.

Why it is nonetheless correct:

1. `GET /api/workspace/shares` is already gated by `_acting_workspace` →
   `principal_reaches_workspace`.
2. Every caller who can list can already **revoke** — strictly more power over the same object
   than reading its URL.
3. The mint response already returns `share_link` (`shares.py:148`); what is new is a *list*.
4. A capability the owner cannot see is one they cannot audit. ADR-529 D1.2's own reasoning —
   *"a link you cannot see is one you cannot verify"* — applies with equal force a week later.

**What stays out**: the public `/s/{token}` projection (ADR-513 D2) is **unchanged**. No token
crosses to an anonymous reader; this is the authenticated list only. The gate asserts both halves
as a pair.

### D3 — The list becomes actionable, not just destructive

Each live link renders: its shape, its **URL with a Copy control**, when it was minted, and
Revoke. Today it renders a role word and Revoke (`ShareDialog.tsx:263-280`).

The asymmetry this removes: an operator could destroy a link they could not read. Revoke is the
most consequential act in the list and it was the only one offered.

### D4 — A share whose file is gone is DARK, not blank (replaces path-chasing)

The share row keeps its `artifact_path` and resolves at read time. When that path no longer names
a live file, the boundary says so:

- **`GET /api/s/{token}` returns `410 Gone`** with a distinct detail — *"The shared file was moved
  or deleted."* Carries `_CAPABILITY_HEADERS` like every other error exit (the 2026-08-03 defect
  class where a bare `raise` shipped without `no-store`).
- **The distinction is preserved, never collapsed.** Three different facts, three different
  answers — `404` no such token · `410 revoked` a decision · `410 file gone` a mutation.
  `grants-and-reach.md` §8a's diagnostic runbook gains the third, because an operator debugging
  *"why can't my client see this"* needs to know which happened.
- **A bare workspace share (no `artifact_path`) is unaffected** — it never named a file.

**The operator learns at the moment they cause it.** The web cannot tell a publisher "you just
broke 14 inbound links"; yarnnn can — the move handler can see live shares on the source path.
This is *not* chasing: nothing is maintained, nothing is rewritten, no obligation lands on future
verbs. The move proceeds either way. The ShareDialog simply renders a live-but-dark link
**honestly, as a broken link with Revoke** rather than as a healthy one — derived at read time by
the same resolution the boundary performs, so a verb that never heard of shares cannot desync it.

That is the whole discipline: **derive the brokenness, never maintain the reference.**

### D5 — The copy states what the shape actually does

Two gaps in current copy, both measured against behaviour:

1. **Transferability is never stated.** The dialog says what the *recipient* gets, never that the
   **link itself travels** — there is no email lock (that is Invite, a different door;
   `accept_share` takes any authenticated principal). A Full-access link pasted into a channel
   lets every reader there join. Full access must say so.
2. **Permanence is never stated.** `expires_at` is `NULL` on every link the cockpit mints.
   View-only should lean into it — *"Anyone with this link sees the current version, always"* —
   because permanence-plus-live-resolution IS the feature, and an operator who does not know a
   link is durable cannot reason about revoking it.

Copy is not decoration here: both are consequences the operator is currently not told.

## 5. What this ADR does NOT do

- **No change to mint or revoke authority.** `assert_may_mint_share` / `revoke_share`
  (ADR-517 D3/D4) untouched. Who may share does not move.
- **No change to the grant shapes**, their axes, or migration 234's RLS.
- **No new transport, no second token class, no artifact-scoped access object.**
- **No publish act** (§2.1). **No file-identity system** (§3).
- **No path-chasing on move/rename** — explicitly rejected, §3.
- **No merge of share and invite** — `create_invite` still carries no `artifact_path` (ADR-515 §4).
- **No rate limiter on `/api/s/{token}`** — ADR-513 D5 named it owed; still owed.
- **No folder-level grant** — ADR-515 §6 q3, still open.

## 6. Singular implementation — the whole surface, enumerated

The sweep, so no second path survives (Core Discipline 2):

| Layer | File | Change |
|---|---|---|
| Service | `services/workspace_shares.py` | `list_shares` selects `token` (D2). `create_share` **unchanged** (D1: no server-side dedupe). |
| Route | `routes/shares.py` | `ShareSummary.share_link` populated in the list response via the one `app_url()` helper the mint path already uses — never a second URL-shaped string. D4's `410` on a resolved-but-missing file. |
| FE client | `web/lib/api/client.ts` | `listShares` return type gains `share_link`. |
| FE | `web/components/workspace/ShareDialog.tsx` | D1/D3/D5 + D4's dark-link rendering. The only component that changes — it is already the singular mint surface (ADR-529 D1). |

**Nothing new is created.** No new component, endpoint, table, token class, or sync helper. No
handler outside the share mechanism is touched — which is the structural proof that D4 imposes no
obligation. That is the test that this is an optimization pass and not a feature: it removes a
dual path (mint-vs-list rendering the same object two ways) instead of adding one.

**Explicitly NOT touched**: `mcp_server/server.py`'s `share` verb (line 1116) mints and returns
its link in one call — no list surface, no reuse problem. Gate parity (ADR-517 D3) is unaffected
because mint authority does not move.

## 7. Owed after this ADR (tracked, not silently open)

- **The launch-handler binding does NOT survive a move** (§3 measurement) — `handle_move_file`
  carries `content`, not `metadata`, so `routes/documents.py:954`'s claim is false. Its own fix,
  and per this ADR's discipline the answer is honest behaviour, not a second sync obligation.
- **Trash / permanent-delete × live shares** — ADR-478 has its own lifecycle. D4 makes a deleted
  file's link dark by the same read-time resolution, but the *deliberate* delete probably wants
  its own signal, distinct from a move.
- **TTL wiring** — `ttl_days` reaches `create_share` and **no surface passes it**. D5 makes
  permanence legible, which sharpens rather than closes it: an operator told "always" may then
  want "until Friday."
- **The revoke-honesty signal** (ADR-531 §6) — revoke is silent about search indexes; D3 makes
  revoke more prominent, so this gets slightly more owed.
- **Links as principal-class rows in the roster** (ADR-515 D6's half-view) — D1/D3 improve the
  per-file view; the per-principal view still cannot see share links at all.

## 8. Phases

1. **This ADR** — the ruling, including §3's recorded refusal.
2. **D2 + D4 backend** — the token in the list projection; the `410` on a resolved-but-missing
   file.
3. **D1 + D3 + D5** — the ShareDialog pass.
4. **Gates** — `api/test_adr534_standing_address.py`, in the ADR-529 executed-not-grepped style:
   the (path, role) reuse lookup run as a real decision over a matrix (both shapes live / one /
   none); the token's presence in the list projection AND its **absence** from the public
   projection asserted as a pair; the three dark states kept distinct. **Each check falsified by
   construction before landing** — a green gate over an unmounted control is the defect class this
   codebase keeps re-finding.
5. **Canon** — `grants-and-reach.md` (§6 standing-address contract + §8a's third dark state),
   ADR-529 amendment banner, ADR-LEDGER.
6. **Click-pass** — the dialog driven in a browser (the Files mount is drivable; the Studio
   mount's opaque-origin iframe defeats CDP, per `grants-and-reach.md` §8). Owed with ADR-529's.

## 9. The one-line statement

**A share link is a standing address: the surface opens on it, hands it back, and keeps it
resolving live — and when the path stops naming the file, the link goes honestly dark instead of
quietly blank, because the web settled this and the ledger already agreed.**
