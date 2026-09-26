# ADR-563 — The MCP scope authorizes; it does not decorate

> **Status**: **Accepted + Implemented** (2026-08-13). Three additive scopes replace the single decorative `read`, enforced per-verb at the one chokepoint every handler already calls. Gate `api/test_adr563_mcp_scope_enforcement.py` 16/16, three falsifiers verified red; enforcement verified at runtime against real SDK token objects, 9/9 cases.
> **Amendment 1** (2026-09-26, operator-ruled): **the scope is granted at consent, never defaulted.** Registration is a ceiling (every tier); the operator picks the tier on the consent screen, write preselected; the bind is the one writer of a code's scope; legacy `read` is honoured and never minted. Migration 266 written, dry-run clean, **not yet applied** (the code does not depend on it). Gate `api/test_adr563_am1_scope_granted_at_consent.py` 12/12, driven end to end, five falsifiers red. See §8.
> **Date**: 2026-08-13
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Mechanism** (Axiom 5). The authorization field existed, was issued, was stored — and was never read.

**Closes**: [ADR-561](ADR-561-the-marketing-surface-states-only-what-the-code-does.md) §7 item 1 — the highest-priority defect that audit surfaced and copy could not address.

**Preserves**: [ADR-310](ADR-310-per-request-mcp-identity.md) **D4** (`resolve_request_client()` is the single per-request identity door — this ADR adds authorization *at* that door rather than beside it), [ADR-533](ADR-533-the-participant-contract.md) **D1/D2** (the roster is data, prose is derived), [ADR-512](ADR-512-file-unit-of-interop.md) **D3** / [ADR-545](ADR-545-binding-completion.md) (the nine verbs and their bindings are unchanged — this ADR classifies them, it does not re-cut them).

---

## 1. Context

ADR-561's marketing audit went looking for false *claims* and found a false *mechanism*.

The connector registered exactly one scope:

```python
valid_scopes=["read"],
default_scopes=["read"],
required_scopes=["read"],
```

…while binding nine verbs, four of which mutate substrate and one of which — `share` — can mint a **member** grant giving full workspace access to whoever opens the link. Nothing anywhere read `token.scopes`. A token **labelled `read`** could delete a file and hand the workspace to a stranger.

This is worse than having no scopes. A surface with no authorization field is honestly permissive; a surface with a `read` label and no check **tells the operator, the host, and the consent screen something untrue**. Claude.ai and ChatGPT both display requested scopes at authorization time — so the lie reached the one screen where the user decides.

The audit could not fix this in copy. ADR-561 stated the real reach honestly (*"a connected assistant can read, write, move, delete, and share files on your behalf"*) and named the code fix as owed. This is that fix.

## 2. D1 — Three additive scopes, and the legacy grant is retained deliberately

| Scope | Reaches | Rationale |
|---|---|---|
| `files:read` | `open` `list` `search` `history` | Pure reads. The safe floor, and the new registration **default**. |
| `files:write` | + `save` `edit` `delete` `move` | Substrate mutations. Each lands an attributed revision, so each is recoverable — but a reader has no business making them. |
| `files:share` | + `share` | **Its own tier.** Granting *reach* is a different act from changing *content*: a token that may write need not be a token that may hand the workspace to a stranger. |
| `read` *(legacy)* | everything | Retained. See below. |

The tiers are **ordered containment** — `files:read ⊂ files:write ⊂ files:share` — so a write-capable client is not forced to request three scopes to do ordinary work.

**`read` is kept as a full-access grant, and that is the load-bearing decision.** Every token ever issued carries exactly `["read"]`: it is the schema default (`ARRAY['read']`, migration 082) and both the OAuth and static-bearer paths hardcoded it. Narrowing it retroactively would have 403'd `save`/`edit`/`delete`/`move`/`share` on **every currently-connected ChatGPT and Claude connector**, on a deploy nobody was watching, with the only remedy being manual re-authorization the user has no reason to suspect they need.

The operator was offered the hard cutover explicitly and chose the additive path. The result: **no live connector breaks, and the label stops lying for every new grant.** `read` is documented in code as the legacy full-access grant it has always effectively been — not as a good grant, but as an accurate name for the authority those tokens already hold.

## 3. D2 — The guard sits at the chokepoint, not at nine call sites

`assert_scope(verb)` is called from **`resolve_request_client(verb=…)`** — the one door every handler already opens to resolve identity — not from nine handler bodies.

This is the same lesson ADR-557 D2 learned about `route_completion`: **a guard a call site can forget is not a guard.** The pre-563 surface is the proof — the scope field was plumbed end to end (issued, stored, refreshed, returned on the token object) and simply never consulted. Nine remembered lines would have been nine chances to ship the tenth verb unguarded.

Two properties follow:

- **Fail closed.** A verb absent from `VERB_SCOPES` is *refused*, not allowed. An unclassified verb is a mistake, and failing open is exactly how the surface got here.
- **The check runs before identity resolution and before any substrate is touched** — a refused call reaches nothing.

**`required_scopes` is deliberately empty.** Requiring a scope at the transport would reject every pre-563 token at the door, before the containment rule in D1 could keep it working. The authorization decision belongs at the verb, where the tier is known.

The stdio / static-bearer path carries no OAuth token and therefore no scopes. It is one process pinned to one user by `MCP_USER_ID` — not a multi-tenant boundary — so it keeps full access.

## 4. D3 — The classification agrees with what the tools already declare

Every `@mcp.tool` already declares `readOnlyHint` / `destructiveHint`. The scope classification is not a second, independently-maintained opinion about which verbs are dangerous: the gate asserts **the `readOnlyHint=True` set is exactly the `files:read` set**.

A new read-only verb therefore cannot land classified as needing write, and a new mutating verb cannot land annotated read-only, without the gate going red. Two declarations of the same fact that can drift are worse than one — so they are pinned to each other.

## 5. Verification

**Gate** `api/test_adr563_mcp_scope_enforcement.py` — 16/16, script-style (pytest reports a false PASS on this family; run with `python3`).

**Three falsifiers, three distinct reds:**

| Falsifier | Result |
|---|---|
| One handler reverted to a bare `resolve_request_client()` | **2 red** — caught as both a missing verb and a bare call |
| `assert_scope` fails *open* on an unclassified verb | **1 red** — the fail-closed assertion |
| Tier containment collapsed so `files:read` reaches writes | **1 red** — the read-only-reaches-nothing-else assertion |

**Runtime verification** (the part source inspection cannot give): the MCP SDK was installed under py3.11 and `assert_scope` exercised against **real `YarnnnAccessToken` objects in a real `auth_context_var`** — 9/9 cases correct, including a legacy `read` token reaching `delete` and a `files:read` token refused on it. The refusal message names the missing scope and the remedy: *"'delete' requires the 'files:write' scope; this connection holds ['files:read']. Re-authorize the connector to grant it."*

Neighbouring gates unaffected: ADR-533 PASS, ADR-543 7/7, ADR-545 11/11, ADR-512 7/7, SDK pin PASS, write-path signatures 5/5, workspace isolation 5/5.

## 6. Owed

1. **A client that actually requests the narrow scopes.** Enforcement is live, but every live token still holds the legacy grant, so in practice nothing is yet *restricted* — the mechanism is correct and currently unexercised in production. The next step is the connector-registration surface offering the tiers.
2. **A consent screen that names them in operator language.** "This assistant will be able to read your files" is the point of a scope; the raw `files:read` string is not that sentence.
3. **The `MCP_BEARER_TOKEN` static path** remains a single hardcoded `MCP_USER_ID` with full access — a dev convenience in a multi-tenant service. Out of scope here; named so it is not forgotten.
4. **`workspace_blobs` `USING (true)`** (ADR-561 §7 item 2) is untouched by this ADR and still owed.

## 7. Consequences

The scope field now means what it says, and the surface can be described accurately: a connection holds a stated authority, the authority is checked per verb, and a refusal explains itself. The honest disclosure ADR-561 shipped — that connected assistants can delete and share — remains true, and is now *bounded* for any grant that asks to be.

## 8. Amendment 1 — the scope is granted at consent, never defaulted (2026-09-26)

**The finding.** A ChatGPT connection could not write, and reconnecting did not help. The refusal said *"Re-authorize the connector to grant it"*; re-authorizing minted another `files:read` token, every time.

**The receipts** (production, 2026-09-26): ChatGPT client `e1d1dd40…` registered 2026-08-14 with scope `files:read`; all seven of its tokens since 2026-09-25 carry `{files:read}`. Claude client `bfc0b555…` registered with the same `files:read`, yet every one of its tokens carries `{read}` — the legacy full-access grant, including delete and share.

**Two defaults decided the grant; the operator never did.**

1. D1 set `default_scopes=["files:read"]` at registration, as the "safe floor". But the MCP SDK refuses any authorize request for a scope the client did not register (`OAuthClientInformationFull.validate_scope`). The registration default was therefore a **permanent ceiling**. ChatGPT asks at `/authorize` for exactly what it registered with, and a reconnect re-uses the same client, so no consent could ever grant it write.
2. The authorize leg wrote `" ".join(params.scopes) if params.scopes else "read"`. Claude asks for no scope, so every new Claude connection was minted the legacy full-access grant — the very label D1 said no new grant would carry.

The consent screen described whichever of those accidents the code carried and offered no choice. D1's "the label stops lying for every new grant" held for neither client.

**D5 — Registration is a ceiling, not the grant.** `REGISTRATION_SCOPES` (every grantable tier) is both the SDK's `default_scopes` and its `valid_scopes`, and so what the server advertises as `scopes_supported`. The legacy `read` is not among them: it is honoured on the tokens that carry it (`SATISFIES`) and never offered or minted. Migration 266 raises every registered client to the ceiling (dry-run: 25 rows).

**D6 — The operator picks the tier; the bind is its one writer.** The consent screen offers the grantable tiers (`consent_tiers()`), each described by the same `describe_scopes` the enforcement table drives, with **`files:write` preselected** (`DEFAULT_GRANT`). The operator's reason: a connected assistant that cannot save is not connected to a shared commons, and every write is signed and revertible. Share stays an explicit opt-in, because it hands the workspace to whoever opens a link. `POST /api/mcp/oauth-callback?scope=` writes the pick onto the code and refuses anything that is not a grantable tier (400). `/authorize` writes no scope at all: what the client asked for does not decide the grant.

**D7 — No default can grant.** A bound code without a scope is refused at exchange, never guessed. Migration 266 drops the `'read'` column defaults on `mcp_oauth_clients.scope`, `mcp_oauth_codes.scope`, `mcp_oauth_access_tokens.scopes` and `mcp_oauth_refresh_tokens.scopes`, so an unnamed scope can no longer become full access anywhere.

**What did not change.** Issued tokens keep exactly the scopes they carry: Claude's legacy `read` tokens still reach every verb and still rotate, and the members pane still flags them (`is_legacy_full`). The tiers, the containment, and the chokepoint are untouched. So is the refusal copy — *re-authorize* is now true, because a reconnect reaches a screen that can grant write.

**Deleted, not kept beside the new path:** `DEFAULT_SCOPES`, `VALID_SCOPES`, `normalize_scopes` (it read the requested scope as the grant), `_LEGACY_SENTENCES` (a copy of the tier sentences), the consent payload's `grants`/`legacy_full_access`, the screen's legacy-warning branch (no input can reach it), and the `["read"]` fallbacks on token reads.

**Gate** `api/test_adr563_am1_scope_granted_at_consent.py`, **12/12**. It drives the real MCP server app (`/register` → `/authorize` → `/token`) and the real API consent router (`/oauth-consent` → `/oauth-callback`) in one process over one stand-in for the service tables, so the code the server mints is the code the API binds and the token endpoint exchanges. It runs under `api/.venv-mcp`, and re-execs itself there. **Five falsifiers, each red:**

| Falsifier | Result |
|---|---|
| Registration default back to `files:read` | 9 red — `/authorize` for write returns `invalid_scope` |
| `/authorize` writes `read` when nothing is asked | 2 red |
| The bind does not write the scope | 3 red |
| Exchange guesses `read` for a scopeless code | 1 red |
| The bind accepts any scope | 3 red |

The pre-am.1 arms in `test_adr563_mcp_scope_enforcement.py` (16/16) and `test_adr563_consent_discloses.py` (23/23) that asserted the old default were rewritten to the ruling.

**Order and what is owed.** The code does not depend on migration 266. A client registered under the old default asks for the scope it registered with, so it passes the SDK check and reaches consent, where the bind writes the operator's pick. Until 266 is applied, a pending code picks up the column default `'read'` between `/authorize` and the bind, and the bind overwrites it. **Owed:** apply 266 (`scripts/db/run-migration.sh supabase/migrations/266_…sql`) and verify the four live defaults read NONE. Then drive a real reconnect (ChatGPT, pick *Read and write*) and read the new token's `scopes` as the receipt.

