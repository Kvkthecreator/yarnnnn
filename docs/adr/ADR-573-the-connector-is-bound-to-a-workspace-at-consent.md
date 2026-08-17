# ADR-573 — The connector is bound to a workspace at consent

**Status**: Accepted (2026-08-17). Ships code + migration 238.

**Completes**: [ADR-373](ADR-373-multi-principal-workspace-and-the-re-key.md) **D6** — the half D6 named as still deferred ("a connector cannot NAME a workspace"). D6 closed the *binding* question (the connector resolves the same workspace the member's default resolves to); this closes the *selection* question.

**Composes with**:
- [ADR-563](ADR-563-the-mcp-scope-authorizes-it-does-not-decorate.md) — scopes answer *what a connection may do*; this answers *where it may do it*. Two independent axes; neither implies the other.
- [ADR-407](ADR-407-the-three-scope-taxonomy.md) Phase 5 — the memberships endpoint (the switcher's) is reused as the picker's option list, so the consent screen and the cockpit cannot disagree about what a principal reaches.
- [ADR-310](ADR-310-judged-substrate-interop-face.md) D4 — the consent leg. The bind stays POST-on-explicit-click; this adds a field to it, not a new door.

**Preserves**: ADR-371's auth mechanism (untouched), ADR-512 D5's handle grammar (no workspace slot added to `yarnnn://workspace/…`), ADR-373 D6's fail-soft resolution posture.

---

## 1. The observation

ADR-373 D6 ends with an explicit deferral:

> Still deferred: a connector cannot NAME a workspace (no header, no tool argument, no token claim), so it takes the principal's default.

That is not a theoretical gap. Queried against production, 2026-08-17:

- **One principal reaches two workspaces.** They own `My Workspace` and hold an active `member` grant into `yarnnn workspace` — the shared commons.
- **Their ChatGPT connector binds to the owner workspace.** All three of their connector-authored versions landed in `My Workspace`.
- **The commons was unreachable from the connector.** Not restricted, not empty — unaddressable. The workspace their membership exists *for* was the one workspace their assistant could not see.

The browser has had the answer to this since ADR-373: `X-Workspace-Id`, validated against reach, fail-closed. The connector had no analog. So the same human, on the same account, reached different substrate depending on which door they came through — and only the browser door could be pointed.

ADR-420 §10's demand-gate does not govern this — that gate is about **connector breadth**, acquiring reach *outward* to a new platform, and nothing is being acquired here. But its underlying test (*build when real demand names the capability, not ahead of it*) is the one applied: the demand is named, from a live account, against substrate that already exists, and the fix widens no external surface.

## 2. D1 — The workspace is chosen at consent, and stamped on the token

The operator picks the workspace on the approve screen. The choice is written onto the pending auth code, carried to the access and refresh tokens at exchange, and read per request.

**Why consent and not per call.** Three shapes were considered:

| Shape | Why not |
|---|---|
| **Per-verb `workspace` argument** | Changes all nine verb signatures; makes the *model* the chooser, so a wrong guess writes to the wrong commons with full attribution; and ADR-512 D5's handle grammar (`yarnnn://workspace/…`) has no workspace slot — adding one re-opens a settled cross-boundary format. |
| **Consent binding + per-call override** | Two mechanisms for one question, each needing its own reach check and audit trail. Strictly more surface than the demand justifies. |
| **Consent binding (chosen)** | One connection, one workspace, chosen once by the human who holds the grant — never by the model. Matches how every other principal binds. Reaching a second workspace is a second connection, which is legible in the members pane as two rows. |

The decisive argument is **who chooses**. A connection is a standing grant of reach; the human who holds the grant should set its extent, at the moment they are consenting, in a browser where they can see the options. Handing that to a per-call model argument moves an authorization decision into a token stream.

## 3. D2 — A stamped workspace NARROWS; it can never grant

`resolve_mcp_workspace(user_id, bound_workspace_id)` routes the stamped id through `resolve_workspace_for_principal` — **the same function the browser's JWT door calls with `X-Workspace-Id`** — which returns it only if the principal reaches it.

Two consequences, both load-bearing:

1. **Reach is re-checked on every request**, not trusted from the token. `principal_reaches_workspace` is deliberately uncached (ADR-373), so a member revoked *after* their token was minted loses reach on their very next call. The token records a *choice*, never an *entitlement*.
2. **The consent door refuses an unreachable workspace with 403**, rather than quietly substituting the default. Silently substituting a different workspace than the one addressed is precisely the incorrect-success D6 was built to end; doing it at the consent door would reintroduce it *with the operator believing they had chosen*.

### The one deliberate asymmetry with the browser

An unreachable *requested* workspace **403s at the JWT door** but **degrades to the default at the MCP door**. This is intentional and narrow: the operator is not present to re-authorize mid-session, and a connector that silently stops working is worse than one that falls back to substrate it can always reach. The reach loss is still enforced — the unreachable workspace is never returned, only the default is. The event is logged at WARNING.

## 4. D3 — NULL is not a missing value; it is "the principal's default"

Every one of the **421 live pre-573 access tokens** carries `workspace_id IS NULL`, and the runtime reads NULL as *resolve the principal's default* — byte-identical to ADR-373 D6.

**No backfill, deliberately.** Stamping live tokens with their currently-resolved default would look harmless and would **freeze** today's resolution for connections whose default may legitimately move later. A connector changes where it writes only when its owner re-authorizes and picks. Nothing repoints on deploy day.

The binding also rides the **refresh token**, because silent rotation is how live connectors stay alive — a rotation that dropped `workspace_id` would migrate every bound connector back to the default with nobody acting. This is the same failure shape ADR-386 D1.a found in the grant auto-provision hook, and it is guarded by its own gate check.

## 5. D4 — The picker appears only when there is a choice

The consent screen shows a workspace selector **only when the operator reaches more than one workspace**. With a single workspace a chooser is noise, and the sentence above it already names the destination.

Options come from the **existing** `/api/workspace/memberships` endpoint (the ADR-407 Phase 5 switcher's), not a second enumeration that could disagree with the cockpit about what the principal reaches. The lookup is best-effort: a failure leaves the default binding and no picker — the pre-573 flow — never a blocked connection.

## 6. What this does NOT do

- **Does not let the connector change workspace mid-session.** No header, no tool argument, no runtime switch. One connection, one workspace, until re-authorized.
- **Does not add a workspace slot to the ADR-512 D5 handle grammar.** `yarnnn://workspace/…` stays workspace-relative; the workspace is ambient to the connection, as it is for the browser.
- **Does not change what the assistant is TOLD.** The connector still is not informed which workspace it is in (ADR-533 D6 refuses to export workspace intent into a third-party context window). Whether the workspace *name* — as distinct from its mandate — should cross that boundary is a separate question, unaddressed here.
- **Does not widen scopes.** ADR-563's tiers are untouched; a bound connection may do exactly what its scopes authorize, only somewhere specific.
- **Does not touch the auth mechanism.** ADR-371's boundary, PKCE, rotation, and reuse detection are unchanged.

## 7. Verification

`api/test_adr573_connector_workspace_binding.py` — 18/18, run under py3.11 (`/tmp/mcpenv/bin/python3.11`; the `mcp_server` package needs 3.10+ syntax).

The gate runs the **real resolver** against a stubbed reach oracle rather than asserting over source, and parses the provider with `ast` for the persistence checks (the file discusses `workspace_id` in prose, and a comment must never satisfy a check about behaviour).

Falsified three ways, each restored:

| Falsifier | Caught by |
|---|---|
| Binding ignored (pre-573 behaviour) | D1 — the commons no longer resolves |
| Token trusted without re-checking reach | D2 ×3 + D4 — the privilege-escalation shape |
| Refresh rotation drops the binding | D5 — the live-population path |

Migration 238 applied and verified against the live schema: three nullable `uuid` columns, `421` tokens, `0` bound — every existing connector unchanged.

## 8. Rejected alternatives

- **FK to `workspaces(id)` on the token tables.** Rejected: these are service-scoped auth rows with their own lifecycle (revoke, rotate, expire, account-delete sweeps). A workspace deletion must not cascade-delete auth history, and the runtime re-checks reach anyway — a dangling id fails closed rather than granting anything.
- **Caching the resolved workspace on the MCP side.** Rejected for the reason ADR-373 D6 already gave: the MCP service is long-lived with no request recycle, so a value cached there outlives a workspace change indefinitely.
- **Defaulting new connections to the *commons* rather than the owner workspace.** Rejected: it would change where existing operators' connectors write based on a heuristic about which workspace "matters", which is exactly the silent repointing this ADR exists to prevent. The operator chooses.
