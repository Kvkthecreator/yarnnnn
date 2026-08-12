# ADR-551: Autonomy is a property of an agent, not of the workspace

> **Status**: **Accepted + Implemented** (2026-08-12, operator-reframed — *"I'm
> thinking if the existing conceptual framing of autonomy of the system agent is
> wrong now… yarnnn's shared workspace, and any of the chats primitives openly
> allow the file mutations and reading as first class… the current housing under
> shared workspace settings pane seems incorrect"*).
> **Date**: 2026-08-12
> **Dimension**: **Identity** (whose property autonomy is) primary, with
> **Surface** consequences (which door may claim it).
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**:
> - **ADR-550 D2** — **this reverses it, on a better argument.** D2 refused the
>   removal on *liveness* grounds and was right about the mechanics; it answered
>   the wrong question. §2 records why.
> - **ADR-491 D4** ("The pane stays") — **superseded.** Its reasoning ("the
>   fallback file IS the steward's dial") is true and does not establish that the
>   *workspace door* is its home.
> - **ADR-454 D4 / ADR-426 / ADR-418 / ADR-412 D5** — the pane's four prior moves.
> - **ADR-408 D3** (`substrate: autonomous`) — unchanged, and the reason the file
>   must not be deleted.
> - **ADR-414 D6** (per-agent sidecar) — where autonomy re-homes.
> - **ADR-421** (a workspace has no constitution of its own) — **the precedent
>   this follows exactly.** Mandate/Identity/Principles left this door for the
>   same reason; autonomy was left behind.

---

## 1. Context — the pane moved four times without its question being re-asked

Autonomy has been re-homed by ADR-412 D5 (agents → workspace-settings), ADR-426
(→ its own door), ADR-454 D4 (→ back, reversed), and ADR-491 D4 (kept, relabelled
"System agent"). Every one of those decided **which door**. None asked whether a
workspace door should carry it at all.

### 1.1 The gate applies only to the steward

`services/primitives/permission.py::resolve_permission`:

```python
if not getattr(auth, "freddie_caller", False):
    return PermissionDecision.APPLY, "non_freddie_caller"
```

This returns **before** the policy is ever read, and `freddie_caller=True` is set
in exactly one place — the steward's own loop (`agents/freddie_agent.py:916`).
So:

| writer | gated by this dial |
|---|---|
| a human in chat, a lane, the Files surface | **no** |
| an external LLM over MCP | **no** |
| the steward's own WriteFile / capital act | yes |

The operator's reframing is exactly this: **file mutation through the chat
primitives is first-class and ungated by design.** A workspace-level "Autonomy"
control sat above a shared commons where almost nothing it named was actually
governed by it.

### 1.2 And the one thing it does govern is dormant

Prod, 2026-08-12: the scheduler ticks every minute and logs
`Completed: invocations=0/0` on **every tick for a week**, unbroken. Zero
`autonomy_requires_approval` / `autonomy_allows` decisions in the API logs over
the same window. The steward does not currently fire, so nothing reaches the
gate.

So the pane was a workspace-scoped control over a steward-only gate that is not
currently running.

## 2. Why ADR-550 D2 got this wrong

ADR-550 D2 (yesterday) refused this same removal, and its *evidence* was sound:
the gate is live code, `should_auto_apply` branches on all three values, and
deleting `_autonomy.yaml` would invert ADR-408 D3 and queue every steward write.
All still true — §3 D2 keeps every bit of it.

The error was **answering "is the mechanism live?" when the question was "is the
workspace the right owner?"** Those come apart cleanly: a mechanism can be
perfectly live and still be surfaced in the wrong place. D2 measured liveness,
found it, and stopped — treating "it works" as "it belongs."

The tell was in D2's own text: it recorded that the pane could not reach the
`substrate:` block, that its copy was false, and that it is inert on a
hired-agent workspace — three defects in one control — and still concluded
*keep*. Three defects in a surface is evidence about the surface, not a list of
follow-ups.

**ADR-421 is the precedent that should have been applied.** It removed
Mandate/Identity/Principles from this door on exactly this reasoning: *"a
workspace has no constitution of its own — those are per-agent concepts."*
Autonomy is the same kind of fact and was simply left behind.

## 3. Decisions

| D | Decision |
|---|---|
| **D1** | **The System Agent group is REMOVED from Workspace Settings.** Autonomy is a property of AN AGENT, not of the shared commons. It re-homes to the agent detail (ADR-414 D6's `agents/{slug}/_autonomy.yaml`, which `load_autonomy` already prefers) when ADR-382 builds the roster. Follows ADR-421 exactly. |
| **D2** | **The MECHANICS stay, untouched and documented.** `review_policy.py` + `permission.py` + `review_proposal_dispatch.py` are unchanged. `governance/_autonomy.yaml` stays a live substrate file — deleting it makes `load_autonomy` return `{}`, defaults `delegation` to `"manual"`, and queues **every** steward write, inverting ADR-408 D3. |
| **D3** | **The scope + status is documented AT THE GATE.** `review_policy.py`'s module docstring now states, in the first screen: who it gates (steward-only, with the `non_freddie_caller` line quoted), that it is currently dormant (with the prod receipt), that the file must not be deleted as cleanup, and why the pane went. This is where an auditor lands. |
| **D4** | **The dead FE chain is deleted, not orphaned.** `AutonomyCard.tsx`, `SystemAgentPanes.tsx` (its other two panes were already mountless since ADR-454 D4), `ConfirmDialChange.tsx` (sole consumer), `lib/content-shapes/autonomy.ts`, and the kernel `autonomy` surface row. `/autonomy` + `/system-agent` redirect stubs now land on the door's default pane. |
| **D5** | **The retired gate is INVERTED, not deleted.** `test_adr238_autonomy_substrate` used to assert the shape module exists; it now asserts it stays gone, with a message naming the correct home. Re-adding an operator dial for a steward-only gate should argue with a red gate, not slip in as a UI addition. |

## 4. What this does NOT do

- **No behavior change.** Not one line of the gate's logic moved. A workspace's
  effective autonomy today is exactly what it was yesterday.
- **No file deletion.** `governance/_autonomy.yaml` remains, operator-editable as
  raw substrate — the same treatment ADR-491 D3 gave `_budget.yaml`.
- **No per-agent surface built.** That waits for ADR-382 and a real hire grant
  (zero exist anywhere). Building it now would ship an unexercised surface.
- **It does NOT claim the gate is unnecessary.** If the steward is re-enabled,
  the gate matters again — and D3/D5 are what make it findable when that day
  comes.

## 5. Open

- **The per-agent dial**, when ADR-382 builds the agent roster. D5's inverted
  gate is the checkpoint that work must consciously re-cut.
- **ADR-550 D3's `substrate:` gap is now moot at the surface** (no pane to be
  wrong), but the underlying asymmetry — the `substrate:` block resolving before
  `default:` — remains for whoever builds the per-agent control.
- **A click-pass**: Workspace Settings should read Access · Billing · Danger
  Zone, and `/autonomy` should land on Members rather than 404 or a blank pane.
