# ADR-503 — The Wallet Follows the Grant: One Per-Role Billing Display

**Status**: Accepted (2026-07-29, operator-commissioned — "check what should be the right information to be displayed for usermenu and workspace setting alike, consistent depending on user role"). Implemented same day.
**Date**: 2026-07-29
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Identity (the grant) + Channel (display)
**Relates to**: ADR-405 (the test: which grant — never which species/role label), ADR-490 (2 free seats + PAYG over one shared balance; the Billing door gated on the server 403), ADR-396 §10 (the prepaid balance is legible in dollars; consumption stays activity-shaped), ADR-429 (per-member attribution), DP29 (commons legibility)
**Amends**: ADR-490's display contract with the per-role split below.

---

## 1. The inconsistency

`GET /api/user/limits` was workspace-bound but not authority-gated, while `GET /api/subscription/status` 403s a caller without billing authority. So the two billing surfaces disagreed for a member: the **UserMenu glance showed the shared workspace's wallet** ("Starter · $36.93 left") while the **Billing pane refused them the same fact** (the 403-derived member state). Same fact, two verdicts, keyed on which surface asked.

## 2. The rule

One split, applied everywhere, derived from the same authority the pane's 403 derives from (`has_billing_authority` — owner OR the `billing` grant scope, never the role label):

| Information | Who sees it | Why |
|---|---|---|
| **The wallet** — remaining dollars, pool composition, top-up, plan management | Billing authority only | The money is the payer's fact (ADR-490's door) |
| **The plan tier** | Every member | A workspace fact, already on the Usage pane header |
| **Consumption** — spend, %-share per member, trend, runs | Every member | Activity-shaped commons legibility (DP29, ADR-396) |
| **Balance state** — `balance_low` / `balance_exhausted` booleans | Every member | An empty pool pauses *everyone's* work; the fact must be legible even when the number is not |

## 3. Mechanics

- **Server** (`/api/user/limits`): computes `billing_authority` for the acting workspace; the dollar fields (`balance_usd`, `raw_balance_usd`, `allowance_usd`, `topup_balance_usd`) ship as `null` without it; `balance_low`/`balance_exhausted` ship to all. Enforcement at the wire, not the renderer — a future surface cannot re-leak the wallet by forgetting a check.
- **`deriveBalance`** (the shared model, `lib/subscription/usage.ts`) returns `null` without authority — every consumer inherits the split from the one function.
- **UserMenu**: authority → "Tier · $X left"; member → "Tier · managed by the owner" (low/exhausted variants keep the warning tone, dollar-free). Both open the same Billing pane, whose member state agrees.
- **Attention bell**: the runway warning stays for every member (work stops for them too) — dollar figure for authority, "the owner manages billing" copy otherwise.
- **Workspace Settings → Usage**: the Balance card shows the wallet to authority; the member sees a one-line pointer ("managed by its owner") above the same activity breakdown everyone gets.
- **SubscriptionCard** (Billing pane): unchanged — already 403-driven.

## 4. Fail direction

The authority probe fails **open** (a transient error shows the owner their own wallet rather than hiding it); the wallet's real enforcement is the subscription/checkout verbs' own gates, which are unchanged. `has_billing_authority` itself fails closed internally.

## 5. Validation

`api/test_adr502_503_gate.py` + `tsc` + `next build`. Human verification: the member session's menu shows "Starter · managed by the owner"; the owner's shows the dollars; the Usage pane shows both the pointer (member) and the wallet (owner) over identical activity sections.
