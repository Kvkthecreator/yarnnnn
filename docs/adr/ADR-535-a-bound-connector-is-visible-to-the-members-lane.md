# ADR-535 — A bound connector is visible to the member's lane

> **⚠️ D1 is NARROWED to its actual subject by [ADR-566](ADR-566-the-workspace-allocates-the-agents-credential.md) (2026-08-13).** *"A connector binding is a property of the member, not the workspace"* is true of **the member's own connector** — the subject this ADR was about — and was **never a ruling about the workspace's own allocated credential**, which ADR-425 D3 had already reserved and ADR-566 built.
>
> **Everything this ADR actually decided stands unchanged**: D2 (`list_integrations` on the uniform lane surface), D3 (the frame states the ceiling affirmatively), D4 (the foreign-caller asymmetry), and §7's ceiling — **a lane still gets no connector CONTENT reach**, and ADR-566 §7 explicitly does not build the per-caller-class rung D4 recorded as owed.
>
> **The read to avoid**: D1 answers *"whose bindings does a member's lane see?"* (theirs, and no others). It does not answer *"may a workspace allocate a credential to its agents?"* — that is ADR-425 D3 → ADR-566. The two stores are disjoint (ADR-566 D2) and never fall back to each other.

**Status**: Accepted (2026-08-07, operator-ratified). **Amends ADR-420 §10** (the connector demand-gate) and **ADR-411 D3** (the lane surface's "no platform tools" clause), narrowly and in one direction: *visibility*. Ships code (D2/D3/D4).

**Supersedes nothing. Amends**:
- [ADR-420](ADR-420-engine-breadth-vs-connector-breadth.md) §10 Amendment — the connector demand-gate. §2 below argues why the gate does not bind this decision.
- [ADR-411](ADR-411-chat-lanes-and-the-lane-tool-surface.md) D3 — "no platform tools" on the lane surface. D3 below takes the visibility half only; the reach half stands.

**Preserves**:
- [ADR-463](ADR-463-capability-not-vendor-the-model-agnostic-carve.md) D4.a — the ceiling. `list_integrations` is already in `READ_ONLY_PRIMITIVES`; this ADR widens the surface by a name that the existing derivation already admits, and adds no new classification.
- [ADR-467](ADR-467-app-residency-and-the-cast.md) D4 — the surface is uniform. This addition is uniform; no per-agent variance is introduced.
- [ADR-307](ADR-307-one-gate-one-queue.md) — the one consequential gate, untouched. Nothing here becomes consequential.
- [ADR-425](ADR-425-the-credential-is-an-account-object.md) — the credential is account-scoped. D1 below is a restatement, not a new rule.

---

## 1. The observation

An operator bound Notion in Settings, then asked an Agent in chat whether it had a Notion connection. The Agent answered:

> "This workspace doesn't have a live Notion connector, and I can't pull/push to Notion directly."

The second clause is true. **The first is false** — the connector was bound, active, and visible in the operator's own settings pane two clicks away. The Agent could not see it, so it guessed, and it guessed wrong about the operator's own workspace.

That is the defect this ADR closes. Not "the lane cannot reach Notion" — that is a deliberate ceiling and it stands. The defect is that **the lane cannot see what the member has bound**, and therefore misdescribes the member's own workspace back to them.

## 2. Why the ADR-420 demand-gate does not bind this

ADR-420 §10's amendment paused connector breadth as *"supply ahead of demand"*: no user had hit "I wish my lane could reach X," so building connector infrastructure would be building ahead of need.

That reasoning is sound **for acquiring reach** and does not reach this decision, for three reasons:

1. **The connector is already acquired.** `platform_connections` is already user-scoped, already OAuth-bound, already surfaced in Settings → Connections. There is no new capability being shopped for, no seed to pick, no moat test to run on a candidate. The binding exists; the question is only whether the member's own lane may observe that it exists.
2. **The moat-leak test measures the wrong vector here.** §10's test retracted Higgsfield as *"a competing commons, not a dumb peripheral"* — the concern is capability leaking *outward* to a rival surface. Reading the *names and statuses of the member's own bindings* moves nothing outward. It is strictly less externally-directed than `WebSearch`, which is already on the lane surface.
3. **Demand was named.** ADR-420 §10 conditions the build on *"real demand names the first capability."* The operator named it, from a live surface, against their own bound connector. The gate's own release condition is met for the visibility half.

**What remains gated**: reaching *through* a connector — reading a Notion page, a Slack channel, a GitHub repo into a lane turn. ADR-420's demand-gate, its moat-leak test, and its seed-list discipline all continue to govern that, and this ADR does not touch it. See §7.

## 3. D1 — A connector binding is a property of the member, not the workspace

Restated, not decided here (ADR-425): a `platform_connections` row is keyed `user_id`; `workspace_id` is vestigial-for-humans. The operator's Notion follows the operator across workspaces.

This composes with **ADR-411 D4** — *"the lane's reach is exactly the member's reach"* — to fix the scope question with nothing left to choose:

> A lane sees the bindings of **the member whose turn it is**, and no others.

If bindings were workspace-scoped, one member's lane would observe another member's private credential inventory, and D4 would break. They are not, so it does not. Concretely: the operator's turns see the operator's Notion; a second member's turns see theirs; the workspace holds neither credential — it holds only the substrate either of them authors.

## 4. D2 — `list_integrations` joins the uniform lane surface

`LANE_SURFACE_EXTRA` becomes `("QueryKnowledge", "WebSearch", "list_integrations")`.

The addition is admissible under the existing ceiling **without widening it**:
- `list_integrations` is already in `permission.py::READ_ONLY_PRIMITIVES` (verified, not asserted) — the ADR-463 D4.a derivation admits it as-is.
- It is metadata-only: `platform, status, connected_at, last_updated`, plus per-platform identifiers already used for addressing. It never calls a provider API and never decrypts a credential.
- It is **uniform** per ADR-467 D4 — every lane and every Agent gets it, or none does. No per-agent `tools` field is reintroduced.

Per the `lane_tool_names()` singular-source discipline, three things update together or the gate fails loud: the declared payload, the execution allowlist, and the prompt prose (D4).

## 5. D3 — The frame stops asserting a closed world

The lane frame currently reads:

> you read this member's commons (QueryKnowledge searches it by meaning) and the open web (WebSearch), and you write only to the commons.

That sentence is a **closed-world assertion**, and D2 falsifies it. Left alone it would be the Scout-bug shape (ADR-467 §1): prose claiming a surface that disagrees with the payload — here, inverted, prose *denying* a surface the model actually holds.

The frame is re-cut to name the third read and, critically, to state the ceiling **affirmatively** rather than by omission. The model must be told both halves in the same breath:

- it can see *which* connectors the member has bound;
- it cannot read *through* them.

Without the second clause, a model handed `list_integrations` will reasonably infer that seeing a Notion binding implies it can read Notion, and will hallucinate a capability one rung above what it holds. **Naming a capability's edge is part of granting it.**

## 6. D4 — The foreign-caller asymmetry, named and deliberately deferred

`resolve_permission` returns `APPLY, "read_only"` at its second branch — **before** the MCP foreign-caller branch (`permission.py`, the `yarnnn:mcp` matcher). Any name in `READ_ONLY_PRIMITIVES` therefore passes for *every* caller class, including a foreign LLM connected over MCP, with no per-principal grant consult.

For `WebSearch` that is harmless: the public web is not the operator's. For `list_integrations` it is a genuine, if narrow, asymmetry — a foreign caller learns **which platforms the operator has bound**. Not credentials, not content; an inventory.

**Ruled**: this is disclosed and accepted for the metadata surface, and it is a **hard blocker** for the content surface (§7).

The reasoning: an MCP-connected foreign LLM is a principal the operator deliberately bound to their own workspace (ADR-373/386), and the fact that the operator uses Notion is not a secret from a principal they have already granted read of their commons — where Notion-derived files may already sit, attributed. The disclosure is proportionate.

It would **not** be proportionate for a connector *content* read, which would exfiltrate the operator's private connected-workspace data through the operator's own OAuth token to a third-party LLM. The gate has no rung between "in `READ_ONLY_PRIMITIVES`" and "per-caller-class scoped." **Building that rung is a precondition of §7's content half, and this ADR records it as owed rather than discovering it later.**

## 7. What this ADR does NOT do

- **It does not give any lane connector *content* reach.** No Notion page, no Slack message, no GitHub file enters a lane turn. `LANE_TOOL_NAMES` is unchanged; no `platform_*` tool joins the surface.
- **It does not un-pause ADR-420's connector breadth.** The demand-gate, the moat-leak test, and the seed-list discipline continue to govern reach. §2 argues only that they do not govern *visibility*.
- **It does not touch the ADR-307 gate,** create a consequential primitive, or widen `READ_ONLY_PRIMITIVES` (the name was already in it).
- **It does not reintroduce per-agent tool variance** (ADR-467 D4). The addition is uniform.
- **It does not compose the outbound MCP client into the lane loop** (ADR-420 §7.1). That remains walled off, deferred to its own ADR.
- **It does not build the per-caller-class scope rung** on external reads (D4). Owed, and blocking for connector content.
- **It does not touch `CONNECTOR_CAPTURE_ENABLED`** (ADR-404 D2). The capture lane stays dormant; this is about a member's lane *seeing* a binding, not a background lane *reading* through one.

## 8. Consequences

**The good**: an Agent asked "do you have my Notion?" now answers from substrate instead of guessing, and answers with the edge included — *"you have Notion bound; I can't read through it."* That is the honest sentence the operator's screenshot should have produced.

**The risk, named**: a model that can see a binding will be tempted to claim it can use it. D3's affirmative ceiling-statement is the mitigation, and it is prose — weaker than a gate. The gate half is that no `platform_*` tool is on the surface, so the *claim* would be a hallucination, not a capability. A hallucinated claim is a prompt-quality defect; a reachable outward write would be a safety defect. This ADR keeps the failure mode in the first category.

**The precedent to watch**: this is the first name on the lane surface that reads the operator's *account* rather than their commons or the public web. §6 discloses the asymmetry it inherits. The next such addition must not inherit it silently — it must clear the per-caller-class rung first.

## 9. Verification

- The D4.a derivation gate (`api/test_agent_registry.py`) must pass **unchanged in kind** — asserting membership in `READ_ONLY_PRIMITIVES` for every `LANE_SURFACE_EXTRA` name, now including the third.
- The three-way agreement (payload == allowlist == prose) must hold for every character, and must **fail loud** on a surface name with no schema.
- A gate must assert the frame no longer makes the closed-world claim, and **does** state the ceiling — the D3 half is prose, so it needs a gate or it will regress silently.
- Made-to-fail: removing the name from `LANE_SURFACE_EXTRA`, or restoring the closed-world sentence, must each turn a gate red.
