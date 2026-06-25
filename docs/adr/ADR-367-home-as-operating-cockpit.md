# ADR-367 — Home as Operating Cockpit: the dashboard acts in place

> **Status:** **Accepted + Implemented (2026-06-25).** FE-only — no schema, no primitive, no backend, no Render-service change. The inline decision reuses the existing ADR-307 gate + the shared `useProposalModal` (ProposalCard) — one modal path, a new entry point. Gate `api/test_adr367_home_cockpit.py` (FE source-guards; the `web/` package has no JS runner, mirroring ADR-350's gate shape). `web/ tsc --noEmit` clean.
> **Date:** 2026-06-25
> **Authors:** KVK (operator) + Claude (collaborator)
> **Discourse base:** the operator's cockpit-vs-widget regroup (2026-06-25) — *"Home is definitely closer to a cockpit than a widget,"* grounded against the macOS precedent (Control Center vs System Settings as deliberate tiered redundancy; interactive widgets since macOS Sonoma as the "act on what you see" evolution; the pro-app main window as the dense-and-acts-in-place archetype) and against ESSENCE's own word for Home — *"a cockpit — the supervisory surface where the operator … sees pending decisions."* The implementation had drifted to a glance-only widget board; this ADR realigns it to the canon noun.
> **Amends:** [ADR-312](ADR-312-home-as-composition.md) (the six-slot semantics: slots are no longer glance-only deep-link heads — the decision-queue slot **acts in place**; the constitution band gains the standing-obligation read), [ADR-340](ADR-340-operator-experience-model.md) §9 / Derived Principle 29 (the deferred "Home re-derivation" program item lands as a **cockpit contract** — *show state, allow the primary decision inline, deep-link for depth* — not the originally-named *widget contract* of glance + deep-link-only).
> **Preserves:** [ADR-346](ADR-346-operation-composition-surface.md) + [ADR-349](ADR-349-launcher-ia-re-sort.md) (**Notifications stays the full act-workbench — NOT demoted**; the operator chose deliberate tiered redundancy, §D3), [ADR-307](ADR-307-unified-permission-taxonomy.md) (one gate, one queue — Home's inline act routes through the *same* gate via the *same* modal, never a second approval path), [ADR-350](ADR-350-standing-obligation-rendered-surface.md) (the standing band is reused, one body / two mounts), [ADR-320](ADR-320-constitution-region-topological-cut.md) (the band reads persona/governance substrate, never writes it), [ADR-358](ADR-358-layout-mode-canvas-vs-desktop.md) (Home fills the Canvas surface; cockpit density is the operator's default operating view), ADR-312 D6 (substrate-forward when empty → operation-forward when running — cockpit density is *earned*, the cold-start stays calm).
> **Amended by:** [ADR-369](ADR-369-home-split-front-page-and-program-cockpit.md) (2026-06-25, hours later) — the `home` surface splits into two internal tabs (kernel **Home** front page + program **‹Program›** cockpit). The cockpit *density* and the ADR-350 standing band (§D4) **relocate to the program tab** (the standing obligation is program-shaped); Home becomes the calm Layer-1 front page. This ADR's *"acts in place"* principle is **preserved** and now spans both tabs — Home keeps it on the kernel-universal decision queue; the program tab acts in place on its own consequential affordances.
> **Dimensional classification:** **Channel** (Axiom 6 — what the operator sees and where) projected through **Purpose** (Axiom 3 — Home renders the operator's *act*, not only the operation's *state*).

---

## 1. The drift this corrects

ESSENCE calls Home a **cockpit**: *"a cockpit — the supervisory surface where the operator consults performance, sees pending decisions, and audits the judgment trail."* The implementation (ADR-312 D2, the six-slot composition) shipped each slot as a **glanceable head that deep-links away to act**. The decision-queue slot says so verbatim in its own code: *"The Home is a composition glance, not the place you act on each proposal (that's /queue + the Feed)."*

That is the **Today-view / widget-board** model: shallow glance, bounce out to act. It produced the exact friction the operator named — Home shows *"Waiting for your OK · 3"* and then makes the operator leave Home to give the OK. The round-trip is dead weight, and it reads as "where do I actually do anything?"

The fix is not a new principle. It is the canon noun, honestly implemented: **Home is the operating cockpit — a pro-app main window (Stocks, Activity Monitor, a trading terminal): dense, detailed, and it acts on what it shows.**

## 2. The decision

### D1 — Home is the operating cockpit, not a widget board

Home is *where the operator lives* when a program is running — the dense, legible operating view. It does not bounce the operator to a separate surface to perform the highest-value act. Density is **progressive** (ADR-312 D6 preserved): a bare kernel renders the calm constitution CTA; density is earned slot-by-slot as substrate accrues, so the cold-start Author posture is never punished.

This rejects the *widget-board* reading of ADR-340's deferred "Home re-derivation" and replaces it with the **cockpit contract**: *a slot shows state, allows the primary decision inline, and deep-links for depth.* (The widget contract was *show state, deep-link to act* — glance-only. The one-clause difference — "allows the primary decision inline" — is this ADR.)

### D2 — The decision-queue slot acts in place (Singular Implementation: the shared modal)

The Home decision-queue slot's rows become **act triggers**, not links. Clicking a pending proposal opens the shared `useProposalModal` overlay (`components/tp/ProposalCard`) — the *same* modal used by `QueueBody`, the chat-stream `ProposalCard`, and the briefing queue. It shows the full Reviewer reasoning, the structured inputs / substrate diff, and **Approve / Reject through the ADR-307 gate** — as an overlay on Home, **without leaving the surface.** On resolve, the slot reloads and the row drops.

This is Singular Implementation, not a new act path: one modal, one gate, N entry points — Home becomes the Nth. No inline-button bypass (the anti-pattern `useProposalModal` was built to kill in 2026-05-11) is re-introduced; Home routes through the canonical modal like every other surface.

### D3 — Deliberate tiered redundancy with Notifications (the macOS principle)

Notifications (ADR-346/349) **stays the full act-workbench** — Resolve · Activity · Schedule, the bell's destination, the breadth view (full list, history, schedule editing). It is **not** demoted. Home and Notifications now *both* act on the same `action_proposals` through the same gate.

This overlap is **intended**, and it is the macOS resolution, not a defect. Apple ships the same redundancy deliberately: brightness is settable in **both** Control Center (quick, atomic, in-place) and System Settings (deep, thorough); a reminder is checkable from **both** the widget and the app. The rule that keeps it coherent: *the same data/action may appear on multiple surfaces as long as each surface owns one clear primary job and the overlap buys a different interaction cost.* The failure mode is not redundancy — it is two surfaces with the same job and no clear primary.

The primary jobs here are distinct:
- **Home (cockpit)** — the live operating view; *act on what is currently visible, in place.* The 80% case: clear the urgent decision without context-switching.
- **Notifications (workbench)** — the dedicated breadth surface reached from the bell; the full queue, the temporal Activity read, the Schedule editor. Where the operator goes when a yes/no isn't enough.

Same substrate, two interaction costs. The operator chose this tiering explicitly over demoting Notifications.

### D4 — The standing obligation lands on Home

The ADR-350 `StandingBand` (the operation's owed-vs-actual + the Reviewer's standing intent) lifts onto Home's head, directly under the constitution band. The cockpit's first read is *what the operation is on the hook for* — the deepest "to-do," above the discrete decision queue. Same component, two mounts (it also remains in the Notifications "To do" pane). It reads persona/governance substrate and never writes it (ADR-320 preserved); it self-hides when there is nothing to stand on.

### D5 — Slot links target the Notifications composition, not the bare mirror

The slot's "Review →" + overflow links repoint from the bare `/queue` mirror to the **Notifications composition's `resolve` pane** (`to="notifications" params={{ pane: "resolve" }}`) — the post-ADR-349 canonical act surface. A routing-drift fix: the slot was still pointing at the pre-composition mirror.

### D6 — Program-shaped slot depth is a program-scoped follow-on

This pass lands the **kernel-universal** cockpit behaviors (inline decide, standing band, routing) that every workspace inherits. The *program-shaped* density — the dense ground-truth hero and live-entity detail (e.g. the trader's expectancy board, position table) — is **bundle work** (ADR-222: the kernel names the slot, the program shapes it), scoped to the alpha-trader / alpha-author SURFACES.yaml, not this kernel ADR. Noted as the next increment so the cockpit deepens program-by-program without the kernel hardcoding a program noun.

## 3. What this does NOT do

- **Does not demote Notifications** — it stays the full act-workbench (operator decision); the redundancy is deliberate (D3).
- **Does not change the gate, queue, schema, primitives, backend, or any Render service** — FE-only; the inline act reuses the existing `/api/proposals/{id}/approve|reject` path through the shared modal.
- **Does not make Home the only act surface** — the mirrors (Feed/Queue/Recurrence) and Notifications all survive as escape hatches / breadth views.
- **Does not add stored notification/attention state** — DP29's derived-never-stored invariant holds (the slot derives from `action_proposals` live).
- **Does not hardcode a program noun into the kernel** — program-shaped slot depth is bundle-scoped (D6).

## 4. Doc cascade (same commit)

- **New:** this ADR.
- **Amend banners:** ADR-312 (slot semantics — decision-queue acts in place; standing band on the head), ADR-340 (§9 / DP29 — Home re-derivation lands as the cockpit contract).
- **FOUNDATIONS:** DP29 one-clause amendment — the Home composition contract is *show state, allow the primary decision inline, deep-link for depth* (cockpit), superseding the glance-only widget reading.
- **GLOSSARY:** the **Home** entry gains "operating cockpit — acts in place"; the **Attention routing** note records the deliberate Home/Notifications tiering.
- **ESSENCE:** no change — this realigns the implementation to ESSENCE's existing "cockpit" word; cited as the anchor.
- **CLAUDE.md:** ADR ledger entry + surface-model addendum line.
- **No CHANGELOG** — no prompt/tool/orchestration change.

## 5. Validation

- `web/ tsc --noEmit` clean.
- `api/test_adr367_home_cockpit.py` — FE source-guards: (a) `KernelDecisionQueue` imports `useProposalModal` and renders the modal element (acts in place, no row-level `SurfaceLink to="queue"`); (b) `HomeRenderer` mounts `StandingBand`; (c) the slot's deep-links target `notifications` `resolve`, not the bare `queue` mirror.
- Sibling gates unaffected: `test_adr312_home_as_composition.py`, `test_adr350_standing_band.py`, `test_adr346*`, `test_adr349_launcher_ia.py` (Notifications preserved → no demotion assertions break).

## 6. Related

- [ADR-312](ADR-312-home-as-composition.md) — Home as composition (the six slots this deepens)
- [ADR-340](ADR-340-operator-experience-model.md) — operator experience model (the Home re-derivation this lands, as cockpit not widget)
- [ADR-346](ADR-346-operation-composition-surface.md) / [ADR-349](ADR-349-launcher-ia-re-sort.md) — the Notifications act-workbench (preserved, co-equal)
- [ADR-307](ADR-307-unified-permission-taxonomy.md) — one gate, one queue (the inline act's gate)
- [ADR-350](ADR-350-standing-obligation-rendered-surface.md) — the standing band (reused on Home)
- [ADR-358](ADR-358-layout-mode-canvas-vs-desktop.md) — Canvas/Desktop (Home fills the Canvas surface)
- [ESSENCE](../ESSENCE.md) — §The System Shape (the "cockpit" word this realigns to)
