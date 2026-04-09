# MCP Workflows — How Tools Resolve Intent

> **Parent**: [README.md](README.md)
> **Audience**: designers, PMs, and engineers who need to see the end-to-end dynamic of each tool working against real conversational situations
> **Scope**: dialogue-level walkthroughs across the four meaningful cases — conversation topic, in-conversation artifact, cold start, and cross-LLM continuity (the load-bearing case)

---

## The "this" problem, briefly

When a user says "work on this" or "remember this" mid-conversation with a foreign LLM, the word **"this"** refers to something in the shared context between user and LLM — not in the tool call's parameters. The resolution mechanism is:

1. The LLM compresses the relevant conversation into a free-form parameter at call time
2. YARNNN uses that compression (plus an optional scope hint) to resolve "this"
3. For `work_on_this` and `remember_this`, if resolution fails, the tool returns structured ambiguity
4. For `pull_context`, the subject is always explicit — if no chunks match, the tool returns empty cleanly
5. The LLM weaves the result into natural conversation

Four cases cover every realistic situation. Below is a walkthrough of each, using the tool most natural for that case.

---

## Case 1 — Conversation topic resolution (`work_on_this`)

**Setup**: User has been in Claude.ai for 2 minutes discussing a competitor. Asks Claude for help working on a memo.

### Dialogue

```
User     › "Anthropic's been making moves in enterprise lately. Saw they
            launched a new pricing tier last week."

Claude   › "Yes — the announcement targets mid-market companies with
            seat-based pricing. It's a shift from their previous per-call
            enterprise contracts."

User     › "That matches what I've been expecting. Help me work on this —
            I want to draft a short note for my team."
```

### What Claude does internally

Claude reaches for `work_on_this` because "help me work on this" is a clear start-of-work signal about a subject likely in YARNNN. The tool description told Claude to compress conversation into `context` and identify a subject if possible.

```python
work_on_this(
    context="User is drafting a team note about Anthropic's new enterprise "
            "pricing tier. We've discussed that it's a shift toward seat-based "
            "mid-market pricing, and the user says it matches their expectations.",
    subject_hint="Anthropic"
)
```

### What YARNNN does

1. **Subject resolution**: `subject_hint="Anthropic"` is clear — fast-path to the entity.
2. **Domain lookup**: Anthropic is in `/workspace/context/competitors/anthropic/`.
3. **Curated composition**: Pull `profile.md`, top 5 entries from `signals.md`, mentions from `/workspace/memory/notes.md`, and the task watching competitors (`competitive-intelligence-weekly`).
4. **Identity relevance**: Grep `IDENTITY.md` for mentions of Anthropic or competitor tracking — none this time, skip.
5. **Citations**: Flat list of all paths touched.

### Tool response (abbreviated)

```python
{
    "success": True,
    "subject": "Anthropic",
    "primed_context": {
        "entity": {
            "name": "Anthropic",
            "path": "/workspace/context/competitors/anthropic/profile.md",
            "content": "Anthropic is a Claude-focused AI lab. Competitive "
                       "posture: primary Claude model provider. User's stance "
                       "as of 2026-03-20: expected to move up-market by Q3..."
        },
        "recent_signals": [
            "2026-04-07: Launched enterprise pricing tier (seat-based). "
            "Competitive intelligence agent flagged as confirming up-market thesis.",
            "2026-03-28: Hired VP of Enterprise Sales from Snowflake.",
        ],
        "prior_decisions": [{
            "path": "/workspace/memory/notes.md",
            "excerpt": "Expected Anthropic to move up-market by Q3, driven by "
                       "gross margin pressure from Claude training costs."
        }]
    },
    "citations": [
        "/workspace/context/competitors/anthropic/profile.md",
        "/workspace/context/competitors/anthropic/signals.md",
        "/workspace/memory/notes.md"
    ],
    "pull_context_hint": "Call pull_context('Anthropic') for deeper material."
}
```

### What Claude produces for the user

```
Claude   › "From your YARNNN workspace — you've been tracking Anthropic and
            had a prior note saying you expected them to move up-market by Q3,
            driven by training cost pressure. Your competitive intelligence
            agent flagged last week's enterprise pricing announcement as
            confirming that thesis. There's also a signal from 2026-03-28
            that they hired a VP of Enterprise Sales from Snowflake.

            Want me to draft the team note as: 'Anthropic's enterprise
            pricing move confirms the up-market thesis we called in March.
            Key implications...'?"

User     › "Yes."
```

### Why this works

- User said nine words. No context explanation, no file hunting.
- Claude did the silent work: compressed the conversation, identified the subject, called YARNNN.
- YARNNN returned a compact curated bundle shaped for starting work.
- The user experiences it as "Claude already knew what I'd been thinking about Anthropic." The MCP call is invisible.

---

## Case 2 — Mid-session reference via `pull_context`

**Setup**: User is 10 minutes into a Claude.ai conversation drafting a competitive response document. Mid-draft, they reference a subject they know lives in their workspace.

### Dialogue

```
User     › "For this section, I need to compare Anthropic's enterprise
            positioning to Acme's. What has my workspace been tracking
            about Acme's pricing model?"
```

### What Claude does internally

Claude is already in a work session — it doesn't need `work_on_this` to start from scratch. The user is asking a *specific* question about a *specific* subject (Acme) and specifying *what* they want (pricing model details). This is the mid-session reference pattern, and the tool description told Claude to use `pull_context` for exactly this.

```python
pull_context(
    subject="Acme",
    question="pricing model, enterprise tier, recent changes",
    domain="competitors"
)
```

Claude passed `domain="competitors"` because it knows from the conversation that Acme is being tracked competitively. This fast-paths the retrieval.

### What YARNNN does

1. **Dispatch to QueryKnowledge primitive**: `execute_primitive(auth, "QueryKnowledge", {"query": "...", "path_prefix": "/workspace/context/competitors/acme/", "limit": 10})`
2. **Semantic ranking**: Postgres RPC returns ranked chunks.
3. **Format chunks**: Extract excerpts (first ~500 chars), preserve full paths, include `last_updated` timestamps and domain labels.
4. **Return**: Success shape with ranked `chunks`, `total_matches`, `citations`.

**No LLM call inside YARNNN.** Pure retrieval.

### Tool response (abbreviated)

```python
{
    "success": True,
    "subject": "Acme",
    "chunks": [
        {
            "path": "/workspace/context/competitors/acme/profile.md",
            "excerpt": "Acme sells vertically to mid-market SaaS companies. "
                       "Pricing: per-seat, with tiered features. Moved from "
                       "usage-based to seat-based in Q1 2026...",
            "relevance": 0.93,
            "last_updated": "2026-04-06T14:00:00Z",
            "domain": "competitors"
        },
        {
            "path": "/workspace/context/competitors/acme/signals.md",
            "excerpt": "2026-04-01: Announced 15% price increase for enterprise "
                       "tier, bundled with new compliance features. User's "
                       "intelligence agent noted this matched their prediction "
                       "from January.",
            "relevance": 0.89,
            "last_updated": "2026-04-01T09:30:00Z",
            "domain": "competitors"
        },
        {
            "path": "/workspace/context/competitors/acme/pricing_notes.md",
            "excerpt": "User's stance (2026-02-14): Acme's pricing is defensible "
                       "because their mid-market customer base is sticky and "
                       "switching costs are high...",
            "relevance": 0.85,
            "last_updated": "2026-02-14T16:20:00Z",
            "domain": "competitors"
        }
    ],
    "total_matches": 12,
    "returned": 10,
    "citations": [
        "/workspace/context/competitors/acme/profile.md",
        "/workspace/context/competitors/acme/signals.md",
        "/workspace/context/competitors/acme/pricing_notes.md"
    ]
}
```

### What Claude produces for the user

```
Claude   › "Your workspace has a good amount on Acme's pricing. Key points:

            - They moved from usage-based to seat-based pricing in Q1 2026,
              mirroring what Anthropic is now doing with their enterprise tier.
            - On April 1, they announced a 15% price increase on the enterprise
              tier, bundled with new compliance features. Your competitive
              intelligence agent flagged this as matching a prediction you
              made in January.
            - Your own recorded stance (from February 14) was that Acme's
              pricing is defensible because of their sticky mid-market base
              and high switching costs.

            So the comparison for your section is: Anthropic is now adopting
            a pricing model Acme pioneered a quarter ago, but Anthropic
            doesn't have Acme's switching-cost moat. Want me to write that
            section?"

User     › "Yes."
```

### Why this works

- User asked a focused question. No need for `work_on_this`'s curated start-of-session bundle — Claude is already working.
- YARNNN returned raw ranked chunks; Claude did the synthesis using its in-conversation context.
- The synthesis is *strictly better* than what a YARNNN-internal composer could do, because Claude has the full drafting conversation as context.
- **Zero LLM cost on YARNNN's side.** Pure `QueryKnowledge` dispatch + format.

---

## Case 3 — Cross-LLM continuity (the load-bearing case)

**Setup**: On Tuesday, the user is in ChatGPT drafting a stance on an acquisition. On Wednesday morning, the user switches to Gemini to brainstorm risks. This is the case the entire design exists to serve.

### Tuesday afternoon — ChatGPT

```
User     › "I need to write a short stance on the Acme deal for my partner
            to review."

ChatGPT  › "What's your current thinking on it?"

User     › "They're overpaying for what is basically a distribution channel
            with a weak product. I'd tell them to pass unless they can
            restructure the deal to get more control over the product
            roadmap."

ChatGPT  › "Here's a draft: 'The proposed Acme acquisition prices the
            company as a product bet, but the underlying asset is
            distribution, not product. At the current valuation, we'd be
            paying a product multiple for a channel. My recommendation is
            to pass unless the terms are restructured to grant roadmap
            control — which, given Acme's team, seems unlikely.'"

User     › "That's exactly right. Remember this."
```

### What ChatGPT does

```python
remember_this(
    content="Stance on Acme acquisition: The proposed acquisition prices "
            "Acme as a product bet, but the underlying asset is distribution, "
            "not product. At current valuation, we'd be paying a product "
            "multiple for a channel. Recommendation is to pass unless terms "
            "are restructured for roadmap control.",
    about="Acme acquisition decision"
)
```

### What YARNNN does

1. **Classification**: `about="Acme acquisition decision"` + content mentioning "acquisition," "valuation," "deal" → routes to `/workspace/context/relationships/acme/decisions.md`. Since Acme is already a tracked entity under relationships and the content is a decision rather than an observation, it writes to the decisions file with a signal-log cross-reference in `signals.md`.
2. **Provenance stamp**: ADR-162 HTML comment with `source: mcp:chatgpt`, the date, and abbreviated `about` as user context.
3. **Synchronous commit**: `execute_primitive(auth, "UpdateContext", ...)` commits to Postgres before returning.

### Tool response

```python
{
    "success": True,
    "written_to": "/workspace/context/relationships/acme/decisions.md",
    "domain": "relationships",
    "entity": "acme",
    "append_type": "decision",
    "provenance": {
        "source": "mcp:chatgpt",
        "date": "2026-04-08",
        "original_context": "Acme acquisition decision"
    }
}
```

```
ChatGPT  › "Saved to your YARNNN workspace under your Acme relationship
            record. Your next daily briefing will surface this for your
            partner to see."
```

The user closes the ChatGPT tab. Goes to dinner.

### Wednesday morning — Gemini

Sixteen hours later, the user opens Gemini fresh. Different browser, different LLM, different session. No prior conversation.

```
User     › "I want to brainstorm risks on the Acme deal. What am I already
            thinking about it?"
```

### What Gemini does

Gemini has **zero** conversation history with this user. It only has the current message and the MCP tools. The user explicitly asked "what am I already thinking" — this is a direct cue to consult YARNNN.

```python
pull_context(
    subject="Acme",
    question="acquisition decision, user's stance, risks",
    domain="relationships"
)
```

### What YARNNN does

Pure retrieval against `/workspace/context/relationships/acme/`. The decision file that ChatGPT wrote 16 hours ago is already indexed and searchable — `UpdateContext` committed synchronously to Postgres, and the workspace search RPC reads from the same table.

### Tool response

```python
{
    "success": True,
    "subject": "Acme",
    "chunks": [
        {
            "path": "/workspace/context/relationships/acme/decisions.md",
            "excerpt": "STANCE ON ACQUISITION (2026-04-08): The proposed Acme "
                       "acquisition prices the company as a product bet, but "
                       "the underlying asset is distribution, not product. At "
                       "current valuation, we'd be paying a product multiple "
                       "for a channel. Recommendation: pass unless terms are "
                       "restructured for roadmap control.",
            "relevance": 0.96,
            "last_updated": "2026-04-08T16:42:00Z",
            "domain": "relationships",
            "source_tag": "mcp:chatgpt"
        },
        {
            "path": "/workspace/context/relationships/acme/profile.md",
            "excerpt": "Acme is a mid-market distribution partner with weak "
                       "product fundamentals. Relationship history: warm but "
                       "transactional. Key contacts: [redacted]...",
            "relevance": 0.87,
            "last_updated": "2026-03-15T11:00:00Z",
            "domain": "relationships"
        }
    ],
    "total_matches": 8,
    "returned": 10,
    "citations": [...]
}
```

### What Gemini produces for the user

```
Gemini   › "From your YARNNN context — you made a call yesterday (via
            ChatGPT, based on the provenance) that the deal prices Acme
            as a product bet when the real asset is distribution, and
            your recommendation was to pass unless the terms give you
            roadmap control. That's your anchor position.

            For brainstorming risks, let's work from that stance. Here
            are the dimensions I'd check:

            1. What if the seller refuses restructured terms and your
               partner wants to proceed anyway? Is there a middle path?
            2. If you pass, does the relationship with Acme survive?
               Your profile notes the relationship is warm but
               transactional — how much capital does a 'no' burn?
            3. What's the distribution replacement cost? If you could
               replicate Acme's distribution in 18 months organically,
               the deal looks different than if you can't.
            4. What signals have you been tracking on Acme's competitive
               position that might change your read?

            Want to start with any of these?"
```

### Why this works — and why it's the load-bearing case

This is what the whole design exists to enable. Concretely:

- **No user re-explanation.** The user didn't have to recap yesterday's ChatGPT conversation to Gemini. Gemini pulled the decision directly from YARNNN.
- **Provenance is visible.** Gemini saw `source_tag: mcp:chatgpt` on the decision chunk and attributed it naturally in its response ("via ChatGPT, based on the provenance"). The user sees the thread across LLMs.
- **Synchronous consistency.** The `remember_this` call on Tuesday committed synchronously to Postgres. By Wednesday morning — or by Tuesday 3:01pm if the user had switched immediately — the content is already available. There is no cache, no propagation delay, no eventual consistency.
- **Different LLM, same substrate, same reasoning quality.** Gemini reasoned over the chunks using its own synthesis style. If the user had opened Claude.ai instead, Claude would have seen the same chunks and reasoned in Claude's style. The substrate is the constant.
- **Zero YARNNN-internal LLM calls.** `remember_this` was deterministic classification. `pull_context` was pure retrieval. At no point did YARNNN spend money on the LLM layer — both LLM surfaces absorbed the reasoning work.

**This is the product.** Not "a connector." Not "a memory feature." The user's thinking stays coherent across rooms because YARNNN is the shared room every other room reaches into.

---

## Case 4 — Cold-start ambiguity resolution (`work_on_this`)

**Setup**: User opens Claude.ai first thing in the morning with no context. Has a vague sense of wanting to work on something but hasn't articulated it yet.

### Dialogue

```
User     › "Work on this."
```

That's the entire first message. No subject. No context.

### What Claude does

Claude sees a `work_on_this`-shaped intent but has no conversation to compress. It calls anyway with an empty context and no subject hint:

```python
work_on_this(
    context="User just opened chat with no prior conversation. Said 'work on this.'",
    subject_hint=None
)
```

### What YARNNN does

1. **Subject resolution**: fails — no hint, no content in context to extract from.
2. **Ambiguity fallback**: query workspace state for currently-active subjects. Pull:
   - Active tasks with `next_run` in the next 24 hours
   - Entities with recent signals (last 7 days) in canonical context domains
   - Draft outputs in `/tasks/*/outputs/` not yet delivered
3. **Rank candidates**: freshness + priority (overdue tasks first)
4. **Return**: top 3-5 candidates with reason strings

### Tool response

```python
{
    "success": True,
    "ambiguous": {
        "candidates": [
            {
                "subject": "Acme acquisition decision",
                "reason": "Decision recorded yesterday via ChatGPT, marked for partner review",
                "path": "/workspace/context/relationships/acme/"
            },
            {
                "subject": "Anthropic competitive brief",
                "reason": "3 new signals this week, weekly brief due Thursday",
                "path": "/workspace/context/competitors/anthropic/"
            },
            {
                "subject": "Q2 market outlook",
                "reason": "Draft output in progress, last touched 2 days ago",
                "path": "/tasks/q2-market-outlook/"
            },
            {
                "subject": "Operations review",
                "reason": "Overdue by 2 days",
                "path": "/tasks/operations-review/"
            }
        ],
        "clarification": "Several active subjects in your workspace. Which one?"
    }
}
```

### What Claude produces for the user

```
Claude   › "You've got a few things in flight right now:

            1. Your Acme acquisition decision — you recorded a stance
               yesterday via ChatGPT and flagged it for partner review.
            2. Anthropic competitive brief — three new signals this
               week, your weekly brief is due Thursday.
            3. Q2 market outlook — draft in progress, last touched
               two days ago.
            4. Operations review — overdue by two days.

            Which one should we work on?"

User     › "The Q2 market outlook."
```

### The second call (now with a resolved subject)

```python
work_on_this(
    context="User selected Q2 market outlook from a list of active workspace "
            "subjects. They want to continue work on the draft.",
    subject_hint="Q2 market outlook"
)
```

YARNNN fast-paths to `/tasks/q2-market-outlook/`, composes a curated bundle, and Claude continues the work from there.

### Why this works

- User said three words. A completely cold start.
- YARNNN's workforce had been doing its job in the background — accumulating context, running tasks, recording yesterday's ChatGPT decision. That accumulation becomes the candidate list.
- The "ambiguous" return shape turned a broken request into a personalized briefing. The user got reminded of what their workforce is working on without opening YARNNN.
- The ChatGPT decision from Case 3 appears as candidate #1, showing that cross-LLM continuity also threads into the ambiguity fallback path — whatever the user wrote via any LLM surfaces as a candidate for work in any other LLM.

---

## The through-line across cases

All four cases share the same skeleton:

1. **LLM compresses conversation into a free-form parameter** at call time (silently, per tool description)
2. **YARNNN dispatches through `execute_primitive()`** to the appropriate primitive — `QueryKnowledge` for retrieval, `UpdateContext` for writes — with thin MCP-layer composition where needed
3. **Tool returns success, ambiguous, or empty** — never an error for the common cases
4. **LLM weaves the response into natural conversation** — no visible tool-call artifacts

The user's experience across all four cases is that **whatever LLM they're in already knows what they know**, and **cross-LLM continuity is the new normal**. The MCP surface is invisible. The workforce is invisible. What the user sees is thinking that stays coherent across rooms.

That experience is the entire point of the design.

---

## What these workflows imply for testing

For each tool, the validation cases track the resolution paths:

| Tool | Happy path | Edge / cold-start path | Cross-LLM path |
|---|---|---|---|
| `work_on_this` | Conversation-context composition (Case 1) | Ambiguity fallback → candidates (Case 4) | Candidates include recent `remember_this` contributions |
| `pull_context` | Mid-session retrieval (Case 2) | Empty chunks returned cleanly for unknown subjects | Same chunks returned regardless of calling LLM (Case 3) |
| `remember_this` | Classification to known entity (Case 3 — ChatGPT side) | Unclassifiable content returns `ambiguous` candidates | Synchronous commit visible to subsequent `pull_context` from any LLM |

Highest-value tests:
- **Case 3 end-to-end** — `remember_this` from one simulated client → `pull_context` from another client → verify same chunk returned with correct provenance tag
- **Case 4 ambiguity fallback** — empty/cold-start `work_on_this` returns ranked candidates from real workspace state
- **Provenance consistency** — `remember_this` from `claude.ai`, `chatgpt`, and `gemini` produce distinct `source_tag` values in the written file, all readable downstream

These are the tests that prove cross-LLM continuity actually works end-to-end rather than just being claimed in the design.
