# ADR-611: The aperture is the member's dial on reach

**Status**: Proposed 2026-08-26 (operator thesis: *"both the reach and aperture are of the similar concern — displaying and allowing the user to control the aperture on available reach"*). **D1–D3 describe LIVE behaviour** (recorded, not built — the mechanism and its editor already exist and were verified in the code). **D4 is deferred with its cost stated**; the schema change is deliberately not taken in the same pass that raised it.

**Builds on**: ADR-405 (permission is a grant, never a species rule) · ADR-577 (the credential is a HUMAN's, keyed `user_id`; an agent caller is refused) · ADR-582 (the connection is consent + credential + aperture; ONE selection store) · ADR-591 (no pull job — the caller is a run) · ADR-594 (D1 deleted per-connection settings; D2 "reach with a receipt") · ADR-596 D1 (authority lives on grants and declarations, never on a being) · ADR-601 D1 (capability lives at the APP).

**Supersedes nothing.** It answers a question the connector ADRs left open: *who chooses which slices a piece of work may reach, and where does that choice live?*

## Context

The operator's question began as "connectors per agent — is this the main knob users work against?" Tested against the substrate, the thesis is right about the KNOB and wrong about its MOUNT, and the correction is worth recording because the wrong mount is the intuitive one.

### The narrowing already exists, and it is not on a being

A strings run reaches like this (`services/strings.py::_reach_connector_sources` → `services/connectors.py::run_connector_capture`):

```
_string.yaml sources   ∩   landscape.selected_sources   →  capture
   (the ASK — a declaration)     (the APERTURE — consent)
```

`run_connector_capture` enforces it directly: *"a consumer can narrow the operator's consent, never widen it"* (`connectors.py:357-374`). So the dial the operator is asking for is **already half-built**. What is missing is not the mechanism but its VISIBILITY and its GRAIN.

### Why per-agent is the wrong mount — three independent reasons

1. **It is coarser, not finer.** Supervisor is the one being at the strings desk. Setting "Supervisor's connectors" would set them for EVERY string in the workspace at once. Editor serves two desks (slides · text), which would be forced to share an aperture. The being is many-to-one with desks and one-to-many with work; the declaration is one-to-one with the work. Mounting a dial on the being loses resolution the declaration already has.

2. **The seam records no caller.** `run_connector_capture` executes under a fixed machinery identity — `caller_identity = "system:connector-capture"` (`connectors.py:310-328`) — identical whether the caller is Strings, a future app, or a direct invocation. "Which agent caused this connector read" is not merely unstored; it is **constant by construction**. A per-agent aperture would require threading identity through a path deliberately built without it, and ADR-577's refusal (`is_agent_caller` → refuse and log) exists precisely to keep agents away from credentials.

3. **It is authority on a being.** A dial saying "this being may reach these sources" is reach attached to a character row — the ADR-460 D3.a cliff that ADR-596 D1 restated positively: *authority attaches to relations and declarations, never to beings*.

### Reach and aperture are one concern, at two altitudes

The operator's reframing is the decision: **reach is what is AVAILABLE; the aperture is the member's dial within it.** They are not competing mechanisms, they are the two halves of one surface — show the connection's full reach, let the member choose the slice.

Both halves are already built. The aperture has a real editor (D3) and the intersection is really enforced. What is NOT built is the join between them: a member tunes the aperture in connection settings, and declares a string's sources somewhere else, with neither surface showing the other. The dial exists; the two ends of it are not in the same room.

## Decision

### D1 — The aperture is the dial, and it mounts on the CONNECTION, not on a being

`landscape.selected_sources` stays the ONE selection store (ADR-582 D2, unchanged). It answers *which slices of this connection may ever be read.* No per-being and no per-agent aperture is introduced — see Context for why all three arguments hold independently.

### D2 — The ASK stays on the declaration

A piece of standing work names the slices it wants in its own declaration (`_string.yaml` sources today). The effective reach is `ask ∩ aperture`, already enforced. This is where per-work granularity lives, and it is finer than any being-level dial could be.

### D3 — The surface shows AVAILABLE REACH and the aperture within it — **already BUILT**

The operator's framing describes a surface that already exists:
`web/components/settings/ManageConnectionSubsurface.tsx` renders the
connection's full landscape (`landscape.resources`) as a checkbox list with
`selected_sources` as the live selection over it, saved through
`api.integrations.updateSources`. Reach displayed, aperture editable, and the
copy already states the consent property — *"Nothing is ever selected for
you."*

Verified rather than assumed: an earlier read of this ADR concluded the
aperture was "real but invisible," which was WRONG — the grep missed the
component because it calls `updateSources`, not the `selected_sources` name the
store uses. Recorded because the same wrong conclusion is one rename away from
being drawn again, and it would have produced a duplicate surface: exactly the
ADR-562 second-home drift.

So D3 requires **no build**. What it does require is that a future connector
proposal check this component first. The open half of the operator's request is
not the editor — it is that the aperture is edited in SETTINGS while the work
that consumes it is declared elsewhere, so a member tuning a string's sources
does not see the aperture bounding them. That is a legibility gap between two
existing surfaces, not a missing control.

### D4 — Workspace scoping is the real cost, and it is NOT taken here

Making the aperture a workspace-level control (rather than an account-level one) requires a re-key, and this ADR states the cost rather than hiding it:

- `platform_connections` is keyed `("user_id", user_id)` — `workspace_context.account_scope_filter`, which states *"there is no workspace resolution, by design."*
- Its RLS is a single policy: `ALL USING (user_id = auth.uid())`.
- `platform_connections.workspace_id` EXISTS but means **routing, never ownership** (ADR-577) — reusing it as a scope key is exactly the conflation ADR-577 withdrew ADR-566's second store for.

So a workspace-scoped aperture is a migration plus an RLS story plus a re-read of every `account_scope_filter` call site. That is a decision of its own, and taking it silently inside a display change is how ADR-566's unfillable second store happened. **D4 is named and deferred, not assumed.**

### D5 — If the question is "which sources may this reach at all," that is a GRANT

There is a real question adjacent to the aperture: *may this workspace / this principal reach my work Slack but not my personal one?* That is **reach**, and reach already has a home — `principal_grants` (ADR-405), per-principal, kernel-held, revocable, audited. It is NOT the aperture and must not be folded into it: an aperture is the owner tuning their own consent; a grant is the workspace deciding who may act at all.

Recorded so a future session asking "should the aperture be per-principal?" finds the answer: no — that question is a grant, and the mechanism exists.

## Consequences

- The dial the operator asked for is **already built** (D3, verified in the component, not inferred). The remaining gap is legibility between two existing surfaces, not a missing control — and it needs no migration.
- Per-agent connectors are refused with reasons, and the reasons are structural rather than stylistic — a future session proposing them again will find all three.
- `standing_executor`-style seams are unaffected: nothing here attaches to a being.
- The connector data model is unchanged by this ADR. D4 is the open question, with its cost stated, for whoever takes it.

**The rule this ADR leaves behind**: an aperture is the owner narrowing their OWN consent; a grant is the workspace deciding who may act. Both are reach; neither is ever a property of a being.
