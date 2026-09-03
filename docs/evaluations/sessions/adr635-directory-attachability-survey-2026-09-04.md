# ADR-635 — which directory servers can actually be attached (2026-09-04)

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
