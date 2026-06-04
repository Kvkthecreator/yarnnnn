---
title: Reviewer Occupant Carve-Out — Seat (Substrate) vs Occupant (Module)
date: 2026-06-04
status: framing → ratified as ADR-315
authors: KVK, Claude
trigger: architecture-audit discourse 2026-06-04 (three-domain decomposition + open-core seam)
related:
  - docs/adr/ADR-315-reviewer-occupant-contract.md (the decision record)
  - docs/architecture/reviewer-substrate.md (the seat canon — to be split)
  - docs/architecture/agent-composition.md §3.2.x (occupant-internal partition discipline)
  - docs/adr/ADR-194-reviewer-layer.md (v2 — retracted the "Reviewer ABC")
  - docs/adr/ADR-256-unified-reviewer-invocation.md (invoke_reviewer single entry)
  - docs/architecture/FOUNDATIONS.md (Axiom 1 §4 substrate-as-bus; Axiom 2; DP 15 seats-persist-occupants-rotate; DP 22 persona-frame collapse)
  - docs/architecture/THESIS.md (Path A/Path B optionality; seat-occupant interchangeability)
  - docs/ESSENCE.md (two-layer model: substrate floor + judgment deepening)
---

# Reviewer Occupant Carve-Out

## TL;DR

The architecture audit (2026-06-04) asked whether the persona-bearing judgment
seat could be made **portable, modular, and separately documented** without
reversing the canon's deliberate "the seat is substrate, not an ABC" decision
(ADR-194 v2 retraction). The answer is yes, because the request resolves into a
distinction the canon already draws but never operationalized:

> **The *seat* is substrate (stays substrate). The *occupant* is a module (carve it out).**

A code audit found the carve is **~90% structurally already done** — the
substrate/kernel never imports the occupant; the occupant (`reviewer_agent.py`)
consumes a substrate-assembled context bag through a single function boundary
(`invoke_reviewer(trigger, context)`); the contract (`ReviewerContext` in /
`ReviewerOutput` out) already exists and is even self-named *"Substrate bag
passed by callers."* What is missing is **naming the boundary as a published
contract** and **splitting the docs by domain**. This doc is the framing; the
decisions land in ADR-315.

This carve is also the concrete first instance of the **open-core seam** named
earlier in the audit: the published occupant contract IS the substrate-bus ABI.
Once named, the occupant becomes the swappable/serviceable unit (`external:<service>`
occupant class, already first-class in canon) while substrate + seat + harness
stay as the domain-agnostic kernel.

## 1. The question and the canon tension

The operator asked: *"can we make the persona-reviewer-agent-related documents
and architecture much more portable, modular, carved-out — given that the seat
is substrate and we need a 'seat / operator-on-behalf' which for now is the
Reviewer agent?"*

There is a live tension to thread. ADR-194 v2 **retracted** v1's "Reviewer ABC":
`reviewer-substrate.md` states *"Not an ABC, interface, or pluggable abstraction
in code… the seat is substrate… Occupant rotation is a file write, not a
dependency injection."* A naïve reading of "make the seat modular" would reverse
that decision.

It does not have to. The retraction was about the **seat**. The thing the
operator wants portable is the **occupant**.

## 2. The decisive distinction: seat ≠ occupant

| | What it is | Where it lives | Disposition |
|---|---|---|---|
| **Seat** | `/workspace/review/*` files + attribution + the wake/verdict contract. The role. | Substrate (kernel domain). | **Stays substrate.** Not abstracted. Premise accepted, not changed. |
| **Occupant** | The AI Reviewer that *fills* the seat: `reviewer_agent.py` + persona-frame + model selection. | Code (personification domain). | **Carve out.** Canon already calls this *"an implementation choice, not an architectural commitment"* (reviewer-substrate:216) and lists `external:<service>` as a first-class occupant class. |

Carving the occupant is not reversing the ABC-retraction — it is **completing
the occupant-rotation principle** (FOUNDATIONS Derived Principle 15: "Agent seats
persist; occupants rotate"). The occupant is the thing that is *supposed* to be
swappable. The boundary between seat and occupant is a **data contract over
substrate** (TypedDicts), not an OO abstraction over the seat. That threads the
needle.

## 3. Receipts — the carve is ~90% structurally done

Dependency direction, as found in code (2026-06-04):

```
SUBSTRATE / KERNEL  (never imports the occupant)
  authored_substrate.py · workspace.py · primitives/ · workspace_paths.py (seat paths + locks)
  reviewer_envelope.py   ── reads /workspace/review/* + governance → produces envelope dict
  reviewer_audit.py      ── writes ReviewerOutput back to decisions.md / judgment_log.md
        │  ReviewerContext  ("Substrate bag passed by callers" — reviewer_agent.py:122)
        ▼
HARNESS  (wake / dispatch — fires the occupant)
  wake.py (singular gateway) · review_proposal_dispatch.py · feed.py
        │  invoke_reviewer(client, user_id, *, trigger, context: ReviewerContext)  (:1028)
        ▼
OCCUPANT  (the AI Reviewer — imports only services.anthropic + path constants)
  reviewer_agent.py ("AI occupant of the Reviewer seat" — its own docstring line 1)
  reviewer_agent_sections.py (persona-frame as a typed section registry, ADR-302)
  reviewer_agent_compat.py
```

Four facts that make the carve cheap:

1. **Substrate never imports the occupant.** `authored_substrate.py` has zero
   behavioral dependency on `reviewer_agent` (grep: one comment). One-directional.
2. **The contract already exists and is self-named.** `ReviewerContext`
   (reviewer_agent.py:122) is documented in-code as *"Substrate bag passed by
   callers."* `ReviewerOutput` (:78) is the return. `invoke_reviewer(trigger,
   context)` (:1028) is the single entry. That triple is the substrate→occupant
   ABI — it just lives privately inside the occupant module.
3. **The substrate→occupant assembler is already a separate kernel module.**
   `reviewer_envelope.py::load_reviewer_governance_envelope()` reads substrate
   and returns an `envelope_dict` *"keyed by ReviewerContext field names — drop
   directly into the context bag passed to invoke_reviewer()."* This is the
   kernel side of the ABI, already carved.
4. **The only reverse leak is one string.** `programs.py` (bundle-fork) imports
   `REVIEWER_MODEL_IDENTITY` from the occupant to seed OCCUPANT.md. A constant,
   not behavior.

### The one structural constraint: source-text gates

Several regression gates pin prior-ADR commitments by **reading
`reviewer_agent.py` as source text** and asserting the symbol definitions live
there: `test_f1` + `test_adr289` AST/regex-scan for `class ReviewerOutput`;
`test_reviewer_context_contract` + `test_adr288` grep for `ReviewerContext`
field lines. Moving the definitions means **retargeting those four gates'
definition-site assertions to the new contract module, in the same commit,
preserving their behavioral assertions** (the construction/usage-site
assertions — the `output: ReviewerOutput = {...}` dict literal, the
`caller_identity=f"reviewer:{REVIEWER_MODEL_IDENTITY}"` injection — stay on
`reviewer_agent.py`). This is exactly the singular-implementation +
docs/tests-alongside-code discipline.

## 4. The carve — three levels (L1+L2 ratified; L3 deferred)

**L1 — Documentation split + contract publication.**
- Split `reviewer-substrate.md` into a **Kernel/Seat-Substrate** doc (the
  seven seat files, attribution, locks, wake/verdict contract — *kernel*
  domain) and an **Occupant** doc (the AI Reviewer, persona-frame discipline,
  model selection, contract consumption — *personification* domain).
- `agent-composition.md §3.2.1/§3.2.2` (persona-frame partition + composed
  coherence — occupant-internal) is referenced from the Occupant doc as its
  partition canon (no content move needed; it is already the singular
  enforcement home).
- New short **Occupant Contract** doc publishing `ReviewerContext` /
  `ReviewerOutput` / `invoke_reviewer` / `reviewer_envelope` as the named seam.

**L2 — Code contract extraction.**
- `api/agents/occupant_contract.py` (NEW) becomes the canonical home of
  `ReviewerContext`, `ReviewerOutput`, `REVIEWER_MODEL_IDENTITY`. Pure data —
  zero heavy imports (no `anthropic`). It imports standalone (proof the ABI is
  decoupled from the LLM runtime).
- `reviewer_agent.py` imports the three symbols from the contract (re-exported
  in its namespace so existing `from agents.reviewer_agent import ...` runtime
  imports keep working — one definition, re-exported, not a dual definition).
- Kernel/harness importers (`programs.py`, `feed.py`, `wake.py`,
  `review_proposal_dispatch.py`) import from `occupant_contract` — killing the
  reverse leak; the kernel now depends on the contract, never on the occupant
  impl.
- Four source-text gates retargeted (definition-site → contract module; usage
  sites unchanged).

**L3 — Package carve (deferred; named, not built).**
- Restructure `api/agents/reviewer_*` into a self-contained package
  (`api/agents/reviewer/`) depending only on the published contract +
  `services.anthropic`. This is the literally-extractable unit — the thing you
  could later run as an external `external:<service>` occupant, or
  version/license independently from the kernel.
- **Trigger to build L3:** a concrete forcing function — productizing an
  external judgment occupant, or an actual open-core decision. Per the repo's
  anti-premature-modularity discipline (Derived Principle 7), the package move
  earns its churn only when a second consumer exists. Until then L2's published
  contract already gives portability + separate documentation; L3 only changes
  the *file layout*, not the boundary.

## 5. Why this is the open-core seam, made physical

The published occupant contract (`occupant_contract.py` + `reviewer_envelope.py`
on the kernel side) IS the substrate-bus ABI named in the 2026-06-04 audit. The
flow `load_reviewer_governance_envelope() → ReviewerContext → invoke_reviewer →
ReviewerOutput → reviewer_audit.write` is the complete contract between the
domain-agnostic kernel (substrate + seat + harness) and the swappable occupant.
Once named:

- The **kernel** (substrate + seat-substrate + wake/dispatch harness) is the
  potentially-open, Claude-Code-aligned layer.
- The **occupant** (persona-frame + judgment-quality engineering) is the
  swappable/serviceable unit — and the **persona content** (IDENTITY/principles)
  is program/operator-authored (bundle-owned per ADR-286). Personification
  already straddles the kernel/program line; this carve names the code seam so
  it can be physically separated *when* (L3) a forcing function arrives.

No open-core *decision* is made here. This carve only makes the seam **legible
and stable** so a future decision is cheap rather than a refactor.

## 6. Recommendation

Land **L1 + L2** as ADR-315. Keep all behavioral logic of `reviewer_agent.py`
byte-identical (move three symbol definitions out, import them back). Validate
the decoupling by importing `occupant_contract.py` standalone (no `anthropic`)
and re-running the four source-text gates against the retargeted module. Defer
**L3** until a forcing function. Do not touch the persona-frame *content* — only
its documentation home and the contract naming.
