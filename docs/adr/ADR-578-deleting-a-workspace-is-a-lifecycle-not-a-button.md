# ADR-578 — Deleting a workspace is a lifecycle, not a button

> **Status**: **Accepted + Implemented** (2026-08-18). Operator-delegated: *"i'd like to
> delegate the details on handling delete, tables and members in a more industry standard
> and conventional method … and thus, also delegate the full implementation scope, ADR, and
> general code to documentation streamlining."*
>
> **Preserves**: [ADR-478](ADR-478-permanent-delete-and-the-trash-contract.md) (permanent
> delete + the no-timer ruling — **this ADR extends its semantics one scope up rather than
> inventing a second delete vocabulary**) · [ADR-476](ADR-476-purge-is-workspace-scoped.md)
> (the purge is workspace-scoped; `has_workspace_clear_authority` is the gate) ·
> [ADR-416](ADR-416-the-workspace-as-billing-unit-and-the-witness-metering-split.md) (the
> workspace is the billing unit) · [ADR-378](ADR-378-the-workspace-as-the-outermost-unit.md)
> (the workspace is the outermost unit — deleting one composes with nothing) ·
> [ADR-405](ADR-405-the-witness-dial.md) (the system does not destroy work unwitnessed).
>
> **Completes**: the Danger Zone, which offered *clear* and had no *delete* — so a discarded
> workspace stayed on the switcher forever as an empty shell. Newly load-bearing because
> deliberate genesis shipped the same day: an operator who can create workspaces will
> accumulate ones they no longer want.
>
> **Dimensional classification** (Axiom 0): **Substrate** (Axiom 1 — what retention means at
> the outermost scope) + **Identity** (Axiom 2 — what happens to the other principals in a
> commons that ends).

---

## 1. Context — the button that could not have worked

The Danger Zone offered two purges (L1 clear work history, L2 clear workspace) and no
delete. Clearing empties a workspace and **keeps the row**, so a workspace the operator is
finished with remains on the switcher, in the memberships payload, and in the billing
surface — permanently, with no way to remove it.

**Probed on production before designing anything.** A raw `DELETE` is not merely untidy —
the database refuses it. Of 22 foreign keys referencing `workspaces`, only 11 cascade:

| Behavior | Tables |
|---|---|
| `CASCADE` (11) | `balance_transactions`, `conversation_members`, `member_state`, `principal_grants`, `scheduled_messages`, `subscription_events`, `workspace_blobs`, `workspace_file_versions`, `workspace_files`, `workspace_invites`, `workspace_shares` |
| `NO ACTION` (10) | `action_proposals`, `activity_log`, `agent_runs`, `agents`, `chat_sessions`, `execution_events`, `platform_connections`, `sync_registry`, `tasks`, `wake_queue` |
| `SET NULL` (1) | `notifications` |

Falsified in a `ROLLBACK` transaction:

- an **empty** workspace deletes cleanly (`DELETE 1`)
- a **populated** one raises
  `ERROR: update or delete on table "workspaces" violates foreign key constraint
  "execution_events_workspace_id_fkey"`

**So a naive delete button ships a 500 for every workspace that has ever been used, and
passes testing on a freshly-created one.** This is the shape the ADR exists to prevent.

Worse: the existing L2 purge does **not** make the row deletable. After a full clear, four
blocking tables still hold rows — `execution_events`, `agent_runs`, `platform_connections`,
`sync_registry` — because the purge was built to empty a workspace someone keeps using, not
to make it disappear.

## 2. The convention, and where canon overrides it

The prevailing SaaS shape is **soft-delete → grace period → hard purge** (Stripe, GitHub,
Linear, Vercel, Notion all ship a variant). It is the right skeleton and this ADR adopts it,
with **one deliberate departure**.

**The grace period does not expire on a timer.** ADR-478 D2 already ruled on exactly this
question one scope down, and the reasoning transfers without modification:

> *"A 30-day timer is the system deleting a member's work with nobody witnessing it —
> precisely what ADR-405's witness dial says the system does not do … Google can
> default-destroy because Drive is a consumer product with vendor-set policy; yarnnn's canon
> puts that decision with the operator."*

Importing the industry timer here would contradict a ratified decision **and re-litigate it
in a second vocabulary** — the dual-approach ambiguity this work is explicitly scoped to
avoid. So: a deleted workspace is soft-deleted and stays soft-deleted until a principal
finishes the job. The grace period is real; its *end* is an act, not a clock.

This is the macOS Trash contract, applied at workspace scope. It is the same answer ADR-478
gave, which is the point — **one delete vocabulary in the product, not two.**

## 3. Decisions

### D1 — Delete is two acts: `deleted` (reversible) then `purged` (terminal)

`workspaces.deleted_at` + `deleted_by`. A soft-deleted workspace:

- **disappears from the switcher** (`/workspace/memberships` filters it) and cannot be bound
  — `principal_reaches_workspace` refuses it, so every request 403s exactly as an unreachable
  workspace already does. No new refusal path.
- **retains everything.** No content is touched. Restore is a column write.
- **stops billing activity** by being unreachable; the row and its financial history remain.

Purge is the second, explicit act. Nothing purges on a schedule.

### D2 — Delete is owner-grade, and reuses the existing gate

`has_workspace_clear_authority` (owner-default + the extensible `workspace:clear` scope),
identical to L1/L2 and to ADR-478 D4. **No new permission concept** — deleting a workspace is
strictly heavier than clearing one, and clearing is already owner-grade, so a separate
capability would add vocabulary without adding a decision.

### D3 — The last owned workspace cannot be deleted

Refused with a named reason. A principal who deletes their only owned workspace lands in the
cold-user door, which mints a fresh one (ADR-465 D2) — so the act would be a confusing
no-op that silently replaces their workspace with an empty one. Members with grants elsewhere
are unaffected; this guard is about the *owner's* own last commons.

### D4 — Other principals are told, not silently evicted (ADR-405)

Deleting a shared commons destroys other people's work. The confirmation **names the
principals who lose access** (count and identities), sourced from the live grant table —
never a generic "this cannot be undone". Their grants survive the soft-delete untouched, so
a restore restores *them* too; only the purge cascades them away.

This is the witness dial doing its job: the operator is not prevented from ending a shared
commons, but they cannot do it without being shown who it lands on.

### D5 — The purge preserves financial history; everything else goes

`balance_transactions` and `subscription_events` currently `CASCADE`, which would destroy
billing records the business may be required to retain — the one place the conventional SaaS
answer is unambiguous and canon is silent. **Migration 241 re-points both to `SET NULL` on a
nullable `workspace_id`,** so the ledger rows survive their workspace with the workspace
identity recorded in a preserved `workspace_ref` column.

Everything else is destroyed, extending ADR-478 D3's semantic — *unrecoverable, not
unremembered* — from a path to a commons. The purge runs the ADR-476 purge for content, then
clears the ten `NO ACTION` tables in dependency order, then deletes the row.

### D6 — One delete vocabulary

The workspace delete **reuses** ADR-478's language (delete → restore → purge), the ADR-476
purge machinery for content, and the existing authority gate. It introduces no parallel
trash, no second retention concept, and no workspace-specific permission. A future reader
should find one answer to "how does deletion work here", at two scopes.

## 4. What this deliberately does NOT do

- **No retention timer** (D2 above; ADR-478 D2). If ever wanted, it ships as an opt-in
  setting — the macOS answer, not the Drive one.
- **No cross-workspace roll-up** — deleting one workspace says nothing about another
  (ADR-378's ceiling).
- **No new permission primitive** — `workspace:clear` carries this.
- **No account deletion change** — L5 deactivate is account-scope and untouched.

## 5. The one-line statement

**Deleting a workspace is a lifecycle, not a button: the database refuses a raw delete on any
workspace that has ever been used, so delete becomes an owner-grade soft-delete that hides
the commons and keeps every byte, followed by an explicit purge that destroys content and
preserves financial history — with no timer, because a schedule that destroys a member's
work unwitnessed is the one convention canon already refused.**
