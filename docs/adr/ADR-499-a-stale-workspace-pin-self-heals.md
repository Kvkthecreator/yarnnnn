# ADR-499 — A Stale Workspace Pin Self-Heals

**Status**: Accepted (2026-07-29, operator-reported — "seems we have an issue with now having an account with no workspace? even if the invite failed, shouldn't we defer or fall back…"). Implemented same day.
**Date**: 2026-07-29
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Substrate (Axiom 1 — a cache of a server fact must not outlive the fact)
**Relates to**: ADR-373 (the `X-Workspace-Id` binding + fail-closed validation), ADR-404 step 5 (invite accept, which writes the pin), ADR-407 Phase 5 (`clearActiveWorkspace` — the clearer that existed but never fired), ADR-386 (revoke = full eviction — the event that stales the pin), ADR-414 D4 (pure genesis — the owner workspace the heal lands on), ADR-498 (the invite work that surfaced this)
**Amends**: nothing. The server contract is **unchanged** — fail-closed is correct.

---

## 1. Context — "an account with no workspace"

After going through the invite flow, the operator signed into the invited account and found every request 403'ing: account stats, notification preferences, surfaces. The reasonable read was *"this account has no workspace — shouldn't there be a fallback?"*

**The account had a workspace the whole time.** Live state at diagnosis:

```
principal_id 2be30ac5… | owner  | workspace 4ca9c664… | active     ← their own
principal_id 2be30ac5… | member | workspace d5b9029b… | REVOKED    ← the invite
```

Genesis had run correctly (ADR-414 D4): the member owns `4ca9c664`. The fallback the operator was asking for **already exists**, in two layers — `resolve_owner_workspace_id`, and a fresh-invitee fallback to the newest active grant.

## 2. The actual cause — a cache that outlived its fact

`X-Workspace-Id` is a **localStorage pin**, written by the invite/share accept (`setActiveWorkspace(result.workspace_id)`) so subsequent calls address the shared commons. The server validates it **fail-closed**:

```python
if x_workspace_id and workspace_id is None:
    raise HTTPException(403, f"No active grant into workspace {x_workspace_id}")
```

That is correct and stays: never silently serve a *different* workspace than the client addressed.

But the pin is a **client-side cache of a server-side fact**, and nothing cleared it when the fact changed. The member's grant into `d5b9029b` was revoked; the browser kept sending the header; every request 403'd. The owner-workspace fallback never got a chance to run, because the header short-circuits it — the account looked workspace-less while its own workspace sat one absent header away:

```
owner-resolution (post-heal)          → 4ca9c664…   (their own workspace)
pinned d5b9029b reachable? (pre-heal) → NO, revoked → 403 on every request
```

`clearActiveWorkspace()` already existed (ADR-407 Phase 5) — wired only to the deliberate "switch to my own workspace" menu action. Nothing called it when the server said the pin was dead. **Remembered state with no clearing path**, the same shape as ADR-491's stale settings pane and ADR-494 D5's restore-class fix, one layer lower and with worse blast radius: those stranded a *surface*, this stranded an *account*.

## 3. D1 — The pin self-heals at the one choke point

`request()` in `web/lib/api/client.ts` — through which every API call passes — now detects the stale-pin 403, clears the pin, and retries **once**. The retry sends no header, so the server resolves the caller's own workspace (the N=1 default).

Placement is the decision: at the single choke point, not per call site (which would be N places to forget, and this bug is precisely a forgotten place).

Three narrowings keep it from becoming a blunt instrument:

- **Matches the server's own detail string** (`"No active grant into workspace…"`). A broad `403 → clear` would swallow ordinary authorization failures — the owner-only verbs on the members roster legitimately 403 and must keep surfacing.
- **Only fires when a pin is actually set.** No pin, nothing to heal.
- **Retries exactly once**, via an internal `__retriedWithoutWorkspace` marker. An unguarded retry against a persistent 403 would spin forever.

## 4. On the operator's question — is the fallback missing?

No, and the distinction matters for where fixes belong. Server-side resolution already has *two* fallbacks, and pure genesis guarantees every account an owner workspace. Adding a third fallback would have been the wrong fix: the request never reached resolution, because an explicit header was being honored fail-closed. **The bug was client-side cache hygiene, not server-side resolution.**

The general rule this writes down:

> **A client-side cache of a server-side fact must clear when the server says the fact is gone.**

## 5. What is NOT changed

The server contract. Fail-closed validation stays exactly as-is — the gate asserts it. A 403 on an unreachable pinned workspace remains the correct answer; the client just stops treating that answer as terminal.

## 6. Validation

- `api/test_adr499_stale_workspace_pin.py` — **11/11**: server contract intact (fail-closed + both fallbacks), the heal at the choke point, server-string matching, pin-set precondition, clear-before-retry, retry-once, internal-only marker, and that an ordinary 403 still throws.
- **Behavioural replay** (not just grep — gates grep text, not execution): the control flow was replayed against a server model. Heals to the own workspace in exactly 2 calls · pin cleared · later calls clean first-try · an ordinary 403 still throws, does *not* clear the pin, and is *not* retried · a persistent stale-403 terminates in ≤2 calls (no loop). 8/8.
- Live DB receipt in §2, reproducible.
- `tsc --noEmit` clean; `next build` green (170/170).

**Not verified** (needs a human): the recovery in a real browser. The invited account should now load on next request instead of 403'ing — no cache clearing required, which is the point.

**Adjacent, deliberately not fixed here**: *why* the member's grant was revoked in the first place is a separate question (the invite `VQfcGO-…` is still pending, so the accept had not yet re-landed). This ADR ensures a revoked grant cannot lock a member out of their own account, whatever the reason for the revoke.
