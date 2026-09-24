# ADR-665 — Browser workflows: work that lives in files and runs in the member's browser

> **Status**: **Proposed** (2026-09-23, draft for operator review — NOT ratified; nothing built). The operator
> set the direction — *"a dedicated surface, app (much like a supervisor agent and app 2.0) wherein, file system
> native with browser use can really open up potentially infinite amount of workflows and automations"* — and
> agreed option B (§3) as the starting point. This draft makes that a decision to ratify.
> **Date**: 2026-09-23
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Trigger** (a declared cadence may start browser work) +
> **Channel** (the member's browser, ADR-664).
> **Gate** (planned, written with the implementation): `api/test_adr665_browser_workflows.py`.

**Would amend**: ADR-615 (attendance is presence) · ADR-661 §6 and ADR-662 D9 (local hands are attended only) ·
ADR-639/603 (the unattended derive turn is toolless — a browser workflow run is the one exception).
**Builds on**: ADR-662 D15 (the extension is the one executor) · ADR-664 (the browser is reach) · ADR-639
(standing work: `_standing.yaml` + `CONTRACT.md`, the one drain loop) · ADR-658 (the Supervisor app, standing
work's surface) · ADR-307 (the proposal queue — it exists for absence) · ADR-209 (one write path).

## 1. The idea

yarnnn already has the filesystem, attribution, agents and one scheduling loop. ADR-662/664 gave it hands on
the web. Together: **a workflow is a folder**, and it runs in the member's browser.

```
workflows/weekly-competitor-prices/
  WORKFLOW.md        the procedure, in plain words — what to open, what to read, what to write, what to send
  _standing.yaml     when it runs (the ADR-639 declaration, unchanged)
  runs.md            append-only: one entry per run, with its receipts (ADR-254 lowercase)
  outputs…           what it wrote, attributed like any file
```

Readable, editable, versioned, diffable, exportable — the same as every other file in the commons.

## 2. Three ways a workflow is made

1. **Teach by doing.** The member does the task once with the agent in a conversation. The turn's receipts
   (ADR-662 D3, `metadata.receipts`) are a step-by-step record; the agent writes `WORKFLOW.md` from them.
2. **Say it.** The member describes it; the agent writes `WORKFLOW.md` and runs it once, attended, to prove it.
3. **Edit it.** `WORKFLOW.md` is a file: change a step, the next run follows it.

## 3. The decision underneath — who is present

Today the browser acts only in a conversation the member is in (ADR-615, ADR-661 §6, ADR-662 D9). A workflow on
a schedule runs when nobody is watching. Three options:

| | Unattended, the browser… | Cost |
|---|---|---|
| A. Presence stays the rule | does nothing; the schedule prepares the run and waits for the member to open it | safe; not automation |
| **B. The member's machine is the attendance** (proposed) | runs when the member's Chrome is open with the extension on — in the visible *yarnnn* tab group, stoppable from the toolbar; reading and filling proceed; a consequential act (send, post, submit, pay) **waits in the proposal queue** unless the workflow pre-authorizes that exact act | amends three ADRs; needs a strong stop and a clear record |
| C. Fully autonomous | acts, sends included | ADR-662 D5's prompt-injection risk with nobody watching; not now |

**B, precisely:**

- **Where it runs**: only through the extension of the member who declared it, on their machine. No server-side
  browser, no remote sandbox (ADR-395 §8.7 stands). If their Chrome is closed, the run waits and says so.
- **What stops it**: the extension's switch; a stop in the Supervisor; closing the tab group. Any of them ends the
  run and records where it stopped.
- **What waits**: every act the executor classes consequential (send, post, submit, pay — the extension already
  names them per act) queues as a proposal with the page's context, unless `WORKFLOW.md` names that act on that
  site as pre-authorized — a sentence the member wrote, versioned and attributed.
- **What never runs**: the default-denied categories (ADR-662 D15) — banking and payments, trading, password
  managers, account security — whatever a workflow says.
- **What it records**: each run appends to `runs.md` with its receipts; outputs are ordinary attributed writes
  (`member:{id} via {model}`, ADR-209).
- **Cost**: a run has a round and spend bound (ADR-662 D8) and stops when stuck.

## 4. Where it lives — the Supervisor, grown

The Supervisor app (ADR-658) is already standing work's surface, over the kernel's one drain loop (ADR-639). A
workflow is standing work whose job happens in a browser, so it belongs there — not in a new app with a second
scheduler and a second meaning of "a job". "Supervisor 2.0": the roster shows browser workflows beside kept
files; a workflow's page shows `WORKFLOW.md`, its runs and their receipts, its queued acts, and Run now / Stop.

## 5. Build order (after ratification)

1. The run: a standing declaration whose job is browser work, dispatched to the member's extension when it is
   connected (the extension holds a connection to the API while on — the one new transport), bounded and
   receipted; consequential acts to the proposal queue.
2. `WORKFLOW.md` and `runs.md` — the file contract, and the frame's instruction to follow it.
3. Teach by doing: from a conversation's receipts to `WORKFLOW.md`.
4. The Supervisor's workflow roster and page.
5. The driven trace: a real workflow on a schedule, in a real Chrome, producing a real file and a real queued act.

## 6. Open questions for ratification

1. B as written, or a narrower first step (reads only, no queued acts)?
2. The unattended transport: the extension holds an authenticated connection to the API while on — a new
   standing credential in the browser (the member's session). Acceptable, or must a run start from a page the
   member opens?
3. What counts as consequential is the executor's call today (per act). Is that enough, or does a workflow
   declare its own?
4. **A run that meets a sign-in wall.** Parked analysis: [access is brokered, never held](../analysis/access-is-brokered-never-held-2026-09-24.md)
   — yarnnn never holds a member's secret; an unattended run stops and asks the member to sign in; a vault is
   an adapter the executor hands sign-in to. It also records points for this ADR's revision (§4 there).
