# Audit Findings — ADR-373 Grant-Consult (§0 of the implementation scope)

**Date**: 2026-06-29
**Hat**: A (system editor). **Phase**: §0 audit, BEFORE any implementation.
**Audits**: [`adr373-grant-consult-implementation-scope-2026-06-29.md`](adr373-grant-consult-implementation-scope-2026-06-29.md) against live code + DB.

**Verdict: the scope doc is SUBSTANTIALLY CORRECT.** Every load-bearing claim
verified with a receipt. One material refinement on the MCP principal mapping
(the scope doc flagged it as the open question; the audit resolves it). One
design subtlety the scope doc did not name — the **allowed-region vs
locked-prefix polarity** — which the implementation must get exactly right.

---

## 1. Audit checklist results (each with a receipt)

| # | Claim | Verdict | Receipt |
|---|---|---|---|
| 1 | Gate is pure-prefix; nothing consults `principal_grants` | ✅ TRUE | `_caller_class` (workspace.py:1761) reads only `caller_identity`/`reviewer_caller`; `_is_path_locked` (workspace.py:1782) reads only `CALLER_WRITE_POLICY`. **`grep principal_grants/principal_id` over `api/**.py` (ex-venv) = ZERO app hits.** |
| 2 | `AuthenticatedClient` carries `caller_identity` + `workspace_id`, **no `principal_id`** | ✅ TRUE | supabase.py:72-76 — fields are `client, user_id, email, caller_identity, workspace_id`. Resolving a principal_id is a real sub-task. |
| 3 | `principal_grants` = owner rows only, `scopes` NULL | ✅ TRUE (count refined) | Live query: **11** `owner`/`active` rows, **11/11 scopes NULL**, 11 distinct ws, 11 distinct principals (1:1). NOT 12 — the migration seeds grants only for workspaces that own substrate (`WHERE EXISTS workspace_files`); one of the 12 workspaces has no substrate yet, correctly no grant. |
| 4 | Non-human principal → principal_id mapping | ⚠️ REFINED (see §2) | Human owner: **principal_id == owner_id::text == auth.users.id == user_id** — all 11 confirmed UUID-shaped + matching owner_id. MCP path is NOT a separate principal row at the floor — see §2. |
| 5 | Green test baseline | ✅ ESTABLISHED | `pytest test_adr320 test_adr307_{taxonomy,platform_write_gate} test_adr373_rekey` → **62 passed**. `test_adr373_rekey` references `principal_grants` ONLY as a static migration-SQL string match (`test_migration_grants_and_notnull`), never behaviorally. |
| 6 | No active concurrent lane on the gate | ✅ CLEAR | `git status` on permission.py / workspace.py / supabase.py / workspace_paths.py = clean. The dirty tree (reviewer_agent.py, FOUNDATIONS.md, etc.) does not touch the gate. |

---

## 2. The MCP principal mapping — RESOLVED (the scope doc's open §3 question)

The scope doc (§3) flagged "how does the MCP caller map to a principal_id?" as
the genuine open design question. The audit resolves it from `mcp_server/auth.py`:

**The MCP `AuthenticatedClient` authenticates AS THE OPERATOR.** `resolve_request_client`
(auth.py:59) reads the OAuth token's `user_id` (the real authenticating human)
and builds the client with `user_id = <that human>` and
`caller_identity = "yarnnn:mcp:<client>"`. The `client_id` (claude.ai vs chatgpt)
names **the room** — it is a *sub-identity within the operator's principal*, not a
separate `principal_grants` row.

**Consequence for the consult:** the MCP caller's grant lookup keys on the
**operator's** `principal_id` (= `user_id`, the owner row). Its *write region* is
already narrowed to the `mcp` class default by `_caller_class` (which maps
`yarnnn:mcp*` → `"mcp"`). So at the launch floor:

- The grant lookup for ANY caller through a human's auth keys on that human's
  `principal_id` (= `user_id`).
- The **class** (operator/reviewer/mcp/agent/system) still comes from
  `caller_identity` via `_caller_class` — UNCHANGED. This is what keeps the
  mcp/reviewer/agent narrowing intact: a foreign LLM writing through the operator's
  auth is still `mcp`-class-locked even though it keys on the operator's grant.
- The grant's `scopes`, when present, **further narrows** the principal's owner-level
  reach. When NULL (today, all 11), the class default applies = today's behavior.

**Operator decision (2026-06-29): ALL principals grant-consulted, uniformly.**
The operator's requirement: the workspace must accommodate MCPs (foreign LLMs),
multiple humans, and 3rd parties (Linear/Slack/Copilot/Cursor via MCP/API) as
principals. The resolution must be stable + scalable, not owner-only.

Live MCP data (receipts): 13 `mcp_oauth_clients` rows (Claude/ChatGPT/codex/…),
each a stable `client_id` UUID. `mcp_oauth_access_tokens` binds
`(client_id, user_id)` — so an MCP caller resolves to: **principal_id = client_id**,
**workspace_id = owner_ws(user_id)**. There are **0 `principal_grants` rows for any
MCP client** today (only the 11 owner rows).

**Resolved design — `resolve_principal_id(auth)` is the uniform abstraction.**
Every principal class resolves to a stable principal_id by the SAME function:

| Class | principal_id | source |
|---|---|---|
| owner / human | `user_id` | `auth.user_id` (= owner grant's principal_id, confirmed) |
| foreign-llm (mcp) | OAuth `client_id` | the token's client_id (the room: claude.ai/chatgpt) |
| agent / specialist | the agent slug | parsed from `caller_identity` (`agent:<slug>`) |
| system | the system actor | parsed from `caller_identity` (`system:<actor>`) — class-default only |
| future member / platform / a2a | their stable id | additive, no gate change |

The gate then looks up `principal_grants(principal_id, workspace_id, status='active')`:
- **grant row with explicit scopes** → allow-list narrowing (§3 polarity).
- **no grant row, OR scopes NULL** → fall through to `_is_path_locked(class, path)`
  = today's exact behavior. **Every live caller hits this branch** (owner rows have
  NULL scopes; no non-owner rows exist), so the consult is byte-identical today.

**This makes the consult genuinely per-principal for ALL classes without requiring
any grant rows to exist.** The moment a `foreign-llm` grant row is written (the
"automatic members" provisioning), the already-wired consult honors it. Provisioning
(auto-create a grant on OAuth authorize) + role scoping are **deferred to the separate
Workspace Members ADR** (operator's call) — building them before that ADR would lock
in a role model prematurely. The floor that ships: **the uniform consult + class-default
fallback.**

---

## 3. The design subtlety the scope doc did NOT name — POLARITY

`CALLER_WRITE_POLICY[class]` is a tuple of **LOCKED** prefixes (roots the class
CANNOT write). The grant's `scopes` (ADR-373 D2/D3) is an **ALLOWED** write-region
set (roots the principal MAY author). These are **complements**. The consult must
not naively swap one for the other.

**The correct consult semantics** (preserving the safety invariant):

```
is_locked(principal_id, workspace_id, caller_class, path):
    grant = lookup_active_grant(principal_id, workspace_id)
    if grant is None or grant.scopes is None:
        return _is_path_locked(caller_class, path)          # ← class default = TODAY
    # explicit scopes present: ALLOW-LIST semantics — locked iff path's root
    # is NOT in the granted regions (narrowing within the class ceiling).
    root = top_level_root(path)
    return root not in grant.scopes
```

- **NULL scopes → fall through to `_is_path_locked` unchanged.** This is the
  byte-identical safety invariant. Every live row hits this branch.
- **Explicit scopes → allow-list.** A grant `scopes=['operation/']` means: locked
  from everything whose root ≠ `operation/`. This is a *narrowing* — it can only
  remove reach, never add it beyond the class ceiling (the class lock still applies
  first conceptually; but since explicit scopes are always a subset the owner
  issues, allow-list-within-ceiling is correct and simpler). For the launch floor
  no explicit-scopes row exists, so this branch is exercised only by tests.

This polarity is the single thing most likely to ship a permission bug if rushed.
The fallback-identity regression test must assert the NULL-scopes path is
byte-identical; the grant-honored test must exercise the allow-list path.

---

## 4. Net assessment

- The work is genuinely **"one function + one table consult"** (ADR-373 §4) — confirmed.
- `principal_id = user_id` at the floor (no separate principal rows exist). The
  `AuthenticatedClient` does need a `principal_id` field for forward-compat and
  clarity, but at N=1 it equals `user_id`, so resolution is a one-liner, not the
  "real sub-task" the scope doc feared.
- The safety invariant (NULL scopes = today) is structurally guaranteed by the
  fall-through branch. The regression test makes it provable.
- The two operator decisions (launch floor scope; FE read-only vs provisioning)
  are real and surfaced below — neither is resolvable from code.

**No blocking discrepancy. Cleared to proceed to the operator decisions, then build.**

---

## 5. Operator decisions (2026-06-29)

1. **Launch floor: ALL principals grant-consulted** (not owner-only). Rationale:
   MCP callers from ChatGPT/claude.ai are already live in workspaces like
   `kvkthecreator` — not speculation. Resolved technically as the uniform
   `resolve_principal_id(auth)` + class-default fallback (§2). Byte-identical today;
   honors grant rows the instant they exist.

2. **Frontend: a dedicated "Workspace Members" panel in Workspace Settings**
   (read-only core feature this session). Named "Workspace Members" (not "Users")
   deliberately — in this model, MCP connectors from external LLMs become automatic
   *members*, so the panel lists humans AND foreign-LLM/3rd-party principals. The
   **grant-role scoping + provisioning workflows are deferred to a separate ADR**
   (operator's call); this session ships only the legibility surface over the
   existing grant rows.

**The principal taxonomy the workspace must accommodate (operator's framing):**
MCPs (foreign LLMs: claude.ai, ChatGPT), multiple humans, 3rd-party tools
(Linear, Slack, Copilot, Cursor) via MCP/API. The uniform consult is built to carry
all of these with zero gate change per new principal type — only a grant row + a
principal-id mapping entry.

---

## 6. ⚠ ADJACENT FINDING — the MCP topology lock was DORMANT (latent gate bug)

**Discovered while wiring the grant-consult; confirmed; fixed in this session
(operator-approved, flagged as a distinct behavior change — NOT folded into the
byte-identical grant-consult).**

**The bug:** the gate's MCP topology lock (permission.py:257) and the class
resolver (`_caller_class`, workspace.py:1768) both matched the MCP caller with
**exact** `caller_identity == "yarnnn:mcp"`. But the LIVE MCP caller_identity is
**room-qualified** `yarnnn:mcp:<client>` (ADR-288 D1 — the cross-LLM provenance
stamp; `resolve_request_client` resolves the room name for all 13 registered
clients). So the exact check **missed every real MCP caller**:

- **Gate (permission.py:257):** the qualified MCP write skipped the MCP branch and
  fell to the `non_reviewer_caller` free-pass (line 324) → **APPLY**. A foreign-LLM
  WriteFile to a locked root (`governance/`, `persona/`, `constitution/`, `system/`)
  was **NOT blocked**. The MCP topology lock has been effectively dormant for the
  live path.
- **`_caller_class` (1768):** the qualified MCP caller fell through to the default
  → classified as **`agent`** (not `mcp`).

**Why it matters:** the handler does NOT independently gate (workspace.py:776 — "No
inline gate here"), so the gate IS the sole enforcement. The dormant lock is a
foreign-LLM write-escalation, live precisely as external-LLM principals are being
onboarded.

**The fix:** widen both matchers to `startswith("yarnnn:mcp")` (mirrors the other
class matchers, which already use `startswith`). This **activates** the
ADR-320-intended MCP lock. **This is a deliberate behavior change**: a
client-qualified MCP write to a locked root now DENYs (was: APPLY). The class
default for `mcp` vs the previously-misapplied `agent` produces the SAME lock
decision on the live roots (both lock governance/contract/constitution/persona/
system; both allow operation/+inbound/), so no OTHER MCP behavior shifts — only the
lock activates. A dedicated regression asserts the new DENY.

---

## 7. VALIDATION RESULTS (substrate-receipts)

**Unit/gate (the floor):** `test_adr373_grant_consult.py` — 20/20 PASS. Full gate
battery `test_adr320 + test_adr307_{taxonomy,platform} + test_adr373_rekey +
test_adr373_grant_consult` — **82/82 PASS**. Adjacent battery (288/293/337/352/364/
366) green.

**Integration (real `resolve_permission` gate):**
- operator → governance/ : `apply` (unchanged)
- MCP(qualified) → governance/ : `deny | mcp_topology_locked` (the activated lock, e2e)
- MCP(qualified) → operation/ : `apply | mcp_caller_unlocked_path` (commons open)
- MCP → ReadFile : `apply | read_only` (reads never gate)
- reviewer → governance/ : `deny | topology_locked`; reviewer → persona/ : `apply` (autonomous)

**Live N=1 byte-identical battery (the confidence mark):** against the live DB,
exercised `_is_path_locked_for_principal` for ALL **11 real owner grants × 9 paths =
99 checks → 0 mismatches** vs `_is_path_locked`. Every live workspace's owner
behaves BYTE-IDENTICALLY after the consult. Receipt: all 11 owner grants confirmed
`scopes NULL` (fall-through branch) + `granted_by=system:adr373-backfill`.

**Live MCP-fix validation:** against a real workspace + a real OAuth client_id (no
foreign-llm grant row, 0 today): `caller_class=mcp`, MCP→governance/ **locked**,
MCP→persona/ **locked**, MCP→operation/ **open**. The dormant lock is now live
against production identities.

**KNOWN, NAMED VALIDATION GAP (not faked):** the competing-principal case — a SECOND
real principal with an explicit *narrowing* grant actually being denied/allowed
end-to-end through the live gate — is **untestable until a second real principal
exists** (ADR-373 D5 / triple-check R4). It is covered by UNIT tests (the
grant-honored allow-list, mocked grant rows) but has no LIVE receipt, because no
non-owner grant row exists in production yet. This is the honest edge: the consult
machinery is proven correct in isolation; its multi-principal *effect* lights up the
moment the first narrowing grant is written (the post-launch provisioning, separate
ADR). Do NOT claim the multi-principal authorization is live-validated — it is
build-complete and unit-proven, awaiting a real second principal.
