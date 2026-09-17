# ADR-654 — An agent's engine is the member's choice

**Status**: Accepted (2026-09-17, operator-ratified)

**Amends** [ADR-562](ADR-562-an-apps-ai-configuration-is-declared-where-the-app-lives.md) §2 D1
(the "why not a workspace folder" paragraph) and [ADR-647](ADR-647-the-conversation-prefix-is-cacheable.md) D7.

**Preserves** (load-bearing, untouched): ADR-460 D3.a (the authority cliff — no
authority-shaped key on an agent row, ever), ADR-460 D4 (a lane's engine is a
HISTORICAL FACT; new conversations only), ADR-647 D5 (a preference NARROWS, it
never grants), ADR-647 D6 (machinery is out of scope — `SYSTEM_CALLS` is keyed
by call type and unreachable from any member preference), ADR-562 D3 (an app's
RESIDENT is resolved server-side from the app's own declaration), ADR-495 D1
(the cast decides who replies).

---

## 1. Context — optionality is the product, and it stopped one level short

The operator's ruling, verbatim:

> "the kernel Agent registry should also, fully accomodate LLM engine, model
> selection and optionality as first class. in the bigger picture, i believe it
> is the right investment in terms of code and architectural design that
> accomodates the truly AI first, interoperable workspace."

And, on scope:

> "optionality should be for all models, not just anthropic."

This is a positioning decision before it is a technical one. An
agent-native operating system whose agents are welded to one vendor's engine is
not interoperable; it is a client for that vendor. The registry already carries
`model` as an ordinary field — what it lacked was any way for a member to
exercise it per agent.

**What was already true.** ADR-647 D4/D5 shipped a member engine preference that
is provider-neutral and already consulted when a BOUND app lane is created —
`resolve_member_engine` in `services/lane_runner.py`, stored in `member_state`,
resolved through the chooser's own two questions. Its own D4 text names the gap
it closed: *"Studio/Text/Slides/Images all run bound lanes, so the surface
carrying most of the spend was the one surface a member could not re-point."*

**What was not.** That preference is ONE engine for the whole member. A member
who wants Editor on a frontier reasoning engine and Blogger on a cheap fast one
has no way to say so — the preference is workspace-wide, so choosing for one
agent chooses for all of them. ADR-647 D7 refused the per-agent form explicitly
(*"It is stored on the member, not on the agent row"*), and ADR-562 §2 D1 refused
the workspace-scoped form as *"the ADR-460 D3.a cliff arriving through a config
file."*

**Both refusals are re-examined here, and one of them was reasoning about the
wrong fact.**

## 2. D1 — The cliff was never about the engine

ADR-562 §2 D1 argued that a member-editable resident would be *"the ADR-460 D3.a
cliff arriving through a config file."* That is correct **about the resident**
and incorrect **about the engine**, and the distinction is the whole of this ADR.

ADR-460 D3.a makes one thing unrepresentable:

> **The kernel Agent registry row shape has NO field for consequential
> authority.** ... The authority is not omitted from the row — it is
> **unrepresentable** in it.

And the row shape ADR-460 §5 D4 ratifies, in the same ADR, is:

```
{ name, icon, model, posture, tools, token_profile }   # + NO authority field (D3.a)
```

**`model` is in the ratified row.** The cliff protects authority — what an agent
may DO. An engine is not authority: it grants no reach, no mandate, no clock, no
credential. ADR-566's cross-reference states the partition in one line —
*"Reach is a grant; authority is a dial; only the second was ever deferred."* An
engine is neither a grant nor a dial.

ADR-460 D5 already filed them as different objects: **Agent configuration** is
Mechanism (Axiom 5) — *"a registry row — engine, tools, posture, token
profile"*; **Agent** is Identity (Axiom 2). Re-pointing an app's RESIDENT changes
identity and stays refused (ADR-562 D3 is preserved verbatim: the app asks, the
server answers WHO). Re-pointing the ENGINE behind that identity is a
configuration change.

**D1 — an agent's engine is configuration, not authority. A member may choose
it. An agent's IDENTITY remains the app's to declare, resolved server-side.**

## 3. D2 — Per-agent, per-member, composed beside the kernel default

ADR-460 §5 D4 sequenced this widening rather than forbidding it:

> kernel Agents ship as constants — every workspace gets the same base set,
> out-of-box, zero configuration. **Per-workspace customization is a later
> widening, forward-compatible by construction** (a workspace-scoped registry
> composes *beside* the kernel set, never replacing it — ADR-450's rule).

This ADR is that widening, at member scope (the operator's choice, 2026-09-17).
Per-member rather than per-workspace keeps ONE storage shape: `member_state` is
already keyed `(workspace_id, principal_id, key)`, so a per-agent override is a
key, not a new table, a new scope, or a second resolution layer.

**D2 — the per-agent engine override is `member_state` key
`agent_engine:{slug}`, resolved beside the member-wide `default_engine` and the
agent's kernel row.** The resolution order, most specific first:

1. the engine named explicitly at the door (chat lanes only — a bound lane's
   colleague is its app's)
2. **the member's override for THIS agent** (new)
3. the member's workspace-wide `default_engine` (ADR-647 D4)
4. the agent's own declared engine (the kernel constant)

Each step NARROWS: every stored value resolves through `offered_lane_models()`
+ `lane_model_availability()`, so a stored engine that is retired, unpriced,
keyless or upstream-refused resolves to `None` and the next step stands. ADR-647
D5's posture is inherited, not re-argued — one resolver, not two.

**Provider-neutral by construction.** The override accepts any row in
`offered_lane_models()`. The two constraints it inherits are not provider
filters: `offered` excludes RETIRED rows (so a new conversation is not created
on a superseded engine while existing lanes keep running — ADR-559 D2), and the
billing-rate requirement is satisfied today by every offered row across all five
providers. An engine with no rate row prices silently at the Sonnet default,
which is the margin leak `_BILLING_RATES` exists to prevent.

**New conversations only.** A lane's engine is persisted at creation and is what
ACTUALLY ran, rendered into every revision's attribution (ADR-460 D4). An
override that re-pointed existing lanes would rewrite what a past revision
claims about itself. This resolves at the creation door and nowhere near the
turn path — the same boundary ADR-647 D4 drew.

**No field is added to `AGENTS`.** The override is member state, not a registry
key; `AGENT_ROW_KEYS` is unchanged and the D3.a whitelist still holds.

## 4. D3 — The token profile resolves with the engine

`token_profile` has been in `AGENT_ROW_KEYS` since ADR-460, is set to `8192` on
all three agents, and **is read by nothing**. The turn path uses
`_LANE_MAX_TOKENS = 4096` (unbound) or `STUDIO_LANE_MAX_TOKENS` (bound). A
declared field with no reader is the class the 2026-09-16 truncated-answer
finding named: `finish_reason` was plumbed from birth with zero consumers, and a
`length` finish with empty text billed 4,438 tokens and showed a blank message.

This matters more once engines are chosen freely, and it matters in BOTH
directions. Choosing a higher-headroom engine while the output ceiling stays
4096 buys a more expensive model with the identical cut-off — the optionality is
nominal. Providers also differ sharply in output ceilings, so a constant tuned
against one vendor is not a sane default across five.

**D3 — the output ceiling for an unbound lane resolves from the agent's
`token_profile`, falling back to `_LANE_MAX_TOKENS`.** Bound lanes keep
`STUDIO_LANE_MAX_TOKENS` (ADR-440 D3 — authoring > chat, gate-asserted;
untouched). The field becomes load-bearing rather than being deleted, because
the headroom lever is exactly what an engine choice needs to carry.

## 5. D4 — The choice has a door, and the door reads labels

ADR-647 shipped the preference with **no way to set it**: `MEMBER_ENGINE_KEY` is
read by `ChatSurface` and written by nothing. A preference a member cannot set
is not a feature; it is a field awaiting its first writer.

**D4 — the agents pane is the door.** `?agents.agent={slug}` already renders
"Runs on"; it gains the picker, served from the `models` roster the SAME
envelope already carries (`lanes.list().models` — no new endpoint, no second
roster to drift). An engine that cannot run is served greyed WITH its reason
(ADR-559 D3 / ADR-647 D8), never filtered.

**The label, not the routing key.** The pane rendered `agent.model` verbatim —
`anthropic/claude-sonnet-5`. `LANE_MODELS` carries `label` for exactly this, and
the registry is emphatic that the label is not chrome: it is written into every
revision's attribution and is what the model is TOLD IT IS. A member reads
"Claude Sonnet 5".

## 6. What this does NOT do

- **It does not let an app's RESIDENT be re-pointed.** ADR-562 D3 stands
  verbatim: the app asks, the server answers who. Identity is the app's;
  only the engine behind it is the member's.
- **It does not touch machinery.** ADR-647 D6 is preserved structurally, not by
  policy: `SYSTEM_CALLS` is keyed by call type and is not reachable from
  `member_state`.
- **It does not add an authority field.** `AGENT_ROW_KEYS` is unchanged.
- **It does not re-point existing lanes.** Ever.
- **It does not change attribution.** A lane's engine remains what ran.

## 7. The gate

`api/test_adr654_agent_engine_choice.py` — the resolution order and its
precedence; the override NARROWS (retired / unpriced / unavailable each fall
through); provider-neutrality (the override accepts every offered provider, and
the resolver contains no vendor branch); new-lanes-only (the turn path never
consults the override); `AGENT_ROW_KEYS` carries no authority key and no new
engine key; `token_profile` is READ (falsified by reverting to the constant);
the pane renders labels, not routing keys.

Falsified in both directions before it ships.

---

**An agent's engine is configuration, not authority — so it is the member's to
choose, per agent, across every provider the door already offers; identity stays
the app's, the choice narrows rather than grants, and the token profile that was
declared-and-unread finally resolves with the engine it belongs to.**
