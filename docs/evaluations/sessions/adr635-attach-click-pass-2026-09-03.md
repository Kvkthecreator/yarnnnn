# ADR-635 — the attach click-pass, run 1 (2026-09-03)

Status: **PRECONDITIONS VERIFIED · THE BROWSER ROUND-TRIP IS NOT YET DRIVEN.**

The owed verification (SESSION-HANDOFF Part N item 1) has an irreducible human
step: a member must sign in at yarnnn.com and grant consent at the provider's
OAuth screen. This record covers everything verifiable without that step, so
that when the browser step is taken, only the genuinely-manual part remains and
a failure there is attributable.

## What is verified

Deployment parity at the arc's commit `02162fc`:

| Surface | Receipt |
|---|---|
| API | Render deploy `dep-dacjrce1egvs7391s0ag`, commit `02162fc`, status `live` |
| Web | `https://www.yarnnn.com/.well-known/mcp.json` serves the ADR-635 D9 shape — **no tool list** (the pre-635 card enumerated `remember`/`recall`/`trace`). The absence IS the receipt: it can only come from 02162fc. |

The doors, driven unauthenticated against production:

```
GET  /api/connectors/directory?q=linear  -> 200, one result (mcp.linear.app/mcp, "Project tracker")
GET  /api/connectors/categories          -> 200, 28 categories from the consumed seed
POST /api/connectors/attach              -> 401  (fails closed; not 404, not 500)
GET  /api/connectors/attach/callback?state=bogus
     -> 307 https://yarnnn.com/settings?settings.pane=connectors&provider=connector
        &status=error&error=OAuth+state+is+malformed
```

The malformed-state callback **degrades to a readable error at the right
frontend origin** rather than 500ing — the ADR-531 outcome posture holds on
this route.

⭐ **The highest-risk pre-consent failure mode is falsified.** A redirect-URI
mismatch would only surface *mid-consent*, after the member has already left
yarnnn. Driven live (`api/.venv-mcp`, against the real provider):

```
discover("https://mcp.linear.app/mcp")
  auth=oauth · issuer=https://mcp.linear.app
  authorization_endpoint=/authorize · token_endpoint=/token
  registration_endpoint=/register
  code_challenge_methods_supported=["S256"] · scopes=["read","write"]

register_client(registration_endpoint, callback_url())
  -> client_id=IGP4f79KmQrvFVt7, token_endpoint_auth_method="none"

callback_url() -> https://yarnnn-api.onrender.com/api/connectors/attach/callback
```

Linear accepted dynamic registration **with the production callback URI** and
issued a client. `API_BASE_URL` need not be set on Render: `callback_url()`
defaults to the public API origin, and that is the value the provider accepted.

Baseline before the click-pass, so any post-run row is unambiguously this arc's
(count-only reads):

```sql
select platform, status, count(*) from platform_connections
  where platform like 'mcp:%' group by 1,2;   -- ZERO ROWS

select family, status, count(*) from action_proposals group by 1,2;
  -- substrate|executed 13 · substrate|expired 62 · substrate|rejected 50
  -- family='external-write': ZERO. The queue has never carried one.
```

That second zero is the load-bearing one: ADR-635 claims a `propose` call is the
proposal queue's **first** external-write producer since the steward retired.
The baseline confirms the queue has never held such a row, so the click-pass's
step 5 is a genuine first, not a re-run.

The aperture fails closed as specified — `aperture_mode()` returns `None` for
any tool not in the aperture, and `None` is DENY. So step 3 (setting one tool
Direct and one Ask-first) is what makes steps 4-5 possible at all; a fresh
connection offers nothing.

## What is NOT verified

**The browser round-trip.** Steps 1-5 of the click-pass are undriven:

1. Settings → Connectors → Find a connector → "linear" → Connect
2. Authorize at Linear → land on `/settings?settings.pane=connectors&settings.connector=mcp:linear`
3. One read tool → Direct, one write tool → Ask first → Save → row reads "2 tools offered"
4. /chat: the Direct tool returns a result; the Ask-first tool says it was queued
5. Notifications → queue: the card names `linear: <tool>` with the argument
   preview → Approve → the replay runs → the effect lands on Linear

Blocked on two things, both outside this session:
- the OAuth consent is a human act;
- the Chrome instance on the devtools profile is held by another client
  (`--remote-debugging-pipe` to a different process), so it cannot be attached
  to from here.

Nothing in the ADR is flipped on the strength of this record. When the browser
run happens, the receipts to capture are:

```sql
select platform, status, metadata->'aperture' is not null as has_aperture
  from platform_connections where platform = 'mcp:linear';

select family, primitive, status from action_proposals
  where family = 'external-write';
```

Expect `active` + `has_aperture=true`, and one `external-write` row with
`primitive` like `mcp__linear__…` reaching `executed` after Approve.

## Method note

The DCR probe registered a real client at Linear. That is a durable side effect
of a verification act — harmless (an unused public client with no grant behind
it), but recorded here rather than left silent, because the ADR's own discipline
is that a verification which changes the world says so.
