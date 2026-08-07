# ADR-531 — The OAuth state carries itself, and a failed connection says so

**Status**: Accepted (2026-08-07, operator-scoped — the operator surfaced the defect from a live
Connectors pane and set the scope as *"you can actually handle it in full … ensure documentation
and streamlined implementation"*).
**Date**: 2026-08-07
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Peripheral (Axiom 5 — how a principal's platform credential is acquired) +
Surface (how a failure becomes legible to the operator who caused it)

**Conforms to (does not invent)**: this ADR adds no principle. It closes three **conformance
gaps** against discipline already ratified — Singular Implementation (one source for one fact),
and the standing rule that a system reports outcomes faithfully rather than failing silently.

**Amends**:
- **ADR-147 / ADR-113** — the OAuth flow's state handling. Neither ADR chose a process-local
  store; it was an unratified implementation detail carrying a self-documented limitation
  (`oauth.py:170-176`, *"Acceptable for single-instance Render deployments"*) whose premise had
  quietly stopped holding.
- **ADR-425 D-connectors-pane** — the Connectors pane gains an outcome banner. The pane was moved
  to the account door; nothing at the time gave it a failure surface.
- **ADR-358 D6** — no change to the namespacing rule. The error redirect had simply never been
  updated to the `settings.pane` spelling the rule established.

**Preserves**: ADR-404 D2 (capture dormancy is untouched — this ADR is about *acquiring* a
credential, not reading with it) · ADR-494 D1/D4 (the registry is still the single source of
offered connectors; the banner reads `displayName` from it rather than re-deriving a name) ·
ADR-392 D9 (write-ready-by-construction scopes unchanged).

---

## 1. Context — three defects on one screen

The operator opened the Connectors pane and photographed it. Two connectors read *"Connected —
not reading (capture is paused)"* — correct, and exactly ADR-404 D2. But the URL bar read:

```
yarnnn.com/settings?provider=notion&status=error&error=Invalid+or+expired+OAuth+state&settings.pane=connectors
```

An audit of the surface and the code behind it found **three** distinct defects in one chain. They
compound: the first causes the failure, the second and third make it invisible.

### 1.1 The state was a lookup key into one process's memory

```python
# oauth.py — before
_oauth_states: dict[str, tuple[str, str, datetime, Optional[str]]] = {}
```

The `state` parameter carried no payload. It was a random key; the facts it stood for (`user_id`,
`provider`, `redirect_to`) lived in a module-global dict. A callback could therefore only succeed
if it landed **in the same process that issued the state**.

That premise fails routinely:

| Cause | Effect |
|---|---|
| Redeploy / restart | Every in-flight OAuth flow fails. Prod deploys from `main`. |
| Multi-worker serving | `/authorize` and the provider's `/callback` are load-balanced independently → fails ~(1 − 1/N). |
| Cold start | A slept instance loses all state. |
| Slow consent (>10 min) | Genuine TTL expiry — the only case the error message actually described. |

The code named its own limitation and the condition under which it would stop being acceptable.
The condition arrived; the comment did not enforce anything. **A documented limitation is not a
gate** — the recurring lesson, in a new place.

### 1.2 The error redirect named a pane that does not exist

```python
params = {"tab": "integrations", ...}   # before
```

`ALL_PANES` on the settings page is `["account", "connectors"]`. `"integrations"` is neither, so
the page's fallback (`page.tsx:139-141`) resolved it to **Account**. Every failed OAuth deposited
the operator on the Data & Privacy pane — a door they had not opened, with no connector in sight.

The *success* path had been updated to the ADR-358 D6 spelling (`settings.pane=connectors`, passed
as `redirectTo`). The error path had not. One branch migrated; its sibling was left behind.

### 1.3 Nothing read the error

The backend carefully URL-encoded a diagnostic message. No component consumed `provider`,
`status`, or `error` — verified by exhaustive grep across `web/`. There was no toast, no banner,
no console line. **From the operator's chair, Connect navigated away and returned with nothing
changed and nothing said.**

This is the arc's own recurring shape: *green gates test the room, not the doorway.* The connector
gates (`test_adr494_connector_registry.py`) assert the capture flag has exactly one reader and pin
the "capture is paused" copy. Not one of them asks whether a **failure** is visible. The error
surface existed in the backend and terminated in a dead parameter.

### 1.4 One message for three causes

`validate_oauth_state` returned `None` for *unknown*, *expired*, and *already-consumed* alike. Even
the server log could not distinguish deploy-loss from user-slowness from a double-callback — so
the failure was undiagnosable from **both** ends.

---

## 2. Decision

### D1 — The state is self-carrying and signed

The state parameter becomes a signed token holding its own payload:

```
base64url(payload_json) "." base64url(HMAC-SHA256(payload))
```

Payload: `{uid, prv, rdr, iat, nonce}`. Signed with `INTEGRATION_ENCRYPTION_KEY`.

**Why that key**: it is already required at boot (`main.py:53`) and already present on API +
Scheduler (CLAUDE.md §5). Using it as HMAC key material adds **no env var, no table, no
migration** — and cannot drift across services the way a new secret would. It neither performs nor
weakens the Fernet token encryption that owns the same secret; the two uses are independent.

**Rejected: a DB table.** It would work, but it buys durability we do not need at the cost of a
migration, a write on every authorize, and a GC job. The state is a 10-minute-lived assertion the
server made to itself. Signing is the smaller mechanism for exactly that shape.

**CSRF is preserved in kind.** The payload carries a 32-byte nonce and the signature makes the
token unforgeable without the server secret — the property that mattered, kept.

**One honest trade, stated plainly.** The dict consumed state on read; a signed token cannot
without reintroducing the storage this removes. So a state is replayable **within its TTL**. The
exposure is a replay of the same user's own authorization, which re-runs an idempotent upsert for
that user — meaningfully narrower than an outage on every redeploy. If a future requirement makes
one-time-use load-bearing, the replay guard is a small table of spent nonces, and it can be added
without revisiting this decision.

### D2 — TTL stays 10 minutes, in one named constant

`OAUTH_STATE_TTL_SECONDS = 600`. The old value was hardcoded twice (GC cutoff + validation), which
is the shape that lets two numbers disagree. One constant now.

### D3 — The failure taxonomy is named

`OAuthStateError(reason, message)` — a `ValueError` subclass, so the callback's existing
`except ValueError` still catches it. Six stable reasons: `malformed`, `bad_signature`, `expired`,
`provider_mismatch`, `provider_denied`, `unexpected`.

Server logs get the reason; the redirect gets it as `error_reason`. Deploy-loss (`bad_signature`,
when a secret differs) and slow-consent (`expired`) are now distinguishable at both ends.

### D4 — The error redirect lands on the Connectors pane

`CONNECTORS_PANE_PATH = "/settings?settings.pane=connectors"` — one constant, the spelling the
frontend actually reads. `tab=integrations` is gone.

### D5 — The failure is visible, and says what to do

The Connectors pane renders an alert when `status=error`: which connector failed (by
`displayName`, from the ADR-494 registry — not a re-derived name), what went wrong, and the
recovery. Copy is keyed on the **stable `error_reason` token**, never parsed from the human
sentence, so both sides' wording can change independently.

The banner renders **above** the loading branch — the operator returns from the provider already
wondering what happened, and a spinner is not an answer. Dismiss clears all four params so a
retried failure does not resurrect on reload.

---

## 3. Implementation

| Concern | Location |
|---|---|
| Signed state mint + verify | `api/integrations/core/oauth.py` — `generate_oauth_state`, `validate_oauth_state`, `OAuthStateError`, `OAUTH_STATE_TTL_SECONDS` |
| Error redirect target | `api/integrations/core/oauth.py` — `CONNECTORS_PANE_PATH`, `get_frontend_redirect_url(..., error_reason=)` |
| Reason plumbing + logging | `api/routes/integrations.py` — `oauth_callback`, all three error exits |
| Param reads + dismiss | `web/app/(authenticated)/settings/page.tsx` |
| Banner + reason→copy map | `web/components/settings/ConnectedIntegrationsSection.tsx` — `OAuthOutcome`, `describeOauthFailure` |
| Gate | `api/test_adr531_oauth_state_and_error_surface.py` (24 assertions) |

**Deleted, not shimmed** (Singular Implementation): `_oauth_states` is gone from the module, and
the gate asserts the name does not reappear in source — a surviving dict would be a second source
for one fact and could revive the process-local dependence on the next edit.

### 3.1 The gate was made to fail first

Each defect was re-injected into the fixed code and the gate re-run, per the standing discipline
that a gate which has never failed against the broken shape proves nothing:

| Injected defect | Gates that went red |
|---|---|
| Process-local dict restored | `test_state_survives_a_process_boundary`, `test_no_module_level_state_store_remains`, + 3 signature/expiry checks |
| `tab=integrations` restored | `test_error_redirect_targets_the_connectors_pane`, `test_error_pane_spelling_matches_the_frontend_whitelist` |
| Param readers removed | `test_settings_page_reads_the_oauth_outcome_params` |

The process-boundary gate reloads the module between mint and verify — discarding every
module-global, exactly as a redeploy or a second worker does. It is the one assertion the old
implementation **cannot** pass.

Two cross-side gates defend the seams that produced defects 2 and 3: one reads `ALL_PANES` out of
the frontend and asserts the redirect's pane is a member (so backend and frontend cannot drift
apart silently again); another asserts every `error_reason` the API can emit has operator copy.

### 3.2 Verification

- ADR-531 gate — **24/24**
- `test_adr494_connector_registry.py` — all checks pass
- `test_adr392_connector_lane.py` — **20/20**
- `test_adr404_capture_dormancy.py` — **4/4**
- `web` production build — compiles clean

**Owed: a browser click-pass.** The banner's *mount* is unproven — the build is green and the gate
reads source, but neither watches a real failed OAuth render the alert. That is precisely the
green-build-is-not-a-mount gap this arc keeps re-learning; it is named here rather than assumed
closed.

---

## 4. What this does not change

- **Capture dormancy** (ADR-404 D2). "Connected — not reading" is correct and stays. This ADR is
  about acquiring a credential, not reading with it. The pane will keep saying capture is paused
  until `CONNECTOR_CAPTURE_ENABLED` is set on API **and** Scheduler together.
- **The success path.** Default `/workfloor`, `redirect_to` honored, `status=connected` unchanged.
- **Scope requests** (ADR-392 D9) and the **connector registry** (ADR-494 D1).
