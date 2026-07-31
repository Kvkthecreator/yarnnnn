# OPERATOR PACKET — settings-surfaces click-pass

**For**: a browser principal with NO repo access — Claude desktop (Cowork), or
the operator driving it by hand.
**Manifest**: [`eval-suites/settings-surfaces-click-pass.yaml`](eval-suites/settings-surfaces-click-pass.yaml)
(the authority; this packet is its portable form).
**Written**: 2026-07-31. **Target**: production (`https://yarnnn.com`).

---

## 0. The split that makes this honest

This pass has **two halves that run in different places**:

| Half | Who runs it | What it produces |
|---|---|---|
| **DOM** — what the page shows, what the click does | the browser principal (desktop Claude / operator) | observations + screenshots |
| **SUBSTRATE** — what the database actually recorded | a repo session (Claude Code, service key + psql) | receipt query output |

**Neither half closes a step alone.** A green DOM with no substrate receipt is
narrative — that is the standing rule this whole lane exists to enforce. So the
browser half's job is to **record faithfully**, including the raw HTTP status of
every call it makes. Do not conclude "the ceiling holds" from a hidden button;
that is precisely the defect class (ADR-501) this pass hunts.

**If you are the browser principal: fill in §6 and hand it back. Do not guess at
the substrate half.**

---

## 1. What you are testing, in one paragraph

YARNNN workspaces are multi-principal: an **owner** and one or more **members**
share one workspace. The two settings doors are `/workspace-settings` (the
workspace: Access, Billing, Usage, Autonomy, Danger Zone) and `/settings` (the
account: Account, Connectors). The question is whether a **member** sees the
right things and — critically — is actually *refused* the things they must not
do, at the server, not merely in the UI.

Historical context that sets the bar: a previous audit found the member write
ceiling was **display-only**. The check keyed on the *transport* (every human
browser session identifies as "operator") instead of the member's *grant role*.
The UI hid the buttons; the endpoints still accepted the calls. **Hidden is not
refused.** That is why several steps below ask you to call the endpoint directly
even when the button is absent.

---

## 2. The two principals

| Role | Email | What they are |
|---|---|---|
| **OWNER** | `kvkthecreator@gmail.com` | owns the live workspace `d5b9029b` |
| **MEMBER** | `seulkim88@gmail.com` | active member grant on `d5b9029b` |

Both are declared test accounts. **No other account may be used as a subject.**

### Getting logged in

Ask the repo session (Claude Code) to run:

```bash
cd api && python3 -m scripts.operator.browser_login_link seulkim88@gmail.com
```

It prints a single-use magic link (~1h). Navigate to it in the browser; you
land signed in as that principal.

> **Known wrinkle**: Supabase only honours `redirect_to` for allow-listed URLs,
> so the link may land you on `https://yarnnn.com` rather than the deep path.
> Just navigate to the pane manually afterwards. Not a defect — a config detail.

To switch principals, sign out (or use a separate browser profile / incognito
window) and mint a link for the other email. **A clean profile per principal is
strongly preferred** — a stale session is the easiest way to produce a false
result in this pass.

---

## 3. Hard guardrails — these are not negotiable

1. **`d5b9029b` is a LIVE workspace with real content.** Read-mostly. The only
   deliberate writes are the ones listed in §5, each with a restore step.
2. **NEVER revoke seulkim88's membership** on `d5b9029b`. It is the standing
   test instrument; revoking it destroys the pair.
3. **Danger Zone / purge verbs: rig workspace only** (`kvk-yarnnn`), never on
   `d5b9029b`. On `d5b9029b` you only ever check that the member is *refused*.
4. **Billing: stop at the LemonSqueezy handoff.** Record the checkout URL and
   go no further. **Never enter payment details.**
5. **Never invite, narrow, or revoke a real external person.** The only invite
   target in this pass is `testacct@yarnnn.com`, on the rig workspace.
6. **Do not paste a magic link** into any commit, issue, or shared log.

---

## 4. How to record an HTTP call (the important technique)

Several steps ask you to call an endpoint directly, because a missing button
proves nothing. From the **logged-in browser's devtools console**, so the
session cookies ride along:

```js
// Example: does the MEMBER's session actually get refused an invite?
const r = await fetch('/api/workspace/members/invite', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'testacct@yarnnn.com' })
});
console.log(r.status, await r.text());
```

**Record the status code verbatim.** `403` = refused (good). `200` = accepted —
a serious finding, and you should stop and report it immediately.

---

## 5. The steps

Work through these in order. For each, note what you SEE and, where asked, the
HTTP status. Screenshot anything surprising.

### A. Render — owner (`/workspace-settings`)

**A1.** Signed in as **OWNER**, open each pane: Access · Billing · Usage ·
Autonomy · Danger Zone.
*Expect*: all five render without an error state. Access lists **both** the
owner and seulkim88 under "People". Danger Zone's two clear cards are **enabled**.

### B. Render — member

**B1.** Signed in as **MEMBER**, open the same five panes.
*Record per pane*: which controls are **visible**, which are **disabled**, which
are **absent entirely**. This inventory is the deliverable — be precise.
*Expect*: Danger Zone's clear buttons are **disabled** with copy along the lines
of "Only the workspace owner can clear shared content."

**B2.** As **MEMBER**, open Billing and Usage.
*Expect*: the member must **not** be presented with the owner's wallet as if it
were their own. A read-only or refused state is correct. **A working top-up
button for a member is a defect** — capture it.

**B3.** As **MEMBER**, open `/settings` → Account, then Connectors.
*Expect*: the member's **own** stats and **own** AI connections. The "Your AI
connections" list is read-only.

### C. The ceiling (the heart of the pass) — all as MEMBER

For each: first note whether the UI even offers the action, then run the call
from the console per §4 **regardless**.

**C1 — invite.**
```js
await fetch('/api/workspace/members/invite', {method:'POST', credentials:'include',
  headers:{'Content-Type':'application/json'},
  body: JSON.stringify({email:'testacct@yarnnn.com'})}).then(r=>r.status)
```
*Expect*: `403`. Record the status.

**C2 — narrow own grant.** (Target the member's OWN principal id
`2be30ac5-b3cf-46b1-aeb8-af39cd351af4` — never the owner's.)
```js
await fetch('/api/workspace/members/2be30ac5-b3cf-46b1-aeb8-af39cd351af4/narrow',
  {method:'POST', credentials:'include',
   headers:{'Content-Type':'application/json'},
   body: JSON.stringify({write_scopes:['operation/']})}).then(r=>r.status)
```
*Expect*: `403`. (A member who can narrow their own grant can also widen it.)

**C3 — clear the workspace.** The highest-consequence step.
```js
await fetch('/api/account/work-history', {method:'DELETE', credentials:'include'}).then(r=>r.status)
await fetch('/api/account/workspace',    {method:'DELETE', credentials:'include'}).then(r=>r.status)
```
*Expect*: **`403` for both.** If either returns `200`, **STOP THE ENTIRE PASS
IMMEDIATELY** and report — a member just deleted shared content.

### D. A write that SHOULD work — as MEMBER

**D1 — notification prefs.** In `/settings` → Account, note the current values,
then toggle "Work delivered" and set "Workspace activity" to `high`.
*Expect*: the change persists across a page reload.
*Then*: set both back to their original values.
This one is meant to succeed — a member editing their **own** preferences is
correct. It proves the door isn't merely refusing everything.

### E. Owner lifecycle — RIG workspace only

**E1.** As **OWNER**, switch to the `kvk-yarnnn` rig workspace (**not**
`d5b9029b`). Invite `testacct@yarnnn.com`, confirm the pending row appears, then
revoke it and confirm it disappears.

### F. Billing boundary — as OWNER

**F1.** On Billing, click Top up with the smallest amount. Follow the redirect
**only until the LemonSqueezy domain appears**, then stop. Record the URL host +
path (no query string). **Do not enter payment details.**

---

## 6. Report template — fill this in and hand it back

```
## Environment
- Date/time:
- Browser + profile used per principal:
- Anything odd about login:

## A. Owner render
A1 panes rendering (all five?):
A1 Access lists both principals?  Y/N
A1 Danger Zone enabled?           Y/N
Notes / screenshots:

## B. Member render
B1 per-pane control inventory (visible / disabled / absent):
  - Access:
  - Billing:
  - Usage:
  - Autonomy:
  - Danger Zone:
B2 what the member sees on Billing + Usage (raw balance? top-up button?):
B3 Account + Connectors show the member's own data?  Y/N
Notes / screenshots:

## C. Ceiling  (RAW STATUS CODES — the load-bearing numbers)
C1 invite               -> status: ____   UI offered it? Y/N
C2 narrow own grant     -> status: ____   UI offered it? Y/N
C3 DELETE work-history  -> status: ____
C3 DELETE workspace     -> status: ____
Any 2xx above? (if yes, STOP and say so loudly):

## D. Member's own prefs
D1 toggle persisted across reload?  Y/N
D1 restored to original values?     Y/N

## E. Rig invite lifecycle
E1 pending row appeared?  Y/N
E1 revoke removed it?     Y/N
Workspace used (must be the rig):

## F. Billing boundary
F1 checkout URL host+path reached:
F1 confirmed no payment entered:  Y/N

## Anything that surprised you
(free text — this is often the most valuable section)
```

---

## 7. What happens next

Hand §6 back to the repo session. It will run the substrate receipts from the
manifest (grant rows, invite rows, `member_state`, `workspace_files` counts),
pair them against your DOM observations, and write the dated finding with a
per-surface verdict: **READY / READY-WITH-FIXES / NOT-READY**.

A finding of "not ready, here are the defects" is a **successful** pass. The
point is to learn the truth, not to produce a green checkmark.
