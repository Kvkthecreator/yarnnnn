# ADR-433 — The Freddie Budget Pane Is Pace, Not a Dollar Envelope

> **Status**: **Accepted** (2026-07-09, operator-ruled from a live-pane audit). FE-facing reframe of the System Agent → Budget pane; one small backend honesty fix (runway projects against the real pooled balance, not the fictional envelope). No schema, no migration, no gate change.

**Date**: 2026-07-09
**Dimension**: Channel (Axiom 6 — what the steward's door shows the operator) + Trigger (Axiom 4 — pace is the "how hard it works" dial, ADR-327's original thesis)

**Supersedes**:
- **ADR-430 D2** ("Budget pane → allocation-only", which KEPT the `$30/$50/$100/$200` dollar amount presets on the argument "declaring a budget is inherently a dollar act"). That reasoning is reversed here: after the pooled-balance model (ADR-396/429), a *per-agent dollar envelope* is a second, fictional money number disconnected from the operator's real money — the exact confusion the operator flagged. ADR-430's other decisions (D1 Autonomy `never_auto` retirement, D3 Activity→Health relabel, the non-dollar draw-down principle) stand.

**Amends**:
- The `BudgetCard` content contract (ADR-430 D2 → this): the dollar amount presets + the standalone envelope framing are removed; the pane shows Freddie's **consumption against the real pooled balance** (non-dollar %, ADR-396) + its **cadence** (how often it works). The `_budget.yaml` `amount_usd` field stays a backend safety envelope (a runaway ceiling) but is no longer an operator-facing dollar dial.
- `api/routes/budget.py` runway computation — projects `runway_days` against the **real effective balance** (`get_effective_balance`, ADR-396/429), not `amount_usd − spent` (the fictional envelope). This is a correctness fix: today the pane says "~15 days left" meaning 15 days until a $50 envelope that isn't the operator's money runs out.

**Preserves**:
- **ADR-418 D1 / ADR-430** — the pane stays on Freddie's door (it is the steward's activity/cadence surface). Placement unchanged.
- **ADR-396** — dollars are not shown; consumption is a percent. This ADR *deepens* conformance (the pane stops showing the `$30/$50/$100/$200` dollar presets, the last dollar figures ADR-430 left).
- **ADR-391 D3** — money is the workspace's concern, on the billing door, "not an agent concern." This ADR removes the residual money-dial pretense from the agent door.
- **ADR-327** — the *thesis* ("how often the agent works is the allocation problem, you decide the ceiling") is preserved; what changes is that the ceiling is the **pooled balance** (ADR-429), not a per-agent dollar envelope, so the operator-facing dial becomes pace directly rather than pace-via-dollars.
- The `_budget.yaml` schema + `per_wake_ceiling_usd` runaway floor + `min_interval_between_recurrence_fires_seconds` — all unchanged (backend safety, not operator dials).

---

## 1. The problem — the pane shows a fictional number

The System Agent → Budget pane (`system-agent.pane=budget`) presents:

- an **"Allocation"** header: *"the spend envelope for your agent … you decide how much it may cost";*
- a draw-down bar: **"36% used (per month) · 64% left · ~15 days left at this pace";*
- dollar amount presets: **`$30 · $50 · $100 · $200`**, with $50 selected;
- a window selector: Monthly / Weekly / Daily.

Every one of those numbers derives from `governance/_budget.yaml::amount_usd = $50` — a per-agent dollar envelope. But the operator's **actual money** (verified on the live workspace `d5b9029b`) is: **`starter` tier, $44.60 balance + $15 allowance**, one pooled meter (ADR-396/429). The $50 corresponds to nothing the operator pays or holds. A user reads "36% of $50 used, 15 days left" and reasonably believes that is their budget — it is not.

Three shipped ADRs contradict each other on this exact pane:

- **ADR-396**: "**dollar amounts are NOT shown to the user**" (the Claude-settings pattern — activity legible, dollars opaque).
- **ADR-430 D2** (2 days prior): KEPT the `$30/$50/$100/$200` dollar presets, arguing "declaring a budget is inherently a dollar act."
- **ADR-429 §12**: the real model is now **one pooled workspace balance** ($20/mo incl. $15 usage) — which makes a *separate per-agent dollar envelope* redundant.

And the envelope is not even the enforcing gate: `budget.py::window_spend`'s own comment records that the **balance hard-stop (`get_effective_balance`)** is what actually stops spend; `amount_usd` computes a `window_spend` percentage purely for display. So the pane layers a fictional soft ceiling over the real balance gate — and projects "days left" against the fiction.

The operator's ruling: **show pace, not a dollar envelope.**

## 2. Why "pace" is the right axis (not "point it at the real balance")

Two reframes were on the table. "Point the envelope at the real balance" was rejected because it keeps **two money surfaces** — the same draw-down would render here AND on the billing door (ADR-396 already shows balance-as-usage-% there), reintroducing the "which number is my money" confusion at a smaller scale. ADR-391 D3 is explicit: money is the workspace's concern, on the billing door, *not an agent concern*.

The steward's door should answer the question the steward's door is for: **how hard is Freddie working, and how do I tune that?** That is the Trigger axis (pace), which ADR-327 always located here — it just expressed it *through* a dollar envelope because, pre-pooled-balance, dollars were the only ceiling. With the pooled balance now the real ceiling (on the billing door), the agent door is freed to show pace directly.

## 3. Decisions

### D1 — Remove the dollar envelope from the operator surface

The `$30/$50/$100/$200` amount presets and the "spend envelope / how much it may cost" framing are removed from the pane. `amount_usd` remains in `_budget.yaml` as a **backend runaway-safety envelope** (paired with `per_wake_ceiling_usd`) — a ceiling the kernel respects, not a dial the operator sets in dollars on this surface. (An operator who truly wants a hard per-agent dollar cap sets it via chat — the escape hatch — which writes the same field; it is simply not a first-class dollar dial competing with the billing door.)

### D2 — The pane shows consumption (non-dollar) + cadence

What the pane shows becomes:

- **Consumption** — a non-dollar draw-down (percent) of the **real pooled balance** this window (ADR-396 conformance), so the operator sees *how much Freddie is drawing* without a fictional ceiling or a dollar meter. Phrased as pace ("Freddie is working at a steady pace this month"), not as budget.
- **Cadence / window** — the Monthly / Weekly / Daily selector is retained as the **measurement + reset window** for the consumption view (it is a legitimate "over what period do I read Freddie's pace" control), relabeled away from "budget window."
- **A pointer to Billing** — "Manage the workspace balance →" deep-links to the Workspace-Settings billing door (ADR-416), where the actual money lives.

### D3 — Runway projects against the real balance (backend honesty fix)

`api/routes/budget.py` computes `runway_days` from `remaining = amount_usd − spent` (the $50 fiction). It changes to project against the **effective pooled balance** (`get_effective_balance`) — so "~N days left at this pace" means N days until the operator's *actual* money runs out, the only honest runway. When the balance signal is unavailable the runway line stays null (as today — no signal, no false projection).

### D4 — A first-class cadence dial is a deliberate NON-decision (open)

The cleanest end state might be an explicit cadence dial (e.g. Relaxed / Steady / Active mapping to a wake-frequency target). This ADR does **not** build one — it would be a new operator dial with backend plumbing (`min_interval`/wake-frequency mapping) beyond the "stop showing a fictional dollar number" fix the operator asked for. The pane shows *observed* cadence + consumption now; whether the operator should *set* cadence directly (rather than let Freddie self-allocate) is reserved for a follow-on if the observed-only view proves insufficient. Recorded so the next session doesn't silently build it or silently assume it exists.

## 4. What this achieves

- One money surface (the billing door), one honest number. The steward's door stops inventing a second budget.
- ADR-396 fully honored on this pane (the last dollar figures — the presets — are gone).
- "~N days left" becomes true (projects against real money).
- The pane answers its actual job: how hard Freddie works, tunable, without pretending to be a wallet.

## 5. Blast radius

| Target | Change | Decision |
|---|---|---|
| `web/components/workspace-concepts/BudgetCard.tsx` | Remove the `AMOUNT_PRESETS` dollar buttons + the "spend envelope / how much it may cost" framing; reframe the header + copy to pace/consumption; retain the window selector as a measurement window; add a Billing pointer | D1, D2 |
| `api/routes/budget.py` | `runway_days` projects against `get_effective_balance` (not `amount_usd − spent`); new `effective_balance_usd` on the response so the consumption % reads against real money | D3, D2 |
| `web/lib/content-shapes/budget.ts` | `BudgetUtilization.effective_balance_usd` field | D2 |
| `docs/adr/ADR-430` | Status banner: D2 superseded by ADR-433 | header |

*(No `api/prompts/CHANGELOG.md` entry — this touches no prompt, tool definition, or orchestration heuristic; the change is a route calculation + an operator-facing pane, not LLM-facing behavior.)*

Byte-identical for the money model (no schema, no gate, no migration). `_budget.yaml::amount_usd` stays as the backend runaway envelope; only its operator-facing *dollar-dial* presentation is retired.
