# ADR-615: Reach follows the principal, not the surface

**Status**: Ratified + implemented 2026-08-28. Operator instruction: *"turn reach should be enabled (and be enabled by default for all workspaces now and into the future) … when users, within workspaces, toggle and manage their agents post connections, it works seamlessly across wherever that agent is accessible."* The framing question that settled the desk half was the operator's: *"a desk is a desk is it not? shouldn't the connectors and associated permissions and scope follow the principal?"*

**Amends**: [ADR-585](ADR-585-turn-reach-the-members-own-connections.md) D2 (the flag's default) · [ADR-612](ADR-612-an-agent-opts-in-to-the-workspace-grant.md) D5 (a desk turn's default-closed posture).

**Builds on**: ADR-405 (permission is a grant) · ADR-577 (the credential is a HUMAN's) · ADR-596 D1 (authority lives on grants, never on a being) · ADR-612 D1–D4 (the opt-in, unchanged) · ADR-467 D4 (one uniform tool surface).

**Disposition** (per the intake-pipeline.md §5 rule, declared first): this is **TURN REACH** — transient, dying with the turn. The intake pipeline, the capture writer, and their dials are untouched.

---

## 1. Two things were true at once, and they did not agree

`TURN_REACH_ENABLED` had never been set on any deployment. ADR-585 built the capability whole and left it dark under the ADR-404 D2 pattern ("built whole, lit deliberately"); ADR-612 then built a per-being opt-in *above* a capability that was still unlit.

The result was observable and confusing: the agents pane offered Slack / Notion / GitHub toggles, a member turned all three ON for Supervisor, and the agent still answered *"there's no tool in my kit that opens a repo."* Every layer was individually correct. The store wrote, the resolver read, the prose derived honestly from the flag. **Nothing was broken; one environment variable was unset,** and the surface gave a member no way to learn that.

A capability every workspace is meant to have should not be an environment variable an operator must discover.

## 2. The cut line that did not survive inspection

ADR-585 D1 confined reach to the **open chat turn**. ADR-612 D5 relaxed that for a desk turn *only* on an explicit per-being opt-in, keeping default-closed as the safety property.

Both rested on the turn's **shape** — `app`, `artifact_path`, `derive_recipe` — standing in for the presence of a principal. Inspect what a lane turn actually is and the distinction dissolves:

- Every lane turn stamps `lane_caller_identity` → **`member:{user_id} via {model}`**.
- Grants resolve by that member's own `principal_id`, at every surface.
- ADR-577's `is_agent_caller` correctly does not trip for any of them: a lane turn is a human's hands.

An open chat turn and a Text desk turn are **the same principal, embodied identically**. "Which pane is open" is a *surface* fact that was standing in for a *permission* fact it never carried. The visible consequence: a connection the member granted was readable when they typed in `/chat` and invisible when they typed in Text — one principal, one grant, two answers.

**What the shape was really a proxy for is ABSENCE** — nobody present. That is a real and important boundary, and it is not the app/chat line. It is the unattended line, and it holds on its own (§4).

## 3. Decisions

### D1 — Turn reach is ON by default, for every workspace, now and future

`is_turn_reach_enabled()` inverts: **unset means ON**. `TURN_REACH_ENABLED` survives as a deliberate **OFF switch** (an explicitly falsey value darkens a deployment), never as an opt-in a workspace must find.

An **unrecognised** value reads as ON, not OFF — the inverse of the old default and the reason this is not a plain truthiness check. Under a default-OFF flag a typo silently withheld a capability nobody was promised; under default-ON a typo must not silently strip one every workspace is meant to have.

### D2 — Reach follows the principal; the turn's SHAPE leaves the decision

`resolve_turn_reach` no longer takes `app` / `artifact_path` / `derive_recipe`. They are **deleted from the signature, not kept and ignored**, so no caller can believe they still steer the answer and no future reader re-derives a cut line from them.

Absence of an opt-in now means **everything granted, at every surface** — which is what ADR-612 D2 already says one layer up. The two layers finally agree.

### D3 — The opt-in becomes purely subtractive, and the cliff test strengthens

The per-being toggles (ADR-612 D1–D4) are unchanged in shape and now do exactly one thing: **narrow**. Four states, all live:

| opt-in | meaning |
|---|---|
| absent | everything the member granted |
| `["slack"]` | Slack only |
| `[]` | **nothing** — an explicit member choice, honoured at every surface |
| — | (`TURN_REACH_ENABLED` falsey → the deployment is dark) |

The ADR-596 D1 cliff test is not merely preserved but *strengthened*: narrowing is now the **only** thing the field can express. `allowed_platforms` still intersects against actually-connected platforms, so widening stays unrepresentable rather than discouraged.

### D4 — A failed lookup degrades to "not scoped", never to an invented scope

Pre-615, a broken opt-in store failed toward *no reach*. Now it degrades to **not-scoped** — the same state as a member who never scoped this being. This cannot over-grant: the downstream intersection bounds it by the workspace's actual grant. The property worth pinning is that a broken store never invents a **scope the member did not set**, and the gate drives that path with a raising double rather than asserting it.

### D5 — The `agents` capability row is derived, not asserted

`connector_does()["agents"]` hard-coded *"no direct platform access — agents read the landed capture files only."* That was **already inaccurate before this ADR**: `get_headless_tools_for_agent` merges capability-scoped `platform_*` tools for headless agents, and `SyncPlatformState` sits in both `HEADLESS_PRIMITIVES` and `FREDDIE_PRIMITIVES`. The sentence was true only because the ADR-577 refusal caught those callers downstream — it described an outcome as though it were a structural boundary.

It now derives from the same flag as its `chat` sibling, for the same stated reason: a hand-kept sentence outlives the capability it describes. The honest half of the old wording is preserved in both branches — an unattended run reaches nothing live.

## 4. What does NOT follow the principal, and why it holds without a flag

**Unattended standing runs reach nothing live.** They execute through `run_bounded_derive_turn`, which is **toolless by construction** ("No tools, one user message") and never calls `lane_tools_openai`. A scoped being gains no live reach in its cron-fired runs.

This is the boundary ADR-612 D5's caution was really protecting, and it is **structural, not a default**: a clock plus a credential is the combination ADR-596 D2 houses on grants and declarations. Reverting D2 of this ADR would not open it; deleting the toolless construction would, which is why the gate asserts that construction directly.

Also unchanged: ADR-577 (no being holds a credential; the opt-in selects among the member's own) · the intake pipeline and capture writer · ADR-563 scopes and ADR-573 binding on the inbound MCP side.

## 4b. What the click-pass found (2026-08-28, same day)

Driving the real surface produced a PASS on the headline claim and one defect the gates could not see.

**PASS** — an Editor at a Text desk fetched a GitHub README live (receipt: `read a GitHub README`, first heading `# YARNNN`), the exact capability it lacked the day before. It also correctly refused a repo outside the declared aperture, named the in-scope repo, and offered both remedies.

**DEFECT — the opt-in was read with the wrong client, so narrowing did nothing.** With Editor scoped to NO connections, it still fetched the README. `member_state` is service-role-only by RLS (migration 202), and a USER client's select against it returns **zero rows, not an error**. `opt_in_for` therefore reported *absent* — which under D2 means **everything granted**. `lane_runner` was passing the turn's `auth.client`.

Two things make this worth recording rather than quietly fixing:

- **This ADR is what made it dangerous.** Pre-615, absent meant *no desk reach*, so the wrong client failed CLOSED and looked correct. Flipping the default turned a latent wrong-client bug into an open door. A default inversion re-grades every fail-open path that was previously masked — that is the class, not this instance.
- **No source-reading gate could catch it.** Every layer read correct in isolation; the store held the right value and the resolver computed the right answer *when handed the right client*. Only driving the surface, then querying the store, separated "computed correctly" from "computed on what the turn actually had".

**Fix**: `_read_map` resolves the service client ITSELF rather than trusting the caller — the write path already did. The caller's client is accepted and ignored (`_client`), because a reader that can be handed the wrong client is a door that only works when every call site remembers. Gate: `test_adr612` §4b, behavioural (an RLS-blind double must still read the recorded opt-in), falsified 3-red against the pre-fix reader.

## 5. Consequences

- A member connects once, toggles per being, and it works wherever that being is accessible — chat and desk alike. The seam that made toggles look broken is gone.
- Turn reach content flows into the member's chosen engine. ADR-585 D5's disclosure is unchanged and, being flag-derived, is now shown by default alongside the capability.
- **Cost**: reach is per-turn and, per intake-pipeline §5, "unbounded unless designed." Default-ON widens the surface on which that is true. Not addressed here, and named as owed rather than silently inherited (§6).

## 6. Owed

- **Cost bound for turn reach.** §5's unbounded-per-turn note predates default-ON. A read-tool call is cheap and platform-rate-limited, so this is a metering question, not a correctness one — but it is now a live surface rather than a dormant one.
- **The ADR-577 / steward boundary.** `is_agent_caller` keys on the `specialist:` / `agent:` prefixes plus a `headless` flag; Freddie stamps `freddie:{…}` and carries neither, so the refusal may not catch the steward on the `SyncPlatformState` path. **Independent of this ADR** — turn reach never touches that path, and the steward is not a lane. Flagged here because it surfaced in the same audit; it needs a DRIVEN TRACE (ADR-577 §7) before anyone writes against it.

**The rule this ADR leaves behind**: reach follows the *principal*, never the surface. A distinction drawn on which pane is open is a surface fact wearing a permission's clothes — the real boundary is whether anyone is there.
