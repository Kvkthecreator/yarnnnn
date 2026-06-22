# ADR-353 — Composio as the Driver Backend for External Hands (Accepted, scoped)

**Status:** **Accepted (2026-06-22) — scoped to new-platform adoption; the seam is canon, the default stays OFF.** Spike complete, all six §12 criteria PASS incl. full live E2E (findings §3a + §9a). Ratified scope (KVK, 2026-06-22): the Composio driver seam is adopted; the SLA is "adopt Composio as the executor for **platforms YARNNN has no first-party client for** — the next Salesforce/HubSpot/Linear/… is wired with zero new client code." **Already-built platforms (Slack/Notion/GitHub) stay first-party for now** — re-routing them is the weak case (partial maintenance savings + a new token-transit dependency; the existing clients also have non-driver callers — landscape sync, exporters). **Future absorption stays open:** if those existing paths later become cleanly absorbable into Composio (e.g. the non-driver callers migrate, or the maintenance/dependency math flips), streamlining them in is a follow-on amendment, not a re-decision — the seam already supports it. No production flip without the §12.4 token-transit sign-off. Drafted Hat-B; ratified as Hat-A canon.

> **Second-order implications (FE / capability-wiring / tool-discovery / UX) are open and tracked separately** — see findings §11 ("Second-order implications") for the discourse agenda. This ADR ratifies the backend seam + adoption scope only; it does NOT decide the operator-facing surface.
**Date:** 2026-06-22
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon, if ratified) — touches `api/` integration layer.

> **Discourse base:** [`positioning-discourse-seat-as-asset-2026-06-22.md`](../analysis/positioning-discourse-seat-as-asset-2026-06-22.md) — §6.6 (the stack axis: kernel vs commodity drivers; *drive the mechanical, never rent the judgment*) + Appendix B (driver-layer market scan). This ADR cashes §6.6's scope license — "YARNNN need not build the integration layer" — into a concrete, scoped first instance.

**Extends:** ADR-335 (Perception Field — transports are peripherals, driver-class, transport-blind judgment), ADR-310 / ADR-311 (the interop face — consume capability below, expose judgment above).
**Relates:** ADR-207 (capability-gating keyed on active `platform_connections`), ADR-307 (unified permission gate at `execute_primitive`), ADR-118 / ADR-130 (RuntimeDispatch → external render service: the existing precedent for calling out to an external execution service), ADR-076 (Direct-API clients, the pattern this would partly retire).
**Preserves (hard invariants — adoption must not break these):** ADR-209 (`write_revision` as the single write path + `authored_by` attribution), ADR-307 (the permission gate stays in-kernel), ADR-320 (five-root topology), ADR-343 (the floor — per-act risk envelope), the kernel/driver boundary (ADR-222).

---

## 1. Problem statement — the integration treadmill vs the commoditized driver layer

YARNNN currently maintains hand-built direct REST clients per platform — `api/integrations/core/{slack,notion,github}_client.py` (plus commerce/trading handlers in `api/services/platform_tools.py`) — each with its own retry/rate-limit/pagination logic, plus first-party OAuth orchestration (`api/integrations/core/oauth.py`) and Fernet token encryption (`api/integrations/core/tokens.py`). Every new platform is a new client, new OAuth config, new maintenance surface. This is the integration treadmill: building in the commodity layer of the stack.

Per the discourse (§6.6 + Appendix B), the driver layer has commoditized hard. MCP registries index tens of thousands of servers; unified-API aggregators (Composio, Paragon, Nango, Merge) collapse "hundreds of integrations" into a single connection on usage pricing. **Composio specifically** exposes 1,000+ integrations / 20,000+ tools through a standardized MCP interface on top of managed OAuth, with action-level RBAC and a zero-data-retention, SOC 2 Type II / GDPR / HIPAA architecture (VPC + self-host available).

The strategic frame the discourse hardened: the connection layer is the *occupant* of the integration world — fungible. YARNNN's moat is **above the waist** (judgment + accountable accumulation), not in the hands. Building hands is competing where we have no edge. This ADR scopes whether to stop building hands and rent them — under a strict boundary so the kernel stays sovereign.

## 2. Decision (proposed)

Adopt **Composio as a driver backend that sits BEHIND YARNNN's existing primitive contract** — not as a replacement for any kernel responsibility. Concretely:

- The kernel keeps its surface unchanged: `execute_primitive()` → `resolve_permission()` (gate) → handler dispatch. The LLM-facing tool names, capability-gating, autonomy gate, attribution, and substrate writes are **all** kernel.
- Composio replaces the *mechanical execution layer only*: the per-platform `_handle_*_tool` handlers in `platform_tools.py` and the direct API clients in `integrations/core/`. Where today `handle_platform_tool()` routes to `_handle_slack_tool()` → `SlackAPIClient`, it would instead route to a thin `composio_driver` that executes the action via Composio's MCP/action API.
- Composio is wrapped behind YARNNN's own driver interface so it is **swappable** — its tool shapes never leak into the substrate or the primitive registry.

**The load-bearing rule (from §6.6): drive the mechanical, never rent the judgment.** Consume Composio's auth + execution + MCP exposure. Do *not* consume its routing/ranking/"agentic" features, and never its "skills that improve over time" loop (see §10) — that is the part that is supposed to be our moat.

This decision is **driver-agnostic in principle**: Composio is the recommended first backend, but the seam is defined so any aggregator (or a return to first-party clients) can fulfill the same interface.

## 3. The kernel/driver boundary (what Composio may and may not touch)

| Concern | Stays KERNEL (sovereign) | Driver-eligible (Composio) | Anchor |
|---|---|---|---|
| Attribution of every mutation | ✅ `write_revision`, `authored_by` | — | ADR-209 |
| Consequential-action gate (APPLY/QUEUE/DENY) | ✅ `resolve_permission` | — | ADR-307 |
| Ground-truth **attestation** (did it happen, what was the outcome) | ✅ kernel reconciliation | transport of the raw datum only | ADR-330 / ADR-343 |
| Capability-gating on active connections + tool surfacing | ✅ `capability_available`, `get_platform_tools_for_agent` | — | ADR-207 |
| Mechanical action execution (send message, append page, list issues) | — | ✅ | this ADR |
| Connector upkeep / API drift / rate-limit handling | — | ✅ | this ADR |
| OAuth token lifecycle | ⚠️ phase-dependent (§7) | ⚠️ phase-dependent (§7) | this ADR |

The precise line (§6.6): **transport is a peripheral; the attestation of outcome is kernel**, even when they ride the same wire. A Composio call may *carry* the bytes that say an order filled; the kernel decides whether that counts as a reconciled outcome.

## 4. Current architecture (audit findings, file-grounded)

End-to-end flow today for "an agent takes an action on an external platform" (e.g., Designer posts to a Slack channel):

1. **Tool surfacing** — `get_platform_tools_for_agent()` (`platform_tools.py`) merges role + task capabilities and calls `capability_available()` (`orchestration.py`), which gates on an active `platform_connections` row for the provider. Surfaces e.g. `platform_slack_send_to_channel`.
2. **Primitive dispatch** — `execute_primitive()` (`primitives/registry.py`) calls `resolve_permission()` (`primitives/permission.py`) → APPLY / QUEUE / DENY by autonomy + action family.
3. **Handler execution** (if APPLY) — `handle_platform_tool()` (`platform_tools.py`) routes to `_handle_slack_tool()`, which fetches the `platform_connections` row, decrypts the token via the Fernet `TokenManager` (`integrations/core/tokens.py`, key `INTEGRATION_ENCRYPTION_KEY`), and calls `SlackAPIClient` (`integrations/core/slack_client.py`).
4. **Attribution** — outcome recorded through `write_revision()` (`authored_substrate.py`), `authored_by=agent:{slug}`. Narrative entry emitted.

Key audited facts that constrain the design:
- The **single seam** for execution is `handle_platform_tool()` → `_handle_*_tool` in `platform_tools.py`. Everything platform-specific lives below that one function.
- `resolve_permission()` already classifies consequential actions into a **capital family** (trading/commerce writes) and an **external-write family** (Slack/Notion/email sends), with operator-addressing infra early-returning as non-consequential. *This existing split is the natural driver boundary* (see §11).
- `write_revision()` is confirmed the single write path; attribution is independent of who executes the action.
- The **RuntimeDispatch → yarnnn-render** path (`primitives/runtime_dispatch.py`, `RENDER_SERVICE_URL` + `RENDER_SERVICE_SECRET`) is an existing, working precedent for calling an external execution service and then authoring the result in-kernel. Composio adoption is the same shape applied to platform actions.

## 5. Slot-in points (seams)

| Seam | Location | Action |
|---|---|---|
| **Primary** | `handle_platform_tool()` dispatch in `platform_tools.py` | Route to `composio_driver.execute(provider, verb, input, token)` instead of `_handle_*_tool`. **This is the only structurally required change.** |
| Platform clients | `_handle_{slack,notion,github}_tool` + `integrations/core/*_client.py` | Delete once Composio coverage is confirmed per platform (singular-implementation discipline — no parallel paths). |
| Tool definitions | `PLATFORM_TOOLS_*` maps in `platform_tools.py` | Keep the tool *names* and capability mapping (kernel contract); source the action metadata from Composio where it differs. |
| Permission gate | `permission.py` | **No change.** Composio actions route through `resolve_permission()` identically. |
| Capability-gating | `orchestration.py::capability_available`, `platform_connections` | **No change.** Connections remain source of truth for which tools surface. |
| Attribution | `authored_substrate.py::write_revision` | **No change.** Execution result authored in-kernel as `agent:{slug}` / `system:*`. |
| MCP server | `api/mcp_server/` | **No change.** Orthogonal — YARNNN's MCP server is a *caller* of `execute_primitive`; Composio is a *backend* of it. |
| OAuth/tokens | `integrations/core/oauth.py`, `tokens.py` | Phase-dependent (§7). |

## 6. What is added / deleted (singular implementation)

**Added:** one new module `api/services/composio_driver.py` (the wrapped, swappable driver) + `COMPOSIO_API_KEY` env var.

**Deleted (after per-platform coverage confirmation, not before):** the `_handle_{slack,notion,github}_tool` handler bodies and the corresponding `integrations/core/*_client.py` clients. Per Execution Discipline #2 (no dual approaches), these are removed entirely once Composio fulfills their verbs — not kept as fallbacks. Trading/commerce handlers are explicitly **out of initial scope** (§11).

**Kept:** OAuth flow, token manager, permission gate, capability registry, authored substrate, MCP server, the `platform_connections` schema.

## 7. Multi-tenancy + OAuth / token handling

**Multi-tenancy is a hard requirement, and it is the exact line that separates the right tool from the wrong one.** YARNNN is itself a platform: many operators, each connecting *their own* Slack/Notion/etc. accounts, with strict per-user credential isolation. The classic failure mode (Zapier / Make / n8n in their personal form) is that they are *single-account automation* — you connect *your* accounts and the automation runs as you; serving N customers would mean N accounts, which structurally cannot model "my customer's Slack." That is the opposite of what we need, and the trap that bites only after implementation.

Composio sits in the *embedded-integration* category, not the personal-automation category: it provides per-end-user connected accounts via a `user_id`/entity parameter, and a single Composio account serves many of our users **without credential mixing** (SOC 2 / ISO / HIPAA-ready; credentials never reach the agent). This maps 1:1 onto YARNNN's existing model — `platform_connections` is already keyed by `user_id`, and `capability_available(user_id, …)` already gates per user. **Composio's entity == YARNNN's `user_id`.** The same holds for the other embedded aggregators (Paragon, Nango, Merge); it does **not** hold for classic Zapier. Verifying this per-end-user isolation empirically is a ratification gate (§12).

Token handling — two phased options:

- **Phase 1 (recommended): keep YARNNN's OAuth, pass plaintext in-process.** `platform_connections` stays the source of truth; the kernel decrypts as today and hands the plaintext token to `composio_driver` for the single execution call. Least disruptive, no new external token custody, fully reversible. The driver is a pure stateless executor. **Multi-tenancy is essentially free here:** YARNNN fetches the *per-user* token and Composio holds no tenant state at all.
- **Phase 2 (evaluate later): Composio-managed auth.** Hand OAuth itself to Composio's connected-accounts; map each YARNNN `user_id` → a Composio entity. Removes more maintenance and makes Composio's per-entity isolation load-bearing (exactly what the embedded category is built for) — but moves token custody to a third party, a larger data-governance and reversibility decision deferred until Phase 1 proves the model.

Recommendation: ship Phase 1; treat Phase 2 as a separate decision gated on a security review.

**Per-platform caveat:** a specific connector can still impose "bring your own developer credentials" when the *underlying platform* changes policy (e.g., Composio had to require user-supplied X/Twitter dev credentials after X moved to pay-per-use). That is a platform-policy wrinkle, not an aggregator limitation, but it can complicate the clean platform-OAuth-app model for individual connectors — check it per platform during the spike.

## 8. Render-service parity (ADR-083 / §5 of CLAUDE.md)

`COMPOSIO_API_KEY` (and any `COMPOSIO_*` config) must live on **both `yarnnn-api` and `yarnnn-unified-scheduler`** — the scheduler executes recurrence invocations that take platform actions, so it needs the driver credentials exactly as it needs `INTEGRATION_ENCRYPTION_KEY` today. **Not** needed on `yarnnn-mcp-server` (read-only context surface) or `yarnnn-render` (independent Docker output gateway). Use the Render MCP `update_environment_variables` across both services in one pass — the classic drift failure is adding the var to the API and forgetting the scheduler.

## 9. Security / compliance

Composio is SOC 2 Type II / GDPR / HIPAA, zero-data-retention, with VPC + self-host options, and keeps credentials out of the agent's reasoning context. The critical reassurance for YARNNN's *own* thesis (the moat is the audit trail): **moving execution to Composio does not dilute provenance, because attribution is authored at decision time in the kernel (`write_revision`), not at execution time in the driver.** Execution is the peripheral; the attested record is the kernel. If the capital family is later in scope, a dedicated security review is mandatory (third-party in the path of money-moving actions).

## 10. Risks

- **Dependency fragility.** Drivers break under you when upstream changes — Composio had to change its X/Twitter approach when X moved to pay-per-use. Mitigation: the wrap-behind-our-contract rule (§2) keeps Composio swappable; the kernel never imports Composio shapes directly.
- **Aggregator consolidation.** The layer is in flux (Pipedream acquired by Workday, Nov 2025). A startup at ~$29M (Series A) is fundable, not permanent. Same mitigation: driver-agnostic seam.
- **Composio climbing into judgment (the strategic risk).** Composio's Series A thesis is explicitly *"skills that improve over time / solving AI's learning problem"* — adjacent to YARNNN's accumulation/judgment moat. Today complementary (they accumulate tool-use skill; we accumulate judgment against reconciled reality). The discipline: consume their hands, **never their improvement loop.** The moment we lean on Composio "learning," we are renting the part that is supposed to be ours.
- **Edge-case config cost at scale.** Reviews note advanced configurations require upfront work and cost rises at high volume. Low immediate concern given YARNNN's few-but-valuable action profile (which also makes action-volume pricing cheap for us).
- **Reliability.** Composio has a public incident history (e.g., Feb 9 2026) — normal for infra, but the kernel must degrade gracefully when the driver is unavailable (surface a QUEUE/retry, never a silent success — cf. Pitfall #4 in CLAUDE.md, the Worker-reports-success-with-0-items class of bug).

## 11. Scope boundary — externalize the hands, keep capital first-party (initially)

The existing `resolve_permission()` family split is the right driver boundary:

- **External-write family + reads (Slack, Notion, GitHub, marketing platforms): Composio-eligible.** Low per-act stakes, high integration-count, exactly where aggregator leverage pays off.
- **Capital family (trading via Alpaca, commerce writes): keep first-party for now.** Routing money-moving actions through a third party adds latency, a compliance surface, and a dependency at the most consequential action class — the one tied to the floor (ADR-343). The kernel should own the capital hands until/unless a dedicated review says otherwise.

This means the alpha-trader program's execution path is **out of scope** for initial adoption; this ADR is about the read + external-write hands that every program shares.

## 12. Decision criteria — what would move this from Proposed to Accepted

1. **Coverage check:** confirm the platforms we actually need (start with the connected set: Slack, Notion, GitHub) exist in Composio with the *specific verbs* our capabilities require — not just the platform, the actions.
2. **Parity spike:** implement `composio_driver` behind `handle_platform_tool()` for **one** platform (Slack), keep the first-party client in place, and compare results/latency/error-shapes before deleting anything.
3. **Cost model:** project action-execution-volume cost against realistic invocation rates (should be low given the few-but-valuable profile).
4. **Token-model security review:** sign off on Phase 1 (plaintext in-process) explicitly; do not drift into Phase 2 without a separate review.
5. **Swappability proof:** demonstrate the driver interface is clean enough that reverting to first-party (or switching aggregators) is a config change, not a refactor.
6. **Multi-tenant isolation proof (hard gate):** in the Slack parity spike, connect *two different test users'* accounts and confirm each executes against its own credentials with zero cross-tenant leakage (Composio entity == YARNNN `user_id`). This is the specific failure that bites after implementation, so it is validated before, not after.

## 12a. Spike results (2026-06-22) — all §12 criteria PASS (now Accepted, scoped — see top banner + §15)

A scoped, flag-gated Slack-only spike was run against the §12 criteria. **Full
findings:** [`SESSION-FINDINGS-adr353-composio-spike-2026-06-22.md`](../analysis/SESSION-FINDINGS-adr353-composio-spike-2026-06-22.md).
Headline:

- **Coverage (§12.1):** Slack 4/4 verbs covered with Composio managed OAuth (no
  bring-your-own-credentials). Notion 5/5, GitHub managed-OAuth + 867 tools
  (specific slugs to confirm live). Finding: Composio action slugs are unstable
  across versions — mitigated by pinning them in one driver-local map.
- **Consumption protocol (§12, task 2):** **REST** (`POST /api/v3/tools/execute/
  {slug}`), not MCP — the swappability comes from our driver interface, not the
  wire; MCP is Composio's agent-facing routing/learning face (the part §10 says
  never to consume).
- **Multi-tenant isolation HARD GATE (§12.6):** **PASS** — Phase-1 injects each
  user's own token per call (`custom_auth_params`); Composio holds zero tenant
  auth state; proven at the wire that each call carries only the caller's bearer
  + `user_id` entity, zero cross-tenant leakage.
- **Parity (§12.2):** **PASS — full live E2E** against YARNNN's own Slack
  workspace (KVK-authorized): all 4 verbs (list_channels, get_channel_history,
  a real post to `#daily-work` ts `1782107616.117459`, forced-fail) live-
  confirmed; result shapes byte-identical to first-party; the live silent-success
  guard fired (Composio `successful:true` + `data.ok:false` → surfaced as failure).
- **Live findings (§3a):** the run caught + fixed two bugs a mock-only spike would
  have shipped — the send slug was wrong (`SLACK_SEND_MESSAGE` → live
  `SLACK_CHAT_POST_MESSAGE`), and Composio's `successful` flag lies about platform
  outcome (the real result is nested at `data.ok`).
- **No silent success (Pitfall #4):** every failure mode (401/429/`successful:
  false`/nested `data.ok:false`/timeout/unmapped/missing-key/missing-token) →
  `{success: False}`. Live-confirmed.
- **Swappability (§12.5):** revert = `COMPOSIO_DRIVER_ENABLED=false` (one env
  var). Capital family hard-excluded.
- **Tests:** 18/18 pass (`api/test_adr353_composio_isolation.py` +
  `api/test_adr353_composio_parity.py`). No regressions.

**Spike recommendation:** **RATIFY the seam** — all six §12 criteria PASS incl.
full live E2E. **But scope adoption to NEW platforms, not a Slack-family re-route**
(decision memo: findings §9a). The audit found the existing clients
(Slack/Notion/GitHub) have callers beyond the driver seam (landscape sync,
exporters) and that OAuth/token lifecycle stays first-party in Phase 1 — so
re-routing already-built platforms buys partial maintenance savings while adding a
token-transit dependency (weak). The strong case is the §1 thesis: the next
platform with NO first-party client (Salesforce/HubSpot/Linear/…) gets wired with
zero new client code. **Recommended next step: do NOT wire Notion/GitHub now;
adopt Composio as the driver for the first genuinely-new platform need.** Deferred
(separate decisions): Phase-2 Composio-managed auth (§7 review) + capital family
(§11). **Status remains Proposed pending KVK's ratification + the §12.4 trust-
boundary sign-off** (Phase-1 transits per-user tokens through Composio in flight —
a known, named property).

## 15. Connection lifecycle — demand-driven discovery + kernel-vs-bundle mapping (2026-06-22)

Two operating questions about the ratified scope ("adopt for new platforms, added
Hat-A"): **(a) how do we discover which connections to add** if it's internal and
operators don't browse a catalog, and **(b) where does a new connection map**,
given connections are program-specific not universal. They are one question:
**demand originates from a program; the mapping is decided by the capability's
altitude; Composio is checked last, only for supply.**

### 15.1 Discovery is demand-driven, never catalog-browse
The signal to add a connection is **never "Composio has it"** — it is **"a program
needs an action against a platform we don't support."** Three demand sources, all
grounded (none speculative):
1. **Bundle author declares it** — `dependencies.lean: [<platform>]` in a MANIFEST
   (the existing "needed but not yet built" slot; alpha-author already uses it for
   deferred publishing-platform writes).
2. **A live recurrence hits the gap** — a `required_capability` whose connection is
   unavailable. Previously swallowed silently (the ADR-227 empty-deliverable
   failure mode); now **captured as a `[CONNECTION-DEMAND]` signal** (§15.4) — the
   discovery queue, generated by real operator need.
3. **A new program's four-flow design** (ADR-332) names the platforms its
   context-in / work-out / outcomes-in flows must touch.

Composio's 1,000+ catalog is the **supply-check, consulted last** — once a program
*names* a platform, confirm coverage via the live tool-enum (the §3a 5-minute
query). Never browse it cold. (OS analogy: you don't browse the driver database;
you plug in a device and the OS has the driver or you install one.)

### 15.2 Mapping — the `feeds:` test decides kernel vs bundle (KVK's instinct, formalized)
A new connection is NOT mapped to "the kernel" monolithically. It maps to one of
two existing homes, decided by the capability's `feeds:` altitude:
- **Kernel-universal** (`orchestration.py::CAPABILITIES`) — generic platform hands
  many programs reuse (`read_slack`/`write_slack`/`read_notion`/…). `feeds:
  context`, OPEN tier.
- **Program-specific** (bundle `MANIFEST.yaml::capabilities[]`) — hands whose data
  IS this operation's ground-truth or whose act IS its mandate (`read_trading`/
  `write_trading`). `feeds: ground_truth | action`, HIGH tier, `requires_connection`.

So KVK's "project-type-specific" instinct is **correct for the program-defining
connections and not for the universal ones** — the two-home split is the answer,
and `feeds:` is the decider. Already enforced by the kernel/program boundary
(ADR-224) + derived-trust-tier gate (ADR-335).

### 15.3 The add pattern (bounded, Hat-A, ~an afternoon)
Per new platform, once demand is named + supply confirmed: one
`_COMPOSIO_ACTION_MAP` entry + one payload adapter + one result adapter + the
platform-level success check (§3a); declare the capability at its `feeds:`-decided
home (§15.2); confirm via the live coverage/parity harness. No new mechanism — the
seam already supports it.

### 15.4 IMPLEMENTED — the connection-demand signal
`api/services/connection_demand.py::record_unmet_capability` emits a structured
`[CONNECTION-DEMAND]` log line at the point in
`get_platform_tools_for_capabilities` where an unsatisfiable requested capability
was previously dropped silently. `reason` distinguishes **`unknown_capability`** (a
Hat-A *add* candidate — YARNNN doesn't offer it) from **`platform_not_connected`**
(an operator-*onboarding* signal — it exists, connect it). Sink is a log line, NOT
a new table and NOT `execution_events` (the ADR-291 cost ledger) — at alpha scale
the demand "queue" is a Render-logs search; promote to a table when volume
justifies. Gate: `api/test_adr353_connection_demand.py` (5/5). This turns
discovery from speculative catalog-curation into a queue of real program demand.

## 16. Adoption criterion — the three auth tiers (2026-06-22, CORRECTED 2026-06-22)

> **CORRECTION.** §16 v1 said "managed-OAuth = strong adopt; BYO-credentials =
> compare vs first-party," treating Slack as the frictionless managed case. That
> was based on a **detector bug** in `composio_discover.py` (it read
> `is_composio_managed`, which is `None` for every toolkit) and a false inference
> (Slack "felt frictionless via Composio" only because YARNNN **already had** a
> first-party `SLACK_CLIENT_ID`/`NOTION_CLIENT_ID` in env — we'd pre-paid the
> app-registration cost years ago first-party). Calibrating the detector against
> Slack/Gmail/Reddit revealed the real signal: `composio_managed_auth_schemes`
> (non-empty for all three) means Composio manages the OAuth *flow* — but
> `auth_config_details` lists `client_id`/`client_secret` as
> `auth_config_creation` **required** fields, i.e. **you still bring the app.**
> "Composio-managed OAuth" is *managed flow, BYO app* — NOT zero-credential. The
> clean zero-credential OAuth case is essentially empty on Composio.

**The corrected model — three auth tiers (per the live scan 2026-06-22):**

| Tier | Examples | What you bring | Friction |
|---|---|---|---|
| **OAuth + BYO-app** | Slack, Gmail, Notion, Linear, GitHub, Reddit, X, LinkedIn | a registered platform dev app (client_id + secret), per platform | **High** — app registration + sometimes a review queue (Reddit's API-access review; X pay-per-use; LinkedIn app review). This is the bulk of write/work platforms. |
| **API-key service** | Exa, SerpAPI, Firecrawl, Perplexity, composio_search | one account + API key with that service | Medium — a credential, but no per-platform OAuth app/review. |
| **Public / zero-credential** | Hacker News | nothing | **None** — works immediately. Rare. |

**The corrected criterion:** auth-tier is NOT the leverage axis I claimed — almost
every *platform* (OAuth) connector is BYO-app, so "managed-OAuth = strong adopt"
described a nearly-empty set. Composio's real value is the **verb mapping +
execution + maintenance**, not auth (you bring the app regardless for OAuth tiers).
So leverage is judged on:
1. **Demand-grounded** (§15.1) — a program declares it;
2. **Loop-closing** (§14) — has the outcomes-in read, not just a send;
3. **Auth-tier as a COST input, not a yes/no** — OAuth+BYO-app carries
   registration/review friction (budget for it; Reddit's review queue is the rule,
   not the exception); API-key is lighter; public is free. For an OAuth platform
   YARNNN already has a first-party app for (Slack/Notion/GitHub), the
   marginal Composio cost is ~zero (app already paid) — so re-routing those is
   cheaper than a *new* OAuth platform, though still the weak §13.4 case.

**Implication for the roadmap (§17):** the lowest-friction *new* capability is a
zero-credential or API-key connector that closes a perceive loop — not another
BYO-app write platform. The discovery tool now reports the correct tier
(`composio_managed auth flow` + `requires YOUR app credentials`) so this is
data-driven.

## 17. Connector roadmap — re-ranked by the corrected tiers (2026-06-22)

Applying the corrected §16 (auth-tier as cost) + §15.1 (demand) + §14 (loop-closing)
to the real candidates:

| Candidate | Demand | Loop-closing | Auth tier | Verdict |
|---|---|---|---|---|
| **Reddit** | content strategy (Tier-1 GEO) | ✅ rich comment reads | OAuth+BYO-app (in review) | **In flight** — built, blocked on Reddit API-access review |
| **Hacker News** | content strategy ("Show HN", not active yet) | ✅ comment threads | **public/zero-cred** | **Highest leverage-per-effort** — perceive loop, ships immediately, no friction wall |
| **Exa / web search** | perception field (ADR-335) | n/a (read) | API-key | strong for context-in; lighter friction |
| **X / Twitter** | content strategy (3x/wk) | ✅ rich engagement | OAuth+BYO-app (pay-per-use) | medium — same friction as Reddit + usage cost |
| **LinkedIn** | content strategy (ICP) | ❌ thin reads (send-only) | OAuth+BYO-app (review) | weak — fails loop-closing (§14) |
| **Gmail / Notion / Linear** | not currently declared | varies | OAuth+BYO-app | defer — no program demand (§15.1) |

The roadmap's near-term shape: **Reddit (in flight) → Hacker News (zero-friction
perceive, ships now) → API-key context tools (Exa) as perception-field demand
warrants.** New BYO-app write platforms (X, Gmail, …) wait for explicit program
demand AND a willingness to pay the registration/review friction.

## 13. Alternatives considered

- **Keep building first-party direct clients (status quo).** Rejected as the integration treadmill — competing in the commodity layer with no edge (the §1 problem).
- **A different aggregator** — Paragon ActionKit (embedded white-label, strong if we ever surface connector UI to operators), Nango (code-first, ships its own MCP server, good if we want deep control), Merge (unified *data model* per category, better for read-normalization than for action execution). Composio preferred for the largest agent-native catalog + MCP-native + action-level RBAC + the action-volume pricing that suits us. The seam keeps any of these viable.
- **Per-platform raw MCP servers without an aggregator.** More servers to manage, no unified auth — reintroduces a treadmill in MCP clothing.
- **Do nothing.** Acceptable short-term; revisit when the next platform request would otherwise mean writing another client.

## 14. Open questions / dependencies

- **Dependency on the positioning fork (partial).** *Which* platforms matter most depends on which wedge/program leads (the still-open `positioning-discourse` §5). But driver-agnostic adoption of the read + external-write hands is largely orthogonal to that fork — it pays off under any positioning. So this ADR need not wait on the positioning decision, except for prioritizing which platforms to validate first.
- **The two-sided question (§6.6).** This ADR is only the "consume capability below" half. Whether YARNNN also *exposes judgment upward* (the kernel other agent stacks call via the interop face, ADR-310/311) is a separate, larger decision left open in the discourse.
- **Operator legibility.** Thinning the integration story sharpens the moat but may blur the buyer pitch ("it connects to my Salesforce" is invisible if it's just a driver). Foreground/background framing — tracked in the discourse, not resolved here.

---

*Internal references: ADR-076 (Direct-API clients), ADR-083 (Render service topology), ADR-118/130 (RuntimeDispatch external service), ADR-207 (capability-gating on connections), ADR-209 (authored substrate single write path), ADR-222 (kernel boundary), ADR-307 (unified permission gate), ADR-310/311 (interop face), ADR-320 (five-root topology), ADR-330 (ground-truth intake), ADR-335 (perception field / transports as peripherals), ADR-343 (aperture/floor). Audited code: `api/integrations/core/{slack,notion,github}_client.py`, `api/integrations/core/{oauth,tokens}.py`, `api/services/platform_tools.py`, `api/services/orchestration.py`, `api/services/primitives/{registry,permission,runtime_dispatch}.py`, `api/services/authored_substrate.py`, `api/mcp_server/`.*
