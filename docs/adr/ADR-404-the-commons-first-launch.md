# ADR-404: The Commons-First Launch — the capture lane goes dormant

**Status**: Accepted (2026-07-03) — operator-ratified strategic direction; implementation phases tracked in §5
**Date**: 2026-07-03
**Dimension**: Purpose (primary, Axiom 3 — what the product is for at launch) + Trigger (the capture cadence goes dormant) + Channel (which surfaces ship)
**Amends**: ADR-392/393/394/401 (the connector capture lane — status becomes *dormant behind a flag*; the canon stands unrevised), ADR-396 (the connector-count tier gate is suspended with the lane; §D5), ADR-380 (the launch composition is Rung 0/1 **plus the multi-principal commons**), SITE-COPY-SPEC-v1 (re-center, phase 6)
**Relates to**: ADR-373 (the re-key — promoted to the critical path), ADR-375 (the interop wedge), ADR-378 (workspace = the commons), ADR-405 (the witness dial), ADR-406 (stale-parent rejection), ADR-386 (grant lifecycle)

---

## 1. Context

Two operator observations converged (2026-07-03):

1. **The permission/notification mismatch.** ADR-400 shipped direct operator
   file manipulation; the resulting asymmetry against Freddie's propose-only
   role and the notification system felt like an axiomatic break in
   multi-principal handling. Diagnosis: not a new break — the un-built half
   of ADR-373 plus a missing name for the witness contract (→ ADR-405), plus
   a real concurrency gap (→ ADR-406).

2. **The connector strategy.** The mechanical 15-minute capture lane
   (ADR-392→401) pulls raw platform dumps with a low true-signal ratio into
   `inbound/`. "Organizing dumps from platforms you already have" is
   commodity territory; the ratified moat — durable **attributed** memory
   led by trace/provenance (ADR-380 §5) — is only *visible* when multiple
   principals share one commons. The operator's call: re-prioritize the
   deferred multi-user work (human invites, multi-party AI participation)
   as the launch, and put the capture lane away.

**Honesty note on F3**: the pivot was weighed while F3 (does the seat derive
from captured raw?) was open. F3 **closed in production the same day** — the
seat does derive (receipts: `docs/evaluations/2026-07-03-rung4-model-stabilization-FINDING.md`).
The lane is therefore hidden on *strategic* grounds, not because it failed
mechanically. Recorded so the ledger doesn't imply otherwise. Two live
defects (the byte-identical rewrite burn ~$60/day, attributed to
`system:sync-platform-state`; the derive-wake re-proposal duplication) are
*silenced* by dormancy and root-caused when the lane returns.

## 2. Decision

**D1 — Phase-1 GTM is the multi-principal shared commons.** The launch
product: one shared, attributed, judged filesystem operated by humans
(owner + invited members) and external AIs (via the MCP interop face —
remember/recall/trace + grants, already live with ChatGPT + Claude
principals). The remaining ADR-373 Phase-1 work — the substrate read sweep
off `user_id`, the grant-based workspace resolver, then member provisioning
(ADR-386 D6) — is promoted to **the** pre-launch critical path.

**D2 — The capture lane goes dormant behind `CONNECTOR_CAPTURE_ENABLED`
(default OFF).** Hide, not revert. The flag follows the `AGENT_ENABLED`
resolver shape but defaults **off** — dormancy *is* the ratified decision;
the env var re-enables per deployment for dev/e2e. Gated sites (the minimal
cut): the scheduler capture drain + connector raw GC, the seed-at-select
call, and the FE CADENCE + YIELD sections + retention dial. **Kept live and
untouched**: OAuth connect/reconnect, granted scopes, the validate probe,
the ACCESS + SCOPE sections, `_watch.yaml`, and every capture module + test
gate. ADR-392/393/394/401 remain canon — a connection is still a mechanical
peripheral with a nine-stage lifecycle; the lane re-enters (flag flip, zero
rebuild) if/when perception-serving-the-commons earns its place again.

**D3 — The AI-connection permission surface is untouched.** Downstream
scopes for AI principals (`principal_grants`, the gate consult, the AI
Connections pane) are the *substance* of the launch, not part of the cut.
The MCP interop face is the multi-party wedge as built.

**D4 — Multi-party scope honesty.** What ships is **hub-of-record**:
external LLMs come *to* the commons (MCP). Outbound orchestration — YARNNN
calling out to Gemini/others in a shared chat — is a different build (an
outbound a2a lane + spend model) and stays named-deferred. GTM copy must
not promise it.

**D5 — Pricing ripple, deferred.** The ADR-396 carve loses its
connector-count gate while the lane sleeps. **Commons-scale** (# principals
in the workspace — the ADR-391 axis ADR-396 superseded) is named the
candidate successor gate; the re-cut lands as an ADR-396 amendment when
member invites ship, not now. Numbers untouched.

## 3. What this is not

- Not a reversal of the peripheral ontology (ADR-401 D1 stands).
- Not a deletion: no capture code, migration, or gate is removed.
- Not a claim that perception is out of the vision — it re-enters as an
  input *serving* the commons once the commons exists to serve.

## 4. Dimensional classification

Purpose (primary): what the launch is for. Trigger: the 15-minute cadence
goes silent. Channel: Cadence/Yield surfaces hide; the members surface
becomes primary.

## 5. Implementation sequence (each its own commit)

1. ✅ This ADR + ADR-405 (witness dial) + ADR-406 (stale-parent rejection) — doc-first.
2. ✅ Capture-lane flag-off (`CONNECTOR_CAPTURE_ENABLED`, D2 cut list; gate `api/test_adr404_capture_dormancy.py` 28/28) + duplicate-proposal cleanup (37 rejected, newest-per-group kept pending; receipt 2026-07-03).
3. ☐ ADR-406 implementation (CAS + linearity guard + 409 contract).
4. ☐ ADR-373 substrate read sweep (core: `workspace.py`, `authored_substrate.py`, `primitives/workspace.py`) + grant-based workspace resolution.
5. ☐ Member invites (grant provisioning UX — `member` role live; ADR-386 D6 unblocked by step 4).
6. ☐ GTM copy re-center on the shared commons.

(Statuses flip in the implementing commits.)
