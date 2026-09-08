# ADR-647 — The conversation prefix is cacheable, and the member picks the engine

**Status**: Accepted · 2026-09-08
**Amends [ADR-634](ADR-634-the-lane-frame-is-cacheable.md)** (the frame is no
longer the re-sent bulk) and **[ADR-559](ADR-559-the-engine-registry-currency-retirement-availability.md)** (an
engine gains a member-scoped default). Respects
[ADR-557](ADR-557-the-router-chokepoint-and-the-transport-product-split.md)
(the transport chokepoint), [ADR-556](ADR-556-systematic-calls-and-the-model-selection-boundary.md)
(machinery never routes on a member preference), and
[ADR-460 D3.a](ADR-460-agents-one-concept-independent-facts-one-gate.md) (no authority
on an agent row).

---

## 1. The report

> "our usage to spending is too high for me to bear on the existing claude
> sonnet 5 … I want us to consider allowing engine change optionality as a
> first class feature within agents … following the logged in users'
> preferences."

Two asks, and the second is the interesting one because **the first has a
cheaper answer than the one proposed.**

## 2. What the meter actually said

30 days of production `execution_events`:

| | cost | share |
|---|---|---|
| **total** | **$75.98** | |
| slug `lane` | $74.63 | **98%** |
| `claude-sonnet-5` | $65.59 | 86% |

So this is entirely a lanes story. The decomposition is where the answer is:

| component | cost | share |
|---|---|---|
| **fresh (uncached) input** | **$50.27** | **67%** |
| output | $18.13 | 24% |
| cache write | $4.67 | 6% |
| cache read | $3.06 | 4% |

**40% of lane calls read zero cache.** Fresh input ran a median of 10.5K
tokens/call, p90 38K, max 84K — against a system frame of roughly 4K.

**The engine price was not the dominant term. The prompt size was.** Switching
to a 20x cheaper engine while sending a 3x larger prompt than necessary buys a
real saving and hides a defect; fixing the prompt buys a comparable saving,
keeps the engine, and helps every engine added afterwards.

## 3. Why the prefix was uncached (D1)

ADR-634 marked the system frame `ephemeral` and stopped, on the stated
reasoning that the ~16KB frame was what got re-sent on every tool round. That
reasoning was correct **when measured** and expired quietly.

What dominates now is the **message prefix**: every prior assistant turn and
every tool RESULT, re-sent verbatim on each of up to 8 rounds. A `ReadFile` of
a real artifact is thousands of tokens that never change again for the rest of
that turn, and they were billed as fresh input every round.

> ⭐ **A cost optimisation is a claim about a WORKLOAD, and a workload moves.**
> ADR-634's numbers were right in July and wrong in September. The fix was not
> a smarter guess; it was re-measuring. An optimisation ADR should be re-run
> against the meter before it is extended, not reasoned forward from.

**D1 — one ephemeral breakpoint on the tail of the message list.** The prefix
is append-only and byte-stable, which is exactly what an ephemeral breakpoint
wants: marking the LAST message caches everything before it, so round N+1 reads
what round N wrote.

**One breakpoint, not one per message.** Anthropic allows at most 4 per request
and caches the whole prefix up to each. The frame holds one; one more on the
tail covers the entire conversation. A breakpoint per message would spend the
budget by round 4 and start silently dropping the earliest — the failure this
single-marker rule exists to avoid. Two total, well inside the limit.

**The marked message is COPIED, never mutated.** The lane loop appends to one
list across rounds and re-sends it; mutating in place would bury a stale
breakpoint mid-prefix on the next round, spending a breakpoint on a boundary
nothing reads. Every round marks its own tail and only its own tail.

**D2 — Anthropic only.** Verified by executing all four LiteLLM transforms
against litellm 1.83.9, not by reading them:

| provider | behavior |
|---|---|
| anthropic | keeps the marker (into `tool_result` and `text` blocks alike) |
| openai · deepseek · xai | stripped by `OpenAIGPTConfig.remove_cache_control_flag_from_messages_and_tools`, inherited through the MRO |
| gemini | dropped by the Vertex transform (parts carry no such key) |

So the marker is inert rather than dangerous off-Anthropic — and those
providers cache automatically without one. Marking there would be dead weight
that still has to be reasoned about at every future transform change.
`_prefix_is_cacheable` narrows to the provider that needs it.

**D3 — one composition site.** `route_completion` and `route_completion_stream`
each built the request list inline, identically. A caching rule applied in one
and not the other is a silent 2x on whichever path the surface happens to take
— and the streaming door is the one members use. Both now call
`_build_messages`. The ADR-634 gate's §3 check, which pinned the old duplicated
literal, is re-cut to assert the RELATION: it would otherwise have failed the
moment the duplication it complained about was removed (*a gate that pins a
spelling pins the defect*).

**The trade, stated in both directions.** A cache write is 1.25x. A one-round
turn whose prefix is never re-read pays the premium for nothing; a two-round
turn already wins. This is the same honest trade ADR-634 recorded, and the gate
asserts both halves rather than only the favourable one.

## 4. The engine is the member's, and it is a DEFAULT (D4)

The second ask. The shape matters, and the recently-closed neighbouring
question makes it easy to get wrong.

[ADR-645](ADR-645-reach-is-the-connection-surface.md) ruled that **reach follows
the member** because a credential carries IDENTITY: adoption breaks attribution
at the boundary, invisibly. It is tempting to read "engine follows the member"
as the same ruling. **It is not the same fact.**

An engine carries **no identity**. It is already stamped per-lane at creation
and is a historical fact (ADR-460 D4) — it is what ACTUALLY ran, rendered into
every revision's attribution string via `principal_display.model_display`
("Kevin via Claude Sonnet 5"). A preference that re-pointed existing lanes
would rewrite what a past revision claims about itself, which is the one thing
a workspace whose invariant is *every change is signed by whoever made it*
cannot do.

**D4 — a member engine preference is a DOOR DEFAULT, never a retroactive
re-point.** It pre-fills the chooser for a NEW conversation and is consulted
when a bound lane is created. Existing lanes are untouched, forever.

**D5 — the preference may narrow to what the door already offers, never widen
it.** It resolves through the same `offered_lane_models()` + `lane_model_availability()`
the chooser uses; a preference naming a retired or unavailable engine is
ignored with the app's own default standing. Same posture as ADR-573's
workspace stamp: **a stored preference NARROWS, never grants.**

**D6 — machinery is out of scope, structurally.** `SYSTEM_CALLS` (ADR-556) is
keyed by CALL TYPE and is not reachable from this preference. A member's
engine choice must never re-point fact extraction or session summary — that is
precisely the boundary ADR-556 drew, and this ADR does not reopen it.

**D7 — the preference is not authority.** It is stored on the member, not on
the agent row. No field is added to `AGENTS`; the ADR-460 D3.a cliff is
untouched. An app's resident still declares the app's voice, and the engine
riding behind that name is now a member-scoped default rather than a constant.

## 5. DeepSeek, and failing loudly (D8)

DeepSeek has been wired, priced ($0.14/$0.28) and offered since ADR-420, and
has been dark since: not a missing key, an unfunded upstream account returning
"Insufficient Balance" (ADR-439 status note).

ADR-559 D3 already built the mechanism — `note_upstream_refusal` /
`clear_upstream_refusal`, an OBSERVED unavailability healed by any success, and
the chooser serves an unavailable engine **greyed with a reason, never
filtered**. The gap was that the reason was generic.

**D8 — an upstream funding refusal is named as such.** `upstream_refused`
carries the provider's own words to the door, so a member who tops up an
account and retries sees the engine heal, and one who has not sees *why* rather
than a blank failure. An engine that is dark for a reason the operator can act
on must say which reason.

## 6. What this does not do

- It does not make the prompt smaller. The frame, the skills index and the
  posture are all ADR-306/DP22 territory and are already ratcheted; this ADR
  changes what they COST to re-send, not what they contain.
- It does not add a per-agent engine field (D7).
- It does not touch attribution. A lane's engine remains what ran.

## 7. Verification

- `api/test_adr647_history_caching.py` — 34 checks. §5 EXECUTES all four
  provider transforms rather than reading them. Falsified both ways: disabling
  the marking reds 6 checks; marking every message (the breakpoint-budget
  defect) reds 4.
- `api/test_adr634_prompt_caching.py` — 29 checks, §3 re-cut to the relation.
  Falsified: reverting one door to its inline assembly reds it.
- `api/test_adr647_member_engine.py` — 39 checks covering D4/D5/D6/D7/D8.
  Falsified both ways: removing the narrowing reds 4 (§2), and making the turn
  path consult the preference reds the attribution check (§4).
- `api/test_adr557_router_hardening.py` — 18 checks. Repointed off the deleted
  `services/radar.py` (see below) and §4 now EXECUTES the flag-off degrade.
- `cd web && next build` exit 0.

### A stale gate found on the way

`test_adr557` read `services/radar.py`, deleted seven weeks earlier in
`15403f1`. It crashed on the `open()` — taking its entire §4 with it, so the
D1 flag-off degrade had been unverified since. Repointed to
`services/standing_work.py` (ADR-639), the live standing lane carrying the
same contract, and §4 now genuinely executes instead of skipping.

⭐ Same family as the ADR-634 §3 check above: **a gate anchored to a name
rather than a relation decays in both directions** — one crashed on a deleted
file, the other would have failed on a fixed one.
