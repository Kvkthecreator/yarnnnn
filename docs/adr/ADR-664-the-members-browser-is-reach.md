# ADR-664 — The member's browser is reach

> **Status**: **Accepted** (2026-09-23, operator: *"yes this should be first class. proceed"*). Implemented with
> this document.
> **Date**: 2026-09-23
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Channel** — a fourth way the workspace reaches past its boundary.
> **No authority change**: no grant, no credential, no kernel mechanism; the tools and their executor are
> ADR-662's.
> **Gate**: `api/test_adr664_the_browser_is_reach.py`.
>
> **Origin** — the operator, after the agent refused X three times on 2026-09-23 (twice while the turn HELD the
> browser tools): *"the prompting lacks awareness, or needs a fundamental revisit wherein … we really orient
> ourselves towards the browser utilization by inference … the browser use has large implications."*

**Amends**: ADR-642 (Reach presents three mechanisms — intake, turn reach, outbound; this is the fourth) ·
ADR-644 (the one reach structure now carries the browser) · ADR-628 D5 as ADR-662 D5 already amended it (the
agent may complete an outward act in the member's browser; a connection still never sends). **Preserves**:
ADR-662 in full (the tools, the executor, attendance, consent) · ADR-645 D1 (no credential moves — the member's
sessions stay in their browser).

## 1. What was wrong

The agent learned its reach from three places, and all three told a connector-only story:

1. the reach section (`reach_status.frame_paragraph`) listed connections and ended *"You cannot send or publish
   anywhere yourself"*;
2. the tools edge said *"cannot … write out to external platforms … write only to the commons"* — a reach
   sentence outside the reach structure, which ADR-644 names a defect;
3. `list_integrations` said *"Asked to send or publish somewhere, you cannot."*

ADR-662 bolted a browser paragraph onto the tools edge. The model read four statements, three of them "you
cannot", and on a request to post to X it checked connections, found none, and refused.

## 2. Decisions

**D1 — The browser is reach, and it is stated where reach is stated.** `reach_status` gains the browser beside
the connections: `browser_sentence(member, held)` for the agent (in the reach section) and `browser_does()` for
the member (on Reach). No other sentence in the frame or a tool description claims or denies it.

**D2 — The browser is the general reach; a connection is the special case.** A connection is one platform's
API; the browser reaches any website, those platforms' own sites included. On a turn holding the browser the
agent is told: a task on a website goes to the browser first; a connection is only a faster route to the same
data. Through a connection it still never sends (the door named there is the member's).

**D3 — Absent, it is still named.** A turn without the browser is told the member's browser can act on a website
once they add the yarnnn extension to Chrome — so the answer to "post on X" is how to get there, not only
"connect it in Settings".

**D4 — The tools section claims no reach.** It says what the tools are and that reach is stated below.

**D5 — `list_integrations` names websites.** Its result carries `websites`: a website needs no connection; the
Browser tools act there when held, and the extension provides them when not. Its description no longer says
"you cannot".

**D6 — Reach shows the browser.** A "Your browser" row heads Reach → Connected (`ReachBrowser`), also when the
member has no connections — who needs it most. Its sentences are served (`GET /api/integrations` → `browser`);
the page adds only what it alone can know: whether the extension answers it.

## 3. What this does not do

It does not let anything use the browser without the member present — that is ADR-662 D9, and the proposal to
change it is ADR-665. It adds no permission, grant or credential. The connected/not-connected state is never
stored on the server: the extension answers the page.

## 4. Gate

`api/test_adr664_the_browser_is_reach.py`: the reach section with the browser held says it reaches any website
and denies nothing; without it, names the extension; the frame's tools section claims no reach;
`list_integrations` names websites and no longer refuses; the integrations route serves `browser_does`; Reach
renders the row in both branches and writes no reach sentence of its own.
