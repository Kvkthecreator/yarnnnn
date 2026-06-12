# ADR-339 — The Operator Experience Model: Mirrors, Compositions, and Attention

**Status:** **Accepted (2026-06-12)** — framing + program-of-work ADR. **P1 IMPLEMENTED same day**: AttentionCenter shipped as a separate top-bar chrome item (`web/components/shell/AttentionCenter.tsx` — badge + dropdown derived from pending `action_proposals` + ADR-219 material-weight narrative + low-balance runway; localStorage read-cursor; zero stored state; rows deep-link via `foregroundSurface`); Budget chip absorbed Balance chip (`BalanceStatusItem.tsx` DELETED, cluster 4→3, `StatusItemPopover` gained an optional secondary footer for the Budget/Billing dual edit-target). Gates: `api/test_adr339_p1_attention.py` 27/27 · ADR-327 30/30 · ADR-297 148/148 · ADR-338 runway 27/27 · `tsc --noEmit` clean. P1 deviation log: warnings class implements low-balance only (budget-runway + capability-gap warnings join when their derivations earn rows); proposal/event rows deep-link to the surface (Queue/Feed), per-item anchors deferred. Phases 2–4 follow audit-first (ADR-338 precedent). **Resolves and closes ADR-338 §7** (the standing question on consequence-legibility and where the OS analogy points).
**Date:** 2026-06-12
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** [`operator-experience-model-2026-06-12.md`](../analysis/operator-experience-model-2026-06-12.md) — the full arc: presenting symptom (founder cannot tell where to look for work; launcher reads as a wall of peer tiles), macro diagnosis (three layers of the OS analogy, Layer 3 unmined), the mirror/composition finding, the derived standing loop, attention-as-derived-routing, the five-chrome-roles observation, the Home correction, and the 17-surface census. Empirical trigger: walking the live launcher and top-bar against the founder's own first-person use.

**Extends:** ADR-222 + ADR-338 D2 (the OS framing gains its **experiential layer** — where the operator dwells, and how often each surface is visited — completing the structural and pedagogical layers), ADR-245 (the L1/L3 discipline is lifted from the file level to the experience level), ADR-312 (the composition contract is generalized from Home to the act-set).
**Amends:** ADR-338 (§7 resolved — see D7), ADR-297 (D20 status cluster consolidated per D3; launcher grouping re-derived per D5; os-config surfaces move window-grade → pane-grade per D4, a `kernel_surfaces` registry change), ADR-309/ADR-312 D5 (registers **remain** as code-level taxonomy and **stop being the user-facing sort key**), ADR-327 (the budget chip absorbs the balance display), ADR-331 (`/setup` keeps its nature and entry paths; its nav tier moves to Utilities).
**Preserves:** ADR-297's mirror discipline (every substrate concern keeps exactly one faithful surface — nothing is deleted), ADR-245 L1/L2/L3, ADR-307 (one gate, one queue — the Queue remains the singular decide surface), ADR-329 (Files first-class), ADR-312's program-weighting contract (kernel owns slots; programs weight/label/shape; kernel never invents a program noun), ADR-219 narrative weight taxonomy, ADR-153 (no shadow state — load-bearing in D3), Derived Principles 12, 16, 26, 28.

---

## 1. Problem statement

Every surface is locally defensible — each has an ADR, a substrate, a register, a passing gate — and the whole does not cohere. The founder's own report: *"I'm confused where I'm supposed to look for work. Queue, feed, activity, recurrence seem similar yet different… the constitution surfaces seem like flat set-ups."* ADR-338 §7 had already frozen bottom-up patching ("no more panes, no consequence-copy bolted on piecemeal — the fix is a framing decision"). This ADR is that framing decision.

The diagnosis (discourse §2): the macOS analogy has three layers — **structural** (where things live; mined by ADR-222/309/312/338-D2, sound), **pedagogical** (how consequence is taught; named by ADR-338 §7, undecided), **experiential** (where the operator dwells and how often each surface is visited; unmined). The launcher groups by architectural register verbatim (`Launcher.tsx:62-64`) — kernel taxonomy doing double duty as experience taxonomy. 10 of 17 windowed surfaces are constitution/config — the inverse of a desktop OS's surface-time distribution. The most consequential consent surface (the Queue — ADR-338 D2's own "permission dialog") is a pull destination, where a real OS makes consent push.

## 2. D1 — Two surface classes: Mirror once, compose few

**The surface census has two classes that canon never separated:**

- **Mirror surface** — one surface ↔ one substrate concern. Complete, neutral, faithful. ADR-297 built this class exhaustively (sources, autonomy, budget, principles, files, activity, recurrence, agents…). Mirrors are correct, are not reworked by this ADR, and are never deleted: they are the escape hatch, the `/proc` of the OS.
- **Composition surface** — one surface ↔ one operator-**act**. Selective, opinionated, program-weighted, synthesized over many substrates. Exactly one existed at ratification: Home (ADR-312) — the proof of the pattern, not a finished instance (D6).

**The ratified principle** (canonized as FOUNDATIONS Derived Principle 29 in the same commit):

> **Mirror once, compose few.** Every substrate concern earns exactly one mirror surface — complete, neutral, the escape hatch. The operator experience is carried by a small fixed set of act-shaped compositions — kernel-owned, program-weighted — one per act of the operator's standing loop, which is derived from the four flows × the consent line, not from a persona. Compositions foreground; mirrors are reachable from compositions, never the default. Attention-routing is an OS responsibility — derived from substrate, never stored — not a destination.

This is ADR-245's L1/L3 discipline lifted one level: L1 raw view is the file-level escape hatch and L3 the file-level interface; mirrors are the *experience-level* escape hatch and compositions the *experience-level* interface. The pre-ADR-339 launcher was L1-weighted at the experience level.

**No new noun above "program."** The "apps that use the system configuration" intuition is satisfied by the existing ADR-312 contract extended from Home to the act-set. Programs remain the opinion layer; the kernel owns act-shaped slots.

## 3. D2 — The operator standing loop, derived (not a persona bet)

macOS serves a billion user-shapes; macOS itself does not — apps do. The OS commits to a tiny biased set of universal *acts*. YARNNN's equivalent act-set is **derived from ratified structure**, hence persona-free: the four flows (DP26) say what the operation does; the consent line (ADR-338 D3) says which moments belong to the operator. Crossing them:

| Act | What it is | Frequency | Carried by |
|---|---|---|---|
| **Decide** | consent moments — queued proposals, attestations | as-routed | Queue (badge/center-routed, D3) |
| **Read** | what happened since I last looked | daily | Feed + attention center |
| **Dwell** | where the operation stands | daily | Home (D6) |
| **Tune** | adjust granted allowances | occasional | System Settings (D4) |
| **Amend** | constitution authorship | rare | Home constitution band → constitution mirrors |
| **Setup** | become operational | once, re-enterable | `/setup` (ADR-331; Utilities tier per D5) |

The *content* of each act is program-specific; the *shape* is kernel. Programs weight the acts exactly as they weight Home's slots today.

## 4. D3 — Attention routing is an OS responsibility, derived never stored

Queue / Feed / Activity / Recurrence blur because all four are time-shaped reads over the operation's events, distinguished only by which substrate they mirror — a system-side distinction. The operator-side resolution is **three attention channels**, none of which owns state:

1. **Badges / menu-bar vitals** — persistent, glanceable (principle behind ADR-338's vitals, now named).
2. **The attention center** — one top-bar item: badge count + dropdown aggregating "what wants me since I last looked," every row a pure deep-link into its real home (Queue item / Feed entry / pane). Routing only; no content of its own.
3. **Dialogs** — in-the-moment consent only when the operator is actively present (rare; the product is asynchronous-first).

**Binding discipline — attention is derived, never stored.** No `notifications` table (the ADR-153 shape of mistake). The derivation substrate exists and is ratified: pending `action_proposals` → the Decide badge; the narrative weight taxonomy (material / routine / housekeeping, ADR-219; mechanical fires silent per ADR-277) → "material events since last seen"; budget runway + capability gaps → the warning class.

**Top-bar placement (grounded in `web/components/shell/system-status/`):** the `SystemStatusCluster` (ADR-297 D20) is the Control-Center analog — standing **state**. The attention center is a different chrome role — **events** — and ships as a separate top-bar item, never an overload of a status chip. Two consolidations land with it:

- **Budget absorbs Balance.** `BudgetStatusItem` (envelope + queue depth, ADR-327) and `BalanceStatusItem` (account funds) are two adjacent money chips; runway is only honest as envelope *paired with* funds (ADR-327 D8's own logic). One money chip: budget window + balance + observed burn; Billing settings stays as popover footer + UserMenu link. Cluster: 4 → 3 (Autonomy · Money/Runway · Connections) + the attention item.
- **UserMenu stays account-only** (profile, billing, sign-out) — neither an attention nor a state channel.

Consequence: **mirrors stop being attention destinations.** Queue remains the full decide surface (ADR-307 preserved — one gate, one queue); the operator arrives by routing, not by remembering. Activity and Recurrence reclassify as Utilities.

## 5. D4 — System Settings consolidation (window-grade → pane-grade)

The seven os-config launcher tiles (budget, autonomy, program, settings, connectors, sources, setup-reference) fold into **one** System Settings surface with sidebar panes, second-order grouped:

- **Perception & transports** (the drivers): Connectors, Sources
- **Governance** (the dials): Autonomy, Budget
- **Program** (the lifecycle): Program management, re-run Setup
- **General**: account/settings

Depth under one well-named door is cheap; breadth at the top level is expensive — macOS goes third-order (General → About / Software Update / Storage) without confusion. Mechanics: os-config surfaces move from window-grade to pane-grade — a `kernel_surfaces` registry change (parent/pane concept or surface absorption — implementation decides the cleaner shape per Singular Implementation), with summon-index and `navigateToSurface` params following. **Registers (ADR-309/312 D5) remain as code-level taxonomy and stop being the user-facing sort key.** The pane-grade surfaces retain their mirror contracts and deep-linkability.

## 6. D5 — Launcher re-sort and the five chrome roles

macOS separates **Dock** (few, pinned, primary) · **menu bar** (vitals) · **Spotlight** (everything, flat, searchable) · **Launchpad** (all apps, grouped) · **System Settings** (nested config). The pre-ADR-339 launcher performed Dock + Launchpad + Spotlight + settings-map at once; flatness is fine for the Spotlight role and fatal for the Dock role. Target top-level IA (~17 → ~7):

> **Home · Feed · Queue · Files** (the loop: dwell / read / decide / artifacts) · **System Settings** (one door, nested panes) · **Utilities** (Setup, Activity, Recurrence, Agents — present, searchable, de-prioritized)

- **Constitution is reached through its composition** — the Home constitution band (ADR-312 slot #1) routes to the mandate/principles/identity mirrors. The three tiles leave the launcher's top level; the mirrors themselves are unchanged. This resolves the "flat set-ups" report without touching pane content.
- **Setup demotes to Utilities** (operator-proposed; macOS receipt: Setup Assistant is not in the Dock, Migration Assistant lives in `/Applications/Utilities`). Its three entry paths are unchanged: first-run redirect (ADR-331), System Settings → Program ("re-run setup"), launcher search.
- **Search stays flat** across all surfaces including pane-grade ones (the Spotlight role).

## 7. D6 — Home is re-derived, not redesigned (the chicken-and-egg resolution)

Operator correction recorded: Home is directionally right and **not** "fine as is" — unclear what one can do there and where it leads. The dependency is one-directional, not circular: this ADR's framing was derived from the four flows × consent line and the census, independent of Home; Home's final shape is derived **from** the framing. ADR-312's six slots already map ≈1:1 onto the act-set (constitution band → Amend, decision queue slot → Decide, judgment trail → Read, ground-truth hero + live entities → Dwell, recent artifacts → Files): Home accidentally encoded the standing loop before the loop was named — which is why it felt right — but its slots are renderings without act-affordances, the ADR-338 §7 gap recurring at the composition level.

**Ratified target:** Home is the **front page of the compositions** — each slot the glanceable head of one act under the **widget contract**: show state, deep-link into the act's surface. Slot-set, ordering, and affordances become derivable from the act-set; ADR-312's program-weighting contract is unchanged. Until the Home phase lands, Home is an explicitly known-moving target — **no slot-level patching**.

## 8. D7 — ADR-338 §7 resolved (the pedagogical layer)

The A/B question ("where does the management plane teach?") resolves as a **synthesis, derived as a corollary of D1**: teaching lives where acts live.

- **Model B for first contact:** the guided flow (`/setup`, ADR-331 Sequence) teaches consent moments once, in sequence — the Setup Assistant analog.
- **Consequence previews on standing panes:** the D4.5 installer `FlowPreview` pattern generalizes — every yaml-backed pane carries a consequence affordance (what this declaration makes the operation perceive/do downstream), the Night-Shift analog. The composition shows consequence; the mirror shows mechanism.
- **No standalone `/sources` claim to primary nav** — it folds into System Settings → Perception & transports (D4), answering §7.4(c).

ADR-338 §7's status flips to RESOLVED with a pointer to this ADR. The Hat-B evaluation §7.4 reserved remains available as post-hoc measurement, its criterion widened per the discourse: *"can the operator infer, from the launcher alone, what to do next and why."*

## 9. Program of work (phased; audit-first per ADR-338 precedent)

| Phase | Scope | Stability |
|---|---|---|
| **P1 — Attention + cluster consolidation** | Attention center top-bar item (badge + dropdown, derived from proposals/weights/runway); Budget chip absorbs Balance chip (4 → 3); UserMenu unchanged | **Scope-stable now** — invariant under all remaining branches |
| **P2 — System Settings consolidation** | os-config surfaces → pane-grade under one Settings surface; `kernel_surfaces` registry + summon-index + `navigateToSurface`; registers retired as user-facing sort key | After P1; registry change |
| **P3 — Launcher re-sort** | Top-level IA per D5; constitution → Home-band route; Setup → Utilities; flat search retained | Depends on P2 (the fold is what enables the re-sort) |
| **P4 — Home re-derivation + consequence previews** | Home slots → widget contract per D6; pane-level consequence affordances per D7 | Derived from D1–D5; last |

Each phase begins with an FE audit (what exists vs. target, consent-line + class classification) before building — the ADR-338 D4 discipline. Regression gates per phase; ADR-297 parity maintained.

## 10. Open items (named, non-blocking)

1. **Queue window fate** — whether Queue remains a window or becomes primarily center-routed with the window as full-decide fallback (P1 evidence informs; ADR-307's one-queue invariant holds either way).
2. **Home slot details** — exact slot↔act affordance shapes (P4; derived, not designed).
3. **Hat-B evaluation** — the §7.4-reserved measurement, criterion widened; optional pre-P3 checkpoint.

## 11. What this ADR does NOT do

- Does not delete, rename, or rework any mirror surface's content — mirrors stay singular and complete (ADR-297 discipline).
- Does not introduce stored attention/notification state of any kind.
- Does not change the register model in code (ADR-309/312 D5 stands as taxonomy) — only its user-facing projection.
- Does not touch the kernel boundary, primitives, or any backend execution path — this is Channel-dimension work rendered by the existing compositor + ADR-245 model.
- Does not patch Home slots or bolt consequence-copy onto panes ahead of their phases.

**Dimensional classification:** **Purpose** (Axiom 3 — the operator's ontology of acts) projected through **Channel** (Axiom 6). Canonized as FOUNDATIONS **Derived Principle 29** + GLOSSARY v2.7 (Mirror surface / Composition surface / Attention routing / Standing loop rows) in the same commit.
