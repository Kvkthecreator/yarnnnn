# Proposal — alpha-polymarket (Deferred)

**Status:** Parked. Revisit after alpha-trader + alpha-commerce E2E validation completes.

**Origin:** 2026-04-23 conversation. A LinkedIn post claiming "$25 → $4,237 in one night" via a Polymarket-scanning Claude agent surfaced the prediction-market-operator pattern as a distinct alpha persona candidate.

## Why This Is Worth Considering

Prediction-market operation exercises YARNNN's Primary Action thesis (ADR-207) on a domain that differs from alpha-trader along every axis except execution shape:

| Axis | alpha-trader | alpha-polymarket |
|------|--------------|------------------|
| Platform | Alpaca (REST brokerage API, OAuth-style auth) | Polymarket (on-chain, wallet + subgraph, signed txs) |
| Primary Action | Submit equity order matching declared signal | Submit outcome-share order matching declared mispricing |
| Edge source | Technical/fundamental signals on equities | Wallet-following + news→market mapping + Kelly on discrete outcomes |
| Context domains | `trading/`, `portfolio/` | `wallets/`, `markets/`, `news_mappings/` |
| Risk math | Stop distance, sector concentration, VIX regime | Kelly on binary outcomes, liquidity depth, resolution risk |
| Reviewer principles | Equity risk framework | Discrete-outcome risk framework (resolve-to-0 losses are total) |
| Settlement | T+1 cash | On-resolution (days to months) |

## Why Keep It Separate From alpha-trader

Folding it into alpha-trader would conflate two distinct Primary Actions. ADR-207 commits to one Primary Action per workspace. A trader and a prediction-market operator are structurally different operators even though both "place orders."

The operator profiles, risk files, and Reviewer principles would diverge so much that any shared MANDATE.md becomes lowest-common-denominator ("submit orders that match rules") — which is exactly the discretionary framing ADR-207 rejects.

## The Actual Stress Test

ADR-188 claims registries are contextual template libraries, not validation gates. Framework primitives (output_kind, agent roles, task modes, pipeline) are fixed; domains, tasks, agents, step instructions are contextual.

alpha-polymarket is a cleaner test of that claim than alpha-trader was, because:

- alpha-trader reused existing `TASK_TYPES` (trading-digest, trading-signal, trading-execute, portfolio-review) that were authored with trading in mind.
- alpha-polymarket would have to scaffold *without* registry-authored templates — pure TASK.md self-declaration per ADR-207 P4b.

**If alpha-polymarket requires new entries in `SYSTEMIC_AGENTS` / `PRODUCTION_ROLES` (the post-LAYER-MAPPING-flip registries in `orchestration.py`) or a new platform-integration agent class, ADR-188 has failed its own test.**

**If it only needs:**
- A new `PolymarketClient` in `api/integrations/core/` (platform API, same pattern as `alpaca_client.py`)
- Platform capabilities added to `CAPABILITIES` dict in `orchestration.py`
- MANDATE.md + `_operator_profile.md` + `_risk.md` + `principles.md` authored by operator
- TASK.md files self-declaring `Required Capabilities`, `Context Reads/Writes`, `Process`, `Team`

…then the domain-agnostic framework thesis holds.

## What Would Be Hand-Authored vs Emergent

**Hand-authored (framework extension — minimize):**

- **`PolymarketClient`** in `api/integrations/core/polymarket_client.py` — wraps three public APIs:
  - **CLOB API** (`api.polymarket.com/clob`) — orders, cancellations, positions, live orderbook. Reads public, writes require L2 auth.
  - **Gamma API** (`gamma-api.polymarket.com`) — market metadata + per-market `feeSchedule` (varies by category, must be read dynamically, not hardcoded).
  - **Data API** (`data-api.polymarket.com`) — historical trades, market history, wallet trade history. Fully public.
- **Capability entries** in `CAPABILITIES` dict — `read_polymarket` (unauthenticated, rate-limited 60 req/min) and `write_polymarket` (requires signed orders).
- **Auth subsystem** — this is the biggest lift and the hardest structural difference from Alpaca/commerce:
  - **Wallet infra**: Polygon wallet per operator, private key storage, MATIC for gas (~$0.50/order). USDC-only collateral.
  - **L1 (wallet → API creds)**: one-time EIP-712 sign against `ClobAuthDomain` v1 chain 137 → `POST /auth/api-key` → receive `apiKey + secret + passphrase`. These are the stored credentials, analogous to Alpaca's API key + secret.
  - **L2 (per-request)**: every request adds 5 HMAC-SHA256 headers (`POLY_ADDRESS`, `POLY_SIGNATURE`, `POLY_TIMESTAMP`, `POLY_API_KEY`, `POLY_PASSPHRASE`). Standard HMAC, reusable across requests.
  - **Per-order EIP-712 signing**: even with L2 auth, each order payload is locally signed with the private key. This is a deliberate security boundary (API compromise alone can't trigger trades) and means the Scheduler service needs private key access, not just encrypted API creds. **This is the biggest operational security concern** — revisit storage model before implementation.
  - **SDK**: `py-clob-client` v0.34.6 (Feb 2026, 1.1M monthly PyPI downloads) is production standard. 96 open issues including round-down bugs on market orders and missing HTTP timeout config — pin version, wrap defensively.
- **Secret storage** — `INTEGRATION_ENCRYPTION_KEY` (Fernet) currently handles OAuth tokens. For Polymarket it would need to hold (a) wallet private key, (b) API key/secret/passphrase. Private key at rest is a material escalation from OAuth tokens — OAuth tokens can be revoked, private keys are permanent until the wallet is drained and replaced.
- **Gas/float monitoring** — new agent responsibility or back-office task: detect low MATIC balance, alert operator before orders start failing. Not needed for Alpaca (brokerage funds execution internally).

**Emergent (operator-authored per ADR-207):**

- MANDATE.md with Polymarket-specific Primary Action
- Context domains (`wallets/`, `markets/`, `news_mappings/`) — materialize on first-write
- Tasks (wallet-digest, market-scan, mispricing-signal, execute-order) — self-declared in TASK.md
- Reviewer principles — discrete-outcome risk framework
- Rate-limit handling in agent orchestration — CLOB POST /order caps at 3,500 per 10s burst and ~60/sec sustained; exponential backoff is a runtime concern, not a registry concern

## Realism Check On The Origin Post

The LinkedIn post that sparked this is aspirational packaging. Specific tells:

- $25 → $4,237 (~170x) across 94 trades on Polymarket with a $25 bankroll implies sub-dollar positions that can't compound like that without absurd edge. Slippage + gas fees + fee ladder would shred it.
- "Scanned 10,000 wallets, cross-referenced win rates" is real data-work (multiple days, not one evening).
- "Reads live news, maps to markets, detects mispricing, Kelly sizing" — four real systems stacked into one overnight build is the fantasy beat.
- The 11:47 PM deploy → wake up to $4,237 narrative is LinkedIn-genre convention. Real operators don't trust day-one overnight runs.

**But the pattern is exactly YARNNN's thesis:** information asymmetry + autonomous execution + supervised review loop. The story is fan fiction; the edge it describes is real.

## Preconditions For Unparking

Before promoting this to an active alpha persona:

1. alpha-trader E2E must complete (currently through observations 01–07 as of 2026-04-22).
2. alpha-commerce E2E must complete.
3. ADR-188 Phases 3–5 must be implemented (TP composition guidance, contextual roster, doc alignment) — otherwise alpha-polymarket just becomes another hand-authored domain and the stress test is invalidated.
4. A real operator willing to supervise. Polymarket P&L math is cleaner than equities in some ways (discrete outcomes), nastier in others (resolution risk, liquidity traps). This needs a human who can author honest `principles.md` based on actual experience.

## Security Escalation vs Alpaca / Commerce

Worth calling out before this is unparked: every prior platform integration stores **revocable credentials**.

- Slack / Notion / GitHub: OAuth tokens, revokable by user in provider UI.
- Alpaca: API key + secret, revokable in Alpaca dashboard.
- Lemon Squeezy / Commerce: API key, revokable in provider dashboard.

Polymarket requires storing a **Polygon wallet private key** on the YARNNN backend. If the key leaks, the attacker can drain USDC and MATIC directly; there is no "revoke" equivalent. The operator must transfer funds to a new wallet.

Mitigation paths, in ascending order of engineering cost:

1. **Hot wallet with small float** — operator keeps main USDC holdings in cold wallet, transfers only working capital to YARNNN-managed hot wallet. Matches how CEXes operate. Simplest; accepts that compromise = loss of float.
2. **Delegated trading via proxy contracts** — Polymarket supports EIP-4337 account abstraction in some configs. Operator-controlled master key signs a delegation that permits YARNNN to trade within guardrails (max position, max daily loss) without full key access. Significantly more engineering.
3. **Defer write capability entirely** — alpha-polymarket starts as read-only + proposal-emitting, operator signs each order manually in their own Polymarket UI. Loses the "autonomous overnight execution" narrative but keeps security bounded.

Option 3 is probably the right Alpha-1 scope. Option 1 is the first live-capital step. Option 2 is a separate architectural project.

## Out Of Scope For Alpha-1

- Live capital. Paper/observation-only if revived. Polymarket doesn't have a native paper mode — would need a simulated-order-book layer, which is its own engineering project.
- Auto-approval ladder. Every order human-approved in the Queue, same as alpha-trader.
- Multi-wallet operation. Single wallet, operator-owned, small float.

## Filing Notes

Not a canonical persona folder (no `docs/alpha/personas/alpha-polymarket/MANDATE.md`) because nothing is implemented. Lives as a single proposal doc until unparked.

When unparked, promote to `docs/alpha/personas/alpha-polymarket/` with the standard persona files, and add an entry to `docs/alpha/personas.yaml`.
