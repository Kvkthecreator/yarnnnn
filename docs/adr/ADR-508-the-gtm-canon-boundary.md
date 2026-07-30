# ADR-508 — The GTM-Canon Boundary: Where Marketing Canon and Kernel Canon Meet

**Status**: **Accepted — operator-ratified 2026-07-30** (the canon-v2 discourse session). Doc-only; changes no code, no schema, no gate.
**Date**: 2026-07-30
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (states a canon-layer rule about which documents may depend on which)
**Relates to**: [CANON-LOCK-2026-07-30](../working_docs/strategy/CANON-LOCK-2026-07-30.md) · [ESSENCE.md](../ESSENCE.md) §The Canon Sentences · [ADR-504](ADR-504-the-interop-principal-invariant.md) (the template for D3) · FOUNDATIONS (the document this ADR keeps decoupled) · CLAUDE.md §The Two Hats
**Amends**: GLOSSARY §Product promise (the stale duplicate one-liner home is replaced by the D4 pointer).

---

## 1. The question

The 2026-07-30 canon discourse ended on an operator question: *should FOUNDATIONS reference the GTM canon lock?* The canon has become genuinely load-bearing — the activation model, the pricing motion, and the product sentence all read from it — and load-bearing things usually get anchored in kernel canon. This ADR answers the question in the open, so the boundary is a ratified rule rather than a session opinion.

## 2. The decision — four rules

**D1 — FOUNDATIONS never references the GTM canon.** The dependency arrow runs one way, by the lock's own charter (*"Not in scope: architecture. This document never overrides an ADR"*): the canon cites FOUNDATIONS-grade decisions as **fixed inputs**; the axioms never cite the canon back. The reverse edge would invert the authority hierarchy — a copy discourse could exert gravitational pull on kernel canon, which is precisely the drift the Two Hats discipline exists to prevent. There is also a churn asymmetry: FOUNDATIONS moves at axiom cadence; the lock is explicitly *working* canon whose sentences may change per discourse. A FOUNDATIONS reference either rots or forces axiom-doc commits for copy changes.

**D2 — ESSENCE §The Canon Sentences is the sole bridge.** ESSENCE already sits at the top of the source-of-truth hierarchy for *product narrative* while FOUNDATIONS owns *architecture*; the canon sentences live there, labeled by slot, under the replace-never-accumulate rule. No other architecture-side document quotes the sentences.

**D3 — kernel guarantees the GTM depends on are minted as explicit invariant ADRs.** When a canon claim needs the kernel to promise something (*"every change signed…"*, *"work with your AI as a real principal"*), the instrument is an ADR stating the invariant — which the canon then cites as a fixed input. [ADR-504](ADR-504-the-interop-principal-invariant.md) (the interop principal invariant) is the template; the signature-grammar enforcement at the write door is its companion. The lock's §7 fixed-inputs list is the registry of these edges.

**D4 — the GLOSSARY carries one non-normative pointer, and loses its stale duplicate.** Discoverability is legitimate: a kernel-side reader should be able to *find* the GTM canon without the axioms depending on it. The GLOSSARY's §Product promise section — which still carried *"Describe your work. Create the agents that do it."*, a one-liner several product generations stale — is replaced by a pointer to ESSENCE §The Canon Sentences and the live lock. This simultaneously deletes the last duplicate one-liner home outside ESSENCE, which is the seven-one-liners failure mode (ESSENCE v16) resurfacing in a different file.

## 3. What this forecloses

- Any future edit that quotes a canon sentence into FOUNDATIONS, or cites a CANON-LOCK file from it, is a breach of D1 and must supersede this ADR explicitly.
- Any second home for the canon sentences outside ESSENCE (D2/D4) — including new "product promise" sections in architecture docs — is the accumulation failure and gets deleted on sight.

## 4. What this does not decide

Nothing about the canon's *content* (that is the lock's), nothing about ESSENCE's internal structure, and nothing about future invariant ADRs beyond naming their template.

---

*Ratified 2026-07-30. The boundary is now canon: one-way arrow, one bridge, invariants by ADR, one pointer.*
