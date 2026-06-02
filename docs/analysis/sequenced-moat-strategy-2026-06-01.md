# Sequenced Moat Strategy — Substrate-Interop First, Judgment Layer Additive

> **⚠️ STRATEGIC FRAMING SUPERSEDED (2026-06-02) — see [judgment-as-center-2026-06-02.md](judgment-as-center-2026-06-02.md).**
> The substrate-as-product thesis this document built (§2 + §8–§10: "substrate is the
> Phase-1 wedge, judgment is the additive Phase-2 layer") is **corrected.** Judgment is the
> center; the portable attributed substrate is its *trust-medium*, not a standalone product.
> "Attributed files / Dropbox-for-agents" was the wrong center (a *property* cannot pull a
> buyer; it has no day-one job). **What survives:** the §9 as-built substrate audit (property
> inventory, still accurate) and the §10 cross-operator-viral / `user_id → workspace_id`
> re-key analysis (still the right *technical* shape if shared workspaces are ever built).
> **What is superseded:** the Phase-1/Phase-2 service-model center-of-gravity. Preserved
> below as discourse trail; do not treat the phasing as a ratified decision.

**Date:** 2026-06-01
**Hat:** B (external developer surface — strategic discourse capture). This is an
analysis/finding, not canon. It *recommends* canon amendments; it does not make
them. The fix, if ratified, lands in SERVICE-MODEL / FOUNDATIONS / THESIS.
**Origin:** a regroup on "what should YARNNN emphasize" that started from the
ADR-308/309 OS-shell work and converged on a sequencing of [ADR-310](../adr/ADR-310-judged-substrate-interop-face.md)'s
"one moat, two faces."
**Status:** Proposed framing for operator (KVK) ratification. No code, no canon
edits in this doc.

---

## 1. The question that produced this

After hardening the OS-shell (ADR-308 redirect transport, ADR-309 two-register
surface model), the regroup question was: *what should the product emphasize,
coupled with what YARNNN is actually trying to achieve?*

The discourse rejected several framings in turn:
- **cockpit-vs-interop "which leads"** — a false binary (ADR-310 already names both as faces of one moat).
- **"money-truth + cockpit faces" as the universal emphasis** — surfaced as a *trader-program skin* leaking into the kernel frame (an author operation has no P&L; its ground truth is publication/coherence).
- **cold-start vs steady-state lifecycle framings** — rejected by the operator as too state/lifecycle-shaped; the question is qualitative, not temporal.
- **relationship / judgment / accountability as the irreducible noun** — all true but all *descriptions of the mechanism*, not the buildable thing.

The resolution did not come from finding the "right" single emphasis. It came
from **dissolving the lead-face question into a sequence.**

---

## 2. The proposal — one moat, shipped as two sequential phases

[ADR-310](../adr/ADR-310-judged-substrate-interop-face.md) ratified: **YARNNN has
exactly one moat — authored substrate under a persona-bearing judgment seat —
served two ways: a Cockpit face (operator, in-app) and an Interop face (foreign
LLM, via MCP).** ADR-310 presents the two faces as co-present.

This analysis sequences them:

### Phase 1 — Substrate-Interop (the wedge)

**Open the authored substrate to other providers/services first.** Portable
authored context, reachable from any LLM the operator already uses, via the MCP
interop face.

- **Value prop, standalone (no Reviewer required):** *cross-LLM continuity /
  portable memory.* "What you author in YARNNN follows you into ChatGPT, Claude,
  any LLM — attributed, retained, portable." This is valuable with the lightest
  possible substrate — it does **not** require a calibrated Reviewer, a running
  autonomous operation, a money signal, or an activated program.
- **Why it's the wedge:**
  - **Categorically unavailable from incumbents.** No LLM provider offers your
    authored context *across* the others — they are each present-bound silos.
    Portability across providers is structurally something only a neutral
    substrate layer can offer.
  - **Network effect.** Each provider/service the substrate reaches compounds
    stickiness; the substrate becomes the hub the operator routes through.
  - **First product mold.** It is buildable now, valuable now, defensible now —
    it does not bet the early product on the hardest, least-proven piece
    (autonomous judgment).
- **What Phase 1 is, in the moat's terms:** THESIS Commitment 4's portability
  clause, *exercised* — "context travels with the operator across any model, any
  agent layer, any future incumbent." ADR-310 D1 already states the interop face
  "is the portability commitment, exercised." Phase 1 ships **that property
  standing on its own**, before it is judged.

### Phase 2 — The Judgment Layer (additive, supplemental)

**The full autonomous Reviewer / judgment-and-intelligence layer sits ABOVE the
substrate + file management as an additive layer** — not a precondition for any
value.

- This is the layer the discourse repeatedly identified as **over-scoped** when
  treated as the foundation. Its correct position is *on top of* an
  already-valuable substrate, not underneath the whole product.
- It makes the already-portable substrate **judged** (ADR-310's "judged hub, not
  storage hub"): `pull_context` carries judgment provenance, `remember_this`
  contributions are Reviewer-evaluated. It also lights up the Cockpit face (the
  ADR-309 in-app supervisory experience) and program-activation (mandate +
  Reviewer principles + cockpit composition + recurrences).
- **Crucially it is additive, not replacing.** Phase 1 substrate-interop does
  not wait for Phase 2; Phase 2 *deepens* what Phase 1 already delivers. A
  Phase-1 operator has portable memory; a Phase-2 operator has *judged* portable
  memory + an in-app cockpit + an operation that runs in their absence.

### Why sequence rather than co-ship

The operator's stated reason — **preserve both, with a clear-cut sequenced
rollout.** Substrate-interop is the low-risk, high-certainty, buildable-now half;
the judgment layer is the high-ambition, compounding, grow-into half. Sequencing:
- lets value ship before the hardest piece is proven,
- gives a network-effect wedge that accrues while the judgment layer matures,
- and keeps the judgment layer at its *correct altitude* (above substrate), which
  is also where ADR-310 and ADR-216 already place it (Reviewer = the judge above
  the doer; orchestration vs judgment).

---

## 3. The floor this implies (re-grounding the bare-kernel ratification)

The bare-kernel ratification (commits `1272c92`, `06e5782`, 2026-06-01)
established **"program-activation is the product floor."** This sequence
*refines* that:

- **Program-activation (judgment + cockpit) is the Phase 2 floor.**
- **Bare authored substrate, served everywhere, is the Phase 1 floor — below
  program-activation.** Portable memory needs no program.

So the honest layering becomes:

```
Phase 2  ┌─────────────────────────────────────────────┐
(add'l)  │  Judgment layer: Reviewer · cockpit ·         │
         │  program-activation · autonomy · money-truth  │   ← makes substrate JUDGED
         ├─────────────────────────────────────────────┤
Phase 1  │  Authored substrate, served everywhere        │   ← portable memory, the wedge
(floor)  │  (filesystem + MCP interop + attribution)     │
         └─────────────────────────────────────────────┘
```

The substrate is the floor; the program (judgment + cockpit) is what you add on
top. This is cleaner and more honest than treating program-activation as the
*only* floor — it gives a value tier *below* activation.

---

## 4. What this resolves (the discourse gaps, closed)

- **"money-truth is trader-skin" (canon scoped wrong):** confirmed. The universal
  is *authored substrate* (Phase 1) + *judged* (Phase 2, ground-truth flavor
  supplied by the program — money for trader, publication/coherence for author).
  "money-truth" is a Phase-2, program-specific expression, not the kernel emphasis.
- **"everything is empty on day one":** dissolved. Phase 1 is valuable the moment
  the operator authors *anything* and it's reachable elsewhere — no accumulation
  required. The compounding (Phase 2 judgment) is the deepening, not the entry.
- **"which face leads":** dissolved into sequence — interop face leads (Phase 1),
  cockpit face deepens (Phase 2). Both preserved.
- **"what should the operator feel":** Phase 1 → "my context is mine and follows
  me everywhere." Phase 2 → "and it's judged, and it runs without me."

---

## 5. Canon this would amend (named, NOT amended here)

If ratified, this sequence touches:

- **THESIS.md** — currently presents the four commitments as co-equal and
  co-present. Would gain a *sequencing* note: Commitment 4 (authored/portable
  substrate) is the Phase-1 wedge that stands alone; Commitments 1–3 (mandate /
  Reviewer judgment / ground-truth) are the Phase-2 judgment layer added on top.
  The four legs remain the definition of *autonomy*; the sequence is about
  *rollout*, not about weakening the four-legs claim.
- **FOUNDATIONS.md** — Axiom 1 (substrate) is already the floor; would gain an
  explicit statement that the substrate is *independently valuable + portable*
  before judgment (the interop face as a first-class Channel per Axiom 6,
  consistent with ADR-310).
- **SERVICE-MODEL.md** — would gain the two-phase layering as the service's
  rollout shape (substrate-served-everywhere as Phase 1; judgment + cockpit +
  program-activation as Phase 2).
- **ADR-310** — this analysis *sequences* its D1 two-faces; ADR-310 itself stays
  correct (it doesn't claim simultaneity is required). A short amendment note
  pointing to this sequencing would keep the trail coherent.
- **NARRATIVE.md** — external story. The Phase-1 wedge ("portable memory across
  every LLM") may be a *sharper external entry beat* than "cockpit for an
  autonomous operation," because it's the thing no incumbent can offer and it's
  available immediately. Worth re-sequencing the narrative beats around it.

---

## 6. Open questions (for the ratification pass, not resolved here)

1. **Phase-1 boundary:** is *file management / the Files cockpit surface* Phase 1
   (you tend the substrate in-app) or Phase 2 (cockpit is the judgment face)?
   Provisional: substrate authoring + Files browsing is Phase 1 (it's how you
   create the portable substrate); the *supervisory* cockpit (Queue, money-truth,
   Reviewer verdicts) is Phase 2.
2. **What "served everywhere" includes at Phase 1:** MCP (ADR-310) is the obvious
   first interop channel. Are there others (direct API, export) in Phase 1, or is
   MCP the singular Phase-1 interop surface?
3. **Does Phase 1 need ANY judgment?** ADR-310's D2 says interop writes are
   "eventually-judged." Strictly, Phase 1 could ship *read* portability + *attributed*
   writes with judgment deferred to Phase 2 — i.e. the substrate is portable and
   attributed in Phase 1, and becomes *judged* in Phase 2. This keeps Phase 1
   genuinely Reviewer-free.
4. **Network-effect mechanics:** is the network effect per-operator (more LLMs I
   connect = stickier for me) or cross-operator (shared substrate)? ADR-310 D4/D5
   confirm per-operator now; cross-operator (shared workspace) is deferred. Phase 1
   network effect is per-operator breadth, not multi-tenant.

---

## 7. Recommendation

Ratify the sequence. It is **additive and supplemental by construction** — it
preserves the entire ADR-310 moat and the four-legs THESIS, and only commits to
*the order in which the one moat's value is delivered.*

> **Note (added §8–§10 below):** subsequent discourse + an as-built substrate
> audit (2026-06-01) materially refined this. The higher-order frame corrected an
> over-weighting of judgment, the growth-engine question was resolved (cross-
> operator viral), and the audit re-sequenced the phases around what's actually
> shipped. §2's "Phase 1 = interop, Phase 2 = judgment" framing is **superseded by
> §10's three-phase shape.** §1–§6 are preserved as the discourse trail.

---

## 8. Higher-order correction — judgment is a RIDER, not the vehicle

The §2 framing risked centering Phase 1 on judgment (treating "judged substrate"
as the thing the substrate is *about*). First-principles re-derivation at a higher
order, with judgment set fully aside, corrected this:

**What makes a substrate worth pulling from — before any judgment exists?** It is
**the canonical, LLM-native, portable, addressable representation of a body of
authored work.** An LLM consumes it cleanly without re-deriving context from raw
web. That value is real with zero Reviewer in the system.

So the substrate's core value (and the network good) is **a context commons in a
format every LLM speaks.** Judgment is **one *rider* on the substrate** — alongside
attribution, retention, structure — that *enriches* a slice ("this has been
weighed") but does **not constitute** the substrate's value or the network's value.
The vehicle is LLM-consumable authored context; judgment is a passenger.

This restores the original objective (judgment as a participating feature of
context management, not the load-bearing center) while preserving the cross-
operator network — because the network good ("LLM-consumable authored context")
does not depend on judgment to be worth consuming.

## 9. The growth-engine question (resolved) + the as-built audit

**Growth engine — first-principles finding.** ADR-310's "per-operator network
effect" is, strictly, **lock-in / data-gravity, not a network effect** (my value
does not rise when *another* operator joins; it rises when *I* connect more of my
own tools). Three real candidates:

1. **Lock-in (per-operator breadth)** — single-player stickiness; grows linearly.
2. **Shared-workspace (within-org)** — team on one substrate; bounded, sold per account.
3. **Cross-operator substrate (viral)** — A's substrate referenceable by B across
   orgs; the *only* true viral network effect; architecturally distant.

**Operator's chosen bet: #3, cross-operator viral.**

**As-built substrate audit (2026-06-01)** — objective property inventory of what
the substrate actually ships today (FOUNDATIONS Axiom 1 + ADR-209 authored
substrate + ADR-310 interop face):

| Rider / property | Status today | Where |
|---|---|---|
| **Attribution** (`authored_by`, 6-role taxonomy, NOT NULL) | ✅ Shipped, maximally load-bearing | `workspace_file_versions`, `write_revision()` (ADR-209) |
| **Retention / versioning** (CAS + parent-pointer chain + head) | ✅ Shipped, universal | `workspace_blobs` + `workspace_file_versions` (ADR-209) |
| **LLM-native format** (markdown/YAML by enforced convention) | ✅ Shipped, canon | FOUNDATIONS Axiom 1 — *"Files are the universal interface across LLM providers and interoperability protocols (MCP)"* |
| **Per-path / per-revision addressability** | ✅ Shipped | `(user_id, path)` + revision id/offset |
| **Structure / relationships** (domains, CONVENTIONS, `_shared/`) | ✅ Shipped | context-domain topology |
| **Portability / interop (MCP face)** | ⚠️ Partial | 3 MCP tools live but single-tenant; `pull_context` flattens `authored_by` to bare paths; `remember_this` bypasses judgment gate |
| **Judgment-on-served-chunk** | ⚠️ Partial / separate | verdicts ARE substrate (`decisions.md`) but don't attach to MCP-served chunks |
| **Cross-operator addressability** | ❌ Absent | every table scopes `user_id == owner`; no membership table (ADR-310 D5) |

**Two audit findings that reshape everything:**

- **The Phase-1 wedge is ~already built.** The differentiated raw material
  (attributed + retained + LLM-native + structured substrate) ships today. The only
  gap to "portable LLM-native context, per operator, across their LLMs" is the
  **thin, MCP-local finish** (per-request identity = *no schema change*; provenance-
  on-read; judged write). Days, not months. Phase 1 is a *finish*, not a *build*.
- **Judgment was never a separate architecture.** Reviewer verdicts are *authored
  substrate like everything else* (attributed `reviewer:<identity>`). "Adding
  judgment" = letting the judgment rider attach to served chunks — a partial-finish
  item, not a foundational lift. This confirms the operator's "sequence, not
  construct" instinct at the code level.
- **The viral network (cross-operator) is the single biggest / only foundational
  lift** — `user_id → workspace_id` re-key across every substrate table +
  `workspace_members` + RLS rewrite (ADR-310 D5).

## 10. The reshaped three-phase sequence (audit-grounded)

> **Phase 1 — Finish the interop face (the wedge).** Per-request MCP identity +
> provenance-on-read. The substrate properties served are *already shipped*; this
> is a thin MCP-local finish (no schema change). Delivers **per-operator portable
> context** — the lock-in / data-gravity wedge — now. *(File management is Phase 1:
> authoring + tending the substrate is how the portable context is created.)*
>
> **Phase 2 — The judgment rider thickens.** Judged write-back, judgment-provenance
> attached to served chunks. Also mostly MCP-local + substrate-native (verdicts are
> already substrate). Makes the portable context *judged* — the "judged hub, not
> storage hub" differentiation. Additive; the substrate runs *through* a judgment
> pass, no new architecture.
>
> **Phase 3 — Cross-operator addressability (the chosen viral bet).** The one
> foundational lift: re-key substrate scoping, membership, RLS. This is where the
> viral network effect lives. **Demand-gated.**

**The strategic resolution to "no winning GTM = the split is useless":** the
per-operator wedge is so cheap (already-built substrate + thin MCP finish) that
**shipping it generates the demand signal that justifies — or kills — the
expensive Phase-3 re-key.** The cheap wedge *de-risks* the foundational viral bet:
you don't pay the biggest substrate cost on faith; you ship near-free portable
context, learn whether operators want it *portable* (lock-in) before betting they
want it *shared across operators* (viral), and let that signal fund the re-key.
Lock-in and viral are not an either/or up front — lock-in is the cheap step that
earns the right to attempt viral.

**Operator's standing intent: cross-operator viral is the committed destination,
not a hedge** — but reached through the cheap wedge, not by paying the foundational
cost first. (Open: whether Phase 1 should be *built anticipating* the Phase-3
re-key — e.g. not hard-coding assumptions that make the `user_id → workspace_id`
migration harder later.)
