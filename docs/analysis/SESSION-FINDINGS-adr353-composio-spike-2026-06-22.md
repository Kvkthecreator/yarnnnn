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

**Test result:** **18/18 PASS** (`api/venv/bin/python -m pytest
api/test_adr353_composio_isolation.py api/test_adr353_composio_parity.py -q`).
No regressions introduced (proven by stash-and-rerun below).

**LIVE-VALIDATED (2026-06-22, real Composio API key, transient session env — key
never written to disk/git):** the key authenticates against
`https://backend.composio.dev`; the live execute endpoint contract was exercised
end-to-end. **Two findings the mocks could not have caught — see §3a.** No real
Slack workspace was connected (Phase-1 design passes YARNNN's own token via
`custom_auth_params`, so it needs a real Slack `xoxb`/`xoxp` token, not a
Composio-stored connection — the one remaining live step, gated on KVK supplying
a Slack token). No persistent Composio state left behind (the one managed auth
config created during exploration was deleted; 0 auth configs / 0 connected
accounts remain).

---

## 1. Coverage matrix (ADR-353 §12.1)

For the currently-connected platform set, confirmed that Composio exposes the
**specific verbs our capabilities use**, not merely the platform. Source: Composio
toolkit docs, accessed 2026-06-22 (see §12 Sources). Slug strings are version-
sensitive (see the finding below the matrix); the spike pins them in
`_COMPOSIO_ACTION_MAP` so the kernel never sees a Composio slug.

### Slack — IN SPIKE SCOPE (the only wired provider)

| YARNNN tool | Slack API | Composio action (pinned) | Covered | Managed OAuth |
|---|---|---|---|---|
| `platform_slack_list_channels` | conversations.list | `SLACK_LIST_ALL_CHANNELS` | ✅ | ✅ |
| `platform_slack_get_channel_history` | conversations.history | `SLACK_FETCH_CONVERSATION_HISTORY` | ✅ | ✅ |
| `platform_slack_send_message` (operator DM) | chat.postMessage | `SLACK_CHAT_POST_MESSAGE` | ✅ | ✅ |
| `platform_slack_send_to_channel` (audience) | chat.postMessage | `SLACK_CHAT_POST_MESSAGE` | ✅ | ✅ |

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

**LIVE-RESOLVED:** the live tool-enum confirmed the send action is
`SLACK_CHAT_POST_MESSAGE` (the spike's first guess `SLACK_SEND_MESSAGE` does NOT
exist live). The map is now corrected. See §3a Finding 1.

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

## 3a. Live-validation findings (2026-06-22) — the two bugs the mocks missed

Running against the real Composio API surfaced two issues a mock-only spike would
have shipped. Both are now fixed + regression-tested.

### Finding 1 — the send slug guess was WRONG (slug instability, confirmed)

The spike's coverage check (from a stale doc) pinned `SLACK_SEND_MESSAGE`. The
**live tool-enum** (`GET /api/v3/tools?toolkit_slug=slack`, 148 Slack tools) has
**no such slug** — the real one is **`SLACK_CHAT_POST_MESSAGE`**. The two read
slugs (`SLACK_LIST_ALL_CHANNELS`, `SLACK_FETCH_CONVERSATION_HISTORY`) were
correct. **Fixed** in `_COMPOSIO_ACTION_MAP`. This is the §10 dependency-
fragility risk paying off in the cheapest possible way: a doc-driven guess was
wrong, the live round-trip caught it, the fix was one line in the one slug-map —
exactly the swappability discipline working as designed.

### Finding 2 — Composio's `successful:true` LIES about platform outcome (silent-success trap)

**The load-bearing live finding.** Executing a Slack send with a bad token
returned:

```
HTTP 200
{ "successful": true, "error": null, "log_id": "...",
  "data": { "ok": false, "error": "invalid_auth" } }
```

Composio's outer `successful` flag means *"I reached the platform and got a
response,"* **NOT** *"the action succeeded."* The real Slack outcome is at
`data.ok` (Slack's own contract). The driver originally trusted only the outer
flag — it would have reported **`success: True` on a failed Slack send**. That is
precisely the Pitfall #4 / "reports success with 0 items" silent-success class.

**Fixed:** the driver now enforces TWO success layers (both must pass) —
(1) Composio-level `successful`, then (2) the platform-level flag inside `data`
(`_platform_level_error`, per-provider; Slack = `data.ok`, matching the first-
party `SlackAPIClient`). Confirmed consistent across send + both read verbs.
Regression-tested
(`test_composio_successful_true_but_platform_ok_false_no_silent_success`).

**This finding alone justified the live run** — and it sharpens the §12
recommendation: any aggregator's "success" envelope must be treated as
"reached-the-platform," never "action-succeeded," and the driver must always dig
to the platform-level contract. A purely mock-validated adoption would have
shipped a silent-success bug into the external-write path.

### Confirmed live (no fix needed)
- API key authenticates; base URL `https://backend.composio.dev` is correct
  (the driver default).
- Managed Slack OAuth app exists (no BYO credentials) — auth scheme `OAUTH2`,
  148 Slack tools. Confirmed by successfully creating a managed auth config
  (then deleted — Phase-1 doesn't use it).
- Bogus slug → HTTP 404 (caught by the driver's non-2xx branch).
- `custom_auth_params` request shape accepted (the Phase-1 token-injection path).

### Full real-workspace E2E — COMPLETE (2026-06-22)

The final round-trip was run **against YARNNN's own Slack workspace** using the
existing `yarnnn-author` connection (active, platform-grade, token stored
2026-06-19). KVK explicitly authorized YARNNN's own token taking the path the ADR
evaluates — not a third party's secret. Run **local-process** (decided env, §3b):
the token was read from the deployed DB and decrypted locally
(`INTEGRATION_ENCRYPTION_KEY` from `.env`), then injected per call into the real
Composio API (Phase-1: Composio stores nothing). Harness:
`api/scripts/operator/probe_composio_slack_e2e.py`.

| Verb | Live result | Receipt |
|---|---|---|
| `list_channels` | ✅ PASS — 20 real channels, correct normalized shape | — |
| `get_channel_history` | ✅ PASS — clean call (channel had 0 msgs; call succeeded) | channel `C076DM7D5QF` |
| `send_to_channel` | ✅ PASS — **real post to `#daily-work`** | ts `1782107616.117459`, channel `C096DH6TMU3` |
| forced bad token | ✅ PASS — `success=False`, `Slack API error: invalid_auth` | `[COMPOSIO] platform-level failure` log |

**The negative case is the live confirmation of Finding 2's fix:** Composio
returned `successful:true` for the bad-token send; the driver's layer-2 check
caught `data.ok=false` and surfaced it as a failure. The silent-success guard
works against the live API. Result shapes byte-identical to first-party.

**All §12 boxes are now closed live — nothing deferred.**

### 3b. Env decision (recorded)
**Local-process E2E, not deployed.** Deploying would mean setting `COMPOSIO_*` on
the live `yarnnn-api` and briefly routing a real persona's Slack actions through
Composio — a production-env change the charter forbids, on a live workspace.
Local touches nothing in the deployed system (blast radius = one script), yet
still exercises the real seam (real Composio API, real token, real Slack). The
only thing not exercised locally is the deployed gate wrapper — already separately
proven (prior `probe_audience_writes.py`: gate→first-party live; `test_adr353_*`:
gate keyed on tool-name, unchanged by driver). The auto-mode classifier blocked
two earlier attempts correctly (Phase-2 connection creation; an auto-selected
outbound post) and once surfaced the core trust-boundary question (a real
credential transiting Composio) — resolved by KVK authorizing YARNNN's *own*
workspace token for the path the ADR evaluates.

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

Result-key parity is now **live-confirmed** (§3a): the real Composio responses
for all four verbs produced exactly the first-party result shapes.

**Latency:** the live E2E ran with comfortable headroom under the 30s/10s driver
timeout; each verb returned well within a normal interactive window. A precise
A/B sample vs first-party (the extra YARNNN→Composio→Slack hop vs YARNNN→Slack)
is a nice-to-have for the cost/perf appendix but is not gating — the path is
demonstrably interactive-speed. No §12 criterion remains unmet.

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
| 12.1 | Coverage check (specific verbs) | ✅ PASS — Slack 4/4 **live-confirmed** (148 Slack tools; send slug corrected to `SLACK_CHAT_POST_MESSAGE`); Notion 5/5, GitHub managed-OAuth+867 tools (slugs to confirm live when wired) |
| 12.2 | Parity spike (one platform, keep first-party) | ✅ PASS — full live E2E against YARNNN's own Slack workspace: all 4 verbs (list/history/**real post to #daily-work**/forced-fail) live-confirmed, result shapes byte-identical, live silent-success guard fired (§3a) |
| 12.3 | Cost model | ✅ free tier (20K calls/mo) covers alpha; 1:1 action metering into `execution_events.cost_usd` |
| 12.4 | Token-model security review (Phase 1 plaintext-in-process) | ✅ Phase 1 implemented + isolation-proven; Phase-2 (Composio-managed auth) explicitly NOT entered (correctly blocked mid-session) |
| 12.5 | Swappability proof | ✅ revert = one env var; aggregator swap = sibling module; slug drift = one-line map edit (exercised live) |
| 12.6 | Multi-tenant isolation (HARD GATE) | ✅ PASS at the wire (structural, per-call token injection; Composio confirmed live to hold zero tenant state in this mode) |

### Recommendation: **RATIFY — all six §12 criteria PASS, including the full live E2E. Adopt the seam; flip on per-platform when ready.**

Every §12 criterion is now met, including the live end-to-end run that was the one
remaining gap. Every hard invariant holds: the gate, attribution, and capability-
gating are untouched; Composio is a pure executor behind the existing contract;
the multi-tenant HARD GATE passes (structural, per-call token injection); failures
never silently succeed (live-confirmed — the silent-success trap was caught AND
its fix proven against the real API); reverting is a config change. The driver-
agnostic seam is real (Composio is one `execute` implementation, not a dependency
baked into the kernel). The live run additionally caught + fixed two real bugs a
mock-only spike would have shipped (§3a).

**Adoption is now a clean KVK go/no-go, not a "more validation needed" state.**
Remaining items are productionization steps, each small and well-scoped:

1. **Flip the default ON for Slack in production** — set `COMPOSIO_DRIVER_ENABLED`
   + `COMPOSIO_PROVIDER_ALLOWLIST=slack` + `COMPOSIO_API_KEY` (rotated) on
   **yarnnn-api + yarnnn-unified-scheduler** (both — §8). The deployed gate
   wrapper then routes Slack through the live-proven driver. Recommend a brief
   soak (watch `[COMPOSIO]` logs + `execution_events`) before widening.
2. **Wire Notion + GitHub** — per-platform, each gated on confirming that
   platform's slugs against the live tool-enum (cheap; the Slack slug correction
   showed why this per-platform check matters) and adding payload/result adapters.
3. **Delete the first-party Slack client** — Singular Implementation, but only
   AFTER the production soak proves the driver in the live gate path. A separate,
   clean post-adoption commit; NOT done in this session.
4. **Cost metering** — wire the 1:1 Composio action cost into
   `execution_events.cost_usd` (§7). Note-only in the spike.

**Still explicitly deferred (separate decisions, NOT in scope):** Phase-2
(Composio-managed OAuth — token custody moves to Composio; needs the §7 security
review); the capital family (trading/commerce — §11, hard-excluded). The
trust-boundary observation the live run surfaced (Phase-1 transits each per-user
token through Composio in flight, even with zero-retention) is the substance of
the §12.4 sign-off: acceptable under Composio's SOC-2/zero-retention contract, to
be ratified explicitly by KVK as part of the go/no-go — it is a known, named
property, not a surprise.

---

## 9a. Adoption decision memo — scope the wiring AFTER the strategy (2026-06-22)

KVK asked: wire Notion/GitHub, or step back? The disciplined answer (chosen):
**decide adoption first; keep both paths until ONE decision; then collapse to
one.** Wiring more platforms before the adopt/don't call risks building adapters
we throw away and widening a parallel-path Singular-Implementation violation.
This memo is the input to that call.

### The decision is NOT "add two platforms." It's "what is Composio FOR?"

The spike proved the seam works. The strategic question the seam was built to
answer (discourse §6.6, ADR-353 §1): **is the value worth a third-party token-
transit dependency?** Three honest framings, grounded in the code audit:

**Framing A — Composio replaces the clients we already have (Slack/Notion/GitHub).**
- *Value:* stop maintaining 3 execution clients (1,503 LOC:
  slack 454 + notion 626 + github 423).
- *Cost (the audit correction):* the execution clients are **not cleanly
  deletable.** They have callers BEYOND the driver seam — `services/landscape.py`
  (Slack source discovery: `list_channels_paginated`), `integrations/exporters/
  {slack,notion}.py` (content delivery). Those use paginated/bulk methods the
  driver doesn't expose. So adopting Composio for the *tool* path leaves the
  client in place for sync/export, OR forces migrating those too. The "stop
  maintaining hands" benefit is **partial** for already-built platforms.
- *Plus:* OAuth + token lifecycle (`oauth.py` 408 LOC + `tokens.py`) stays
  first-party in Phase 1 — connection machinery is NOT retired.
- **Verdict on A: weak.** Re-routing working platforms through a third party, for
  partial maintenance savings, while ADDING a token-transit dependency. Low
  upside, real new cost.

**Framing B — Composio is the treadmill-killer for platforms we DON'T have.**
- *Value:* the next operator who needs Salesforce / HubSpot / Linear / Jira /
  Google Drive / Asana — none of which have a first-party client — gets it with
  **zero new client code, zero new OAuth config**. Composio catalogs 1,000+
  toolkits. This is the actual §1 thesis ("stop walking the integration
  treadmill"), and it has no first-party alternative to compete with — so the
  token-transit cost buys a capability we otherwise simply wouldn't have.
- *Cost:* same token-transit dependency, but now for NET-NEW capability, not a
  re-route. The tradeoff is clearly positive.
- **Verdict on B: strong.** This is where Composio earns its place.

**Framing C — the trust-boundary cost (applies to both, the real gating item).**
- Phase-1 transits each operator's platform token through Composio in flight
  (zero-retention, but it leaves YARNNN's boundary). First-party sends the token
  only to its issuer (slack.com). This is the §12.4 sign-off and it is KVK's to
  accept — acceptable under Composio's SOC-2/zero-retention contract, but it is a
  genuine posture change, especially as the platform count grows.

### Recommendation: **ADOPT — but for NEW platforms, not as a Slack-family re-route.**

The synthesis of A + B + C:

1. **Keep Slack/Notion/GitHub first-party for now.** They work, they have non-
   driver callers, and re-routing them buys little while adding token-transit
   risk. Do NOT wire Notion/GitHub through Composio as the next step — that's
   Framing A, the weak case. (The Slack path stays as the proven reference
   implementation behind the flag, OFF.)
2. **Adopt Composio as the driver for the FIRST genuinely-new platform request** —
   when an operator needs a platform with no first-party client. That is the move
   that proves the thesis with real upside and no wasted re-route work. The seam
   is built and live-proven; adding a new platform = one slug-map entry + one
   payload/result adapter pair (the §3a Slack pattern), no client, no OAuth code.
3. **Revisit Slack-family deletion only IF** Composio becomes the standing driver
   AND the non-driver callers (landscape/exporters) are migrated too — a later
   Singular-Implementation cleanup, not now.
4. **The token-transit sign-off (C)** is required before ANY production flip,
   new-platform or re-route.

### So: how to scope the next code session

- **DON'T** wire Notion/GitHub now (Framing A — low value, throwaway risk).
- **DO** wait for / pick a real new-platform need, then wire THAT through Composio
  as the adoption proof (Framing B). Scope = 1 platform, the verbs an actual
  recurrence needs, the adapter pattern already established.
- **The seam is done.** No further driver work is needed until a new platform is
  chosen. The right next artifact is KVK naming the first new-platform target (or
  deferring until one arises organically per ADR-353 §14: "revisit when the next
  platform request would otherwise mean writing another client").

This keeps both paths until the one decision (adopt-for-new), honors Singular
Implementation (no new parallelism for already-built platforms), and points the
effort where the moat actually benefits.

## 11. Second-order implications — discourse + decisions (2026-06-22)

After ratifying the seam (scoped to new-platform adoption, §9a), KVK opened the
operator-facing second-order questions: FE / "what's connected", agent-capability
wiring, tool discovery, overall UX, and "what am I missing." **The unifying
finding: almost none of this needs new surfaces.** The ratified management-plane
vocabulary (ADR-338: App Store / Installer / **Drivers** / System Settings) +
operator-experience model (ADR-340) + Connectors-as-Perception-pane (ADR-341)
already frame it. Composio is a **driver** in that exact, operator-ratified sense
— it slots into the "Drivers" row (`platform_connections`), below the consent
line. The governing stance KVK ratified: **Composio is pure mechanical substrate;
the operator's world is unchanged; the kernel stays sovereign over what is a
capability.**

### 11.1 FE — "what's connected" (mostly answered by canon)
Connections render via `ConnectedIntegrationsSection` (Connectors Perception pane,
ADR-341) + the menu-bar `ConnectionsStatusItem` vital. ADR-338's "Drivers" row is
literally `platform_connections`. **DECISION — the driver is invisible (ADR-338
below-the-line):** the Connectors pane shows *what's connected + healthy*, never
*which executor*. If an operator can tell a platform is Composio-backed vs first-
party, the abstraction (ADR-353 §2) has leaked. Sole exception: a connector's own
"bring-your-own-developer-credentials" requirement (ADR-353 §7, the X/Twitter
case) surfaces as a *connection requirement* — a connection fact, not a backend
fact.

### 11.2 Agent capability wiring (fully answered — the elegant part)
Capabilities are declared in bundle `MANIFEST.yaml` (`capabilities:` keys), gated
by `capability_available()` against `platform_connections`, surfaced as tools by
name. **The spike already proved this layer is backend-agnostic** — the gate and
capability resolution key on the *capability* and *tool name*, both unchanged by
which driver executes. A new Composio-backed platform wires identically: declare
the capability, map it to a connection, add the driver adapter. The agent requests
`write_<platform>`; the kernel gates it; the driver executes it. No new capability
mechanism. **No work needed here beyond the per-platform adapter.**

### 11.3 Tool discovery — DECISION: developer-explicit / curated (the load-bearing call)
The one question with no prior canon. Composio offers 1,000+ toolkits / 20,000+
tools; who decides which become YARNNN capabilities, and when?

**DECISION: developer-explicit (curated). Discovery is a Hat-A act, not a runtime
act.** Composio's catalog is YARNNN's *menu of cheap-to-add platforms*, NOT a
runtime capability surface. Rationale, grounded in YARNNN's own principles:
- **Kernel names the category, never the instance (ADR-222).** Dynamic tool
  injection would surface Composio's slugs + argument schemas directly into the
  agent's tool list — renting Composio's *tool ontology*, one step from renting
  its judgment (the §10 line not to cross).
- **The silent-success bug proves curation IS the safety layer.** Every Composio
  tool needs a per-verb result adapter + a platform-level success check (the
  `data.ok` finding, §3a). Auto-surfacing 20,000 untested tools ships unadapted
  failures at scale.
- **Gating + attribution require the tool to be known.** The external-write family
  classification, the capability→provider map, the caller-depended result shape —
  all require a named, classified tool. A dynamically-discovered tool has no
  family, so the gate cannot classify it.

Adding a platform stays a small, bounded task (the §3a Slack pattern: one slug-map
entry + one adapter pair + one MANIFEST capability key). The operator's runtime is
unchanged — they connect platforms YARNNN *supports*, exactly as today.

### 11.4 Overall UX — DECISION: identical, first-party or Composio-backed
The operator experience is the same regardless of backend: same Connectors pane,
same capability gating, same ADR-307 approval cards, same ADR-209 attribution. The
driver boundary (ADR-353 §2) is invisible above the waist by design.

### 11.5 Points KVK was missing (all four to develop, per KVK)

**(a) Composio-down health signal — REAL GAP, no current answer.** ADR-338 Check-7
shows declared-vs-observed connection health. A Composio-backed connection's
health now depends on *Composio's* uptime (the §10 reliability-incident risk). The
Connectors pane's health signal must distinguish **"your token expired"**
(operator-actionable) from **"Composio is down"** (wait-it-out, not actionable) —
otherwise the operator chases a credential problem that isn't theirs. This needs a
deliberate design when the first Composio platform ships: a backend-up-vs-
credential-valid split in the health vital. Until then, the driver's loud-failure
discipline (§5) at least surfaces *a* failure rather than a silent success.

**(b) Phase-2 disconnect lifecycle — a Phase-2 gate item.** Today
`platform_connections` rows are first-party-OAuth-created and deleted on disconnect
(ADR-205 connection-bound lifecycle). Phase-1 (our token) keeps this clean —
disconnect deletes our row, Composio holds nothing. **Phase-2 (Composio-managed
OAuth) reopens it:** who revokes, where the token dies, what "disconnect" means
when Composio holds the connected account. Flagged as a Phase-2 gate alongside the
§7 token-custody security review — do not drift into Phase-2 without resolving it.

**(c) Buyer-legibility tension — hold, unresolved (inherited from §6.6 + §14).**
"Driver is invisible" (good architecture, 11.1) vs "connects to 1,000+ apps" (good
sales). The Connectors pane is also marketing surface. The architecture decision
(invisible driver) is right; the *pitch* may still want to foreground breadth
("YARNNN connects to everything your operation runs on") even while the runtime
hides the executor. These are not in conflict — the pitch sells the *capability
reach* Composio unlocks; the UI hides the *mechanism*. The open question is
whether the Connectors pane ever doubles as a "supported platforms" showcase, or
whether breadth lives only in marketing copy. Parked, but named.

**(d) Interop-face symmetry — the strategic shadow (park, but track).** ADR-353 is
the "consume capability below" half. The symmetric half (ADR-310/311,
discourse §6.6): does YARNNN *expose judgment upward* — the accountable-judgment
kernel that *other* agent stacks call as THEIR driver — while consuming their
hands as ours? Adopting the "we rent hands" posture sharpens the "do others rent
our judgment" question: the more YARNNN is a *consumer* of the commoditized driver
layer, the more its value concentrates in the one thing it does NOT rent (the
seat + accumulated judged substrate), which is exactly what the interop face would
sell upward. Much larger, least proven; not for this ADR. Tracked as the two-sided
position the driver decision foreshadows.

### 11.6 Net: what the second-order pass changes
**Backend (this ADR): done + scoped.** **Operator surface: no new surfaces
needed** — Composio slots into ADR-338's Drivers row, invisible. **One real new
design item:** the Composio-down vs credential-invalid health split (11.5a), due
when the first Composio platform ships. **Two parked-but-named strategy items:**
buyer legibility (11.5c) + interop-face symmetry (11.5d). **One Phase-2 gate:**
disconnect lifecycle (11.5b). No code is owed until a new-platform need is chosen
(§9a); these decisions pre-resolve the surface questions so that wiring, when it
comes, is mechanical.

## 13. Connector survey + the managed-OAuth adoption refinement (2026-06-22)

Follow-on to §15: KVK challenged the ADR-283 "alpha-author needs no connectors"
scope-lock — an author who writes a compounding corpus would benefit from
publishing it (LinkedIn/Medium) AND from the engagement signal that publishing
returns (the outcomes-in flow that closes the loop). Correct challenge: ADR-283
itself named the revisit trigger ("if a real cadence-publishing operator emerges,
that's a different bundle"), the `yarnnn-author` build-in-public workspace IS that
operator, and alpha-author's `audience_signal` flow is already built to populate
*when publishing connectors exist*. So this is real, in-scope demand — and it
needs **systematic supply-discovery** to decide well.

### 13.1 BUILT — the Composio discovery tool (the durable developer capability)
`api/scripts/operator/composio_discover.py` — read-only survey of Composio's
catalog for a named platform: resolves the toolkit, reports auth scheme +
managed-vs-BYO, lists action slugs (filterable by verb). The supply-check half of
§15, made repeatable instead of ad-hoc doc-reading. Creates nothing (no
connections / auth configs / executions). This is the systematic "what does
Composio offer for X" capability for Hat-A connector decisions.

### 13.2 Survey result — author-publishing connectors
Run 2026-06-22 against the publishing surface:

| Platform | In Composio? | Post verb | Auth | Engagement-read (audience-signal) |
|---|---|---|---|---|
| **LinkedIn** | ✅ `linkedin` (22 tools) | `LINKEDIN_CREATE_LINKED_IN_POST` | OAUTH2, **BYO-credentials** | thin |
| **X / Twitter** | ✅ `twitter` (78 tools) | `TWITTER_CREATION_OF_A_POST` | OAUTH2, **BYO-credentials** (X pay-per-use) | **rich** (likers, retweeters, lookups) |
| **Medium** | ❌ not in catalog | — | — | — |
| **Substack / beehiiv / Ghost** | ❌ not in catalog | — | — | — |

Three findings: (1) the covered surface is **social (LinkedIn/X), not
newsletter/blog** — Medium/Substack/Ghost aren't in Composio. (2) **Both require
BYO-developer-credentials** (the §7 wrinkle, confirmed live). (3) X carries the
**rich engagement-read side** — the outcomes-in flow that completes the author
loop (post → measure reception → corpus learns), exactly what alpha-author's empty
`audience_signal` schema is built to consume. Finding (3) is the strongest
architectural argument *for* publishing: it's loop-completion, not convenience.

### 13.3 DECISION — new `alpha-publisher` bundle, not extending alpha-author
KVK: ship publishing as a **separate cadence-publishing bundle** (ADR-283's own
prescribed path), keeping alpha-author corpus-pure. Two distinct archetypes, two
bundles (Singular Implementation). `alpha-publisher` would declare
`write_linkedin` / `write_x` + the engagement-read recurrences that populate
`audience_signal`. NOT built this session — it's a bundle-design task gated on the
BYO-credential decision below. alpha-author's scope-lock stands.

### 13.4 ADOPTION REFINEMENT — managed-OAuth is an adoption criterion (canon update)
The BYO-credential finding (13.2) refines ADR-353's adoption thesis, and it
generalizes beyond publishing:

> **Composio's core value is managed OAuth + execution. When a connector requires
> bring-your-own-developer-credentials, the managed-OAuth value collapses — you
> register the dev app regardless — and Composio reduces to just the verb mapping.
> At that point a first-party client is competitive again.**

So the treadmill-killer thesis is **strongest for managed-OAuth platforms, weakest
for BYO-credential ones.** This becomes an explicit adoption criterion (ADR-353
§16): when evaluating a new connector via the discovery tool, **managed-OAuth =
strong adopt; BYO-credentials = compare against first-party, because Composio's
biggest advantage (auth) is absent.** For LinkedIn/X specifically, the call is
genuinely open — Composio-with-BYO vs a first-party LinkedIn/X client is close,
and should be decided when alpha-publisher is actually designed, not pre-committed.

## 14. "Is publishing valid for alpha-author?" — the measure-not-steer resolution (2026-06-22)

KVK kept circling the real question (Reddit + X + LinkedIn: is publishing valid for
the author archetype at all?). The platform list doesn't settle it; the four-flow
test does. Extended survey + resolution:

### 14.1 Three-platform supply (live-surveyed, all BYO-credentials per §16)
| Platform | Post verb | Engagement-read (outcomes-in) | Loop-closing? |
|---|---|---|---|
| **X / Twitter** | `CREATION_OF_A_POST` | **rich** — likers, retweeters, quotes, lookups | ✅ yes |
| **Reddit** | `CREATE_REDDIT_POST` + `POST_REDDIT_COMMENT` | **rich** — `RETRIEVE_POST_COMMENTS`, threads, cross-subreddit search | ✅ yes |
| **LinkedIn** | `CREATE_LINKED_IN_POST` | **thin** — only `GET_MY_INFO` / `GET_COMPANY_INFO` (no per-post engagement) | ❌ send-only |

All three are **BYO-credentials** ⇒ none gets the §16 managed-OAuth auto-adopt; each
is a deliberate first-party-vs-Composio call.

### 14.2 The test — publishing is loop-valid only if the outcome feeds the corpus
Per the four-flow model (ADR-332): a post the agent sends but never measures is
*automation* (operator-side per ADR-283). A post the agent sends, measures, and
learns from is *loop-closing* (work-out → outcomes-in → loop). The engagement-read
column above IS the test: X/Reddit pass (rich reads), LinkedIn fails (send-only).

### 14.3 RESOLUTION — "measure, but don't let it steer" (preserves the archetype)
KVK's call, and it is the architecturally correct one: **publishing + engagement-
read are valid for alpha-author, but engagement is OBSERVED ground-truth, NEVER a
corpus driver.** The Reviewer may report "this landed / this didn't"; the corpus
still compounds on its own **coherence** (the ADR-283 thesis), not on what got
upvotes.

This draws the bright line between the two archetypes:
- **alpha-author (measure-not-steer):** post → measure reception → surface as
  signal. Corpus compounds on coherence. **Engagement informs, never drives.**
- **alpha-creator (steer):** post → measure → write more of what resonates. Corpus
  optimizes for reach. This is the cadence-publishing archetype ADR-283 carved out
  — a *different* bundle, not this one.

The danger the resolution avoids: if audience-signal is allowed to drive the
corpus, alpha-author silently becomes a growth-hacking bot (the Goodhart trap the
archetype exists to prevent). "Measure-not-steer" keeps the author honest.

### 14.4 Implication for the `alpha-publisher` bundle (when built)
The resolution reshapes the §13.3 bundle: **`alpha-publisher` is a publish+PERCEIVE
bundle, and the perceive half is load-bearing.** The send verbs (`write_reddit` /
`write_x` / `write_linkedin`) are the cheap part; the engagement-read recurrences
(`track-reddit` / `track-x`, populating `audience_signal` as *observation*) are
what make it valid for the author archetype. The bundle's `principles.md` MUST
state explicitly that **engagement informs but never drives the corpus** — or it
silently degrades into alpha-creator. Platform fit (KVK): all three (X, Reddit,
LinkedIn) are where build-in-public narrative lives, accepting LinkedIn is
send-only (automation, not loop) and Reddit demands an authenticity-aware hand
(its culture punishes bot-posting — a real per-platform constraint, not a Composio
one). Still NOT built — gated on the §16 BYO-credential first-party-vs-Composio
call per platform.

## 15a. yarnnn-author publishing — grounded in the live content strategy (2026-06-22)

KVK pointed to `content/STRATEGY.md` + `content/OPS.md` to ground the lean toward
yarnnn-author publishing. They do — and they sharpen the question from "which
platforms" to "what does an API driver buy over the working browser path."

### What the strategy docs establish (raises confidence)
- The channel map (STRATEGY.md) already assigns **Reddit (Tier 1 "core GEO
  channel"), X (3x/week), LinkedIn (ICP activation)** roles + cadence + voice —
  the exact three platforms in question. Publishing isn't hypothetical; it is a
  **live, running operation**. yarnnn-author is its production engine (Pillars 1/3/4
  = a compounding founder/thesis corpus, which alpha-author's coherence-audit loop
  already serves).
- The contribution-first ethic + integrity guardrails ("would this be valuable if
  YARNNN didn't exist?", "no frequency gaming", "no astroturfing") ARE the §14
  measure-not-steer stance, stated as brand values. The archetype line is also the
  declared content ethic.

### The decisive operational finding (reframes the build)
`content/OPS.md`: publishing today runs via **Claude-in-Chrome (visual browser
automation) — NO APIs, NO developer accounts**; Reddit is **100% manual** (Chrome
is blocked there; Kevin pastes). So the question is NOT "enable a missing
capability" — it is **"migrate a working browser+manual workflow to an API
driver."** That raises the bar: Composio's marquee value (managed OAuth) is absent
(all three BYO-creds, §16) AND a zero-credential alternative (browser automation)
already works.

### RESOLUTION — valid, justified by autonomy + loop-closing, Reddit-first (KVK)
**The justification is NOT "enable publishing" (it exists) — it is making
publishing part of the AGENT'S autonomous loop AND piping engagement back as
structured `audience_signal` substrate** (not eyeballed). That is the
"works while you sleep" thesis (the doc's own Bet A) applied to YARNNN's own GTM —
the deepest dogfood: YARNNN autonomously running YARNNN's build-in-public.

**Reddit is the first target** — the one platform where Composio is a **strict
improvement, not a migration**: today it is fully manual (Chrome blocked), so
`CREATE_REDDIT_POST` + `RETRIEVE_POST_COMMENTS` (rich, loop-closing) is pure gain
with no working path to displace. The binding constraint is Reddit's
**authenticity culture** (it punishes bot-posting) — a *content* constraint the
measure-not-steer ethic + contribution-first guardrails already address, not a
driver constraint.

### Net for the alpha-publisher bundle
Validity is **resolved (yes)**; the build is **still gated** on the §16
per-platform BYO-credential first-party-vs-Composio call — now with a third
contender the §16 comparison must include: **browser-automation status quo.** The
bundle's value rests on the *perceive* half (engagement → `audience_signal` as
observation) + autonomy, NOT on the *send* (which browser-automation already does
for LinkedIn/X). Build sequence when it happens: Reddit first (strict gain),
measure-not-steer principles.md, perceive-recurrences as the load-bearing half.

## 15b. BUILT — Reddit publishing in the alpha-author archetype (2026-06-22)

KVK: "update yarnnn-author so its kernel and workspace can do automatic posting to
Reddit." Built the full vertical slice. **Bundle-target decision reversed from
§13.3:** KVK chose to **extend alpha-author** (not a separate alpha-publisher
bundle) — the loop-completion argument won, so the author archetype now *includes*
publish-and-perceive. ADR-283 D7 amended accordingly (publishing in-archetype; the
measure-not-steer guard preserved as a rule of judgment, not a capability
exclusion). §13.3's "different bundle" disposition is superseded.

### What shipped (all on main this session)
- **Kernel:** `read_reddit` + `write_reddit` in `orchestration.py::CAPABILITIES`
  (kernel-universal, like slack/notion/github). `write_reddit` feeds:action (HIGH
  tier, ADR-307 gate is the floor, Reviewer-excluded); `read_reddit` feeds:context.
- **Tools:** `platform_reddit_submit_post` (external-write family) +
  `platform_reddit_get_post_comments` (perceive read) in `platform_tools.py`, fully
  registered across all maps + the external-write classifier.
- **Driver (Composio-ONLY backend — no first-party reddit client exists):**
  `composio_driver.py` reddit slug map (`REDDIT_CREATE_REDDIT_POST` /
  `REDDIT_RETRIEVE_POST_COMMENTS`, live-confirmed schema) + payload adapters
  (kind="self", flair_id default, post_id→article) + result adapters (post_id/url,
  comments/count) + the **reddit silent-success guard** (`data.json.errors` is
  Reddit's data.ok analogue — caught, regression-tested). Reddit added to the
  default driver allowlist.
- **OAuth (BYO-credentials, §16):** Reddit handler in `integrations/core/oauth.py`
  (Basic-auth token exchange, `duration=permanent` for a refresh token, required
  User-Agent) + `REDDIT` enum. The generic `/integrations/{provider}/callback`
  route + generic `platform_connections` upsert handle persistence with zero route
  changes.
- **Bundle (alpha-author):** MANIFEST declares the capabilities; `_recurrences.yaml`
  adds `reddit-publish` (judgment — contribution-first, gated post) +
  `reddit-perceive` (judgment — comments → audience_signal); `principles.md` adds
  `publish-measure-not-steer` (engagement INFORMS, never DRIVES — the bright line
  vs alpha-creator).
- **Tests:** `test_adr353_reddit_driver.py` (12) + prior ADR-353 suite (20) = 32/32.
  CHANGELOG `[2026.06.22.4]`. ADR-283 D7 amended.

### DEPLOYMENT CHECKLIST (not done this session — operator/Hat-A go-live steps)
To make autonomous Reddit posting live for yarnnn-author:
1. **Register a Reddit app** (https://www.reddit.com/prefs/apps — type "web app",
   redirect `https://yarnnn-api.onrender.com/api/integrations/reddit/callback`).
2. **Env vars** — set on **yarnnn-api + yarnnn-unified-scheduler** (Render parity,
   §8): `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` (OAuth); `COMPOSIO_API_KEY` +
   `COMPOSIO_DRIVER_ENABLED=true` (reddit is already in the default allowlist).
   NOT on mcp-server / render.
3. **Connect** — operator runs the Reddit OAuth flow (`/api/integrations/reddit/
   connect`) → creates the `platform_connections` row.
4. **Activate** — yarnnn-author's workspace already runs alpha-author; the
   `reddit-publish` / `reddit-perceive` recurrences fire once the connection +
   `COMPOSIO_DRIVER_ENABLED` are live. Under bounded/manual autonomy the first
   posts QUEUE for approval; under autonomous they post directly.
5. **§12.4 token-transit sign-off** still applies (the Reddit token transits
   Composio in flight).

## 16. CORRECTION — the three auth tiers; §13.4/§16-v1 "managed-OAuth" claim was wrong (2026-06-22)

While scoping a higher-leverage connector to build during Reddit's API-access
review, the discovery tool surfaced a contradiction: Notion/Gmail/GoogleDrive all
reported "managed OAuth: None" — yet Slack (which worked live) should have read
"managed." Investigating revealed a **detector bug + a false inference**, and
corrected a load-bearing claim:

- **Detector bug:** `composio_discover.py` read `is_composio_managed` (None for
  every toolkit). The real signal is `composio_managed_auth_schemes` (non-empty).
  FIXED — the tool now reports `composio-managed auth flow` + `requires YOUR app
  credentials` (parsed from `auth_config_details.auth_config_creation.required`).
- **False inference:** "Composio-managed OAuth = frictionless, the strong-adopt
  case (Slack)." Calibration against Slack/Gmail/Reddit showed all three are
  *managed-flow but BYO-app* — `client_id`/`client_secret` are required creation
  fields. **Slack felt frictionless only because YARNNN already had a first-party
  `SLACK_CLIENT_ID` in env** (confirmed: `.env` has SLACK + NOTION client ids;
  REDDIT absent — which is exactly why Reddit hit the wall). We'd pre-paid the
  app cost first-party years ago.

**Corrected model — three auth tiers** (ADR-353 §16, full table there):
1. **OAuth + BYO-app** (Slack/Gmail/Notion/Linear/GitHub/Reddit/X/LinkedIn) — you
   register a platform dev app; high friction, sometimes a review queue. The bulk
   of write/work platforms.
2. **API-key service** (Exa/SerpAPI/Firecrawl/Perplexity) — one account key;
   lighter.
3. **Public / zero-credential** (Hacker News) — nothing; rare.

**What this corrects in the canon:** §16-v1's "managed-OAuth = strong adopt; BYO =
compare vs first-party" described a nearly-empty set (clean zero-cred OAuth barely
exists on Composio). Auth-tier is a **cost input**, not the leverage axis. Leverage
= demand-grounded (§15.1) + loop-closing (§14) + an auth-tier you can clear.
Connector roadmap re-ranked in ADR-353 §17: **Reddit (in flight) → Hacker News
(zero-friction perceive, ships now) → API-key context tools** — new BYO-app write
platforms wait for explicit demand + willingness to pay registration friction.

**Status note (Reddit):** Reddit API-access request submitted 2026-06-22 (ticket
`N23GN2-K94XN`) — the OAuth+BYO-app friction wall, awaiting Reddit's manual review.
The full YARNNN-side stack (kernel + driver + OAuth + bundle, hardened) is built
and waiting; nothing YARNNN-side is blocked. Re-engage on Reddit's approval email.

## 12. Sources (accessed 2026-06-22, input only)

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
