# ADR-626: The room is multi-party, and the agent can see who is in it

**Status**: Ratified 2026-09-01 (operator ruling, from an audit they commissioned
after spotting a contradiction on the being page: *"i think your finding deems we
should update the chat room handling to make multi agent and humans (principal
agnostic) to be first class."*). Implemented same day.

**Builds on**: ADR-495 (the cast is the single authority on who replies) ·
ADR-608 (workspace membership on the timeline) · ADR-625 (the two cast doors ask
one question) · ADR-460 D3.a (no being holds authority over another).

**Amends** ADR-495 D3's rendering: the cast section stays, but it is no longer
the *only* thing telling an agent who is in the room.

## Context

ADR-625 fixed the cast DOORS. This ADR fixes what happens once someone is
through them.

An audit of the whole chat path found a clean split:

> **An agent was a first-class member of the CAST, and a second-class member of
> the CONVERSATION.**

Membership is genuinely species-blind and complete — add, list, **remove**,
visibility window, RLS, and the FE affordance all treat a human and an agent
the same, through one `add_participant` / `remove_participant` pair. That half
of the ADRs' claim holds.

The conversation half did not. Three findings, each verified in code:

### F1 — The transcript the agent reads has no authorship

`_fetch_history` (`routes/lanes.py`) selected `metadata` and read **only**
`attachments` out of it, then emitted:

```python
out.append({"role": r["role"], "content": text})
```

`author_principal_id` and `agent_slug` are both written at persist time
(`meta = {"author_principal_id": auth.user_id}`; `extra["agent_slug"] =
responder`) and both were dropped at replay. Two structural consequences:

- **Multi-agent**: agent A read agent B's replies as its own prior turns — both
  are bare `role: "assistant"`. A believed it had said everything B said.
- **Multi-human**: every human's message arrived as one undifferentiated
  `role: "user"`, under a frame that says *"you are {member}'s hands"*, where
  `{member}` is whoever pressed send **this** turn.

The frame tried to compensate — *"You are not speaking for the others and must
not answer as them or invent what they said."* That is **asking the model to
distinguish something the input does not encode.** A prompt cannot repair a
transcript.

The FE, notably, got this right all along: it reads `author_principal_id` and
`agent_slug` off metadata and renders faces. **Only the agent was blind.**

### F2 — Human cast members were anonymous to the agent

`_build_cast_section` renders a human as `p.get("display_name") or
p.get("email")`, else `"- another person"`. But `list_participants` selects
neither column (the table stores no label), and `enrich_cast_labels` — which
exists precisely to attach `display_name` — had **one non-test caller**: the
mentions *write* chokepoint, not the turn path.

So in a room with Kevin + Dana + Editor, Editor's frame read `- another person`.
It could count the humans and name none of them.

### F3 — An agent's visibility window was written and never read

`add_participant` stores `visible_from_sequence` for both species, and the FE
offers the control for both. But `visibility_floor` had exactly one caller,
always with a **human** principal, and `_fetch_history`'s clamp is the acting
human's floor. An agent added "from now" still read everything the sender could.

## Decision

### D1 — The transcript carries its speakers

`_fetch_history` resolves each row's author from the metadata it already selects
and prefixes the content with a speaker tag when — and only when — the room is
multi-party.

**The Messages API has no `name` field on messages** (verified against the
current contract), and the transport is litellm across several providers, so the
identity must live in the CONTENT and must be provider-neutral text. The
encoding is a single leading line:

```
Dana: what do you both think?
```

Deliberate properties:

- **Only when it disambiguates.** A room with one human and one agent gets
  byte-identical messages to before — no tag, no cache churn, no behavior
  change on the overwhelmingly common case. The tag appears when there are 2+
  humans (tag human turns) or 2+ agents (tag assistant turns), each decided
  independently.
- **`role` is untouched.** A human is still `user`, an agent still `assistant`.
  Tagging is additive; nothing about the two-role contract changes.
- **The responder's own turns are tagged too**, when tagging is on. An agent
  reading `Editor: …` beside `Supervisor: …` can locate itself; a transcript
  where only *others* are named would imply the untagged ones are its own —
  the same ambiguity, one level in.
- **Applied at the ONE assembly site.** `_fetch_history` is where history is
  built for both tool loops, so both get it (the twin-loop trap this repo has
  hit before).

### D2 — The cast section names people

`_fetch_lane_cast` (the turn path's cast read) routes through
`enrich_cast_labels`. One call, reusing the resolver the FE roster and the
mention parser already share, so a person has ONE handle everywhere.

Best-effort is preserved: an admin-API failure leaves rows unlabelled and the
section degrades to `"- another person"`, exactly as today. A turn must never
fail over a label.

### D3 — An agent's visibility window is enforced

`_fetch_history` clamps to `max(acting human's floor, responder agent's floor)`.

The primitive was already species-blind (`visibility_floor` takes a
`principal_id` and reads the same column for both kinds); it was simply never
invoked for the second species. This is the invocation, not a new mechanism.

**MAX, not the agent's alone**: the human's floor is an authorization boundary
(what *they* may see), and an agent acting in a lane must not become a way to
read past it. The agent's floor is an additional narrowing, never a widening.

### D4 — What is NOT built, and why

**An agent still cannot initiate a turn.** Both entry points require a human
caller; there is no wake, no agent-to-agent handoff, no round-robin. This is
deliberate and stays: a being that could summon another being is authority over
a being (ADR-460 D3.a), and a being that could speak unprompted is a clock on a
being (ADR-596 D1). Two agents in a room take turns *through* the member, and
the frame already says so.

This ADR makes the room **legible**, not autonomous. Those are different
questions and only the first one was a defect.

**No add-door for an out-of-cast agent by mention.** Typing `@editor` where
Editor is not in the room resolves to nobody, while `@dana` offers an
add-door. Named here as a real asymmetry, deliberately not fixed in the same
pass: the mention menu's add-door is an ADR-605 attention-routing surface, and
widening it to beings is that ADR's question, not this one's.

## Consequences

- A multi-party room is something the agent can **perceive**, not something it
  is told about in prose. The `_CAST_SECTION` instruction ("must not answer as
  them") becomes enforceable rather than aspirational, because the transcript
  now distinguishes what it refers to.
- A solo conversation — the overwhelming majority — is byte-identical. The tag
  is a function of the room, so nothing changes until the room does.
- Attribution is now consistent across the three readers of one fact: the
  ledger stores it, the FE renders it, and the agent reads it.
- Gate: `test_adr626_the_room_is_multi_party.py` — the tag appears only when it
  disambiguates, on both axes; `role` is never rewritten; the responder tags
  itself; labels reach the cast section; the visibility clamp takes the MAX.
  Every check falsified against the pre-change tree.
