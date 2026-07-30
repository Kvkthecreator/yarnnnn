# yarnnn — The Growth Loop

**Status**: Active (v1.1 — working canon: locked in full, subject to evolve by discourse)
**Date**: 2026-07-30 (v1.0: 2026-07-29)
**Authority**: Owns activation and the growth loop. Written from [CANON-LOCK-2026-07-30](../strategy/CANON-LOCK-2026-07-30.md) §4 (operator-ratified) and §8 (the falsifiers). v1.1 folds in the 07-30 canon re-cut (the ease center promotes "what activation is not" from hygiene to promise; falsifier 5 arms the "nothing to set up" claim; the settle falsifier retires with the verb per ADR-507) — the loop's structure is unchanged.
**Supersedes**: `ACTIVATION_100USERS.md` v3 (archived — it assumed `/setup`, a five-expert roster, tasks-as-unit, and a $19/mo Pro plan, all deleted or superseded; ADR-437 A, ADR-460, ADR-231, ADR-490).
**A confession carried forward, on purpose**: the two prior activation plans (v2 and v3 of ACTIVATION_100USERS) were **written and never run** — every tracking table in both is still empty. This document is deliberately shorter, and its tables are empty *with a commitment to fill them*. If a third plan goes unrun, the failure mode is us, not the plan.

---

## 1. What "activated" means

> **Activated = the first co-work moment: two distinct principals with attributed revisions on the same file.**

Not signups. Not tasks. Not connectors attached. The metric is **time-to-first-co-work-moment**, and it is readable from the existing ledger (`workspace_file_versions` attribution + `principal_grants`) with **no new telemetry**.

## 2. The loop

```
MCP door        →   the desk      →   the share link
first co-work       daily co-work     co-work with a person
acquire             retain            expand
(free, day one)     (free)            (paid at head 3)
```

- **Acquire — the MCP door.** The second principal arrives as a *surface*, not a person: an external AI (`foreign-llm`/`a2a`, ADR-445) reaching the commons over the interop face. Free, unlimited, day one, no invite.
- **Retain — the desk.** Where the product is experienced and where retention lives (ADR-457 D5, not reversed by this lead). Daily co-work across the acts — Think, Make, Perceive (ADR-507) — every change signed.
- **Expand — the share link.** `/s/{token}` → a human colleague lands on the shared artifact, inside a populated commons, `trace` visible (ADR-465). Two humans free; revenue begins at the third head ($20/mo, ADR-490). The proof moment *is* the growth moment.

## 3. Two channels only

Per ADR-437, a stranger becomes an activated principal through exactly two channels. **There is no third, and there is no wizard.**

### Channel 1 — cold discovery. LEAD DOOR: connect your AI first.

**Primary CTA: "Co-work with the AI you already use."**

The first act is attaching yarnnn to an AI the person already has, so the second principal exists **before the member has authored anything**. The first thing they see at the desk is a write they didn't make, signed by something that isn't them — the moat on contact (ADR-437 D3: *"a cold user who drops a file or states a fact and watches it placed, attributed, and recallable has seen the moat on contact"*).

Why the MCP door leads (CANON-LOCK-2026-07-30 §3.2, promoting ADR-457 D6's named-but-unproven candidate): it is the only lead unfenced by an armed falsifier; the only channel where the second principal arrives free on day one; and it demos the moat in sixty seconds with no tenure. Under the ease center the CTA needs no plurality rationale — it reads as *give the work you're already doing in ChatGPT a place to land*. (The v1.0 fourth leg — directories pre-qualify for *plural* — is dropped with the plural center; directories remain distribution.)

### Channel 2 — invited / shared.

`/s/{token}` → signup → broad member grant → land on the shared artifact with `trace` visible, inside a populated commons. **Shipped** (ADR-437 Phase D, ADR-465). The artifact is the landing page.

## 4. What activation is not

No setup wizard · no workspace constitution · no program pick · no roster discovery · no "assign your first task" · no blank-canvas empty state. All deleted or retired (ADR-437 D1, ADR-421, ADR-414 D4/D5, ADR-460, ADR-231). **Entry is a flow, not a ceremony** (ADR-465). **v1.1: this list is promoted from hygiene to promise** — the subhead now says *"nothing to set up"* out loud (CANON-LOCK-2026-07-30 §1), so every item here is copy-load-bearing and guarded by falsifier 5.

## 5. Metrics

Per CANON-LOCK-2026-07-30 §4.4.

| Class | Metric | Definition |
|---|---|---|
| **Primary** | Time-to-first-co-work-moment | Signup → two distinct principals with attributed revisions on one file. **Target class: minutes, not days** (falsifier 5) |
| Secondary | Connector-attach rate | Cold channel: % of signups that attach an external AI |
| Secondary | Share→accept rate | Warm channel: % of `/s/{token}` sends that become a member grant |
| Secondary | Third-head rate | % of workspaces that add a 3rd human (revenue) |
| **Guardrail** | Desk-return rate among connector-origin users | The §7 falsifier-1 sentinel |

### Tracking — to be filled, not decorated

| Week of | Signups | Median time-to-co-work | Connector-attach % | Share→accept % | 3rd-head count | Connector-origin desk-return % |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — |

| Channel test | Budget | Window | Result | Read |
|---|---|---|---|---|
| — | — | — | — | — |

## 6. Named build dependency

**Leading with the MCP door makes the connector attach path the highest-leverage unbuilt surface.**

- **ADR-437 Phase C** (the cold empty-state design pass) is still open — and it is now **on the critical path**, not beside it.
- **The connector registry (ADR-494)** is the surface the attach path leans on. **The attach must be a sixty-second act** — connect, see the first foreign write land signed — **or the lead door is aspiration rather than strategy.**

**v1.1 escalation (CANON-LOCK-2026-07-30 §4.5)**: Phase C hardens from wedge-dependency to **product-sentence-dependency** — *"nothing to set up"* is now in the hero, so a clunky attach doesn't weaken the strategy, it **falsifies the copy**. First build priority by the canon's own logic. Until it ships, Channel 2 is the only fully-shipped channel and the loop runs on its warm leg.

## 7. Falsifiers — armed, evaluated against declared criteria

Per CANON-LOCK-2026-07-30 §8.

1. **The wedge.** Within 60–90 days of leading with the MCP door: if connector-origin users do not open the desk — no second surface, no share — then MCP is a feature of other people's products, not a door into ours. **Revert the lead to the shared team commons.** The guardrail metric in §5 exists for exactly this read.
2. **Settle — RETIRED with the verb** (ADR-507, 2026-07-30). Read before removal; did not fire on its own terms (low adoption ≠ abandonment); the retirement was structural. Nothing in this loop leads with settle; no successor falsifier needed.
3. **Radar/briefs** (ADR-486 D8.2): if briefs go unopened, do not GTM-lead with Radar. Currently fenced; not in this loop's lead.
4. **Correction owed to ADR-457 D8.3.** As written — *"MCP traffic dwarfs desk traffic → the hum is the true wedge; flip priority back"* — **it would fire on success**, since MCP dominance is this canon's *expected* acquisition pattern. It must be re-cut to distinguish *MCP as the acquisition door* (expected, good) from *MCP as the whole product* (the real failure — which is falsifier 1 above). The re-cut belongs to an ADR amendment pass, not to this doc; until it lands, read D8.3 through falsifier 1.
5. **The ease claim (new, v1.1).** If the median cold-signup → first-co-work-moment is not measured in **minutes** once the lead door ships, *"nothing to set up"* comes out of the subhead — the claim is aspiration, not copy. Same ledger query as the primary metric; no new telemetry.

---

## Maintenance

Update when: a §5 table row is filled (weekly once the lead door ships); a §7 falsifier fires or clears; ADR-437 Phase C or the ADR-494 attach path ships (§6 closes); CANON-LOCK-2026-07-30 §4 is amended. The ICP lives in [ICP.md](../strategy/ICP.md) v2; the story in [NARRATIVE.md](../../NARRATIVE.md) v7; the language in [GTM_POSITIONING.md](../strategy/GTM_POSITIONING.md) v6.
