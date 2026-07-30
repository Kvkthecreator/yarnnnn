# ADR-504 — The Interop Principal Invariant: an External LLM Is a First-Class Principal in the Ledger

**Status**: **Accepted — operator-ratified 2026-07-30** (the canon-v2 discourse session; "do the owed ones" ratification). Doc-only at ratification; the companion signature-grammar enforcement (author-taxonomy validation at `write_revision`/`delete_live_file` + `api/test_author_grammar_gate.py`) landed in the same pass — it enforces the *shape* of attribution the invariant protects the *classes* of.
**Ratification note (2026-07-30)**: under [CANON-LOCK-2026-07-30](../working_docs/strategy/CANON-LOCK-2026-07-30.md) this invariant became MORE load-bearing than when drafted — the v2 ICP's **Shared** qualifier counts a single connected AI as a real second principal (the single-AI user readmitted), so the entire activation model now stands on `foreign-llm`/`a2a` staying principal-grade even at N=1 AIs.
**Date**: 2026-07-29 (drafted) · 2026-07-30 (ratified)
**Authors**: KVK (operator, via the canon-lock discourse) + Claude (collaborator)
**Hat**: A (states a kernel invariant; the GTM documents that depend on it are Hat-A canon consumers)
**Dimension**: Identity (Axiom 2 — who acts)
**Relates to**: [CANON-LOCK-2026-07-29](../working_docs/strategy/CANON-LOCK-2026-07-29.md) §2.2 + §7 · ADR-445 (principal roles: `foreign-llm · a2a · own-agent · platform`) · ADR-460 (an Agent at the desk is the member's hands, not a principal) · ADR-465 (*"a one-member commons is a diary"* — the second principal switches the moat on) · ADR-373/386/431 (the grant machinery that makes the external LLM a principal today)
**Amends**: nothing. This ADR adds no behavior; it **forecloses one specific future collapse**.

---

## 1. The invariant

> **An external LLM reaching the commons over the interop face is a first-class principal in the ledger** — its own grant row (`foreign-llm` / `a2a`, per ADR-445), its own attribution line, its own entry in the revision chain.
>
> **This may not be collapsed into member attribution** the way ADR-460 collapsed kernel Agents into *the member's hands*.

The two rulings are complementary, not in tension, and this ADR fixes the boundary between them:

| Actor | Ledger fact | Ruling |
|---|---|---|
| An Agent addressed at the desk (`Scout · Gemini` et al.) | `member:{user} via {model}` — the member's hands | ADR-460: **not a principal.** Correct; unchanged. |
| An external LLM over the interop face (ChatGPT, Claude, a2a callers) | its own `principal_grants` row + its own attribution | **A principal. This ADR makes that an invariant, not an implementation detail.** |

The distinguishing fact is not the model — it can be the *same model* on both sides. It is the **grant under which the write lands**: the desk Agent acts under the member's grant; the external LLM acts under its own.

## 2. Rationale — what depends on this

The locked product sentence and the activation model both stand on this invariant:

1. **The product claim.** The hero subhead — *"work with ChatGPT, Gemini, and Claude together"* — is a claim about the ledger. If foreign-LLM writes ever collapse into member attribution, the claim degrades to **one principal wearing three faces**: the ledger would show a single member acting via three transports, and *"every change signed by whoever made it, human or not"* would be false in exactly the case the hero advertises. The GTM loses its ledger backing (CANON-LOCK §7).
2. **The activation species.** CANON-LOCK §2.2 names the external AI as the **activation species** of second principal — free, day one, no invite. ADR-465's moat switch (*"the act that creates the second principal is the act that switches the moat on"*) fires on the interop connection **only because** the connection creates a genuinely distinct principal. Collapse it, and cold-channel activation (GROWTH-LOOP §3 Channel 1) produces diaries: one-principal commons with extra transports.
3. **The proof asset.** The attribution walk — *"you · Aug 2 · your agent · Aug 5 · Claude · Aug 6"* — is the one place the moat is felt (CANON-LOCK §3.4). Its third line exists only under this invariant.

## 3. Why the ADR-460 precedent is the named risk

ADR-460 was a correct collapse: a named preset at the desk *is* the member's hands, and marketing it as a colleague would be a claim the ledger contradicts. But the precedent it set — "a named AI face resolves to member attribution" — generalizes one step too far if applied to the interop face. A future simplification pass (one attribution taxonomy, fewer grant roles, "all AI writes are somebody's hands") would be locally tidy and would silently delete the product's central claim. This ADR exists so that pass has to overturn a ratified invariant in the open rather than absorb it in a refactor.

## 4. What this binds

- The `foreign-llm` and `a2a` roles in `principal_grants` remain **principal-grade**: own grant row, own scopes, own attribution prefix in `workspace_file_versions`. (Already live — ADR-373 grant-consult, ADR-386 lifecycle, ADR-431 connecting-member key; this ADR adds nothing to them.)
- Any future attribution-taxonomy change that would record an interop write as `member:{user} via {model}` (or any member-derived form) is a **breach of this invariant** and requires superseding this ADR explicitly.
- Marketing copy may treat the external AI as a second principal (CANON-LOCK §2.2) **because and only while** the ledger does.

## 5. What this does NOT decide

- Nothing about desk Agents — ADR-460 stands in full.
- Nothing about a2a *outbound* orchestration (the named-deferred lane, ADR-404).
- No new roles, no schema, no gate changes, no widening of any grant.

---

*Ratified 2026-07-30. The invariant now binds: any future pass that would record an interop write as member-derived attribution must supersede this ADR explicitly, in the open.*
