# ADR-664 — The member's browser is reach

> **Amended** — [Amendment 1](#amendment-1-2026-09-24--the-browser-is-not-a-desktop-feature) (2026-09-24): the browser
> has its own Settings pane, one install action, and the public site names it once it can be installed.
>
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

## Amendment 1 (2026-09-24) — the browser is not a desktop feature

Operator: *"if the chrome extension is available on all our platforms … shouldn't we update it on all our surfaces
and communications as such."* The extension works from yarnnn on the web in Chrome and from the desktop app (which
relays to it); the code always treated them alike. The words did not.

**Found**: the one on/off switch sat in **Settings → Desktop app**, where no web member looks, beside "in the desktop
app, keep Chrome open"; the agent sent a member without the browser to "(Settings → Desktop app)"; three surfaces
each built their own store link with their own fallback words; the public site never named the capability, and
`/download` said the browser needs "nothing to install"; `client_tools.py`, `primitives/browser.py` and
`primitives-matrix.md` still said the desktop app (or its deleted pane) performs the acts.

**D7 — The browser has its own pane.** Settings → **Your browser** (`BrowserSetting`, renamed from
`DesktopBrowserSetting`), on the web and in the desktop app; "keep Chrome open" only inside the desktop app. The
agent's absent-browser sentence names the web, the desktop app and that pane.

**D8 — One install action.** `components/shared/AddToChrome.tsx` is the only reader of `CHROME_EXTENSION.storeUrl`
that builds a link; Settings, Reach, the Supervisor's install step and the marketing site render it, with one
"not yet" line (`extension.notYet`).

**D9 — The public site names the browser once it can be installed.** A FAQ answer, a How-it-works step, a line on
the home page and one on `/download`, each shown only when `EXTENSION_PUBLISHED` — the same `storeUrl` switch.
Setting the store link turns on the install buttons and the public words together; until then nothing public
promises what only developer mode can install.

Gate: this ADR's gate, 15 new arms; 8 proven RED in place.
