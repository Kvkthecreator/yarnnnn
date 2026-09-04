# ADR-635 — which directory servers can actually be attached (2026-09-04)

> **SUPERSEDED IN PART by the same day's follow-up — read the amendment at the
> foot of this file before quoting any number here.** The tally below measured
> what OUR CODE did and reported it as what THE SERVERS require. Two of the
> four "refusals" were defects in `register_client()`, and the 11 `NO_DCR`
> servers were never blocked at all — only refused by us.

Driven live against all 55 seed servers (`api/.venv-mcp`, production callback):
`discover()` on each, then `register_client()` where OAuth + a registration
endpoint were advertised.

| Verdict | N | Meaning |
|---|---|---|
| `DCR_OK` | 29 | discovery + dynamic registration both succeeded |
| `NO_DCR` | 11 | OAuth, but **no `registration_endpoint`** — needs a pre-registered client |
| `ANON` | 10 | no auth required; attaches with no sign-in |
| `DCR_REFUSED` | 4 | registration endpoint present, refused our request |
| `DISCOVER_FAIL` | 1 | Biorender — timeout (transient, not classified) |

**Attachable today: 39 of 55. Unattachable: 15 (27%).**

`NO_DCR` — Asana · Box · Docusign · Github · Hubspot · Owkin · Pagerduty ·
Slack · Zoom Mcp · Zoom Docs Mcp · Zoom Whiteboard Mcp

`DCR_REFUSED` — Figma (`403 Forbidden`) · Gong (`invalid_client_metadata`:
scope) · Square (`invalid_redirect_uri`) · Zoominfo (`invalid_client_metadata`:
vendor)

## ⭐⭐⭐ The seed's `auth` hint cannot carry this

The seed already has an `auth` field, inferred by
`scripts/refresh_connector_directory.py` from upstream's plugin config
(`header` if headers, `preregistered` if oauth, else `oauth-or-anonymous`).
Cross-tabbed against the probe:

```
header               NO_DCR        3
preregistered        NO_DCR        1
oauth-or-anonymous   ATTACHABLE   40
oauth-or-anonymous   DCR_REFUSED   4
oauth-or-anonymous   NO_DCR        7
```

It catches **4 of 15**. Eleven unattachable servers sit in
`oauth-or-anonymous`, indistinguishable from the 40 that work. Upstream's
config describes how *Claude's plugins* authenticate (many ship a pre-registered
client id), which is a different question from whether a third party can
dynamically register. **Only probing answers our question.** And nothing reads
`auth` today — the UI renders an identical Connect button for all 55.

## What the member sees now

Every one of the 15 offers a **Connect** button that cannot work. The failure
surfaces only after the click, as `dirError` — one state shared by two
different failures (the directory *search* failing, and one *server's* attach
failing), rendered above the list. So the message has no referent: "could not
reach the server: registration refused (403): Forbidden" appears with no
indication of which row produced it.

## Recommendation (not built — scope is the operator's call)

1. **Stamp attachability in the seed at refresh time.** The refresh script
   already reaches the network; have it record a probed verdict per server
   alongside the existing provenance. A missing `registration_endpoint` is a
   property of the server, not of an attempt.
2. **Move the error onto the row.** Split `dirError` into a list-level error
   and a per-row one. This is the actual presentation bug, and it is a
   placement fix.
3. **A modal is the wrong instrument here.** It would make a better-presented
   failure; the failure should not be reachable. A modal earns its place only
   when there is a decision to make — e.g. if we later accept a member-supplied
   client id for the `NO_DCR` servers, that form wants one.

Caveat: a `DCR_REFUSED` verdict is a point-in-time observation and could move
(a provider may open registration later). `NO_DCR` is structural. The refresh
script's diff is the right place for that churn to show up.


---

## ⭐⭐⭐ Amendment (same day) — the audit was measuring itself

Driven against the actual refusal bodies rather than trusting the classifier:

**Two of the four `DCR_REFUSED` were ours, not theirs.**

- **Gong** answered `invalid_client_metadata: "scope is required"` while
  advertising `mcp:read mcp:write` in its own `scopes_supported`. RFC 7591
  makes `scope` optional and we omitted it. Sending it surfaced a second
  defect: Gong rejects `token_endpoint_auth_method: "none"` — it wants a
  confidential client, and we already keep a secret when one is issued, so
  "public" was our preference, not a requirement. **Gong now registers.**

**The 11 `NO_DCR` servers were never blocked.** Their AS metadata genuinely
carries no `registration_endpoint` (verified by direct probe on Slack, Github,
Asana, Box, Hubspot, Docusign, Pagerduty) — but every one publishes a working
`authorization_endpoint` and `token_endpoint`, and everything in `begin_attach`
after the client id is obtained is identical whether that id came from DCR or
anywhere else. They were blocked by ONE hard `raise`.

Probed with an unregistered client id, most **serve their authorize page** and
defer client validation to sign-in:

```
Github     302 -> its own /login
Asana      200 (authorize page)
Box        200 (authorize page)
Hubspot    200 (authorize page)
Docusign   200 (authorize page)
Pagerduty  400
```

## Resolution

**Attempt the flow; let the provider answer.** Refusing was a guess about what
the provider would say, made on the member's behalf and always in the negative.
Whether a member's account can complete a sign-in is between them and the
provider — not something we can compute, and not ours to pre-empt. The callback
already surfaces the provider's own `error_description` (ADR-531), which is
strictly more information than our refusal carried.

A member who has registered yarnnn at the provider themselves may pass
`client_id`/`client_secret`; absent that, the attach goes out under the
unregistered client id `yarnnn` — which names us honestly rather than
impersonating a registered app.

**Opted out (3), and only these:** a refusal *no member can resolve by signing
in* is the one case where listing manufactures a dead end.

| Server | The provider's own words |
|---|---|
| Square | `Invalid redirect URI … domain not in allowlist` |
| Zoominfo | `Vendor with name yarnnn was not found in approved vendors` |
| Figma | bare `403`, no body — no signed-in path observed |

Keyed by URL **host** (`_OPTED_OUT_HOSTS`), so a seed refresh cannot re-list one
under a renamed key, and the live-registry path is filtered too. Deleting an
entry is how one comes back.

**Directory: 52 listed, 41 attachable by DCR or anonymously, 11 attempted with
an unregistered client, 3 opted out.**

Gate: `test_adr635_attached_connectors.py` §12 (89 checks). Falsified against
the old refusal — 12a-12c fail, and 12a catches the exception rather than
propagating it, so a refusal reports as a failed check instead of aborting the
run and silently skipping every later section.
