# Layer-1 click-pass, run 2 — G3 + G4 driven in production (2026-08-26)

**Lane**: surface (browser). **Target**: Layer-1 G3 (realtime bell) + G4 (mention
polish) at `40b23da`. **Principals**: owner `kvkthecreator@yarnnn.com` ·
member `testacct@yarnnn.com`, one isolated context each, identity re-asserted
from the page before each observation. Rig `bf5b25a9`, restored at the end.

## Verdict

| Claim | Result |
|---|---|
| **G4(a)** own handle chips | not isolated this run (see Not covered) |
| **G4(b)** DM says "a direct chat" | **PASS** — server + UI |
| **G4(c)** outsider add-door is wired | **PASS** — opens the real drill-in |
| **G3** mention badges in seconds | **FAIL as shipped** — socket joined ANON; ~10s via poll. Fixed in `a991105` |
| (incidental) **G1** stamp at chokepoint | **PASS** — confirmed on a real member turn |

## G4 — passes

**(c) the add-door is a real action, not an inert row.** In a lane whose cast
excluded `testacct` (a workspace member, not a participant), typing `@` listed
them with an **"add…"** affordance whose a11y description states the rule
outright: *"Opens Add people — adding them is your call, never a mention's side
effect."* Clicking it navigated to `chat.detail=add` and opened the genuine
add-participant drill-in — "ADD TO THIS CONVERSATION", `testacct` under PEOPLE,
and an explicit **"Let them read what came before"** disclosure checkbox
(ADR-495 D2 made visible). No auto-invite. Completing it moved the cast 1 → 2.

**(b) the DM rule holds, derived not stored.** With the cast at 2 humans /
0 agents, the lane list and header relabelled to **"testacct · Direct chat"**,
and — read as the RECIPIENT — `GET /api/mentions` returned
`conversation_name: "a direct chat"`, author `kevin kim`. The pre-fix shape is
still visible in the ledger for contrast: an older row reads *"seulkim88
mentioned you in “seulkim88@gmail.com”"* — the recipient's own address echoed
back, which is exactly what G4(b) removes.

**(G1, incidentally) the stamp fires at the chokepoint.** A real member turn
persisted with `"mentions": ["500f3ae7-…"]` in its metadata, and the recipient's
`/api/mentions` served it. The parser was also exercised directly:
`resolve_member_names` → `{testacct, kevin kim}`, `mentioned_humans` → the right
principal.

## G3 — the claim does not hold as shipped

**Measured**: the bell's websocket joined as
`wss://…/realtime/v1/websocket?apikey=***&vsn=2.0.0` — **no `access_token`**.
Realtime re-checks RLS per subscriber against the socket's JWT; anon resolves
`auth.uid()` NULL, so `session_messages` INSERTs are never delivered. The
channel reports SUBSCRIBED and delivers zero.

Third probe, clean instruments: mention queryable **+9.2s**, badge lit
**+10.1s**. The badge tracked the API by ~0.9s — the bell reacts promptly to
data that arrives late. That is the poll, not a push (a push debounces at
750ms).

**Cause**: `setAuth` was called fire-and-forget in a `.then()` beside
`.subscribe()`. `use-file-revisions-realtime` had already diagnosed this in its
own comment — *"a race whose losing side is the silent one … it would work
locally, where the session resolves from cache, and fail on a cold load"* — and
sequences with `await`. The G3 hook diverged from the sibling it was modelled on.

**Fixed** (`a991105`), and the new gate walks the realtime directory rather than
a hand-list — which immediately found the **same race in
`use-session-messages-realtime`**, the chat transcript's own stream, whose
comment reads "Set BEFORE subscribing" directly above the racing form.

## Second defect found on the way in — ADR-499's heal was dead

A re-invited member **could not accept the invite**: the invite page 403'd with
`No active grant into workspace bf5b25a9` because the browser still sent a stale
`X-Workspace-Id` from the revoked membership, and nothing cleared it.

ADR-499's self-heal exists and is well-built — but it tested `data.detail`,
while `main.py`'s envelope normalizes EVERY HTTPException to
`{error:{code,message,hint}}`. The string it needed was at `error.message`, so
the branch never fired in production.

Proven live in one call: the shipped reader saw `undefined`; the repaired reader
recovered the exact string; clearing the pin returned **200** and the invite
rendered. One `errorDetailFrom` extractor now serves all three transports.

**Why the gate missed it**: it asserted the client matched *"the server's own
detail string"* — true of both files in isolation, and silent about what
survives the wire. The playbook's own §2 names this trap ("two wire shapes for
errors"); the gate predated the check.

## Guardrails re-asserted

- Owner grant on `bf5b25a9` active and untouched.
- Qualifying membership grants restored to **0** (baseline).
- Probe lane archived.
- Rig principals only; no live-workspace principal used.

## Not covered

- **G4(a)** (own handle chips in your own transcript) — not isolated; needs the
  author's transcript view read directly.
- **G5** suppression live-proof — still unbuilt.
- Re-drive of G3 latency **after `a991105` deploys** — the fix is proven by gate
  + falsification, not yet by a second live measurement.
- Pre-existing, unrelated: `test_adr412_chat_surface.py` fails at HEAD on a
  missing `web/components/agents/AgentContentView.tsx`.
