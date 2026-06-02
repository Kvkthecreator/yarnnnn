# Home-as-Composition — Two-Persona Surface Stress Test

**Date:** 2026-06-02
**Hat:** B (external developer surface — conceptual stress test prior to implementation). This is a finding, not canon. It *recommends* the canon decision drafted in ADR-312; it does not make it.
**Origin:** the ESSENCE v13.0 substrate-first rewrite (commit `c16e862`) surfaced a load-bearing cold-start fork — *what is the bare-kernel workspace's home surface, Files or cockpit?* The operator could not decide. The resolution came not from picking a pole but from running real personas through the question "what is invariant across all of them?" and finding the binary was false.
**Status:** Proposed framing for operator (KVK) ratification. No code, no canon edits in this doc.
**Companion ADR:** [ADR-312](../adr/ADR-312-home-as-composition.md).

---

## 1. The question that produced this

After re-centering the product on authored portable substrate (Phase-1 floor) + judgment layer (Phase-2, additive), the cold-start surface became undecidable as posed: a bare workspace rendered as a *de-activated trader cockpit* (empty money-truth, empty queue, empty faces) → "blank." The fork "Files or cockpit as home?" had no obvious answer because **it was the wrong question.**

The operator supplied a wide persona set to stress the binary: international partnership manager (Malbon USA), record-label co-founder / A&R, alpha trader, alpha author, solo founder, B2B merchandise manager, SCM manager, product designer, front-end engineer, back-end engineer.

## 2. The invariant — same constituents, different weights

Running every persona through "what is the center of gravity of their workspace" yields one structure with shifting weights:

| Persona | Heaviest constituent | Primary output channel |
|---|---|---|
| Alpha trader | work-in-flight (signals→proposals) + judgment trail | external write (orders); money-truth |
| Alpha author | delivered artifacts (the corpus) | substrate artifacts |
| Partnership mgr (Malbon) | accumulated context (partner relationships) | addressed (decks/emails to partners) |
| Record label / A&R | accumulated context (artist roster) + artifacts (contracts, release plans) | mixed |
| B2B merch mgr | accumulated context (catalog/SKUs) + work-in-flight (POs) | external write |
| SCM mgr | work-in-flight (shipments, exceptions — monitoring) | external write + alerts |
| Product designer | delivered artifacts (specs, designs) | substrate artifacts |
| FE/BE engineer | work-in-flight (PRs/issues) + artifacts (code) | external write (commits/PRs) |
| Solo founder | all, unevenly | mixed |

**Every workspace has the same six constituents:**

1. **Standing intent** — why it exists (mandate). *Purpose.*
2. **Accumulated context** — what it knows: domain entities (partners / positions / artists / SKUs / corpus / codebase). *Substrate.*
3. **Work in flight** — what's being produced or decided now (drafts / proposals / PRs / orders / signals). *The live operation.*
4. **Delivered artifacts** — what came out (reports / contracts / published pieces / shipped code). *Channel output.*
5. **Judgment trail** — what's been decided and why. *Phase-2.*
6. **Governance + vitals** — autonomy, pace, budget, connections. *OS config.*

The weight shifts by job; **the weight-shift is exactly what a *program* declares.** The kernel provides the six constituents; the program weights, orders, and labels them. This is the axiom.

## 3. The surface map — one kernel, two operations

Same home contract, six slots top→bottom. Only content, weight, and labels change (program-declared). Empty constituents do not render.

| Home slot (kernel contract) | **Alpha trader** | **Malbon partnership manager** |
|---|---|---|
| **1. Constitution band** (top, collapsible) | "Run a stat-arb edge on a $25k paper book, capital-preservation first." · Reviewer: Simons | "Grow Malbon's international partner network — qualify, structure, close profitable APAC/EU partnerships." · Reviewer: seasoned BD director |
| **2. Ground-truth hero** (program-declared shape) | money-truth strip: P&L, positions value, win rate | pipeline-stage board: partners by stage (prospect→qualified→structuring→active), activation count |
| **3. Decision queue** (ADR-307 generic) | capital actions awaiting approval (orders) | substrate+addressed actions ("draft outreach to X", "structure terms for Y") |
| **4. Live entities** (program-labeled) | "Positions" — open instruments + regime | "Partners" — active relationships + deal stage |
| **5. Recent artifacts** | pre-market brief, weekly review (low weight) | decks, term sheets, recap emails, pipeline report (high weight) |
| **6. Judgment trail** | decisions.md + outcome reconciliation (money) | decisions (pursue/pass/restructure) + outcomes (stage moves, deals closed) |
| *menu-bar vitals* | Autonomy: **autonomous** · Pace: daily · Balance · Alpaca | Autonomy: **manual** · Pace: weekly · Balance · Slack/Notion |

**Observed:** the same kernel renders a stat-arb trading desk and a golf-apparel partnership desk with structurally identical homes and completely different centers of gravity — and neither reads as the other's leftovers. The axiom holds.

## 4. Findings — where the axiom strained (these become the kernel home contract)

- **F1 — the hero slot must be generic ("ground-truth panel"), not "money-truth."** Trader centers a P&L strip; Malbon a pipeline board; author a coherence/publication panel. **Receipt of the trader-skin leak:** `web/lib/content-shapes/money-truth.ts` hardcodes `CANONICAL_L3 = 'TraderMoneyTruth'` — the kernel content-shape is bound to a trader component. The kernel must name slot #2 generically; the trader component is one *program binding*. This is the concrete code instance of the "money-truth = trader-skin in the kernel frame" finding from `sequenced-moat-strategy-2026-06-01.md` §8.
- **F2 — the live-entities slot must be program-labeled.** "Positions" / "Partners" / "Pieces" / "Open PRs" are all *the operation's currently-live entities*. Hardcoding "Positions" leaks the same skin as F1.
- **F3 — the queue is the strongest program-agnostic surface; no change needed.** Trader queues capital actions; Malbon queues substrate+addressed actions; ADR-307's generic gated-action queue (`(primitive, inputs)` + family-shaped `decision_context`) already serves both. Reassurance, not a fix.
- **F4 — autonomy *default* is program-declared, not a kernel default.** Trader runs `bounded`/`autonomous` (rule-bound, capped, reversible-ish); relationship operations (Malbon, A&R) default `manual` (high-touch, hard to reverse — you cannot un-send a partner proposal). The bundle ships the default. → bundle spec / ADR-226 fork.
- **F5 — the constitution band's *empty state IS the onboarding entry.*** Present, collapsible, top; when empty (no mandate) it renders "Declare what this workspace is for / activate a program." The home doubles as onboarding. Resolves the "is constitution a separate surface?" question — it is a *section of the home*, not a tab.
- **F6 — the cold-start home is now obvious.** Bare kernel = empty constitution band (CTA) + slot #4 shows "your authored files" + vitals (Balance, Connections). No ground-truth hero, no queue, no faces — those constituents don't exist yet. **Honest Phase-1 home, not a blank cockpit.** The fork is answered by the model itself.

## 5. Cleanup scope (sized against the codebase)

- **"cockpit" is overloaded into two unrelated things.** Raw counts (`grep -rli cockpit`): web 182, api 50, docs 191. They split into: **(a) the HOME surface** — `slug:"cockpit"`, `/cockpit`, `CockpitPage`, `CockpitRenderer`, `SurfaceRegistry` (the load-bearing rename → `home`); **(b) `/api/cockpit/*` trader DATA routes** — money-truth, positions, regime, signals, indicators, portfolio-history, recent-orders (alpha-trader program data mis-namespaced under "cockpit"). The operator elected to **fold (b) into the same sweep** (one clean pass). Sub-nuance: `/api/cockpit/pace` is a *kernel governance dial*, not trader data — it folds to a kernel location, not the trader-program namespace.
- **Register split** (amends ADR-309): flip `register` for `mandate`/`principles`/`identity` from `settings` to a new `constitution` value in `kernel_surfaces.py` + shell handling. Localized.
- **Substrate-by-role** (consumes ADR-281): the home composes constitution / context / artifacts / trail by role — additive rendering over an existing taxonomy, not a rename.

## 6. Recommendation

Ratify the home-as-composition model with the kernel home contract naming slots #2 (ground-truth hero) and #4 (live entities) generically so no program-skin leaks into the kernel. The decision is drafted in ADR-312. Confirmed operator decisions feeding the ADR: home name = `home`; `/api/cockpit/*` fold = **in scope** (one sweep).
