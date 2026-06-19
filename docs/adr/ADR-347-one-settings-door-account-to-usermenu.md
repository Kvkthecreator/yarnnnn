# ADR-347 — One Settings Door: the operation's settings; the account lives in the UserMenu

**Status:** **Accepted + Implemented (2026-06-19)** — same session. Supersedes the two-door split of ADR-341 D1/D3/D6. Gate `api/test_adr347_one_settings_door.py`. Sibling gates updated to the one-door contract (ADR-341 / ADR-340 P2/P3 / ADR-346). `tsc --noEmit` clean.
**Date:** 2026-06-19
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** [operator-experience-for-wide-workspace-cases-2026-06-19.md](../analysis/operator-experience-for-wide-workspace-cases-2026-06-19.md) §10 — the operator's standing discomfort with the ADR-341 allocation (*"the governance sub-group should actually be in Workspace"*), grounded against the live registry and surfaced as a seam error: ADR-341 (yesterday) files Governance under System Settings, but ADR-346 (Proposed same arc) §7 names the Operation/Workspace neighborhood as the natural home of the Rhythm · Witness · Expected-Output triad. Canon contradicted itself about where governance belongs; the operator felt it before reading either ADR.

**Supersedes:** ADR-341 D1 (two top-level Settings doors), D3 (the `configure` launcher tier holding two doors), D6 (pane re-homing *into* System Settings). The two-door split is reversed.
**Amends:** ADR-340 D4 (the "one System Settings door" consolidation is corrected, not by re-splitting but by pulling the *account* out to the UserMenu where the human/principal lives — finishing D4's own instinct), ADR-340 P3 launcher tiers (the `system-config` + `workspace-config` pair collapses to one settings tier).
**Preserves:** ADR-312 D5 (constitution stays first-class on the Home band; the Settings Constitution group is the read/manage pane door), ADR-340 D1 (mirror discipline — no mirror's content is deleted or duplicated), ADR-340 D3 (the UserMenu is the account/principal affordance), ADR-307 (one gate, one queue), ADR-320 (the five-root permission topology is unchanged — only its *door projection* changes), ADR-346 (the Operation composition is untouched; this ADR harmonizes the triad's home with ADR-346 §7).

---

## 1. The seam error ADR-341 cut on the wrong axis

ADR-341 split the settings surface into two doors on the **permission-region** line: `governance/` (agent-can't-write) → System Settings; `constitution/`+`operation/`+`persona/` (agent-amends) → Workspace Settings. The line is *substrate-correct* but it answers the wrong operator question.

The operator does not navigate by *"can the agent write this file?"* They navigate by **"am I configuring the machine, or shaping my operation?"** By that test:

- **Autonomy (Witness dial) and Budget (Rhythm) are not machine config.** They are how *this operation* runs — a trader runs autonomous/fast, an A&R scout manual/weekly; as per-operation as the mandate. The `governance/`-can't-write fact is a *permission detail*, not an operator-facing object boundary.
- **The only genuinely machine-level, program-agnostic, cross-workspace things are Billing · Usage · Account.** These belong to the **human/principal**, identical across every workspace the human owns — not to any single operation.

ADR-341 manufactured a "System governs the agent" object by **borrowing Governance from the operation** so the System door would hold something besides account. Remove the borrowing and the System door has nothing operation-shaped left.

## 2. Decision

### D1 — One Settings door (the operation)

There is **one** Settings door. Its slug stays `workspace-settings` for now (the live slug; a rename to `settings` is a deferred cosmetic per ADR-347 §6 OQ1). Its pane groups, top→bottom:

| Group | Panes | Substrate region |
|---|---|---|
| **Constitution** | Mandate · Identity · Principles | `constitution/` + `persona/` |
| **Contract** | Budget (Rhythm) · Autonomy (Witness) · **Expected Output** | `governance/` |
| **Operation** | Program | `operation/` |
| **Perception** | Connectors · Sources | transports |

The **Contract** group is new — it gathers the three machine-readable operating-contract declarations (Rhythm · Witness · Expected Output, per the [heartbeat discourse](../analysis/operation-heartbeat-and-autonomy-as-witness-2026-06-19.md)) in one place. Budget + Autonomy move *in* from the dissolved System Settings door; Expected Output is built into it by the companion ADR-348.

### D2 — The account goes to the UserMenu

Billing · Usage · Account are the human/principal's concern, not the operation's. The `settings` surface (the former System Settings door) is **demoted out of the launcher** (`launcher_tier: search-only` — reachable by flat search + the UserMenu, never a peer door) and becomes the **account window the UserMenu opens.** Its pane set shrinks to **Billing · Usage · Account** (the General group only); the Governance group is gone (moved to the one door, D1).

**Receipt that this is correct (Usage placement, operator-delegated):** the Usage endpoints are `user_id`-scoped, not workspace-scoped — `/user/limits` + `/user/usage-detail` call `get_usage_summary(client, user_id)` / `get_usage_detail(client, user_id)` (`api/routes/integrations.py:1811,1862`), returning the human's `balance_usd` / `spend_usd` (the ADR-171/172 account balance). Usage is the human's spend ledger, the same axis as Billing → UserMenu. The *per-operation* burn signal is not lost: the Contract group's Budget pane shows this operation's `_budget.yaml` envelope + window-to-date utilization (`budget.ts`, computed from this workspace's `execution_events`). The two reads diverge the moment a human runs ≥2 operations — Usage = total spend across operations (UserMenu), Budget utilization = this operation's spend vs envelope (Contract group) — so the placement is future-correct, not just convenient.

The UserMenu gains an **Account** item (alongside Settings + Sign out) that opens the account window. *(Singular Implementation: the account window is the existing `settings` page component with its pane set narrowed; it is NOT duplicated.)*

### D3 — Launcher: one settings tier

ADR-340 P3 / ADR-341 D3's `workspace-config` + `system-config` tier pair collapses. The one Settings door sits in a single **`configure`** launcher tier (the ADR-341 D3 tier name, now holding one member). At-rest launcher:

```
WORKSPACE   Home · Operation · Files   (ADR-346)
CONFIGURE   Settings                   (the one operation-settings door)
UTILITIES   Setup · Recurrence · Agents · Feed · Queue   (ADR-346)
```

The account window (`settings` slug) is `search-only` — not in any at-rest tier; reached via the UserMenu (its primary door) or flat search.

### D4 — Registers unchanged; doors are a view over them

No register change (ADR-340/341 principle: registers are code taxonomy, not the user-facing sort key). Autonomy/Budget keep `register: os-config`; Expected Output is `os-config` (governance-region machine config). Door membership is expressed through `pane_of` only: the three governance panes re-parent `pane_of: "settings"` → `pane_of: "workspace-settings"`, `pane_group: "Contract"`.

## 3. The editability rule (sharpened — supersedes ADR-341 D2's over-generalization)

ADR-341 D2 asserted *"Settings is read-mostly with zero inline substrate editors"* — but the **Autonomy and Budget panes are live inline editors** (`autonomy.ts` `setDelegation/setPause/setNeverAuto`; `budget.ts` `setBudget`; both `WRITE_CONTRACT='configuration'`). The blanket rule was stale — it described only the constitution panes it reasoned about. With governance moving into the one door, the contradiction must be named. The true rule, which the code already follows:

**Editability is determined by *who authors* the substrate, not by which door it sits behind:**

- **Operator-authored** (governance-region scalars/structured contract — Budget, Autonomy, Expected Output) → **inline editor**. The operator owns these exclusively (ADR-320 agent-can't-write); a control is safe.
- **Agent-co-authored** (constitution/persona prose — Mandate, Identity, Principles) → **read + edit-via-chat** (ADR-206 D6; inline editing would race the agent's revision chain).

The rule is now per-pane (which group), not per-door (there is one door). It is *cleaner*, not weaker.

## 4. What this does NOT do

- Does not change the five-root permission topology (ADR-320) — only its door projection.
- Does not delete or duplicate any mirror's content (ADR-340 D1) — the account panes move from one door's General group to the UserMenu-opened window; the governance panes move from one door to another; no content forks.
- Does not touch the Operation composition (ADR-346), the Queue (ADR-307), the constitution Home band (ADR-312 D5), or any backend execution path.
- Does not rename `workspace-settings` → `settings` (deferred cosmetic, OQ1).

## 5. Implementation

- `api/services/kernel_surfaces.py` — `autonomy`/`budget` re-parent `pane_of: "settings"` → `"workspace-settings"`, `pane_group: "Governance"` → `"Contract"`; `settings` container `launcher_tier: system-config` → `search-only`; `workspace-settings` container `launcher_tier: workspace-config` → `configure`. The `settings` summary updates to account-only.
- `web/app/(authenticated)/workspace-settings/page.tsx` — PANE_GROUPS gains the **Contract** group (Budget · Autonomy · Expected Output); renderPane handles them via `BudgetCard`/`AutonomyCard`/`ExpectedOutputCard` (the last from ADR-348).
- `web/app/(authenticated)/settings/page.tsx` — PANE_GROUPS shrinks to the General group (Billing · Usage · Account); Governance panes + their imports removed.
- `web/components/shell/UserMenu.tsx` — gains an **Account** item opening the account window (`foregroundSurface('settings')` already opens it; add an explicit Account entry; "Settings" repoints to the one operation door `foregroundSurface('workspace-settings')`).
- `web/components/shell/Launcher.tsx` — `KERNEL_TIER_GROUPS` collapses `workspace-config` + `system-config` → one `configure` row.
- `web/types/desk.ts` + `web/lib/compositor/types.ts` — `launcher_tier` union: add `'configure'` (the merged tier); `'workspace-config'`/`'system-config'` retired.
- `api/test_adr347_one_settings_door.py` — regression gate.
- ADR-341 / ADR-340 P2/P3 / ADR-346 sibling gates updated to the one-door contract.

## 6. Open questions (carried)

1. **Rename `workspace-settings` → `settings`?** With one operation door + an account window, the operation door is *the* Settings door; "Settings" is the obvious name. Deferred (cosmetic, churns slugs + redirect stubs + gates); the account window would need a non-`settings` slug (e.g. `account`). Tracked, not done here.
2. **ADR-341 D-pedagogy retired:** ADR-341 claimed "the door structure teaches the lock model for free" (sidebar mirrors ADR-320 topology). That pedagogy is given up — Contract (can't-write) sits beside Constitution (can-amend) in one door. Assessment: it was a post-hoc rationalization of a substrate fact, not an operator need; the lock model is taught by the consent line (ADR-338 D3) and the panes' own copy. Small cost; one coherent operating-contract door is the larger gain.

**Dimensional classification:** **Channel** (Axiom 6) projected through **Purpose** (Axiom 3 — the operator's ontology: machine-vs-operation, with the machine going to the principal's UserMenu).
