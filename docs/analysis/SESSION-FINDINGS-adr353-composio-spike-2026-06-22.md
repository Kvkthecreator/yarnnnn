# SESSION FINDINGS — ADR-353 Composio Driver Spike (2026-06-22)

**Hat:** B (external developer of the system) → recommends a Hat-A decision. This
is a **spike, not a migration**. No first-party client deleted. No default
flipped. The Composio path is built behind a feature flag (default OFF), proven,
and reported here. **Whether to adopt — and then delete first-party code — is
KVK's decision, AFTER this spike.**

**Reference:** [ADR-353](../adr/ADR-353-composio-as-driver-backend.md) (Status:
Proposed) §12 decision criteria. **Discourse base:**
[positioning-discourse §6.6](positioning-discourse-seat-as-asset-2026-06-22.md)
("drive the mechanical, never rent the judgment").

**Artifacts produced this session:**
- `api/services/composio_driver.py` — the swappable driver (new).
- `api/services/platform_tools.py` — flag-gated branch in `handle_platform_tool`
  + `_route_via_composio` Phase-1 token path (+82 LOC, additive; no deletions).
- `api/test_adr353_composio_isolation.py` — multi-tenant HARD GATE (2 tests).
- `api/test_adr353_composio_parity.py` — parity + no-silent-success + flag (15 tests).

**Test result:** **17/17 PASS** (`api/venv/bin/python -m pytest
api/test_adr353_composio_isolation.py api/test_adr353_composio_parity.py -q`).
No regressions introduced (proven by stash-and-rerun below).

---

## 1. Coverage matrix (ADR-353 §12.1)

For the currently-connected platform set, confirmed that Composio exposes the
**specific verbs our capabilities use**, not merely the platform. Source: Composio
toolkit docs, accessed 2026-06-22 (see §10 Sources). Slug strings are version-
sensitive (see the finding below the matrix); the spike pins them in
`_COMPOSIO_ACTION_MAP` so the kernel never sees a Composio slug.

### Slack — IN SPIKE SCOPE (the only wired provider)

| YARNNN tool | Slack API | Composio action (pinned) | Covered | Managed OAuth |
|---|---|---|---|---|
| `platform_slack_list_channels` | conversations.list | `SLACK_LIST_ALL_CHANNELS` | ✅ | ✅ |
| `platform_slack_get_channel_history` | conversations.history | `SLACK_FETCH_CONVERSATION_HISTORY` | ✅ | ✅ |
| `platform_slack_send_message` (operator DM) | chat.postMessage | `SLACK_SEND_MESSAGE` | ✅ | ✅ |
| `platform_slack_send_to_channel` (audience) | chat.postMessage | `SLACK_SEND_MESSAGE` | ✅ | ✅ |

**Slack coverage: 4/4 verbs. Composio managed OAuth app — NO bring-your-own
developer credentials required.**

### Notion — recorded, NOT wired (allowlist excludes)

| YARNNN tool | Composio action | Covered | Managed OAuth |
|---|---|---|---|
| `platform_notion_search` | `NOTION_SEARCH_NOTION_PAGE` | ✅ | ✅ |
| `platform_notion_get_page` | `NOTION_GET_PAGE_MARKDOWN` | ✅ | ✅ |
| `platform_notion_create_page` | `NOTION_CREATE_NOTION_PAGE` | ✅ | ✅ |
| `platform_notion_append_block` | `NOTION_APPEND_TEXT_BLOCKS` | ✅ | ✅ |
| `platform_notion_create_comment` | `NOTION_CREATE_COMMENT` | ✅ | ✅ |

**Notion coverage: 5/5 verbs, managed OAuth (also supports API-key auth).**

### GitHub — recorded, NOT wired (allowlist excludes)

| YARNNN tool | Composio action (expected) | Covered | Managed OAuth |
|---|---|---|---|
| `platform_github_list_repos` | `GITHUB_LIST_REPOSITORIES_FOR_THE_AUTHENTICATED_USER` | ✅ (likely) | ✅ |
| `platform_github_get_issues` | `GITHUB_LIST_REPOSITORY_ISSUES` | ✅ (likely) | ✅ |
| `platform_github_get_repo_metadata` | `GITHUB_GET_A_REPOSITORY` | ✅ (likely) | ✅ |
| `platform_github_get_readme` | `GITHUB_GET_A_REPOSITORY_README` | ✅ (likely) | ✅ |
| `platform_github_get_releases` | `GITHUB_LIST_RELEASES` | ✅ (likely) | ✅ |

**GitHub: managed OAuth confirmed; toolkit advertises 867 tools.** The five
specific slugs were not all visible in the truncated public doc excerpt — marked
"likely" and to be **confirmed against the live tool-enum** (`GET /api/v3/tools`
filtered by toolkit) when a GitHub connection is wired. Not a blocker for the
spike (Slack-only); a per-platform confirmation step before GitHub goes in scope.

### Finding: Composio action slugs are unstable across versions

The same Slack chat.postMessage action surfaced under **three different slugs**
across Composio doc versions: `SLACK_SEND_MESSAGE`, `SLACK_CHAT_POST_MESSAGE`,
`SLACK_SENDS_A_MESSAGE_TO_A_SLACK_CHANNEL`. This is exactly the
dependency-fragility risk ADR-353 §10 names. **Mitigation, already implemented:**
the verb→slug map lives in ONE table (`_COMPOSIO_ACTION_MAP`) inside the driver;
the kernel contract is the YARNNN tool *name*, never the Composio slug. A slug
rename is a one-line driver edit, invisible to every caller. Composio's execute
endpoint also accepts a `version` field (defaults to "latest") — pinning a
version is a follow-on hardening option.

**Coverage verdict: PASS for Slack (the spike scope). No stop-condition triggered.**

---

## 2. Consumption-protocol decision (ADR-353 spike task 2)

**Decision: consume Composio's REST API (`POST /api/v3/tools/execute/{slug}`),
NOT its MCP interface.**

| | MCP interface | REST/SDK (chosen) |
|---|---|---|
| Protocol cleanliness | ✅ swappable with any MCP server | ⚪ Composio-shaped wire |
| Statefulness | ❌ client session / handshake / discovery per use | ✅ stateless single POST |
| Return shape | streamed tool-call envelope | ✅ synchronous `{successful, data, error}` |
| Surface consumed | agent-facing routing/ranking (the §10 "learning loop" face) | ✅ pure execution endpoint |
| Coupling | lower at the wire | higher at the wire |

**Rationale (one paragraph):** the swappability ADR-353 demands is provided by
*our own driver interface* (`composio_driver.execute`), not by the wire protocol
underneath — so the protocol-cleanliness argument for MCP buys us nothing the
driver wrap doesn't already give us, while costing a client-session lifecycle per
call. Decisively, Composio's MCP face is the **agent-facing routing/learning
surface** — exactly the part §2/§10 say never to consume ("drive the mechanical,
never rent the judgment"). The REST execute endpoint is the opposite: opinion-
free pure hands, a single stateless POST returning the synchronous
`{successful, data, error}` shape we map directly to the `_handle_*` return
shape. We take REST; whether the driver speaks REST or MCP underneath is an
implementation detail invisible to `handle_platform_tool`.

---

## 3. Architecture proof — Composio is an executor BEHIND the gate, never a gate

File-grounded confirmation of every hard invariant:

1. **Gate untouched (Invariant 1).** `resolve_permission`
   (`api/services/primitives/permission.py`) runs inside `execute_primitive`
   (`registry.py:812`) **before** `handle_platform_tool` is ever called. It keys
   on the **tool name** via `is_consequential_platform_tool(name)` /
   `consequential_platform_family(name)` (`platform_tools.py:2800-2819`) — which
   is **unchanged by which driver executes**. The driver branch lives strictly
   inside `handle_platform_tool`, downstream of the gate. `permission.py`,
   `authored_substrate.py::write_revision`, and
   `orchestration.py::capability_available` were **not modified** (verified).
2. **Attribution stays kernel (Invariant 2).** `handle_platform_tool` returns a
   plain result dict; its callers (`registry.execute_primitive`,
   `services/harvest.py`, `services/primitives/sync_platform_state.py`) author
   the outcome via `write_revision` as `agent:{slug}` / `system:*`. The driver
   never touches the substrate. Result-key parity (§4) keeps those callers byte-
   compatible.
3. **Capital out of scope (Invariant 3).** `driver_enabled_for` **hard-excludes**
   `trading` + `commerce` even if mis-added to the env allowlist
   (`test_capital_family_never_enabled` ✅). The action map contains zero capital
   verbs.
4. **No silent success (Invariant 4).** §5 — every failure mode maps to
   `{success: False}`.
5. **Swappable (Invariant 5).** Reverting is `COMPOSIO_DRIVER_ENABLED=false` —
   one env change, no code change (`test_revert_is_config_change` ✅). Switching
   aggregators = a sibling module with the same `execute` signature;
   `handle_platform_tool` is the only call site.

---

## 4. Parity result (ADR-353 §12.2)

Identical YARNNN inputs through the driver yield **the same result-dict keys** as
the first-party `_handle_slack_tool`, so callers are byte-compatible:

| Verb | First-party result keys | Driver result keys | Match |
|---|---|---|---|
| `send_to_channel` | `{ts, channel}` + top-level `message` | `{ts, channel}` + `message` | ✅ |
| `list_channels` | `{channels:[{id,name,is_private,is_archived}], count}` | identical | ✅ |
| `get_channel_history` | `{messages:[{user,text,ts,reactions?}], count}` | identical | ✅ |

The driver's result adapter re-derives **exactly** the first-party fields from
Composio's `data` (drops no-id channels, drops empty-text messages, applies the
`name_normalized` fallback — all matching first-party behavior). Input field
remapping (`channel_id`→`channel`) verified at the wire
(`test_arguments_mapped_to_composio_shape` ✅).

**Latency:** not measured against a live Composio account in this spike (no
`COMPOSIO_API_KEY` provisioned — env not set per spike charter). Expected: one
extra network hop (YARNNN → Composio → Slack) vs first-party (YARNNN → Slack).
The driver timeout matches the first-party client (30s total / 10s connect). A
live A/B latency sample is a pre-ratification follow-on, cheap to run once a key
exists. **This is the one §12 criterion not closed in-spike** (see §8).

---

## 5. Error-shape result — no silent success (Pitfall #4)

Every Composio failure mode maps to `{success: False, result: None, error: ...}`
— **never** `success: True` on a failed action. Verified:

| Failure mode | Driver outcome | Test |
|---|---|---|
| HTTP 401 (auth failure) | `success: False`, error contains "401" | ✅ |
| HTTP 429 (rate limit) | `success: False`, error contains "429" | ✅ |
| `successful: false` body, HTTP 200 (Slack `ok=false` analogue) | `success: False`, error = Composio message | ✅ |
| Timeout | `success: False`, "timed out" | ✅ |
| Unmapped verb | `success: False`, "unsupported action" | ✅ |
| Missing `COMPOSIO_API_KEY` | `success: False`, "not configured" | ✅ |
| Missing platform token | `success: False`, "token" | ✅ |
| No active connection | `success: False`, loud + no Composio call | ✅ |

A `{success: False}` flows to the gate's QUEUE/retry path exactly as a first-party
failure does — the failure surfaces, never a false outcome into the substrate.
**No silent fallback:** when the driver is enabled for a provider it OWNS that
provider; a driver failure is returned as a failure, not masked by a second
attempt down the first-party path (the "reports success with 0 items" class of
bug is structurally impossible here).

---

## 6. Multi-tenant isolation result — THE HARD GATE (ADR-353 §12.6) — PASS

The specific failure that bites *after* implementation: an aggregator that runs
every action as ONE account leaks credentials across tenants when serving N
customers. **Proven structurally isolated:**

Two distinct users (`user-A`, `user-B`), each with their own active Slack
connection storing their own encrypted token. With the flag ON, the **same**
action for each user:

- carries **only that user's** bearer token to Composio — A's call carries
  `Bearer xoxb-AAAA-token`, B's carries `Bearer xoxb-BBBB-token`;
- the other tenant's token **never appears** in the request body (asserted on the
  serialized JSON);
- `user_id` (Composio entity) matches the caller — `user-A` / `user-B`;
- a user with **no** connection gets a loud failure, never another user's creds.

**Why this is structural, not incidental:** Phase 1 (ADR-353 §7) injects each
user's own decrypted token **per call** via `custom_auth_params`. Composio holds
**zero tenant auth state** — there is no Composio-stored connected-account
credential that *could* be mixed. Composio entity == YARNNN `user_id`. This holds
regardless of whether Composio is "embedded" or "personal-automation" category,
because YARNNN owns the token fetch and scopes it by `user_id` exactly as the
first-party path does.

**Isolation verdict: PASS. No stop-condition triggered.**

> Note (Hat-B honesty): this is proven at the **wire** with a mocked Composio
> endpoint — the driver provably sends each user only their own bearer + entity.
> It does **not** yet exercise two *real* Composio-connected Slack accounts
> end-to-end (needs `COMPOSIO_API_KEY` + two live test workspaces). The wire-
> level proof is the load-bearing one (it shows YARNNN can never *send* a crossed
> credential); the live two-account run is the confirmation step before any
> default flip — staged, not a blocker for the spike conclusion.

---

## 7. Cost note (ADR-353 §12.3 — note only, no metering built)

Composio pricing (accessed 2026-06-22):

- **Free:** 20,000 tool calls / month, $0.
- **$29/mo:** 200,000 tool calls / month; overage $0.299 / 1,000.
- **$229/mo:** 2,000,000 tool calls / month; overage $0.249 / 1,000.
- Premium tools (search APIs, sandboxes, ML inference) priced separately — **none
  of our Slack/Notion/GitHub read+external-write verbs are premium.**

**Implication:** YARNNN's "few-but-valuable action" profile makes this trivially
cheap — the entire alpha cohort's external actions fit inside the **free tier**.
One Composio tool call == one YARNNN external action (1:1; reads + sends each
count once).

**How it would meter (ADR-291) — note only:** the canonical cost ledger is
`execution_events.cost_usd` (sole ledger, ADR-291; written via
`services/telemetry.py`). A Composio action cost would be recorded as an additive
`cost_usd` component on the `execution_events` row for the invocation that fired
the action — the same row that already carries model cost. No new table, no
parallel ledger. **Not built in this spike** (per charter) — recorded as the
integration point.

---

## 8. Render-service parity note (ADR-353 §8 — documented, NOT set)

`COMPOSIO_API_KEY` (and any `COMPOSIO_*` config: `COMPOSIO_DRIVER_ENABLED`,
`COMPOSIO_PROVIDER_ALLOWLIST`, optional `COMPOSIO_API_BASE`) belongs on:

| Service | Needs it? | Why |
|---|---|---|
| **yarnnn-api** (`srv-d5sqotcr85hc73dpkqdg`) | ✅ | chat/addressed paths take platform actions |
| **yarnnn-unified-scheduler** (`crn-d604uqili9vc73ankvag`) | ✅ | recurrence invocations take platform actions |
| yarnnn-mcp-server (`srv-d6f4vg1drdic739nli4g`) | ❌ | read-only context surface |
| yarnnn-render (`srv-d6sirjffte5s73f90pfg`) | ❌ | independent Docker output gateway |

**Classic drift failure** (CLAUDE.md Pitfall #4 sibling): adding the var to the
API and forgetting the scheduler — the scheduler would then silently fall back
to the disabled-driver path. Set both in one `update_environment_variables` pass.
**No production env was set in this spike** (default OFF everywhere; the driver
self-reports "not configured" when the key is absent).

---

## 9. §12 criteria scorecard + recommendation

| # | Criterion | Status |
|---|---|---|
| 12.1 | Coverage check (specific verbs) | ✅ PASS — Slack 4/4, Notion 5/5, GitHub managed-OAuth+867 tools (slugs to confirm live) |
| 12.2 | Parity spike (one platform, keep first-party) | ✅ result-key parity proven; ⚠️ live latency A/B deferred (no key) |
| 12.3 | Cost model | ✅ free tier covers alpha; 1:1 action metering into `execution_events.cost_usd` |
| 12.4 | Token-model security review (Phase 1 plaintext-in-process) | ✅ Phase 1 implemented + isolation-proven; Phase-2 (Composio-managed auth) explicitly NOT entered |
| 12.5 | Swappability proof | ✅ revert = one env var; aggregator swap = sibling module |
| 12.6 | Multi-tenant isolation (HARD GATE) | ✅ PASS at the wire (structural, per-call token injection) |

### Recommendation: **RATIFY-LEANING — adopt the seam; gate the default flip on two live confirmations.**

The spike clears the conceptual and structural bar decisively. Every hard
invariant holds: the gate, attribution, and capability-gating are untouched;
Composio is a pure executor behind the existing contract; the multi-tenant HARD
GATE passes structurally; failures never silently succeed; reverting is a config
change. The driver-agnostic seam is real (Composio is one `execute`
implementation, not a dependency baked into the kernel).

**Two confirmations remain before flipping any default to ON in production** —
both cheap, both requiring a provisioned `COMPOSIO_API_KEY` + a live test Slack
account, neither a design risk:

1. **Live end-to-end run** of all four Slack verbs against a real Composio-
   connected account (confirms the pinned slugs + argument shapes against the
   live `latest` version — the slug-instability finding makes this worth one real
   round-trip).
2. **Live two-account isolation run** (the wire proof, re-confirmed against two
   real Composio entities) + a **latency A/B sample** vs first-party.

**Recommended path:** keep the flag OFF on main; merge the spike (both paths
coexist, default OFF, zero behavior change for operators); KVK provisions a
Composio key in a non-production context; run the two confirmations; THEN decide
the default flip and, separately, whether to delete first-party Slack client code
(Singular Implementation — a clean post-ratification change, NOT done in this
session).

**Do NOT** in this session: flip any default, set production env, delete any
first-party client, or enter Phase-2 (Composio-managed auth) — that last is a
separate token-custody security review (ADR-353 §7).

---

## 10. Sources (accessed 2026-06-22, input only)

- [Slack — Composio Toolkit](https://docs.composio.dev/toolkits/slack)
- [Slack MCP Server — Composio](https://composio.dev/toolkits/slack)
- [Slackbot — Composio Toolkit](https://docs.composio.dev/toolkits/slackbot)
- [Notion — Composio Toolkit](https://docs.composio.dev/toolkits/notion)
- [GitHub — Composio Toolkit](https://docs.composio.dev/toolkits/github)
- [Execute tool — Composio API Reference](https://docs.composio.dev/api-reference/tools/post-tools-execute-by-tool-slug)
- [Custom Auth Parameters — Composio Docs](https://docs.composio.dev/docs/custom-auth-params)
- [Injecting Custom Credentials — Composio](https://docs.composio.dev/auth/injecting-custom-credentials)
- [Pricing — Composio](https://composio.dev/pricing)
- [Composio free tier (20K tool calls) — FreeTier.co](https://freetier.co/directory/products/composio)

---

## Appendix — regression proof

The two failures in `tests/test_platform_runtime_capabilities.py`
(`test_capability_scoped_tools_follow_connected_provider`,
`test_headless_tool_resolution_uses_agent_capabilities`) are **pre-existing**,
unrelated to this spike: they assert stale expectations about tool *surfacing*
(`get_platform_tools_for_capabilities`), while the spike touches only the
*dispatch* path (`handle_platform_tool`). Proven by stashing the spike change and
re-running — both fail identically with the change removed. The other 34 tests in
that file pass. The spike introduces **zero regressions**.
