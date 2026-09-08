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

## ⚠️ BLOCKER — the roster guard admits two real external humans

The playbook §3 states the rule as enforced in code: *"Never add a real
external address to the roster. Verify the guard refuses one as part of
setup."* Run as setup, the guard **minted a working magic link** for
`seulkim88@gmail.com`.

It is not a code defect — `browser_login_link.ALLOWED_EMAILS` lists
`kvkthecreator@gmail.com` and `seulkim88@gmail.com` under a
"live-workspace principals" comment, added deliberately. So the roster and the
playbook disagree, and the roster wins silently.

`seulkim88@gmail.com` is a **real person's Google account**, not a rig. Minting
a session for it is the account takeover the rule exists to prevent, regardless
of intent. **The link was not used.** The member's DOM half is blocked behind
an operator ruling:

1. **Remove both live addresses from `ALLOWED_EMAILS`** (playbook-consistent),
   and give the rig owner a connection so Connected has rows to render there;
   or
2. Keep `kvkthecreator@gmail.com` (the operator's own account — self-service,
   not takeover) and **remove `seulkim88@gmail.com`**, leaving the member DOM
   half permanently unrunnable without that person's participation; or
3. The operator obtains that person's consent, recorded.

Option 1 is the only one that makes the member DOM half repeatably runnable.
It costs one OAuth connect on the rig.

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
