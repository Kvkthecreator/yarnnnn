# Four-Flow Completeness, the Perception Field, and the Program Floor Reaffirmed

**Date:** 2026-06-10 (fourth session capture, same day)
**Hat:** B (external-developer surface — discourse capture, receipts-grounded).
**Origin:** continuation of the 2026-06-10 regroup, after the scoped ADR session
(ADR-330/331) began running. Sequence: the operator asked whether "reality in"
was conceptualized too small → the perception-field framing → the operator
corrected the "perception is commodity" line → asked whether perception
warrants dedicated architecture and whether it is first-class *now* → diagnosed
why generic workspaces feel "off" → asked for a double-check of the prior
decision NOT to create a default/kernel workspace type, against the new insight.
**Succeeds / refines:** `reality-in-current-standing-and-setup-as-rendering-2026-06-10.md`
(closes its §5.5 open question), `author-blindness-and-invariant-capabilities-2026-06-10.md`
(extends the flows framing).
**Status:** Hardened: the four-flow completeness model, the perception-field
correction, the Direction-A reaffirmation, flow-completeness-as-bundle-conformance.
Fenced: nothing here changes ADR-330/331 scope.

---

## 1. The four-flow completeness model

"Reality in" was conceptualized too small. The full frame sorts on two axes —
*whose reality* (self vs. world) × *when* (past vs. present) — plus one
coupling term:

| | **Past** | **Present** |
|---|---|---|
| **Self** (your platforms, your work) | **Harvest** — the pre-YARNNN archive (ADR-331 territory) | **Live reads + operator-push** (built; shelf-state per the reality-in capture) |
| **World** (reality independent of you) | Field history — the domain's canon (ad hoc via WebSearch; rarely needs more) | **The perception field** — what the operation *watches* (§2). The previously underscoped cell. |
| **Self × World coupling** | **Outcomes-in** — *the world's verdict on your acts.* The consequence pipe (ADR-330). Neither pure self nor pure world — which is why it is the moat's spine. | |

An operating workspace runs **four flows**: perception in (context), work out
(artifacts/transactions/messages), outcomes in (consequences), and the loop
(calibration). 

**The flow-incompleteness diagnosis (the operator's "offness," named):**
alpha-trader feels like an *operation* because all four flows run — it is
currently the only flow-complete instance. A generic workspace has flow 2
fully, fragments of flow 1, and neither flow 3 nor 4 — i.e., a document
generator with a chat interface. The "off" feeling of generic workspaces is
not a UX, ICP, or cold-start problem; it is **flow-incompleteness**. This
explanation supersedes the looser ones used previously (empty substrate,
missing program, cold start) — those are symptoms; the flow gap is the
structure.

---

## 2. The perception field — and the commodity-line correction

**The framing:** not "RSS in" (transport) nor "headless APIs" (mechanism) but
**the operation's field of perception**: the operation *declares* what it
watches (its universe), the system reads it on cadence, **distills** it into
attributed signal substrate, and wakes reactively on thresholds. The trader
runs this end-to-end today — `_universe.yaml` → track-regime / track-universe
recurrences → `_regime.yaml` + per-ticker signal files → signal-evaluation
fires a proposal. Bespoke, program-private, proven.

**The operator's correction (concede + record):** an earlier line called
perception "the least defensible flow in isolation — every AI tool will read
RSS." Wrong emphasis. **No tool can read every signal in the universe.** The
signal space is infinite; therefore *reading* is commodity but **selection is
judgment**: which signals, of infinite possible signals, this operation
watches — declared, distilled, and accumulated over tenure — is authored
substrate, scarce by construction, and part of the asset. ChatGPT can search
the web; it cannot show anyone *their* declared universe's distilled history
under *their* judgment. The corrected statement:

> **Reading the world is commodity. The declared, distilled, tenured
> perception field is not — it is the substrate's world-facing half.**

This also strengthens ESSENCE v14: the cumulative workspace accumulates not
just your work but your *distilled history of the world you operate in*.

**Architecture verdict (asked directly: does perception warrant dedicated
architecture?):** the *pattern* is stabilized (recurrences, wake sources,
mechanical mirrors, attributed writes — all post-collapse kernel machinery);
the *kernel abstraction* is absent (the watch-declaration is trader-private
vocabulary; no generic transport for connectionless workspaces). Verdict: **no
new subsystem** (a "perception manager" with source/freshness state would be
the dual-tracking disease again); **yes a kernel slot** — the same shape the
ground-truth generalization took (`substrate_abi.ground_truth` promoted a
trader-private file to a MANIFEST-declared slot). Perception is **arc 3 of the
same move**: third trader-private pattern promoted to kernel vocabulary.
Sequencing: consequence pipe (ADR-330) → doors/setup (ADR-331) → senses
(arc 3, future ADR) — each makes the previous more valuable. At most one small
generic transport (cadenced web/RSS read) justifies early build so a
connectionless workspace can watch *something*; the rest is demand-pulled.

**Guard:** perception is a flow, never a gate — a workspace with only uploads
and websearch remains valid (alpha-author's lean shape is legitimate).

---

## 3. The structural double-check — Direction A reaffirmed, and strengthened

**What the record actually says** (verified 2026-06-10):

- `docs/architecture/bare-kernel-product-floor-2026-06-01.md` — **Direction A
  RATIFIED 2026-06-01: program-activation is the product floor.** The bare
  kernel is an *inspect-only resting state*. Three code receipts: (1) the
  conversational onboarding agent is dead code in the live feed path (ADR-257
  deleted the System Agent LLM stream; the mandate-first onboarding prompt has
  no caller); (2) `review/IDENTITY.md` has exactly one writer — bundle-fork
  (ADR-286 single-writer); (3) the Reviewer is the only live conversational
  intelligence. A no-program workspace is structurally incapable of starting
  an operation through conversation.
- ADR-240 D1: "Start without a program" exists as an honest secondary card
  ("run the kernel as-is; activate later").
- ADR-222: workspaces don't have types; the program declaration is the
  implicit type. "Workspace type" is a banned term.

**Reassessment against the four-flow insight: Direction A survives and is
strengthened.** The four-flow model gives Direction A its positive account:

> **A program IS a flow-declaration set.** What a bundle ships — oracle +
> `substrate_abi.ground_truth` (outcomes), context_domains + `_universe.yaml`
> + `_recurrences.yaml` (perception), capabilities (transports), deliverable
> specs (work out), plus the Reviewer persona and surfaces — is precisely the
> four flows, declared. "You cannot operate without a program" therefore
> means: **you cannot operate with undeclared flows.** Direction A was the
> right call stated without its deepest reason; the four-flow model supplies
> the reason.

Consequences, in order of importance:

1. **No default program. The §5.5 open question (reality-in capture) is
   CLOSED.** A "default program" would be a flow-declaration set with no
   operation behind it — re-creating the shapeless generic workspace one
   level up. The bare kernel stays a resting state; the singular path is:
   signup → resting kernel → `/setup` (ADR-331) → **pick a program → fork →
   walk the program's declared flows to completeness.** One path, no types,
   no default.
2. **ADR-331's `/setup` sequence is, correctly framed, flow-declaration
   walking** — constitution (purpose) → connect + watch (perception) → bring
   in reality (self-past) → first artifact (work out) → ground truth live
   (outcomes). Setup is the kernel's definition of "becoming operational,"
   rendered as a sequence. This framing is a *lens* on ADR-331, not a scope
   change — fenced below.
3. **Flow-completeness becomes bundle conformance.** The structural fix for
   "alpha-author feels partial" is not product copy — it is that the bundle
   shipped flow-incomplete (no ground truth). Proposal for the arc-3 ADR:
   every **active** program must declare all four flows (or explicitly mark a
   flow N/A with rationale), enforced in
   `api/test_adr287_bundle_conformance.py` per ADR-287 discipline. Mostly
   *naming and gating what already exists* in MANIFEST sections — not new
   schema.
4. **The kernel-slot framing is corrected against last turn's drift:** flow
   slots are **what programs must declare**, not freehand workspace-level
   declarations. A workspace-level declaration path independent of programs
   would quietly revive the freehand-assembly route Direction A closed.
   Operator-assembled programs (the agent-composed application horizon,
   ADR-312) remain the *deferred* answer to the horizontal ambition — when
   that arrives, it arrives as "assembling a program," not as "declaring
   flows without one." Singular path preserved.

---

## 4. Fences + carried items

- **ADR-330/331 scope unchanged.** This doc supplies the *frame* (setup =
  walking a program's declared flows; consequence pipe = the coupling term),
  not new requirements. Perception/arc-3 is explicitly NOT in 330/331.
- **Arc-3 ADR (future):** perception field — watch-declaration kernel slot,
  signal-substrate convention, one generic cadenced web/RSS transport,
  flow-completeness conformance gate. Demand-pull trigger: bundle #3, the
  first non-trader watch need, or alpha-author's post-330 deepening.
- **Canon cascade candidates (operator to ratify):** four-flow model into
  FOUNDATIONS-adjacent canon (likely a short architecture doc or a Derived
  Principle); ESSENCE v14 "cumulative workspace" enriched with the
  world-facing half (§2); GLOSSARY entries (perception field / flow
  completeness / consequence pipe) when arc-3 lands.
- **Carried open:** the ICP lock (evidence-gated) · layman noun · pricing ADR
  · Path-A proof session · operator-assembled programs horizon.
