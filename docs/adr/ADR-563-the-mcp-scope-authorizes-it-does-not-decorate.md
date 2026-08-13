# ADR-563 — The MCP scope authorizes; it does not decorate

> **Status**: **Accepted + Implemented** (2026-08-13). Three additive scopes replace the single decorative `read`, enforced per-verb at the one chokepoint every handler already calls. Gate `api/test_adr563_mcp_scope_enforcement.py` 16/16, three falsifiers verified red; enforcement verified at runtime against real SDK token objects, 9/9 cases.
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
