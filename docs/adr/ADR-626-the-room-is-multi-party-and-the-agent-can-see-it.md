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
caller; there is no wake, no agent-to-agent handoff, no round-robin. Two agents
in a room take turns *through* the member, and the frame already says so.

This ADR makes the room **legible**, not autonomous. Those are different
questions and only the first one was a defect.

> **⚠️ Citation corrected 2026-09-01 (amendment, same day).** This paragraph
> first justified the refusal with **ADR-460 D3.a**, and that citation is
> WRONG — corrected here rather than left standing, because an imprecise reason
> in ratified canon is what later blocks a legitimate feature or gets worked
> around for the wrong one. D3.a says *"the kernel Agent registry row shape has
> NO field for consequential authority… the authority is not omitted from the
> row — it is unrepresentable in it."* That is about **consequential external
> action** and is enforced by the row shape. Routing a turn is not that, and an
> agent suggesting a colleague answer is not authority over that colleague —
> the frame already invites it (*"you may suggest it when their question is
> better aimed elsewhere"*).
>
> ADR-603 D3 carries the same imprecision (*"'Supervisor hires Editor' —
> authority over a BEING. Violates ADR-460 D3.a"*). Its **conclusion is right
> and its own better argument sits two lines below it**: authority attaches to
> declarations, never to beings. Noted here; not rewritten there — a ratified
> ADR is a record of what was decided.

**The three real reasons, stated so they can be reasoned from:**

1. **Spend without a witness.** Every agent turn costs the member money. Today
   every turn traces to a human act — you sent a message, one reply came back:
   a bounded, consented unit of spend. If agent A can trigger agent B, spend
   becomes SELF-SUSTAINING and the system can bill for a conversation nobody
   asked to continue. That is the property ADR-592 deleted an app for and
   ADR-618 spent an arc bounding. A runaway loop is the acute case; the chronic
   case is a room that costs money while the member sleeps, and neither is
   bounded today.
2. **A clock on a being** (ADR-596 D1) — this one holds exactly. A being that
   speaks unprompted has acquired a clock by construction rather than by
   declaration.
3. **No contract, so "did it work?" is unanswerable** — ADR-603 D1's own
   argument. Unattended work without a contract is precisely what the standing
   declaration exists to replace.

**Consequence for a future build:** agent-to-agent turn initiation is
**scoped and buildable**, not a cliff. It needs what standing work already has —
a balance check before the fanned turn, a bound on depth, and a receipt. That is
an ordinary ADR. What stays refused is an agent triggering a turn in a room the
member is not in: that is standing work wearing a chat room, and it belongs in a
declaration.

### D4.a — Orchestration is declaration-mediated, not conversation-mediated

Asked directly whether chat rooms should be the first-class route for
long-standing agent orchestration, the answer is **no, and the canon already
ruled** (ADR-603 D3): *"Editor arrives at a declaration because the **app**
derives it, never because Supervisor summoned it."*

The shape, already built and running:

```
Supervisor writes a declaration → names an APP → the app derives its resident
                                → run_bounded_derive_turn (bounded, toolless,
                                   contract-checked, with a receipt)
```

**Agents do not orchestrate agents; declarations do.** A being names what must
stay true; the app derives who does it; nobody commands anybody. This is why it
scales without an authority model — and why a chat room would be the worse
route even setting spend aside: a conversation has no contract, so it cannot
answer "did it work?"

Note the execution path is genuinely different, not a chat turn wearing another
name: standing work runs `run_bounded_derive_turn` (`services/derive_turn.py`),
which is tool-less and bounded by construction.

### D4.b — The mid-task case, and the fossil that does NOT serve it

One case the declaration model does not cover: **A needs B's craft mid-task and
needs the result back** (Editor drafting a deck that needs an image). That is
neither standing work (no schedule, no contract) nor a chat handoff (nobody
wants a second speaker). It is **delegation with a return value**.

**Audited 2026-09-01, because this ADR nearly cited it as the ready-made
mechanism:** `services/primitives/dispatch_specialist.py` (530 lines) is
**dormant and structurally uncallable**, not merely unregistered —

- absent from **every** roster: `HANDLERS`, `CHAT_PRIMITIVES`,
  `HEADLESS_PRIMITIVES`, `FREDDIE_PRIMITIVES`, `PRIMITIVES` (verified by
  execution, not grep);
- `VALID_SPECIALIST_ROLES` is the **empty set** — ADR-272 narrowed it to one
  role (`designer`) and the ADR-417 follow-on removed that, so a call would
  refuse on any input;
- its own comment points at a survivor that no longer exists: *"harvest.py
  dispatches `role='researcher'` via HeadlessAuth, a separate mechanism"* —
  `services/harvest.py` is **deleted**.

**And the rot goes one layer deeper than the module.** Tracing that comment:
`HeadlessAuth`'s two builders (`get_headless_tools_for_agent`,
`create_headless_executor`) have exactly **one caller each, both inside
`dispatch_specialist.py`** — the fossil. So the headless-dispatch stack is dead
**end to end**, and `HeadlessAuth`'s own docstring was citing `harvest.py` as
evidence the path was still exercised. Both comments are corrected in place.

So the module was a fossil describing a world that is gone.

**DELETED 2026-09-01** (operator ruling, after testing whether headless dispatch
is axiomatic: *"is this feature a axiomatic feature… if not, i'm leaning towards
delete"*). **Unattended work IS axiomatic** — it is ADR-603 D1's standing
declaration. **This mechanism was not.** It answered *"who does this work?"* with
a ROLE ON A BEING, the shape ADR-596→610 dismantled across five ADRs; the live
answer is capability-at-the-app with the being DERIVED.

⭐ **The tell that settled evolve-vs-delete**: every live unattended lane grew its
OWN narrow auth rather than reaching for the general one sitting right there —
strings runs a plain service client through `run_bounded_derive_turn`, capture on
`_CaptureAuth`, kernel mirrors on `_MirrorAuth`. Three independent lanes voted
against the abstraction. It did not decay; it was superseded.

Removed: `primitives/dispatch_specialist.py` (545 lines) + `HeadlessAuth`,
`get_headless_tools_for_agent`, `create_headless_executor` (138 lines) — the
whole stack, since the class's only callers were inside the primitive.
**Net −1,120 / +299 across 15 files**, `HANDLERS` unchanged at 41.

⭐⭐ **What SURVIVES, deliberately: the `specialist:` attribution prefix.** It is
live vocabulary in `authored_substrate.py`, `narrative.py`, `supabase.py` and
`platform_credentials.py`, where ADR-577 D1.a's credential guard keys on it. **A
prefix is a VOCABULARY; the class that stamped it was a MECHANISM.** Only the
second went. The two identities the class emitted (`specialist:{role}` and the
`specialist:unknown` tripwire) are now pinned by `test_adr577` §2b, so a future
headless caller must stamp one of them to be refused a human's token.

⭐ **The one gate that made this delicate**, recorded because it constrains any
future cleanup of this shape: `test_adr577_credential_claim.py` §2b drove the
REAL `HeadlessAuth` on purpose — *"the pre-577 defect lived precisely in the gap
between what a test's fake auth carried and what HeadlessAuth actually
carries."* Re-cutting it to a loose stand-in would re-open the gap that sentence
names, so it was re-cut to pin the two SHAPES instead, plus an inverted check
that the class stays deleted. It now runs 20/21 (was 15/16) — more coverage, same
single pre-existing failure.

Eleven other gate files were re-anchored; every one returned to its measured
baseline, and three that had been RED on stale assertions (`test_adr261_phaseB`
asserted the primitive was REGISTERED — a world ADR-417 ended) came back green.

If the mid-task case earns a build, the live mechanism to extend is
`run_bounded_derive_turn` — already bounded, tool-less, routed, and used by
standing work — not the dormant primitive. **Deliberately not built here**:
production holds zero rooms with two agents doing anything, so building either
mechanism now would abstract from no instances, which is the error ADR-603 D6
refuses by name.

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
