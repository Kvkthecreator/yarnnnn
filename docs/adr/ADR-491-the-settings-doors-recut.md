# ADR-491 — The Settings Doors Re-Cut: Billing Behind the Workspace Door, the Governance Panes Collapse

**Status**: Accepted (2026-07-28, operator-ratified — "aligned on the proposed direction and approach in full"). Implemented same day (FE + kernel registry; rides ADR-490's pricing model).
**Date**: 2026-07-28
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Channel (Axiom 6 — where workspace money + governance surface) + Identity (Axiom 2 — whose dial the autonomy pane is)
**Relates to**: ADR-490 (the pricing model this renders), ADR-429 §8/§13.3 (the placement history), ADR-416 D1 (billing authority is a grant), ADR-433 (Budget pane → Pace; the dollar dial retired), ADR-414 D6 (the governance re-allocation map — autonomy per-agent, budget → balance + allocations), ADR-454 D4 (the System group this trims), ADR-405 (witness dial), ADR-407 (three-scope taxonomy)
**Supersedes/Amends**: supersedes **ADR-429 §13.3** (Billing/Usage return to the workspace door — third and final placement flip, made durable below). Completes **ADR-433** (the Budget pane is dissolved — the envelope exists, the pane doesn't). Renders **ADR-414 D6** surface-side (the workspace autonomy pane is named as the system agent's dial).

---

## 1. Why the door moves — and why THIS flip is durable

The placement has flipped twice (ADR-416 follow-on → workspace door; ADR-429
§13.3 → account door, Vercel-style). ADR-429 §8 ruled the door "a rendering
choice the model has made safe," so either is canon-legal. What changed since
§13.3 is the deciding variable: **members are real now** (seats live,
invites shipping). Two consequences the account door cannot express cleanly:

1. A member opening Settings → Billing saw the workspace's plan with
   upgrade/top-up verbs the server refuses them (`_resolve_billing_workspace`
   403s a plain member) — the don't-offer-403-verbs discipline broken.
2. The moment visibility must be role-gated, the content has revealed itself
   as **workspace governance** — and workspace governance behind the account
   door means the account door must know your role in the workspace, which is
   backwards. The enterprise convention (ChatGPT/Claude Team: org settings →
   billing, admin-visible) puts it behind the workspace door.

**Decision D1**: Billing + Usage move to **Workspace Settings** (a BILLING
group between Access and System). The account door tightens to Account +
Connectors (genuinely user-scoped: identity, prefs, personal credentials —
ADR-425). Legacy `settings.pane=billing|usage` links redirect across.

**D2 — gating keys on the grant, not the role enum**: the Billing pane's gate
signal is the server's own 403 from `GET /subscription/status` (billing
authority, ADR-416 D1) surfaced as `isForbidden` — a member sees a calm
"managed by the workspace owner" state, never dead verbs. **Usage stays
visible to every member** — per-member attribution is the commons-legibility
half of the caps model (DP29); only money-management is authority-gated.

## 2. The Budget pane dissolves (D3)

ADR-433 already retired the dollar dial; the pane's remaining content was a
second rendering of other surfaces: % of balance drawn + runway = the Usage
meter's numbers; the money itself = Billing; per-principal draw = member caps
+ "Who used it". Under ADR-490 (usage = PAYG from the balance) the redundancy
is total. The pane, `BudgetCard`, and `useCockpitBudget` are **deleted**; the
**runway line ("~N days at this pace") moves to the Usage pane** (served by
the surviving `GET /api/budget`); the `window` dial drops to the kernel
default (nobody tunes a backstop's sampling window from settings —
`governance/_budget.yaml` remains the runaway envelope, machine-owned). The
`budget` kernel-surface row (search-only, zero live callers) is deleted; a
stale `?pane=budget` falls to the shell's default-pane fallback.

## 3. The Autonomy pane is the system agent's dial (D4)

The enforcement path is already per-agent (ADR-414 §9a: `load_autonomy`
resolves the judgment home; hired agents carry their own sidecar). The
workspace pane's fallback file — `governance/_autonomy.yaml` — IS the system
agent's witness dial. The pane stays (cheap re-frame, ADR-454 D4's group),
relabeled **"System agent"** with copy that says whose dial it is. The
end-state (per-principal governance rows on the Members roster — grant ·
cap · dial, ADR-405 rendered literally) is deferred to the ADR-382
Altitude-3 roster build, and deliberately sequenced AFTER the ADR-445 §9 cap
choke-point closes (a governance row that looks like enforcement must not
precede the mechanism).

## 4. End state

- **Workspace Settings** (the org-settings door): Access (Members) · Billing
  (Billing [authority-gated] · Usage) · System agent (Autonomy) · Danger Zone.
- **User Settings** (the personal door): Account · Connectors.
- Deep-links repointed: UserMenu balance glance, AttentionCenter runway
  warning, the balance-exhausted narrative link → workspace-settings billing.
