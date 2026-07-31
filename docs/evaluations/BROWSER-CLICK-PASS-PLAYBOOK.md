# Browser Click-Pass Playbook

**Feature-agnostic.** This is the method for verifying any operator-facing
surface through a real browser, with two principals, against production. It was
distilled from the 2026-07-31 settings-surfaces pass, but nothing here is about
settings — reuse it for Files, Studio, Chat, Agents, Billing, or whatever
surface ships next.

**Read this before writing a `suite_kind: browser` manifest.**

Sibling docs, different jobs — do not conflate them:

| Doc | Answers |
|---|---|
| [EVAL-PHILOSOPHY](EVAL-PHILOSOPHY.md) / [EVAL-ARCHITECTURE](EVAL-ARCHITECTURE.md) / [EVAL-SUITE-DISCIPLINE](EVAL-SUITE-DISCIPLINE.md) | Does the AGENT reason coherently against its mandate? (LLM judgment, `suite_kind: thesis`) |
| **This doc** | Does the SURFACE behave correctly for each principal? (deterministic, `suite_kind: browser`) |
| [VERIFICATION](VERIFICATION.md) | Which lane is due, and what does "done" mean for it? |

The two lanes are not graded the same way and are not fired the same way. A
thesis suite is fired by `run_eval_suite.py` and read as prose. A browser suite
is fired by a **browser principal** (Claude in Chrome, or an operator driving
the packet) and read as **PASS/FAIL per step with receipts** — because surface
behavior is deterministic, and a deterministic thing that "mostly worked" failed.

---

## §1 The governing rule: neither half closes a step

> **Every step has a DOM half and a SUBSTRATE half. A step that observed only
> one is NOT run.**

This is the whole method, and it is not ceremony. The 2026-07-31 pass found a
privilege escalation where the DOM was *identical* before and after the fix —
the menu offered the same three verbs either way. Only the network response and
the changed database row distinguished a sound system from a broken one.

The inverse also bites: an invite landed in substrate while the roster showed
nothing, so a substrate-only check would have called it a clean pass and missed
a defect that made operators double-invite.

- **DOM half** — what the principal sees and can click.
- **Substrate half** — what actually changed, read with `psql`, not inferred
  from a toast.

**Corollary — a hidden control proves nothing.** Absence from the DOM is not
enforcement. When a step tests a ceiling, issue the underlying call and record
the raw status code, even where the button is absent or disabled. "Disabled" is
a DOM state; a gate is a server behavior.

---

## §2 Chrome / tooling nuances (the ones that cost hours)

**Tool availability is frozen at session start.** Browser tools do not hot-reload.
If `/chrome` → Enable was clicked after this session began, the tools are not
here and no amount of retrying summons them. Start a fresh session. Verify with
an exact-name `ToolSearch` (`select:...`) — keyword search returns semantic
neighbours like `WebFetch` and reads as a false negative.

**One isolated browser context PER PRINCIPAL — mandatory, not tidiness.**
Contexts share cookies. Log in as the owner, then the member, in the same
context and the second login silently overwrites the first; every subsequent
"member" observation is really the owner, and the whole pass is worthless while
looking perfectly plausible. Use the `isolatedContext` parameter, one named
context per principal, and re-assert identity from the page (the avatar's
`aria-label` or a `/api/workspace/members` row) before trusting any observation.

**An a11y snapshot is NOT a DOM state check.** This one produced a wrong finding
in run 1. A snapshot lists `<button>` descendants of a `<fieldset disabled>`
without surfacing the disabled state, so "the member had editable dials" was
reported when the pane was correctly gated. **Before calling a control live,
query the real DOM** — `fieldset.disabled`, `aria-disabled`, `[role="alert"]`
contents. Snapshots are for finding `uid`s to click, not for verdicts.

**Bot protection will fire, and it looks like a deploy failure.** A burst of
automated requests can trip Vercel's Attack Challenge Mode; every response
becomes a 403 challenge page. The trap: `curl | grep <marker>` then returns
"marker absent", which reads as *the deploy has not landed* when it actually
means *you are not talking to the app*. **Always assert you reached the app**
(a known app marker, not just the absence of your new one) before concluding
anything about a deploy. The challenge is usually transient — pace requests and
it clears. Do not attempt to defeat it.

**Detect deploys behaviorally, not by grepping HTML.** Client markers live in
hashed JS chunks the HTML does not inline, so "marker not in HTML" proves
nothing. Either drive the behavior and see whether it changed, or check the
platform API (`mcp__render__list_deploys` for the API; the deploy status for
the FE). Remember the FE and API deploy **separately** — an API fix is not live
because Vercel finished.

**Two wire shapes for errors.** Raw FastAPI raises surface as `{detail}`;
anything through the envelope middleware arrives as `{error: {code, message}}`.
A client reading only one compiles, ships, and silently shows a generic
fallback forever. When testing whether a refusal is *legible*, assert the
operator sees the SERVER's words, not merely that some error appeared.

---

## §3 Accounts: pick the instrument before writing steps

The principal pair IS the instrument. Choosing it wrong silently narrows what
the suite can test, and the narrowing is invisible in the manifest.

**Prefer disposable rigs over live principals.** The 2026-07-31 pass was first
cut against the live workspace and a standing member. That forced every
mutating step into attempt-and-restore, and made the entire JOINING half
untestable — the member's grant already existed and may never be revoked, so
*becoming* a member (the first thing a real operator does, and the most likely
to be broken) could not be exercised at all. Re-cut onto two rig accounts, the
same suite ran the full lifecycle for real: invite → accept → member → narrow →
revoke, each with a receipt, each reversible by construction.

**A cold principal is a distinct instrument.** An account that owns nothing and
has never signed in is the shape a real invitee arrives in. That state is
consumed the first time you use it — so verify it (`0` grant rows anywhere)
before the run, and know that re-running the joining half needs a reset.

**Roster hygiene.**
- Test principals live in the login instrument's roster and are **enforced in
  code**, not by discipline. Minting a browser session for a real user is an
  account takeover, not an evaluation.
- Never add a real external address to the roster. Verify the guard refuses one
  as part of setup.
- Never set or read a principal's password to get in. Use the magic-link
  instrument.

**Guardrails belong in the manifest**, naming the specific rows that are never
touched (a standing member's grant, real externals, the live workspace when the
rig is the subject). Then *assert them at the end* — a guardrail you did not
re-check is a hope.

---

## §4 Writing criteria that survive contact

**Execute every receipt query against the DB before declaring the manifest
authority.** Two receipts in the 2026-07-31 manifest were dead on arrival and
would have failed mid-pass:

- one queried `member_state.user_id` — no such column (the table is keyed
  `(workspace_id, principal_id, key)`);
- one read `principal_grants` without pinning `status='active'`. A principal
  accumulates one row per grant event, so the query returned a revoked row
  alongside the active one — **a destroyed active grant would still have read as
  a pass.**

Both were written carefully by someone who knew the system. Careful is not the
same as executed.

**Pin the discriminating column.** Any table that accumulates rows per event
(`principal_grants`, `workspace_invites`, `workspace_file_versions`) needs the
status/version pinned in the receipt, or the query answers a different question
than the one asked.

**Prefer absent → present over value → value.** The cleanest receipt is a row
that does not exist at baseline. `count = 0` before, one row with the expected
JSON after, restored to absent. No ambiguity about whether the write landed or
the value merely already matched.

**Capture the destructive baseline BEFORE the destructive step.** For any step
whose failure mode is data loss, record the count first — there is no restore
if it fails, which is exactly why the number must exist beforehand.

**Every `mutates: true` step carries `receipt:` AND `restore:`.** This is
machine-checked (`api/test_eval_suite_gate.py`). The gate names the offending
step; keep it that way.

---

## §5 Gates: the trap this session actually fell into

The three legibility fixes shipped with a gate. **Its first version passed both
deliberate reintroductions of the defect.** It read a fixed 1400-character
window from each handler; the handlers sat ~1330 characters apart, so one
handler's window reached into the next and matched its *neighbour's* `catch`.
A second assertion tested for the mere presence of an identifier, which
survives deleting the assignment that gives it meaning.

Both were caught only by falsifying. Rules that follow:

- **A gate is not verified until it has been made to FAIL.** Break the thing it
  guards, watch it go red, restore. Do this for every assertion, not the suite
  as a whole — a suite can be green in aggregate while one assertion measures
  nothing.
- **Bound your search to the construct.** Brace-match a function body; do not
  slice a fixed window. Windows overlap neighbours and match their code.
- **Assert the ASSIGNMENT, not the identifier.** `/membersForbidden/` stays
  green when the line that sets it is deleted; `/membersForbidden = status ===
  403/` does not.
- **Assert the RENDER, not just the state.** A fix that stores an error nobody
  displays is not a fix. Include the "state set but never shown" case in
  falsification.
- **Counting gates cannot defend per-site invariants.** "N routes call the owner
  helper" passes when a new route is added unguarded and another gains a call.
  Enumerate the sites, assert per-site, and add a **completeness assert** that
  fails when a new matching route appears unclassified. On 2026-07-31 that
  completeness assert immediately caught two routes whose real paths differed
  from what the author assumed.
- **AST/text gates check text, not behavior.** When logic has subtle polarity
  (NULL meaning "class default" rather than "nothing"), verify the behavior at
  runtime across the real cases too.

---

## §6 Running the pass

1. **Preconditions.** Browser tools present (exact-name search). Deploy verified
   live for BOTH surfaces you are touching. Login instrument mints a working
   session. Roster guard refuses a non-test address.
2. **Baseline.** Run every receipt query and record the numbers, including the
   guardrail rows you must not disturb. This is also the manifest's first real
   execution — dead receipts surface here, before they can corrupt a verdict.
3. **One isolated context per principal**, identity re-asserted from the page.
4. **Walk the steps**, DOM + substrate for each. Ceiling steps: issue the call
   and record the raw status even when the control is absent.
5. **Restore**, then **re-assert baseline AND guardrails**.
6. **Account for every delta.** If a number moved for a reason outside the pass
   (concurrent operator work), say so explicitly with evidence. An unexplained
   baseline drift is exactly what a run record must not hand-wave.

---

## §7 The run record

One file per pass, per-step verdicts, receipts inline.

**Say what you did NOT run.** A pass that covers 8 of 13 steps is not a
sign-off; write the number. Sequencing coverage behind a discovered defect is
defensible, but the gap must be legible.

**Rank method strength, and never let it silently upgrade.** These are not
equivalent, and a later summary will flatten them if you do not stop it:

| Strength | What it means |
|---|---|
| **Probed** | A live call by the real principal, with a receipt |
| **Verified by code + live data** | The gate exists and evaluates correctly against real rows — but no live call |
| **Inferred** | Read the code and reasoned. Not evidence. |

If a step lands at the middle tier, write the caveat into the record so nobody
later calls it probed.

**Correct yourself in the record, in place.** Run 1 reported "editable dials"
from a misread snapshot; run 2 withdrew it explicitly and named the cause. A
withdrawn finding with its cause stated is more useful than one quietly deleted
— the next person learns the failure mode.

**A receipted negative is a real result.** "I suspected X, here is the query
showing X is not happening" is worth writing down. It stops the next session
re-deriving the same suspicion.

---

## §8 Marking a lane validated

`mark-validated.sh <lane>` is a **note to the next session** — "checked at this
SHA, don't re-check" — not a certificate of total coverage. Two consequences:

- **Withholding the mark because coverage is partial is the wrong instinct.**
  It leaves the radar noisy forever and teaches sessions to ignore it. Mark it,
  and **write the partiality into the record.**
- **The record must open with an explicit scope section** naming what the green
  lane does NOT cover: untested principal classes, steps that rest on
  code-reading, scale conditions never exercised (N>2 members, paid tiers).
  A future session inherits the limits along with the mark.

Check the lane's exit criteria **literally** in [VERIFICATION.md](VERIFICATION.md)
before marking. On 2026-07-31 the hesitation to mark turned out to be about a
different lane than the one being withheld, and both lanes' criteria were in
fact already met.

---

## §9 Quick checklist

```
PRE     browser tools present (exact-name search) · both deploys live
        login instrument works · roster guard refuses a real address
BASE    every receipt query executed · guardrail rows recorded
        destructive-step counts captured BEFORE
RUN     one isolated context per principal · identity re-asserted
        DOM half + substrate half per step
        ceiling steps: raw status code even when the control is hidden
        DOM state via real query, never an a11y snapshot
POST    restored · baseline re-asserted · guardrails re-asserted
        every delta accounted for, including ones you did not cause
REC     per-step verdicts · steps NOT run named · method strength ranked
        corrections in place · scope-of-sign-off section
GATE    every assertion falsified and restored
        bounded to the construct · assignment not identifier · render not state
        per-site + completeness assert, never a count
```
