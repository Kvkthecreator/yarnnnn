# ADR-645 reach-scope click-pass, run 1 — the N>1 case, driven in production (2026-09-08)

**Lane**: surface (browser) + substrate. **Target**: ADR-645 D1/D3 at `ce86fea`.
**Method**: [BROWSER-CLICK-PASS-PLAYBOOK.md](BROWSER-CLICK-PASS-PLAYBOOK.md).

**Principals**: `kvkthecreator@gmail.com` (owner of live `d5b9029b`, 5
connections) · `seulkim88@gmail.com` (**real external human**, `member/active`
on `d5b9029b` since 2026-07-29, 0 connections).

## Why the live workspace and not the rig

The playbook (§3) prefers a disposable rig. **It could not be used here**, and
the reason is the finding that made this run worth doing:

- Rig `bf5b25a9` owner holds **0 platform connections**. Connected would render
  an empty state — the pass would observe nothing about connection scoping.
- All five connections in the entire database belong to `2abf3f96` (the live
  owner). The instrument the suite needs exists in exactly one place.
- **N>1 is already true in production**: `d5b9029b` carries a
  `member/active` grant. No member needed minting.

## Verdict

**ADR-645 D1 PASSES on the substrate half, driven at N>1.** The DOM half for
the member was **NOT RUN** — see the blocker below. This is 1 of 2 halves;
per §7 the number is written rather than implied.

## What was driven — the account-scoping claim

`connection_rows(client, user_id)` against production, both principals, same
workspace:

| Principal | Rows | Platforms |
|---|---|---|
| owner `2abf3f96` | **5** | github · mcp:linear · notion · slack · wordpress |
| member `2be30ac5` | **0** | — |

**The member cannot see the owner's connections**, standing inside the owner's
workspace. This is the row that only exists at N>1 and the one ADR-645 D1 rests
on.

**Non-vacuity** (the check that the result is scoping and not coincidence):

- `connection_rows` takes **no workspace parameter** — signature
  `(client, user_id)`. A member's view provably cannot vary by where they
  stand. The member owns two other workspaces (`4ca9c664`, `d38376f4`); there
  is no code path by which standing in one could change the answer.
- The owner's rows **do** carry `workspace_id = d5b9029b` — present, and not
  the selector. ADR-425 AD1's "routing, never ownership", observed rather than
  asserted.

## What was driven — the refusal grid (ADR-645 D1's enforcement point)

`resolve_platform_credential(auth, 'slack')` on the live workspace, every
principal shape:

| Caller | `is_agent_caller` | Result |
|---|---|---|
| owner, own request | False | the credential |
| owner's LANE (AI driving) | False | the credential |
| **MEMBER, own request** | False | **None (refused)** |
| **MEMBER's lane** | False | **None (refused)** |
| agent (`specialist:`) | True | None (refused) |
| agent, unreadable identity | True | None (refused) |

Every cell matches D1. The member rows are new information: previous runs had
one principal, so "the member is refused the owner's token" had never been
executed — only reasoned about.

## Method strength (§7 ranking, so a later summary cannot upgrade it)

- Account scoping + refusal grid: **PROBED** — live calls through the real
  functions against production rows.
- The member's DOM (what Connected renders for a non-owner): **NOT RUN**.
- "Read by" (workspace declarations reading a member's connection):
  **NOT RUNNABLE** — `_standing.yaml` count across the entire database is
  **0**. The line has nothing to render anywhere. It is asserted in the ADR and
  remains unexercised; do not record it as verified.

## ⚠️ BLOCKER → RESOLVED 2026-09-09 (`ab5535c`), with a correction

**As first written, this section overstated the finding, and the correction is
the more useful result** (§7: correct in place, name the cause).

What was observed stands: run as the playbook's setup step, the guard **minted
a working magic link** for `seulkim88@gmail.com`. The link was discarded unused.

What was wrong was the conclusion — "two real external humans". Checked
afterwards, **both gmail entries are accounts the operator personally
controls**: their own, and the alpha-trader persona instrument, whose second
workspace is literally named *"seulkim tester"* and which has served as a
principal in prior passes (the 2026-08-25 mentions run). Neither is an
unwitting third party. The cause of the misread: I inferred "real person" from
the address shape (`gmail.com`) without checking what the account IS — the same
error class as reading a registry row as a live path.

**The real defect was underneath, and it was worse than the symptom.** The
roster could not be audited. `test_roster_guard_is_still_enforced_in_code`
asserted only that `ALLOWED_EMAILS` *exists* — an assertion that stays green
with every real user in the world listed. The fact distinguishing a legitimate
operator account from a stranger's lived in one person's head, so a genuinely
wrong entry would sit beside the right ones and nothing would go red.

**Fixed** (`ab5535c`): `ALLOWED_EMAILS` is now `email -> reason` with two valid
reasons (`rig`, `operator`); the refusal prints every entry with its reason, so
the roster is auditable at the moment someone is refused; and the gate IMPORTS
the module (a regex cannot tell a live entry from a commented one) and fails
when an external address is declared anything but `operator`. Falsified four
ways — `"someone.real@gmail.com": "rig"` reds it, with a message naming a rig
as the correct answer.

**The member DOM half stays NOT RUN**, but for an honest reason rather than a
blocked one: the rig owner still holds 0 connections, so Connected renders
empty there, and driving the operator's own second account would show the same
empty pane the substrate half already proved. It becomes worth running when a
rig owner connects a platform, or when a second principal holds their own
connection — the case where Connected must show two principals different
NON-EMPTY sets.

## Guardrails re-asserted

- **Nothing was mutated.** No invite, no grant change, no connection touched.
  Reads only, through the service client.
- Grants on `d5b9029b` unchanged: owner active, member active, 2 foreign-llm
  active, the rest revoked.
- The minted link for a real external principal was discarded unused and is not
  recorded here.

## Not covered by this run

- The member's DOM on Reach → Connected (blocked above).
- The member's DOM on Leaving/Crossed (workspace-scoped panes — a member SHOULD
  see these; unverified).
- "Read by" (no declarations exist).
- A second member holding their OWN connection — the case where Connected must
  show each principal a different non-empty set. No such row exists in
  production.
