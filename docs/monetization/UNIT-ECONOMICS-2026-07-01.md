# Unit Economics — grounded in real production spend (to inform the model shape)

> **Status**: Analysis (Hat A). **Numbers first, to inform the pricing-model decision** — not the decision itself. Grounded in the live `execution_events` ledger (queried 2026-07-01) + the real 2× rate card, NOT invented figures. The goal: know what an invocation, a workspace-month, and a customer actually cost/yield, so the model shape (subscription vs usage vs base+usage) is chosen against economics, not vibes.
> **Date**: 2026-07-01
> **Authors**: KVK (operator) + Claude (collaborator)
> **Sources**: `execution_events` (12 live judgment rows), `telemetry.py::_BILLING_RATES` (2× Anthropic), `STRATEGY.md` (balance/grant structure). Supersedes the ballpark figures in `COST-MODEL.md` (task-pipeline era, pre-Freddie) with real Reviewer/Freddie-loop numbers.

---

## 1. The atomic unit: what one invocation actually costs (real data)

Every dollar flows through one unit — a **judgment invocation** (a Freddie wake, a chat turn, an interop review). The live ledger (12 rows, all judgment mode):

| Invocation kind | Billed (2×) | Our COGS (½) | Fresh input tok | Output tok | Cache-read tok |
|---|---|---|---|---|---|
| `bare-steward-sweep` (heavy Freddie wake) | **$0.08–0.16** | $0.04–0.08 | 11K–46K | 1.4K–3.1K | 55K–134K |
| `mcp-foreign-write-review` (interop → Freddie) | **~$0.06** | ~$0.03 | ~6.9K | ~0.8K | ~47K |
| `addressed` (a chat turn) | **~$0.08** | ~$0.04 | ~10.5K | ~0.7K | ~56K |
| `web-search` | **~$0.004** | ~$0.002 | 2.2K | 50 | 0 |
| **Average judgment invocation** | **~$0.08** | **~$0.04** | — | — | — |

**Three facts that shape everything:**

1. **A judgment invocation is ~8¢ billed / ~4¢ COGS.** Cheap in absolute terms. This is the pay-as-you-go quantum.
2. **Cache dominates.** Every wake reads a 47K–134K-token cached governance envelope but only 6K–46K *fresh* input. Cache bills at 10% of input rate — so the envelope is cheap to re-load, and **our margin structure already depends on caching working** (ADR-291 passes the discount through at exactly 2×; the markup is the margin, not the cache).
3. **Mechanical actions are $0.** Not in the ledger's cost at all. Substrate writes, connector syncs, `recall`/`trace` reads — zero. (The interop *read* face is free; only the interop *write* triggers a costed review.)

## 2. The workspace-month: realistic usage profiles

Scale the ~8¢ invocation to plausible monthly activity. Three operator archetypes (invocations/month × ~$0.08 billed = the balance draw):

| Profile | Chat turns | Freddie wakes | Interop writes | ~Invocations/mo | **Billed/mo** | **Our COGS/mo** |
|---|---|---|---|---|---|---|
| **Light** (personal memory, occasional chat) | 40 | 15 | 20 | ~75 | **~$6** | ~$3 |
| **Active** (daily use, a running operation) | 200 | 120 | 100 | ~420 | **~$34** | ~$17 |
| **Heavy** (multi-principal, high interop) | 500 | 300 | 400 | ~1,200 | **~$96** | ~$48 |

*(Assumes ~$0.08/invocation. Heavy skews cheaper per-call — more interop reviews at $0.06 — so treat Heavy as an upper band.)*

**What this tells us about the current model (pay-as-you-go, $3 grant):**
- The $3 signup grant = **~37 invocations** = a few days of Light use, or one good afternoon of chat. It's a *trial taste*, not a month.
- A Light user spends **~$6/mo**; the old Pro $19/mo (=$20 refill) **massively over-covers** them (they'd never exhaust it). Pro is mispriced *against usage* — it's a commitment/predictability play, not a usage match.
- An Active user (~$34/mo billed) **exceeds** a $20 refill — they'd top up. This is the real revenue profile.

## 3. Margin structure: where the money is (and isn't)

At 2× Anthropic, **gross margin on metered usage is exactly 50%** by construction (billed = 2× COGS). That is the *entire* current margin story. Concretely:

- Light user: $6 billed − $3 COGS = **$3 gross/mo.**
- Active user: $34 billed − $17 COGS = **$17 gross/mo.**
- Heavy user: $96 billed − $48 COGS = **$48 gross/mo.**

**The problem this exposes numerically** (your earlier point, now quantified): our margin is a **50% markup on a commodity we resell.** A Light user nets us $3/mo — below the cost of a single support email. Pure usage-metering doesn't clear the bar of a real business at the *low* end, and at the *high* end we're leaving value on the table (a Heavy multi-principal workspace getting enormous value pays us $48 — priced on *our tokens*, not *their value*).

**And the moat earns $0.** `recall`/`trace` (the differentiator) is free + a small un-recovered embedding COGS. Every number above is *LLM-call* revenue; the durable-memory asset contributes nothing to the columns.

## 4. What the numbers say about each model shape

Now the payoff — testing each candidate against the real economics:

### Pure usage (today: balance, 2× markup)
- **Yields**: $3 (Light) / $17 (Active) / $48 (Heavy) gross/mo. Linear in usage.
- **Verdict**: **floor is too thin** (Light nets less than a support ticket); **ceiling underprices value** (Heavy pays for tokens, not the memory asset). Fine as a *floor*, insufficient as *the whole model*. **The data confirms the reframe: usage alone doesn't clear a business bar.**

### Subscription base (a flat monthly for the substrate)
- **The economics case**: a base decouples revenue from token-COGS. If a base is, say, ~$15–25/mo, it *covers the Light user's usage entirely* (they spend $6) and turns the thin $3 into a healthy margin — because you're charging for the **asset** (durable memory), not the **calls**.
- **The number that matters**: a base only works if the substrate value ≥ the base for a Light user who barely spends. At ~$6 usage, a $19 base is **$13 of pure asset-margin** — *if they'll pay it.* That's the felt-value bet, now quantified: **you need durable-memory-served-everywhere to be worth ~$13/mo to someone spending $6 on compute.**
- **Verdict**: **fixes the thin floor** (converts $3 → $13+ gross), **but bets on felt value** at the exact price point.

### Base + usage (the "free to remember, pay to operate" candidate)
- **The economics**: base covers the substrate + Light usage; heavy operation-usage draws additional metered balance on top.
- Light: $19 base (usage absorbed) = **~$16 gross** (base − their $3 COGS).
- Active: $19 base + ~$14 usage-over-base = **~$16 + $14×0.5 = ~$23 gross.**
- Heavy: $19 base + ~$77 usage-over = **~$16 + $38 = ~$54 gross.**
- **Verdict**: **best of both** — the base rescues the floor, usage captures the heavy tail. The margin curve is healthy across all three profiles *and* monetizes the moat (base) + the compute (usage). **This is where the numbers point.**

### Seats / per-operation (ADR-334, deferred)
- **The economics don't apply at launch** — priced on the autonomy dial, which is degenerate at Rung-1 (Freddie). No consequential operation = nothing to seat-price. Confirmed Phase-2.

## 5. What the numbers tell us to decide (the shape, informed)

The economics point clearly:

1. **Keep usage as the floor** — it's honest, it caps our risk (hard-stop-at-zero), and it's built. But **it cannot be the whole model** — the data proves the low end is unviably thin and the high end underprices.
2. **Add a base** — the *only* lever that fixes the thin floor (converts a $3-gross Light user into a $13–16-gross one) and monetizes the moat instead of the commodity. **The base is where the business is.**
3. **The base's viable range is ~$15–25/mo**, set by two real numbers: it must exceed a Light user's usage-COGS (~$3) by enough to be a business, and it must be ≤ the felt value of durable-memory-served-everywhere (the unvalidated number — the one thing the economics *can't* tell us; only a customer can).
4. **The shape the numbers support = base + metered usage** (the "free to remember, pay to operate" candidate) — healthy margin across Light/Active/Heavy, monetizes both the asset and the compute.

**The one number the economics cannot supply**: the **felt value of the base** to a low-usage user. Everything else is grounded. That single unknown is what a first paying customer resolves — and it's why numbers *inform* but don't *finalize* the model. The economics say "base + usage, base in the $15–25 band"; the market says whether $19 clears.

## 6. Honest caveats
- **N=12 rows, 2 dev users.** The per-invocation cost (~$0.08) is solid (it's mechanical, model-driven). The *monthly profiles* (§2) are modeled from plausible activity, not observed — a real user's invocation-count is the missing empirical. Treat §2's counts as scenarios, §1's per-invocation cost as fact.
- **Cache assumption**: the ~$0.08 depends on the governance envelope staying cached. A cold-cache wake (first of a session) costs more (cache_create at 125%). At scale most wakes are warm; the average holds.
- **Anthropic price moves**: COGS = billed/2 today. If Anthropic cuts rates, our *absolute* usage-margin shrinks proportionally — which is *exactly* the argument for a base (base-margin is immune to Anthropic's pricing). The economics make the base a hedge, not just an upsell.
