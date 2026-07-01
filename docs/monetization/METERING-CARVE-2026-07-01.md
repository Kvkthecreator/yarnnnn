# The Metering Carve — what a Type-B subscription actually meters vs gates vs leaves free

> **Status**: Design (Hat A). Decides, one level below the model shape, **exactly which matrix rows the subscription meters, which it tier-gates, and which stay free** — grounded in real cost mechanics (queried 2026-07-01). Numbers/tier-prices are NOT set here (that's the pricing ADR); this decides *what is charged against a tier at all*.
> **Date**: 2026-07-01
> **Authors**: KVK (operator) + Claude (collaborator)
> **The model** (decided): **Type-B subscription** (like OpenAI/Anthropic — a paid plan tier with included allowance + overage), **activity transparent but dollar amounts NOT shown to the user** (the Claude-settings pattern: you see *what happened / usage*, not a running $ meter). This doc carves what that plan meters.
> **Sources**: the `execution_events` ledger, `get_effective_balance` RPC, `connector_retention.py`, `embeddings.py`. Builds on [UNIT-ECONOMICS-2026-07-01.md](./UNIT-ECONOMICS-2026-07-01.md).

---

## 0. Double-charge check (the legacy risk, CLEARED)

**Verified clean.** The `get_effective_balance` RPC sums **exactly one ledger** — `SUM(execution_events.cost_usd)` since last refill. The legacy `token_usage` table **no longer exists** (dropped by ADR-291). Every LLM call writes one `execution_events` row; the balance nets against that one sum. **There is one meter and no double-charge.** (This was the real risk the operator flagged; it's a fact-check, and it passed.)

## 1. The three verbs: METER, GATE, FREE

A Type-B plan doesn't meter everything — it meters what *costs per-use*, gates what *costs to hold*, and leaves free what *costs nothing* (or is the acquisition lever). Three verbs, applied to every matrix row:

- **METER** = draws down the included allowance per use (the `execution_events` model). For things with a real, variable per-use cost.
- **GATE** = a tier *ceiling*, not a per-use draw. For things with a real cost to *hold/scale* but not per-use (storage, connector count).
- **FREE** = no meter, no gate. For $0-cost actions AND the deliberate acquisition levers (the moat's reads).

## 2. The carve (every matrix row, with its real cost mechanic)

| # | Action row | Real cost mechanic | **Verb** | Why |
|---|---|---|---|---|
| **D** | **LLM judgment** — Freddie wakes, chat turns, reflection, inference | **Real per-call $** (~$0.08 billed/invocation), recorded in `execution_events` | **METER** | The obvious one. Variable per-use compute cost. This is the allowance-draw. Already built + single-ledgered (§0). |
| **E** | **Consequential ops** — a trade, a publish, the LLM round deciding an external write | **Real per-call $** (the deciding LLM round, in `execution_events`) | **METER** (via D) | Same mechanic as D — it's an LLM round. Not a *separate* meter at launch (the *act* itself is $0 transport; the *judgment* is the metered D-round). Seat-pricing the act is Phase-2 (ADR-334). |
| **B′** | **Interop/recall EMBEDDING** — the OpenAI `text-embedding-3-small` on every `recall`/`trace` fuzzy path + on derive | **Real per-call $ (~$0.00002/query) — OpenAI COGS, NOT in `execution_events`, currently UN-RECOVERED** | **FREE (absorbed by base)** | The one place we spend and don't record. Tiny per-call, but real. **Decision: absorb into the base, do NOT meter** — metering reads is hostile (the ADR-327 D4 principle) and the base covers it. But it must be *acknowledged* as a COGS line the base has to clear (UNIT-ECONOMICS §3). |
| **C′** | **Connector RETENTION** — raw connector history held in `workspace_files` (`inbound/{platform}/`) | **Recurring STORAGE cost** (not per-use; a cost to *hold*) | **GATE** | Real cost to hold, zero cost per-use → a tier *ceiling* (max retention window per tier), not a meter. **Already built pricing-ready**: `connector_retention.py::resolve_retention_days(tier_max_days=)`. The pricing layer passes the tier's max; GC honors it. THE model's first non-LLM tier axis. |
| **C″** | **Connector COUNT / perception breadth** — # of connected platforms, # watches | **Marginal** (each connector = more sync volume, more storage, more derive-wakes) | **GATE** (candidate) | A scale dimension of the commons. Cost is indirect (drives D + C′). A tier ceiling on # connectors is a legible scale axis. *Candidate — confirm demand before gating.* |
| **A** | **Substrate writes** — WriteFile, place, derive-and-cite, EditFile | **$0** (the write is free; the *derive* that precedes it is a metered D-round) | **FREE** | The write itself costs nothing. The judgment that produces it is already metered as D. Metering the write would double-count the D-round. Leave free. |
| **C** | **Perception / connector SYNC** — mechanical `SyncPlatformState`, `TrackWebSources` | **$0 mechanical (zero-LLM)** | **FREE** | Zero cost per-use. The *storage* it produces is gated (C′); the *sync* itself is free. |
| **B** | **Recall / trace READS** (the response, minus the embedding) | **$0** (pure substrate read, no LLM) | **FREE** | The moat's distribution flywheel. Free by design — the base monetizes the asset's *existence*, not each read (UNIT-ECONOMICS: "free to remember"). |

## 3. What this nets to (the plan's actual meters)

Stripping to essentials, a Type-B YARNNN plan has **exactly one meter and two gates**:

```
  METER (draws the included allowance):
    • LLM judgment invocations (D + E)  ← the ~$0.08/call, execution_events
      = the ONLY per-use meter. One ledger. No double-charge.

  GATE (tier ceilings, not per-use):
    • Connector retention window (C′)   ← resolve_retention_days(tier_max_days=)  [BUILT]
    • Connector count / breadth (C″)    ← candidate, demand-gated

  FREE (no meter, no gate):
    • Substrate writes (A)              ← the write is free; its judgment is the D-meter
    • Perception sync (C)               ← mechanical, $0
    • Recall/trace reads (B)            ← the moat flywheel, free by design
    • The recall embedding COGS (B′)    ← absorbed by the base (tiny, un-metered)
```

**The headline**: we meter **compute** (LLM judgment), we gate **scale** (retention, connectors), we give away the **moat's usage** (reads/interop). That is the honest carve — and it maps 1:1 onto the UNIT-ECONOMICS finding (usage-floor = the D-meter; base = the asset + the gates; free reads = the flywheel).

## 4. The transparency contract (activity yes, $ no) applied to the carve

The model shows **activity, not dollars**. Applied to each verb:

- **Metered (D/E)**: show the operator **what ran and how much allowance is left as a USAGE quantity, not a $ figure** — the Claude-settings pattern. "You've used 62% of this month's included activity" / "Freddie ran 240 times", NOT "$21.30 of $34 spent". The $ exists in the backend (`execution_events`) for *our* accounting; the *user* sees usage, not cost.
- **Gated (C′/C″)**: show the ceiling as a **plan feature**, not a meter. "Your plan keeps 30 days of connector history" — a capability line, no draw-down anxiety.
- **Free (A/B/C)**: show as **pure activity legibility** — "Freddie tidied 12×, served ChatGPT 40×". This is the moat legibility surface (the rollup already built), and because it's free, showing it is pure reassurance with zero bill-anxiety.

**So the activity surface stays — but it's a LEGIBILITY surface (what happened), never a BILLING surface (what it cost).** The $ lives invisibly inside the flat plan. This resolves the capture-first↔hide-the-$ tension: transparency of *action*, opacity of *dollars*, because under a Type-B plan the user reasons in *allowance*, not *cost*.

## 4b. Overage + currency — DECIDED (2026-07-01): balance IS the currency, no credit layer

The Type-B defining choice — what happens past the included allowance — is **decided**, and it needs **no new currency**:

- **The plan** refills `balance_usd` monthly (a `subscription_refill` — the included allowance; the machinery already exists, ADR-172).
- **Overage** = **hard-stop at zero**, then **top-up the same `balance_usd`** to keep going (the existing top-up machinery, $10/$25/$50). Closer to the Claude model: a hard stop, and you can buy more usage.
- **No separate credit currency.** `balance_usd` (real dollars, 1:1 with COGS) *is* the "usage you can buy more of." A credit unit with its own exchange rate would be a **second ledger + a balance-sheet liability (unspent credits owed) + a reversal of the ADR-171/172 work-credits deletion** — and it is **not needed**, because the Type-B "show usage not $" contract (§4) already hides the dollar figure at the *display* layer. Hiding it at the *ledger* layer too (credits) is redundant complexity: `balance → COGS` (display-as-usage) does the same job as `credits → $ → COGS` with one fewer layer and zero liability.
- **"Credits" as a UI word is fine** (a friendly label for the balance); a credit *currency* (separate unit, exchange rate, second ledger) is what we avoid. The currency question is not just deferred — under this decision it is **resolved: we don't introduce one.**

**Dividend**: the whole overage path ships on existing machinery — `subscription_refill` + top-up + hard-stop all exist today. The only new build is the *plan-tier record* + displaying *balance-as-usage-quantity*. No new currency, no new ledger, no migration of the money model.

## 5. Open decisions for the pricing ADR (this doc doesn't set them)
1. **The included-allowance unit** (DISPLAY): express the metered D-allowance to the user as invocation-count, an "activity" quantity, or a soft rate-limit (ChatGPT-style)? The *underlying* unit is decided (real $ balance, §4b); this is purely how it's *shown*. (Leaning: a legible activity quantity — on-brand transparency.)
2. **Which gates are v1**: retention (built) is in. Connector-count (C″) — confirm demand before gating.
3. **The base absorbs B′ (embedding COGS)** — confirmed free-not-metered; the pricing ADR sizes the base to clear it (~$0.00002/query, named).
4. **~~Overage behavior~~ — DECIDED (§4b)**: hard-stop + top-up the existing balance, no credit currency. Remaining sub-question: the *tier numbers* (base price + included-allowance size) — the customer-gated last mile (UNIT-ECONOMICS §5).

## 6. What this doc decided
- **One meter** (LLM judgment, D/E) — confirmed single-ledger, no double-charge (§0).
- **Two gates** (retention C′ built; connector-count C″ candidate) — scale, not per-use.
- **Free** — substrate writes, sync, and the moat's reads/interop; the embedding COGS absorbed by the base.
- **Transparency = activity, not $** — the surface shows what happened + allowance-remaining as a usage quantity, never a running dollar meter.

The metering shape is now carved. The pricing ADR sets the numbers, the allowance unit, and the overage behavior (§5) on top of this carve.
