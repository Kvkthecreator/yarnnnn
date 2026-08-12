# ADR-550: The members pane says where you stand, and the dial says what it governs

> **Status**: **Accepted + Implemented** (2026-08-12, operator-directed — two
> polish jobs raised from prod screenshots: *"make more clearer on the workspace
> members pane if they are owner or member"* and *"the system agent section and
> autonomy pane is actually outdated at large… consider removing it completely"*).
> **Date**: 2026-08-12
> **Dimension**: **Identity** (what a principal is told about their own standing)
> primary, with **Channel** consequences (whether a control's copy is true).
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**:
> - **FOUNDATIONS DP35** ("affordances render per grant coverage, never a role
>   enum") — D1 says the grant in words; the affordances stay derived.
> - **ADR-373 D2** (the multi-principal roster) — the pane this re-heads.
> - **ADR-491 D4** — **the ruling that keeps the Autonomy pane.** D2 upholds it.
> - **ADR-454 D4** — killed the ADR-426 *door*, not the dial.
> - **ADR-408 D3** (`substrate: autonomous` — "reversible file work is the
>   steward's hands") — the seeded block D3 names as unreachable from the pane.
> - **ADR-338 D4.2** (the schema-inert `bounded` copy) — same class of defect,
>   fixed once for `bounded` and missed for `manual`.
> - **ADR-414 §9a** (`load_autonomy` resolves the judgment home) — the per-agent
>   resolution the FE does not mirror (D4, latent).

---

## 1. Context

### 1.1 The members pane described the list, never the reader

The pane's most prominent line read *"Everyone — and everything — that can write
to this workspace."* True, and already said twice below it: the two section
headings name the People/AI split, and each AI row states "Connects over MCP ·
writes as itself".

What it never said is **where the reader stands**. An owner and a member saw an
identical sentence over a roster whose affordances differ completely — invite,
narrow, revoke, and set-cap are all owner-only. The role was inferable only from
which buttons were absent, which is inference from a negative.

### 1.2 The Autonomy pane was suspected dead — and is the opposite

The operator's read was that the System Agent group was "outdated at large" and
a candidate for removal. **The audit refutes that, decisively.**

`governance/_autonomy.yaml` is read on **every consequential primitive call**,
and its value branches between APPLY and QUEUE:

- `review_policy.py:440-473` — `should_auto_apply` branches on all three values
  for both the capital and substrate classes.
- Live callers: `primitives/permission.py` (three gates — ask, platform-write,
  substrate), `review_proposal_dispatch.py:466` (post-verdict capital binding).
- Reached from `execute_primitive`, the universal primitive chokepoint, and from
  the scheduler's wake drainer.
- **ADR-491 D4 (the newest ruling) explicitly says "The pane stays."**

Deleting the file would not be a cleanup. `load_autonomy` returns `{}` on a
missing file, `should_auto_apply` then defaults `delegation` to `"manual"`, and
**every** steward file write would become an operator-queued proposal — a full
inversion of ADR-408 D3's shipped default. The workspace would look like it had
stopped working.

The reason it *looked* dead is worth recording: there is no `/autonomy` API
route (it writes through the generic `PATCH /api/workspace/file`), so grepping
`api/routes/` for "autonomy" returns nearly nothing. **Absence of a route is not
absence of a mechanism.**

### 1.3 But the pane is a leaky controller — one live defect

The dial is live; the pane is not a faithful controller of it.

`autonomy_for_substrate` (`review_policy.py:295`) resolves the **`substrate:`
block first**, falling back to `default:`. The pane writes only `default:` — its
serializer strips exactly `default` / `domains` / `paused_until` / `pause_reason`
(`autonomy.ts:341-345`) and preserves everything else verbatim. And workspace
genesis seeds a `substrate: delegation: autonomous` block
(`orchestration.py:914`).

So on a stock workspace:

> An operator who set the dial to **Manual** still had an agent applying every
> file edit immediately — while the pane told them *"Every action waits for your
> approval before executing."*

The control was not broken; its **copy was false**. This is the same class
ADR-338 D4.2 already fixed for `bounded` and missed for `manual`.

## 2. Decisions

| D | Decision |
|---|---|
| **D1** | **The members pane names the workspace and the viewer's role.** A header block states the workspace, a role chip ("You're the owner/member/viewer"), what that role can actually do, and the roster counts. Derived from the roster already fetched — the server marks the viewer's own row with a `(you)` label — so no second request and no role prop. |
| **D2** | ⚠️ **REVERSED by [ADR-551](ADR-551-autonomy-is-a-property-of-an-agent-not-of-the-workspace.md) (2026-08-12, next day).** The pane is removed. D2's *evidence* stands in full — the gate is live, and deleting `_autonomy.yaml` still inverts ADR-408 D3 (ADR-551 D2 keeps every bit of it). The error was answering **"is the mechanism live?"** when the question was **"is the workspace the right owner?"**. The gate applies ONLY to the steward's own calls (`permission.py` returns APPLY at `non_freddie_caller` before reading it), so a workspace-scoped control named a scope it never had. D2's own text recorded three defects in the control and still concluded *keep* — three defects in a surface is evidence about the surface. ADR-421 was the precedent to apply. Original text follows. ~~**The Autonomy pane STAYS. The removal is refused, with the measurement.**~~ It is the live before/after-witness gate (ADR-405 D2), re-affirmed by ADR-491 D4. §1.2 names what breaks if it goes. |
| **D3** | **The dial's copy names the scope it actually governs.** `manual` no longer claims "every action"; it says spending and outside actions wait, and everyday file edits still happen on their own — which is what the seeded `substrate:` block makes true. Widening the *control* to write the `substrate:` block is deliberately NOT done here (§4). |
| **D4** | **The hired-agent inertness is recorded, not fixed.** `load_autonomy` prefers `agents/{slug}/_autonomy.yaml`; the FE hardcodes `governance/_autonomy.yaml`. On a hire-granted workspace the pane would read and write a file the gate never consults — **latent today** (zero hire grants exist anywhere), so fixing it now would be building against a case that has never run. |

## 3. What this does NOT do

- **No role prop, no new endpoint, no second fetch.** D1 derives from data the
  pane already had.
- **No affordance keyed on the role string.** DP35 forbids `role ===` gating;
  the buttons stay driven by the server's 403 exactly as before. D1 adds a
  *sentence*, not a gate.
- **No change to what the dial enforces.** D3 is a copy fix. The gate's
  semantics are untouched.

## 4. Open

- **The `substrate:` block is unreachable from the pane** (§1.3). Two honest
  options — surface it as a second control ("file edits: ask me / do them"), or
  have the pane co-write it from the one dial. Both are real design calls about
  whether an operator should be able to make the steward ask before every file
  edit, and ADR-408 D3 deliberately said no. **D3 makes the copy true in the
  meantime; it does not settle that question.**
- **D4's per-agent resolution**, when a hire grant first exists.
- **A click-pass on the new header** as owner and as member — the role chip and
  hint must differ, and the workspace name must match the switcher.
