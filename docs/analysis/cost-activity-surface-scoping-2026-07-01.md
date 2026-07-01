# Cost & Activity Surface — scoping (Layer 1 of capture-first)

> **Status**: Design scoping (Hat A). Scopes the **Layer-1 capture surface** the capture-first reframe named ([PRICING-CONSOLIDATION-2026-07-01.md](../monetization/PRICING-CONSOLIDATION-2026-07-01.md) §2). **Design-first, grounded in the live production ledger** (queried 2026-07-01). No pricing content. Names what the surface renders, what it reads, the one data gap it's blocked on, and the build sequence. **Not a build order yet — a scope for one.**
> **Date**: 2026-07-01
> **Authors**: KVK (operator) + Claude (collaborator)

---

## 1. The live standing (production, queried 2026-07-01 — ground truth, not inference)

The entire live cost ledger is **12 `execution_events` rows, 2 users, ~$0.90 total spend** (a dev/eval workspace). What it actually captures:

| Fact | Receipt |
|---|---|
| `execution_events` is keyed on **`user_id`** — **no `principal_id` column** | 20 columns queried; `principal_id` absent. |
| The ledger records **only LLM calls** | The 12 rows: `bare-steward-sweep` (Freddie evals), `mcp-foreign-write-review` (interop writes → Freddie), one `addressed` chat, one `web-search`. No substrate-write rows, no `recall`/`trace` rows (those are $0 LLM → never written). |
| **The interop face fires in production but is un-attributable** | 5 `mcp-foreign-write-review` rows = an external LLM wrote to the substrate and Freddie reviewed. Cost charged to the **owner's `user_id`**; the ledger **cannot say which external principal caused it.** |
| `cost_usd` per row is present + honest | Freddie sweeps ~$0.08–0.16; interop reviews ~$0.03–0.08; web-search ~$0.004. |

**The finding that sets the scope**: the moat is already firing in production (external LLMs writing, Freddie reviewing, real money spent) and **the ledger cannot attribute it to a principal.** The capture surface's whole value — "who spent what" — is blocked on exactly one absent column.

## 2. What EXISTS today (the surface is NOT greenfield)

| Surface | Route | Renders |
|---|---|---|
| **Budget pane** | `/agents?…pane=budget` (from `/budget`) | Freddie's spend envelope: "$X of $Y used, $Z left, ~N days runway" (`GET /api/budget`). One workspace number. |
| **Activity / Runs** | `/recurrence?…pane=activity` (from `/activity`) | `ActivityLog.tsx` — `execution_events` grouped by slug, with per-slug success/failed counts + summed cost. *"Did my recurrences run, what did they cost?"* |
| **Members** | Settings → Access | `WorkspaceMembersCard` — the `principal_grants` roster (who's in the workspace). Read-only. |
| **Balance** | Settings → Billing | The account wallet (`balance_usd`). |

**The gap is not "nothing exists" — it's that these four are disconnected, and none joins cost to principal.** `ActivityLog` already groups + sums cost by slug (the rendering muscle exists); `WorkspaceMembersCard` already renders the principal roster (the "who" exists). **The surface is largely a *join* of two things that already render, plus the column that makes the join possible.**

## 3. What the Cost & Activity Surface IS (the scope)

A single legible surface answering one operator question the current four cannot: **"What happened in my workspace, by whom, and what did it cost?"** — the `trace` of spend (capture-first §1).

### 3.1 The legible-not-raw grammar (the render contract)
Three tiers, mirroring the substrate's own compact-index-then-drill model (ADR-159/221/289/340):

1. **Rollup (default, calm)** — a per-principal summary: *"Freddie tidied your substrate 12× · ChatGPT wrote 5× (you reviewed) · web-search ran 1× · $0.90 this month."* Human sentences, not a token table.
2. **Per-principal drill** — click a principal → its actions grouped by kind (sweeps, reviews, writes) with counts + rolled-up cost. (This is `ActivityLog`'s existing slug-grouping, re-pivoted from slug → principal.)
3. **Raw event (opt-in depth)** — the individual `execution_events` row (the `trace` floor): tokens, model, duration, cost. Already rendered by `ActivityLog`; it becomes the deepest tier, not the default.

### 3.2 What it reads (all existing substrate, one new column)
- `execution_events` (ADR-291 cost ledger) — **the LLM-cost actions** + **the new `principal_id`** (§4).
- `principal_grants` (ADR-373/386) — the principal roster (names/roles for the rollup).
- *(later)* the ADR-209 revision chain — **non-LLM substrate actions** (writes, placements) that `execution_events` doesn't capture, if the surface is to show the *full* action matrix and not just LLM calls. **Scope decision needed (§5 Q2).**

### 3.3 Where it lives
Candidates (decide at design-review, not here): a promoted **Activity** surface (the current `ActivityLog` grown from runs-log → action-ledger), OR a new lens on the **Channels** activity group (which already hosts In/Out/Flow), OR a pane on **Freddie** (co-located with Budget, since Freddie is the steward whose spend it mostly shows). Lean: **grow ActivityLog in place** (Singular Implementation — it's already the one `execution_events` body) and re-pivot it principal-first.

## 4. The one data gap it's blocked on: `principal_id` on `execution_events`

**The surface cannot deliver its core value (per-principal legibility) without this column.** Today `mcp-foreign-write-review` rows can't name the external LLM that caused them. This is:
- **ADR-391 §5 item 2** (already named as a Layer-1 capture step).
- **Capture, not pricing** — recording *who acted* is a truth/completeness fix, not a commercial decision. It belongs to Layer 1 by definition.
- **Small + reversible** — one nullable column + populate it at the `record_execution_event` call sites from the caller identity already resolved by `resolve_principal_id` (ADR-373, the principal-id abstraction already exists in `services/supabase.py`).
- **N=1 safe** — for a solo workspace every row's `principal_id` = the owner; byte-identical rollup. The value appears exactly when a second principal (an interop LLM, a persona-agent) acts.

**Without it**, any surface built now is a re-pivot of the run-log that already exists (workspace-level cost, no "who"). **With it**, the surface delivers the per-principal legibility that is its entire reason to exist.

## 5. Open scope questions (for design review)
1. **Does the surface show ONLY LLM actions (`execution_events`) or the FULL action matrix (incl. non-LLM substrate writes via the ADR-209 chain)?** LLM-only is far smaller + ships fast; full-matrix is the true "capture everything" but joins two ledgers. **Lean: LLM-only v1** (it's where all the cost + the interop story is), non-LLM actions a follow-on. *(This keeps v1 honest about being the COST surface; the full action ledger is a v2.)*
2. **Home for the surface** (§3.3) — grow ActivityLog in place vs new lens. Design-review call.
3. **Rollup verbs** — the calm sentences ("tidied", "served", "reviewed") are a render-vocabulary that maps slug/mode → human phrase. Needs a small mapping (kin to the ADR-289 feed row-grammar). Scope it with the FE.
4. **Does the surface show the *balance draw* per principal, or just *action counts + cost*?** (i.e. is it a spend surface or an activity surface?) — the capture-first thesis says show cost honestly; lean **both** (cost is the honest number, activity is the legible framing).

## 6. Recommended sequence (blocked-on-data → design → build)
1. **Close the data gap first**: add `principal_id` to `execution_events` + populate at `record_execution_event` from `resolve_principal_id`. The foundational Layer-1 capture step; unblocks everything; ships independently (the existing surfaces just gain an unused column until the surface renders it). *(This is the operator's earlier "close the gap first" instinct — the design pass confirms it's the true blocker.)*
2. **Design-review the surface** (§3 + §5) against the now-attributed ledger.
3. **Build** the re-pivoted, principal-first, legible-rollup surface.

> **The honest bottom line for "where's the current standing"**: it's four disconnected fragments over a 12-row user-keyed ledger; the capture surface is docs-only; and it's blocked on exactly one column. The design is a *join* of things that already render — once `principal_id` exists.
