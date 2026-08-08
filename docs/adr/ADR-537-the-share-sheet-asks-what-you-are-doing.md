# ADR-537 — The share sheet asks what you are doing: the link tab and the people tab

**Status**: **Accepted** (2026-08-08, operator-ratified across the discourse that produced it).
The operator read the shipped ADR-534 dialog and pushed one level up: *"i can't tell if the two
options of buttons on top with the link below is structurally and thus visually layout correct or
full access requires a more dedicated flow"*, then ruled the housing — *"i'd say full access
doesn't leave but either re-directs via a small button or a sub, dedicated flow via tab or
alike"* — and, shown a stacked three-zone alternative, corrected it to a tab: *"this is why i
recommended a tab system… i want share to feel very simple, BUT, the invite flow is there as
secondary."* Layer 3's scope and the authority question were **delegated**.
**Date**: 2026-08-08
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Channel (Axiom 6 — the doors a file travels through) + Identity (Axiom 2 — who may
reach what, and who may decide it)

**Amends**:
- **ADR-534 D1** — reuse-first is **preserved and narrowed to the act it was right for**. Opening
  on the live link is correct for an *address*; it was never right for an *invitation*, and
  ADR-534 applied it to both because the two shared one radio stack. **That was an execution
  error in ADR-534, not a gap in its axiom** — §1.2.
- **ADR-529 D1** — the dialog's "exactly four things" become **two tabs**. The contents survive;
  the flat stack does not.
- **ADR-517 D3** — mint authority is **extended to the invite door** (D3 below): `invite_member`
  was owner-only while share-mint allowed write-holders under the dial, so the two doors to
  membership disagreed on who may open them.
- **ADR-512 D6** — `FileReach` **moves** out of `NodeDetailsPanel` into the People tab. Moved,
  never copied.

**Preserves**: ADR-373 (the grant is the authorization fact) · ADR-405 (species-blind) ·
ADR-434 (the powerbox) · ADR-513 (the public view) · ADR-531 D3 (**no publish act** — §2.1) ·
ADR-534 D2/D4/D5 (the token in the list, the honest dark states, the standing-address copy).

---

## 1. Context

### 1.1 The dialog asks one question that has two different answers

ADR-534 shipped and works (operator click-pass 2026-08-08: "link active" badge, visible URL,
per-row Copy, "Create a separate link", the standing copy). The defect it revealed is one level up.

The dialog asks **"how much access?"** and offers two answers as peers. But the honest question is
**"what are you doing?"**, and the answers are not degrees of one thing:

| | **View only** | **Full access** |
|---|---|---|
| Produces | a **permalink to a document** | an **open enrollment offer** |
| The URL is | the deliverable | a **coupon** for a membership that has not happened |
| Redeemed | never (reading needs no acceptance) | by anyone holding it, **repeatedly** |
| Right cardinality | one per file, reused forever | one per recipient |
| Scope granted | nothing | **the whole workspace** (`scopes=None` → class default) |
| Bills | no | **yes** — `HUMAN_SEAT_ROLES = ("owner","member")` |

Full access is **two steps**, and the dialog shows only the first: mint (governance — a row in
`workspace_shares`, no grant yet), then accept (binding — `accept_share` mints the
`principal_grants` row, and `ShareClient` redirects the acceptor into `/files`). The link is not
the grant; it is a standing offer to become a member.

Three misreadings the layout invites, each measured against behaviour:

1. **"I shared a file."** No — an enrollment offer was opened, scoped to the workspace, not the
   file.
2. **"Revoke undoes it."** No — revoke closes the *offer*. Grants already minted survive, and are
   removed only from the Access rail, a surface the dialog never mentions.
3. **"link active · Aug 8"** — the wrong fact for an offer. The operator wants *has anyone joined
   through this?* `last_accepted_at` is **already selected by `list_shares`** and never projected.

### 1.2 The error was ADR-534's, and it is worth naming precisely

ADR-534 D1's axiom — *a live link is a standing address; open on it* — is correct. Its
**execution** applied that axiom to both shapes because they shared one control. Reuse-first for
an invitation is wrong: an invitation's natural cardinality is one per recipient, so "hand back
the existing one" is the opposite of what the act wants.

Stated plainly so a future session does not read ADR-534 as wholly superseded: **the address half
was right and ships unchanged. The invitation half was mis-housed.**

### 1.3 What the roster changes, and why it was impossible to state before

The dialog has never shown **who already has access**, and that absence is why permission level
was the only thing left to ask about. With no "who", the surface could only offer "how much".

`getMembers(path)` already answers it — per-principal read/write over this path, *computed
server-side by the same powerbox matcher the gate consults, so the panel and the gate cannot
disagree* — and `listInvites()` already returns pending invites. The state was fetchable all
along; no surface asked.

## 2. The axiom

> **The share sheet asks what you are doing, not how much access to grant. Handing out a
> document's address and bringing a person into the workspace are different acts, at different
> scopes, with different lifecycles — so they get different tabs, and the simple one is the
> default.**

### 2.1 Why the tab is NOT Notion's tab, and NOT the publish act

The operator's reference (Notion's share modal) splits **Share** from **Publish**. We deliberately
have no publish act — ADR-531 D3 refused it, because publishing is a **distribution** act
(audience, reach) and sharing is an **interop** act (a specific collaborator in a specific
document). Importing that division would build the one thing we said we would not.

What this ADR takes from the reference is the **body**: Notion's dialog is a *list of who has
access*, with the link demoted to a footer. Ours had no roster at all. The tab division here is
**by scope**, which is our own seam:

| Tab | Scope | Weight |
|---|---|---|
| **Link** | *this file* — terminal, revocable, grants nothing | the simple default |
| **People** | *the workspace* — governance, seat-billing, not file-scoped | secondary, complete |

Stacking them implied one scope. Tabbing them states two.

## 3. Decisions

### D1 — Two tabs; **Link** is the default and is nearly the whole dialog

**Link** carries exactly what ADR-534 shipped and the operator verified: the reuse-first live link,
visible and selectable, with Copy, the standing-address sentence, inline Revoke, and "Create a
separate link". No role choice, no roster to scan past. *Share opens, the link is already there,
you copy, you leave.*

**People** carries everything membership: who can reach this file, pending invites, the email
field, and the open-join-link disclosure.

**The tab is labelled "People", not "Full access".** "Full access" was a permission level for a
link; the tab is a place where people are. Naming it by the noun stops it reading as the link's
louder sibling.

**The People tab carries a count badge** when something is outstanding (a pending invite, or a
live open-join link). Tabs hide things, and the hidden one is the consequential one — without the
badge, an operator who never opens People never learns a join link is live on this file. Both
lists are already fetched, so the badge is free. **This is a deliberate trade** (simplicity bought
with a discoverability cost) and it is the item most worth re-checking after a click-pass.

### D2 — `FileReach` MOVES into the People tab

Relocated from `NodeDetailsPanel`, not duplicated. Two surfaces rendering per-file reach is the
dual-surface problem ADR-529 D4 finished deleting; reintroducing one here would undo that in the
same arc that praises it.

The People tab renders the roster **for this file** — deliberately not the workspace-wide roster,
which stays the Access rail's job (ADR-515 D6: *the flow grants reach as a step toward addressing
something; the rail governs reach as a standing fact*). A footer line — *"Manage access in
Workspace Settings →"* — **crosslinks ADR-515 D6's named half-view for the first time**: per-file
and per-principal views stop being uncrosslinked.

### D3 — The two doors to membership agree on who may open them

`invite_member` is **owner-only** (`_require_owner_workspace`); share-mint allows **write-holders**
under the `share_mint_policy` dial (ADR-517 D3). So a non-owner member who can mint a full-access
link **cannot** send an email invite — two doors to the same outcome, two different authorities.

Under D1 the People tab leads with the email field, so a non-owner would meet a control the server
refuses: **"a control that exists but cannot be entered"**, the exact defect class ADR-532 §3a was
written to remove.

**Ruling**: invite-creation adopts **`assert_may_mint_share`** — the same gate, the same dial, the
same species-blindness. Not a loosened `_require_owner_workspace`: that helper's docstring carries
a **receipted production incident** (2026-07-31, a member widened their own grant via `/narrow`),
and `narrow` / `revoke-member` / `spend-cap` must keep it **unchanged**. Those mutate an *existing*
principal's reach; inviting creates a *new* principal, which is precisely what share-mint already
governs.

**What does NOT change**: the seat gate. `create_invite`'s free-tier `upgrade_required` check
lives in the service, independent of the caller, so widening authority cannot widen billing.
Invite **listing and revocation** stay owner-only — reading and rescinding the workspace's
outstanding offers is standing-state governance, not the act of bringing someone in.

### D4 — The open join link states its redemption, honestly and incompletely

`list_shares` already selects `last_accepted_at`; the projection now carries it, and the join
link's row reads *"last joined Aug 8"* — or *"no one has joined yet"*.

**A name is deliberately NOT rendered.** `accepted_principal_id` is a **single column overwritten
on every accept**, so a link redeemed five times records only the fifth. Showing one name would
imply a complete list — the same class of dishonesty ADR-534 D4 removed at the public boundary.
Per-redemption history needs a redemptions table: a migration, its own ADR (§6).

### D5 — The copy says what the acts actually do

- The join link states it is **forwardable** (no email lock — `accept_share` takes any
  authenticated principal) and that revoking **closes the offer without removing anyone who
  already joined**. Neither is currently said anywhere.
- The email invite states the consequence: *"They'll get an email. Joining gives full access to
  this workspace and uses a seat."* — workspace scope and seat cost, both currently silent.
- The Link tab's standing-address sentence (ADR-534 D5) is unchanged.

## 4. What this does NOT do

- **No publish act** (§2.1). **No new transport, token class, or grant shape.**
- **No change to `accept_share`**, the grant model, RLS, or the ADR-517 revoke authority.
- **No path-chasing on move/rename** — ADR-534 §3's refusal stands, and its structural gate stays.
- **No workspace-wide roster in the dialog** (D2) — that is the rail's.
- **No invite-with-`artifact_path`.** Still named-owed since ADR-515 §4, and still the thing that
  would make the People tab file-scoped rather than workspace-scoped. Its absence is *why*
  membership ended up inside a file dialog in the first place.

## 5. Singular implementation

| Layer | File | Change |
|---|---|---|
| Route | `routes/workspace.py` | D3 — `invite_member` gates on `assert_may_mint_share`. `narrow` / `revoke-member` / `cap` / invite-list / invite-revoke keep `_require_owner_workspace` **unchanged**. |
| Route | `routes/shares.py` | D4 — `ShareSummary.last_accepted_at` projected. |
| FE client | `lib/api/client.ts` | `listShares` gains `last_accepted_at`. |
| FE | `components/workspace/ShareDialog.tsx` | D1/D4/D5 — the two tabs. The only component that changes shape. |
| FE | `components/workspace/NodeDetailsPanel.tsx` | D2 — `FileReach` **deleted here** (it moves). |

No new component, endpoint, table, or token class. The roster, the invite door, and the pending
list all already exist; this ADR is a **rehousing**, which is why it can be singular.

## 6. Owed (tracked, not silently open)

- **Per-redemption history** (D4) — `accepted_principal_id` overwrites. A redemptions table, its
  own migration and ADR.
- **Invite with `artifact_path`** (ADR-515 §4) — unowned, and the real fix for file-scoped
  membership.
- **The click-pass for this ADR**, with the badge trade (D1) as the specific thing to watch.
- Everything ADR-534 §7 still lists: the launch-handler binding that does not survive a move,
  trash × live shares, TTL wiring, the revoke-honesty signal.

## 7. The one-line statement

**Share opens on the link and asks nothing; People is one tab away and carries the whole of
membership — because handing out a document's address and bringing someone into the workspace were
never the same question.**
