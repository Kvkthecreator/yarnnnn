# ADR-340 — The Operator Experience Model: Mirrors, Compositions, and Attention

**Status:** **Accepted (2026-06-12)** — framing + program-of-work ADR. **P1 IMPLEMENTED same day**: AttentionCenter shipped as a separate top-bar chrome item (`web/components/shell/AttentionCenter.tsx` — badge + dropdown derived from pending `action_proposals` + ADR-219 material-weight narrative + low-balance runway; localStorage read-cursor; zero stored state; rows deep-link via `foregroundSurface`); Budget chip absorbed Balance chip (`BalanceStatusItem.tsx` DELETED, cluster 4→3, `StatusItemPopover` gained an optional secondary footer for the Budget/Billing dual edit-target). Gates: `api/test_adr340_p1_attention.py` 27/27 · ADR-327 30/30 · ADR-297 148/148 · ADR-338 runway 27/27 · `tsc --noEmit` clean. P1 deviation log: warnings class implements low-balance only (budget-runway + capability-gap warnings join when their derivations earn rows); proposal/event rows deep-link to the surface (Queue/Feed), per-item anchors deferred. **P2 IMPLEMENTED same day** — the System Settings consolidation (D4): five os-config surfaces (budget · autonomy · program · connectors · sources) are **pane-grade** via the registry `pane_of: "settings"` + `pane_group` model (the "parent/pane concept" option); the `settings` surface is retitled **System Settings**, the one os-config window, with a sidebar of grouped panes (General = the three legacy tabs · Perception & transports · Governance · Program, with the re-run-setup door on the Program pane); `?pane=` is the canonical intra-surface param (`?tab=` legacy alias); `foregroundSurface()` resolves pane-grade slugs to parent window + `?pane=` so all call sites stay pane-blind; viewport + dock filter pane-grade slugs from window mounting; the five old routes are ADR-308 server redirect stubs; the five window page components are DELETED (cards render in the container). Setup stays window-grade (Sequence, ADR-331). Gates: `api/test_adr340_p2_settings_fold.py` 51/51 · registry-parity 15/15 (rewritten to the window-grade contract) · sources 37/37 · ADR-327 30/30 · ADR-297 148/148 + nav 21/21 + D19.6 26/26 · installer 26/26 · `tsc --noEmit` clean. **Numbering note**: this ADR briefly carried the number 339; renumbered to 340 same day after a concurrent lane landed ADR-339 (working-tree perception economics) first — commits `b07167b`/`e35a20e` reference the pre-renumber id. **P3 IMPLEMENTED same day** — the launcher re-sort (D5): every navigable kernel surface declares a `launcher_tier` (`primary` = the standing loop Home·Feed·Queue·Files · `system` = System Settings, the one door · `utilities` = Setup·Activity·Recurrence·Agents · `search-only` = constitution mirrors + Settings panes); the launcher renders **act-tier groups at rest** (Workspace / System / Utilities — ADR-338 IA Move A's register grouping superseded; registers stay code taxonomy) and goes **flat when searching** (every navigable surface incl. search-only + panes, the Spotlight role, D5 honored); pane rows in search are labeled "System Settings pane"; the Home constitution band gains the **ConstitutionLinks trio** (Mandate · Principles · Identity via foregroundSurface) — the band is now the canonical door to the constitution mirrors; the band's autonomy badge repoints to `/settings?pane=autonomy`. At-rest launcher: 17 rows → 9 (4+1+4) + program tiers. Gates: `api/test_adr340_p3_launcher.py` 18/18 · runway-launcher 24/24 (Item-6 assertions rewritten to the tier contract) · P2 51/51 · P1 27/27 · parity 15/15 · ADR-297 148/148 + nav 21/21 · sources 37/37 · installer 26/26 · ADR-327 30/30 · concurrent ADR-339 25/25 · `tsc --noEmit` clean.

**Validation plan (ratified with P3): two-stage checkpoint, not a single post-P4 pass.** **Stage 1 (now, post-P3)**: (a) operator browser smoke walk (ADR-236 validation-checkpoint precedent) — launcher at-rest tiers + flat search, System Settings sidebar + pane deep-links + redirect stubs, attention center badge/dropdown, constitution band trio; (b) the **Hat-B evaluation** reserved by ADR-338 §7.4 with the §10 widened criterion ("can the operator infer, from the launcher alone, what to do next and why"), walked against a real workspace — its findings are the **forcing evidence for P4** (Home is derived, not designed; measuring before deriving is the §7.4 pattern). **Stage 2 (post-P4)**: closing smoke + eval re-run on the consequence-legibility criterion (the Home widget contract + pane consequence-previews are the measured artifacts). Rationale for not deferring all validation to post-P4: P4's shape should be informed by Stage-1 findings, and the P1–P3 surfaces are independently shippable artifacts whose regressions are cheapest to catch now.

**Stage 1 EXECUTED + P4 IMPLEMENTED same day — PROGRAM COMPLETE (P1–P4).** Stage-1 evaluation (`docs/evaluations/2026-06-12-162404-operator-experience-stage1-legibility/`, commit `a3d3625`): C1 launcher PASS (residue = two Utilities summaries), C2 consequence gap confirmed + sized, C3 attention PASS (primitive-slug labels flagged), C4 band door PASS. **P4 shipped the evidence-forced set**: **F1** Activity + Recurrence summaries rewritten in operator vocabulary; **F3** ONE shared proposal labeler (`web/lib/proposal-labels.ts`) — the two pre-existing parallel implementations (Home decision slot's inline map + ProposalCard's formatter) consolidated, AttentionCenter joins; capital verb phrases ("Submit a trade order") at the moment of highest consequence; **F2** consequence previews — the Sources pane teaches the §7.1 chain (declare → perception → wake → Queue) and the Autonomy confirm modal carries a **live** consequence line derived from the actual pending queue at the switch moment ("Right now: N pending capital actions would become eligible to auto-execute…") — derivation-only, no stored state; **D6 audit finding**: the kernel Home slots already satisfied the widget contract (decision slot → /queue, artifacts → /files + /recurrence?task=, judgment trail → decisions.md, constitution band trio per P3) — pinned by gate rather than rebuilt; the remaining D6 horizon (program-weighted slots under the widget contract) is program-side per the ADR-312 contract, not kernel work. Gates: `api/test_adr340_p4_legibility.py` 22/22 · P3 18/18 · P2 51/51 · P1 27/27 · parity 15/15 · ADR-297 148/148 · sources 37/37 · ADR-327 30/30 · concurrent ADR-339 25/25 · `tsc --noEmit` clean. **Stage 2 (closing)**: C2 re-run + closing smoke recorded at `docs/evaluations/2026-06-12-*-operator-experience-stage2-close/`. **Remaining open after close**: the operator's own browser walk (Stage-1 findings §5 + Stage-2 addendum — anthropic criterion, requires human eyes); Queue window-vs-routed fate (deferred, evidence-driven per §10); program-weighted Home slot bindings (program bundles' work). **Resolves and closes ADR-338 §7** (the standing question on consequence-legibility and where the OS analogy points).

**D8 IMPLEMENTED (2026-06-18) — post-program residue cleanup.** The Stage-1-flagged "two Utilities summaries" residue (Activity + Recurrence near-duplicate tiles) resolved by folding Activity to pane-grade under Recurrence (`pane_of: "recurrence"`, the generic P2 mechanism), declaration-led with a Schedule↔Runs lens toggle; Activity body extracted to one shared `ActivityLog` component (Singular Implementation); `/activity` becomes an ADR-308 redirect stub → `/recurrence?pane=activity`. Utilities tier 4 → 3. Both substrate reads + deep-links preserved (mirror discipline intact — §12). See §11. Gates: `api/test_adr340_d8_machinery_fold.py` + P3 18/18 · P2 51/51 · ADR-297 parity · `tsc --noEmit` clean.
**Date:** 2026-06-12
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)
**Amended by:** [ADR-367](ADR-367-home-as-operating-cockpit.md) (2026-06-25) — the deferred "Home re-derivation" program item (§9 / the D6 program-weighted-slots horizon) lands as a **cockpit contract**, not the glance-only *widget contract* this ADR's program-of-work named: a Home slot *shows state, allows the primary decision inline, and deep-links for depth*. The decision-queue slot acts in place through the shared proposal modal (ADR-307 gate, no surface jump). DP29's Home-composition clause is amended accordingly.
**Amended by:** [ADR-370](ADR-370-context-surface-the-operations-boundary.md) (2026-06-25) — a **third composition** surface lands (after Home and Notifications): **Context** (In · Out · Flow), one operator act over the operation's boundary. The §9 "launcher IA re-sort" + "mirror once, compose few" arc continues — the `feed` mirror folds into Context as the Flow lens (a mirror becomes a lens of a composition; net top-level surfaces unchanged). The DP29 mirror/composition taxonomy holds: Context is a composition (one surface ↔ one act), its lenses re-mount existing mirror bodies (one body, two mounts — D8). The narrative's appearance in both Notifications → Activity and Context → Flow is **deliberate tiered redundancy** (the ADR-367 D3 macOS principle), consistent with DP29's attention-routing-is-OS-owned clause.

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

This is ADR-245's L1/L3 discipline lifted one level: L1 raw view is the file-level escape hatch and L3 the file-level interface; mirrors are the *experience-level* escape hatch and compositions the *experience-level* interface. The pre-ADR-340 launcher was L1-weighted at the experience level.

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

macOS separates **Dock** (few, pinned, primary) · **menu bar** (vitals) · **Spotlight** (everything, flat, searchable) · **Launchpad** (all apps, grouped) · **System Settings** (nested config). The pre-ADR-340 launcher performed Dock + Launchpad + Spotlight + settings-map at once; flatness is fine for the Spotlight role and fatal for the Dock role. Target top-level IA (~17 → ~7):

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
4. ~~**Machinery residue** — the Stage-1 eval flagged "two Utilities summaries" (Activity + Recurrence) as near-duplicate launcher tiles.~~ **RESOLVED by D8 (§12).**

## 11. D8 — Machinery consolidation (Recurrence + Activity → one launcher entry, two lenses)

**Status: Accepted (2026-06-18), Implemented same day.** Post-P3 residue cleanup, derived directly from D1 + D3, and the Utilities-tier analog of D4's os-config fold.

**The problem (named in D3, sized by the Stage-1 eval):** Recurrence and Activity are two of the four time-shaped mirrors D3 identified as *blurring* ("distinguished only by which substrate they mirror — a system-side distinction"). At the operator layer they are one concern — **the machinery** — seen at two moments: the *declaration* lens ("what's scheduled, what fires when," `_recurrences.yaml` + `_hooks.yaml`) and the *execution* lens ("did it run, did it succeed, what did it cost," `execution_events`). The Stage-1 legibility evaluation surfaced the residue concretely: two adjacent Utilities tiles whose summaries read as near-duplicates. P3 demoted both to Utilities but left them as two peer tiles.

**Decision: one launcher tile, two lenses — declaration-led, execution as drill-down.** Activity becomes **pane-grade** under Recurrence (`pane_of: "recurrence"`), exactly the P2 mechanism (the `pane_of`/`pane_group` registry contract is generic — nothing hardcodes `settings` as the only valid parent). The launcher shows **one** Utilities tile ("Recurrence"); Activity is reached as a lens inside that window (`?pane=activity`) and remains fully deep-linkable. Utilities tier: 4 → 3 (Setup · Recurrence · Agents).

**Why declaration-led (the lens order is derived, not preference):**
1. **Foreign-key direction.** The pre-existing deep-link already flows declaration → execution (`/recurrence?task=X` → "View runs →" → `/activity?slug=X`). Many runs point to one declaration; leading with the declaration keeps the one-to-many pointing the natural way. Execution-led would invert it.
2. **Authored substrate before ledger.** `_recurrences.yaml` is operator-authored, operator-editable, constitution-region substrate (what `Schedule()` writes). `execution_events` is append-only telemetry. "Substrate is the asset, artifacts are the dividends" — read the asset first, drill into its yield. (ESSENCE v14.1.)
3. **Survives the empty workspace.** A fresh program has declarations before it has runs (substrate-forward-when-empty, ADR-312). Execution-led opens empty on day one; declaration-led shows the scheduled shape immediately.

**Mirror discipline preserved (§11 is NOT violated).** "Mirror once" requires each substrate concern keep exactly one faithful surface — it does **not** require each mirror be a separate launcher tile. Both routes survive: `/recurrence` (window) and `/activity` (now an ADR-308 server redirect → `/recurrence?pane=activity`). Each lens still faithfully reads its own substrate; neither mirror's content is deleted or reworked. This is the D4 shape (window-grade → pane-grade) applied to a Utilities pair instead of the os-config set.

**Implementation shape (per D4's "implementation decides the cleaner shape" license).** Recurrence is not a config drawer, so the in-window lens switch is a **two-lens header toggle** (Schedule ↔ Runs), not a SettingsPage-style pane sidebar. The Activity body is **extracted into one shared component** (`web/components/activity/ActivityLog.tsx`) rendered identically by the in-Recurrence pane and consumed by nothing else — Singular Implementation (one Activity body, two never; the old full-page route becomes a redirect stub). The generic window-manager machinery (`foregroundSurface` pane resolution, viewport/dock pane filtering, flat-search "pane" labeling) carries this with zero changes — it was already data-driven on `pane_of`.

**What D8 does NOT do:** does not delete Activity's substrate read, route, or deep-linkability; does not merge the two substrates behind one read (each lens reads its own); does not change Queue (the one genuine *act* among the four mirrors stays primary, ADR-307 preserved).

## 12. What this ADR does NOT do

- Does not delete, rename, or rework any mirror surface's content — mirrors stay singular and complete (ADR-297 discipline). **D8 clarifies the discipline: "mirror once" governs substrate↔surface faithfulness, not launcher tile count — two mirrors may share one launcher entry as panes.**
- Does not introduce stored attention/notification state of any kind.
- Does not change the register model in code (ADR-309/312 D5 stands as taxonomy) — only its user-facing projection.
- Does not touch the kernel boundary, primitives, or any backend execution path — this is Channel-dimension work rendered by the existing compositor + ADR-245 model.
- Does not patch Home slots or bolt consequence-copy onto panes ahead of their phases.

**Dimensional classification:** **Purpose** (Axiom 3 — the operator's ontology of acts) projected through **Channel** (Axiom 6). Canonized as FOUNDATIONS **Derived Principle 29** + GLOSSARY v2.7 (Mirror surface / Composition surface / Attention routing / Standing loop rows) in the same commit.
