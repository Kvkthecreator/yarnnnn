# ADR-476 — Purge is workspace-scoped, and its surfaces say so

> **Status**: Accepted 2026-07-21. Ratified by KVK.
> **Decides**: purge re-keys `user_id → workspace_id`; clearing shared content
> becomes an owner-grade act; the surfaces move to Workspace Settings.
> **Amends**: ADR-244 (the danger-zone surface) · ADR-407 (three-scope taxonomy
> — this is the missing application of it) · ADR-474 (`_collect_blob_shas`
> inherited the `user_id` bug).
> **Preserves**: ADR-373 re-key · ADR-405 witness dial · ADR-411 member lanes.

---

## 1. The finding

**`workspace_purge` deletes by `user_id`. Everything beneath it is keyed by
`workspace_id`.**

| Layer | Keyed by | Since |
|---|---|---|
| Files, revisions, blobs | `workspace_id` | ADR-373, ADR-474 |
| Permissions | `principal_grants(principal_id, workspace_id)` | ADR-373 |
| **Purge** | **`user_id`** | pre-ADR-373 — never re-keyed |

The re-key (ADR-373) moved the substrate's binding unit from user to workspace
and swept the read paths. Purge was not swept. It has been quietly wrong ever
since; N=1 hid it, because at N=1 the owner's `user_id` and the workspace's
contents are the same set.

### It is latent, not yet live — and measurably so

Live data, 2026-07-21:

- One workspace (`d5b9029b`) has **3 humans** (1 owner + 2 members).
- All **138** of its files carry the **owner's** `user_id`.
- 21 revisions are `member:`-authored — but all are *the owner* acting through a
  lane (ADR-411), so they carry the owner's `user_id` too.
- Across all workspaces: **0 files** whose `user_id` differs from the workspace
  owner.

So nothing is broken *today*. The two non-owner members simply have not written
yet.

### Why it breaks the moment they do

Every route calls `write_revision(user_id=auth.user_id, …)` — the **acting**
member's id (`routes/lanes.py:909`, `routes/documents.py:736`). The first save
by a non-owner member stamps that member's `user_id` on the file. Then:

1. **The owner clears the workspace → members' files survive.** The purge
   matches only the owner's `user_id`. The workspace reports "cleared" and is
   not.
2. **A member's content is unreachable by any purge.** No surface deletes rows
   belonging to a non-owner member.
3. **ADR-474's blob collection inherits the bug.** `_collect_blob_shas` filters
   `.eq("user_id", user_id)`, so it collects only the purging user's content.
   ADR-474 made purge *able* to reach content; this ADR makes it reach *the
   workspace's* content. Recorded plainly because ADR-474 is one commit old and
   its claim needs this qualification.

## 2. The decision

**D1 — Purge is scoped to the workspace.** `purge_l2_workspace` and its helpers
key on `workspace_id`, resolved via the same `effective_workspace_id` spine the
read paths use. `user_id` survives only as the N=1 fallback, exactly as
`authored_substrate._substrate_scope` already does. Byte-identical at N=1;
correct at N>1.

**D2 — Clearing shared content is an owner-grade act.** L1 (work history) and
L2 (clear workspace) destroy *other people's* work in a multi-member commons.
They gate on workspace ownership: `workspaces.owner_id`, or an active grant
carrying the `workspace:clear` scope — the exact shape of
`has_billing_authority` (ADR-416 D1), including its owner-default. **Not a role
enum** (ADR-405: no rule may key on species; authority is a grant).

The owner-default matters for a reason found in the live data and already
documented at `principal_grants.py:315`: two legacy workspaces have an owner
with **no owner-grant row**, so keying on the grant alone would 403 real owners.
`owner_id` is the ground-truth; the grant is the extension.

**D3 — The surfaces follow the scope.** Under ADR-407's three scopes:

| Action | True scope | Home |
|---|---|---|
| L1 clear work history | workspace content | **Workspace Settings** |
| L2 clear workspace | workspace content | **Workspace Settings** |
| L3 disconnect platforms | member's own AI connections (ADR-431) | Account |
| L4 full reset | account | Account |
| L5 deactivate | account | Account |

L1/L2 move to a **Danger Zone** pane in Workspace Settings. L3/L4/L5 stay in
Account. This is the first honest application of ADR-407 to the danger zone —
it was authored before the three-scope taxonomy existed and has been
scope-blind since.

**D4 — Order of work: re-key before re-house.** Moving the UI first would make
the product *more* misleading: a button labelled "Clear workspace" sitting in
Workspace Settings that silently clears one person's rows is worse than the same
button in Account, where the placement at least hints it is personal. Scope
first, surface second — in that order, in this ADR.

## 3. What this does not change

- **Nothing about what a purge deletes conceptually.** L2 still preserves
  `platform_connections`, `user_admin_flags`, `execution_events`. Only the
  *scope predicate* changes.
- **No new permission concept.** `workspace:clear` is a grant scope in the
  existing `principal_grants.scopes` list, consulted the way every other scope
  is.
- **Not the ADR-405 witness dial.** Purge is a direct operator act, not an agent
  action passing through the proposal gate.

## 4. Risk, and why it is acceptable

The change makes purge delete **more** than it did — that is the point, and it
is also the risk. Three things bound it:

1. **N=1 is byte-identical.** In a single-member workspace the workspace's rows
   and the owner's rows are the same set. 13 of 14 live workspaces are N=1.
2. **The one N>1 workspace has 0 non-owner-authored files**, so even there the
   first run of the new code deletes exactly what the old code would have.
3. **The gate narrows who can call it.** Today any authenticated user can clear
   "their" rows; after D2 only the owner (or a `workspace:clear` grantee) can.

**The falsifier to watch**: if a member expects "clear workspace" to remove only
*their* contributions, D1 surprises them by removing everyone's. That is the
correct semantic for a shared commons (ADR-378: the workspace is the unit), but
it is a semantic change, and the surface copy must say so explicitly rather than
rely on the label.

## 5. The invariant

> **A purge's scope predicate matches the substrate's binding unit.** Purge
> deletes exactly the rows of the workspace it names — no more, and no fewer.

Assertable: after a workspace purge, `count(workspace_files WHERE workspace_id =
X) == 0`, regardless of which member authored them.

## 6. Falsifiers

1. **Member-scoped deletion is the wanted product behavior.** If operators want
   "remove my contributions only," that is a *different* verb (a per-principal
   retraction) and D1 does not provide it. This ADR asserts no such demand
   exists; the demand it answers is "clear the workspace" actually clearing it.
2. **`workspace:clear` is too coarse.** If a co-owner needs to clear work
   history but not the whole workspace, one scope is too blunt and should split
   per-level. Deferred until asked for.
3. **The N=1 byte-identity claim.** It rests on files' `user_id` matching the
   workspace owner. Verified today (0 divergent rows across all workspaces); a
   future writer that stamps a different `user_id` would break the equivalence —
   which is precisely the bug being fixed, so it fails safe.

## 7. The one-line statement

**The substrate's binding unit became the workspace two ADRs ago, but purge kept
deleting by user — so in a shared workspace "clear everything" quietly means
"clear my own rows"; this re-keys the predicate, makes clearing shared content
an owner-grade act, and moves the surfaces to where the scope actually lives.**
