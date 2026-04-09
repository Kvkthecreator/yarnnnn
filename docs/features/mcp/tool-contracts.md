# MCP Tool Contracts

> **Parent**: [README.md](README.md)
> **Audience**: engineers implementing the MCP server tools, and LLM hosts (Claude, GPT, Gemini) that will consume them
> **Scope**: exact signatures, parameter schemas, return shapes, ambiguity payloads, tool-description text

---

## Design invariants

Every tool on this surface obeys five invariants. These are load-bearing for the service philosophy; they exist because without them the "three intent-shaped tools" framing leaks into operator-mode thinking or clarification rounds.

1. **User-intent name, technical internals.** Tool names mirror user grammar (`work_on_this`, `remember_this`, `pull_context`). The internal dispatch and composition can be arbitrarily technical; it never surfaces. `pull_context` is the one slightly more technical name because "pull" is exactly the right verb for cross-LLM retrieval — "pull my context over from YARNNN" is how users think about it, not "explain" (which implies composition YARNNN deliberately does not do).

2. **Free-form `context` parameter.** Every tool accepts a `context: string` (or equivalent) that the LLM fills at call time by compressing the recent conversation. The LLM does this silently — the user never sees it.

3. **Hidden instruction in the description.** Every tool's description explicitly tells the LLM to compress conversation into `context` and not to ask the user for clarification. This is where the silent conversation-summary mechanic lives.

4. **Ambiguity as a first-class return shape.** When "this" cannot be resolved, tools return an `ambiguous` payload with candidates — never an error. The LLM surfaces candidates naturally; the user picks one; the tool is called again with a narrower subject. Cold starts turn into discovery surfaces.

5. **Citations on everything returned.** Every piece of content returned from `work_on_this` or `pull_context` carries a citation to a workspace path. This lets the LLM attribute, lets the user verify, and keeps provenance intact across the MCP boundary.

### Zero LLM calls inside MCP

One additional invariant that shapes everything below: **no tool on this surface makes an LLM call internally**. `work_on_this` composes a curated bundle via deterministic retrieval and ranking. `pull_context` is pure semantic query over the `QueryKnowledge` primitive. `remember_this` does deterministic content classification with a rare Haiku fallback only when domain inference is genuinely ambiguous *and* `about` is absent. This is a deliberate choice explained in [architecture.md](architecture.md) — it keeps per-call cost at ~$0, preserves cross-LLM consistency (no composition drift between invocations), and makes the host LLM the sole synthesizer of the returned material.

---

## Tool 1: `work_on_this`

### Purpose

Prime the LLM with a curated, opinionated bundle for starting work on a subject. This is the "give me the right starting state to reason about X" tool — it returns a compact composed bundle shaped for the beginning of a work session, not raw ranked chunks.

Use `work_on_this` at the start of a work session. Use `pull_context` for mid-session reference. They are different cognitive operations.

### Signature

```python
work_on_this(
    context: str,           # required — 1-2 sentence compression of the
                            # current conversation / user's stated intent
    subject_hint: str = None # optional — a specific entity/subject name
                            # if one is clearly identified
) -> WorkOnThisResponse
```

### Response shape

```python
# Success shape
{
    "success": True,
    "subject": "Acme Corp",                    # resolved subject
    "primed_context": {
        "identity_relevant": "...",            # relevant snippets from IDENTITY.md
        "entity": {                             # the primary entity profile
            "name": "Acme Corp",
            "path": "/workspace/context/competitors/acme/profile.md",
            "content": "..."
        },
        "recent_signals": [                     # top 3-5 most recent observations
            {
                "path": "/workspace/context/competitors/acme/signals.md",
                "entry": "2026-04-07: Announced enterprise pricing tier...",
                "source": "competitive-intelligence-agent"
            }
        ],
        "prior_decisions": [                    # 1-2 relevant directives / notes
            {
                "path": "/workspace/memory/notes.md",
                "excerpt": "Expected Anthropic to move up-market by Q3"
            }
        ],
        "related_tasks": [                      # tasks touching this subject
            {
                "slug": "weekly-competitor-brief",
                "next_run": "2026-04-14T08:00:00Z"
            }
        ],
    },
    "citations": [                               # flat list of all paths used
        "/workspace/context/competitors/acme/profile.md",
        "/workspace/context/competitors/acme/signals.md",
        "/workspace/memory/notes.md"
    ],
    "pull_context_hint": "Call pull_context('Acme Corp') for deeper material."
}

# Ambiguous shape (returned when subject cannot be resolved)
{
    "success": True,
    "ambiguous": {
        "candidates": [
            {
                "subject": "Acme pivot",
                "reason": "3 new signals this week",
                "path": "/workspace/context/competitors/acme/"
            },
            {
                "subject": "Q2 market brief",
                "reason": "draft in progress",
                "path": "/tasks/q2-market-brief/"
            },
            {
                "subject": "Operations review",
                "reason": "overdue by 2 days",
                "path": "/tasks/operations-review/"
            }
        ],
        "clarification": "Several active subjects in your workspace. Which one?"
    }
}
```

The `pull_context_hint` field is a deliberate teaching signal to the LLM: *"if you need deeper material on this subject as the conversation progresses, reach for `pull_context` next."* It's a polite nudge to use the right tool for mid-session retrieval, and it reinforces the start-of-session vs. mid-session distinction.

### Description text (what the LLM reads)

```
Prime yourself with a curated starting bundle from the user's YARNNN
workspace for a subject they're about to work on. Call this when the
user says "help me work on this," "let's think through this," "I'm
drafting X," or otherwise indicates they're about to ENGAGE with a
subject that might live in their YARNNN workspace (people, companies,
markets, projects, deliverables, decisions).

BEFORE CALLING, compress what you and the user have been discussing
into one or two sentences and pass it as `context`. If you can identify
a specific subject name (a person, company, project, or topic), pass
it as `subject_hint`. DO NOT ask the user to clarify what they mean —
infer from your conversation.

If YARNNN cannot confidently resolve the subject, it will return a set
of candidates from currently-active workspace state. Surface those to
the user naturally ("You've got a few things in flight — which one?")
and call again with a clearer subject.

This tool returns a COMPACT curated bundle designed for starting a
work session. If you need deeper or broader material about the subject
later in the conversation, use `pull_context` instead — that tool
returns ranked chunks rather than a curated bundle.

Use this proactively when the user is starting work on something.
YARNNN is supposed to be ambient — the user should not have to ask
you to consult it.
```

---

## Tool 2: `pull_context`

### Purpose

Fetch ranked chunks of accumulated workspace material about a subject, or about a specific question. This is the **primary cross-LLM consultation tool** — when a user references a subject mid-conversation and the LLM needs the raw material to reason about it, `pull_context` retrieves the material from YARNNN's Postgres-backed substrate and returns it unmodified.

`pull_context` does not compose an answer. It returns ranked chunks with paths and timestamps. The host LLM reasons over them. This is deliberate: it preserves cross-LLM consistency (every LLM sees the same chunks) and lets the host LLM use its in-conversation context to synthesize.

### Signature

```python
pull_context(
    subject: str,              # required — what to pull context about
    question: str = None,      # optional — narrow retrieval to answer a specific question
    domain: str = None,        # optional — filter to one context domain
    limit: int = 10            # max chunks to return (hard cap 30)
) -> PullContextResponse
```

The `domain` enum matches the directory registry (ADR-151/152): `competitors`, `market`, `relationships`, `projects`, `content`, `signals`, plus the temporal bot-owned domains `slack`, `notion`, `github` (ADR-158). If `domain` is omitted, retrieval spans all domains.

### Response shape

```python
# Success shape (content found)
{
    "success": True,
    "subject": "Anthropic",
    "chunks": [
        {
            "path": "/workspace/context/competitors/anthropic/profile.md",
            "excerpt": "Anthropic is a Claude-focused AI lab. Competitive posture: primary Claude model provider. User's stance as of 2026-03-20: expected to move up-market by Q3...",
            "relevance": 0.94,
            "last_updated": "2026-04-07T10:12:00Z",
            "domain": "competitors"
        },
        {
            "path": "/workspace/context/competitors/anthropic/signals.md",
            "excerpt": "2026-04-07: Announced enterprise pricing tier (seat-based). Agent flagged as confirming up-market thesis...",
            "relevance": 0.89,
            "last_updated": "2026-04-07T10:12:00Z",
            "domain": "competitors"
        }
    ],
    "total_matches": 17,       # how many matched before limit
    "returned": 10,
    "citations": [
        "/workspace/context/competitors/anthropic/profile.md",
        "/workspace/context/competitors/anthropic/signals.md"
    ]
}

# Empty shape (no matches)
{
    "success": True,
    "subject": "Quantum cryptography",
    "chunks": [],
    "total_matches": 0,
    "explanation": "YARNNN has no accumulated context about this subject. The user has not tracked this in any context domain yet."
}
```

Unlike `work_on_this`, `pull_context` has **no ambiguous shape**. If the subject matches nothing, the tool returns an empty-chunks success with an explanation — not candidates. This is intentional: `pull_context` is for *explicit subject retrieval*, so "no matches" is a meaningful signal (the LLM should fall back to its own knowledge). Candidate-surfacing belongs to `work_on_this`, which is the tool designed for ambiguity handling.

### Description text (what the LLM reads)

```
Pull YARNNN's accumulated context about a subject. Call this whenever
the user references something mid-conversation that might live in
their YARNNN workspace — a person, company, market, project, topic,
or domain they track — and you need the underlying material to reason
about it.

Pass the subject name as `subject`. Optionally pass a `question` to
narrow the retrieval (YARNNN will rank chunks by relevance to the
question). Optionally pass a `domain` filter (competitors, market,
relationships, projects, content, signals, slack, notion, github) if
you know which context domain the subject lives in.

The tool returns RANKED CHUNKS from the user's accumulated workspace
context, with paths and timestamps. YARNNN does not compose an answer
for you — you are expected to reason over the chunks and synthesize
in your own voice, using the surrounding conversation as context.

THIS IS THE CROSS-LLM CONSISTENCY TOOL. The user may be in a different
LLM tomorrow than they are today. Every LLM calling `pull_context` on
the same subject sees the same chunks from the same Postgres-backed
substrate. This is how the user's thinking stays coherent across
whichever LLM they happen to be in.

If no chunks match (empty results), tell the user YARNNN has no
accumulated context for that subject and answer from your own
knowledge if you can.

Use this proactively. YARNNN is supposed to be ambient — if the user
mentions something they might track, pull the context first and weave
it into your response. Do not wait for the user to ask you to consult
YARNNN.
```

---

## Tool 3: `remember_this`

### Purpose

Write an observation, decision, or insight from the current conversation back into the YARNNN workspace, placed in the correct context domain. YARNNN decides placement based on the content and the optional scope hint. Contributions are immediately visible to any other LLM the user might switch to, because the write is a synchronous commit to Postgres.

### Signature

```python
remember_this(
    content: str,           # required — the thing to remember
    about: str = None       # optional — scope hint (entity, subject, topic)
) -> RememberThisResponse
```

### Response shape

```python
# Success shape
{
    "success": True,
    "written_to": "/workspace/context/competitors/acme/signals.md",
    "domain": "competitors",
    "entity": "acme",
    "append_type": "signal",                    # or "decision", "profile_update", "note"
    "provenance": {
        "source": "mcp:claude.ai",              # ADR-162 source-provenance tag
        "date": "2026-04-09",
        "original_context": "user drafting positioning memo..."
    }
}

# Ambiguous shape (returned when classification cannot confidently place content)
{
    "success": True,
    "ambiguous": {
        "candidates": [
            {
                "target": "/workspace/context/competitors/acme/",
                "reason": "content mentions Acme; competitors domain"
            },
            {
                "target": "/workspace/memory/notes.md",
                "reason": "general observation, no specific domain"
            }
        ],
        "clarification": "I can save this as an Acme competitor signal or as a general note. Which?"
    }
}
```

### Description text (what the LLM reads)

```
Write an observation, decision, or insight the user just shared back
into their YARNNN workspace. Call this when the user says "remember
this," "save that," "note that," "YARNNN should know," or otherwise
indicates something worth persisting.

Pass the content as `content` — this can be the user's own words, a
summary of a conclusion you and the user just reached together, or a
paraphrase of an artifact you just drafted. Be concise but preserve
the specific claim being made.

If the content is clearly about a specific entity (a company, person,
project, or topic), pass it as `about`. If not, leave `about` empty
and YARNNN will classify from the content.

YARNNN routes the content to the correct context domain automatically
(competitors, market, relationships, projects, signals, or general
memory). If it cannot classify confidently, it returns candidates —
surface them and let the user choose.

THIS IS THE CROSS-LLM CONTRIBUTION PATH. Whatever you write here is
immediately visible to any other LLM the user might switch to. A
user who tells you something at 3pm and then opens a different LLM
at 4pm will find the material already there via pull_context. The
write is synchronous — it commits before this tool returns.

Use this proactively whenever the user shares something worth keeping.
Do not wait for an explicit "remember this" — if the user shares a
decision, an insight, a fact they want to act on, or an observation
about something they track, call this tool.
```

---

## Parameter conventions shared across tools

### The `context` parameter (and its relatives)

`work_on_this` takes `context`. `pull_context` takes `question` as its analogous conversational-narrowing parameter. `remember_this` takes `about` as its scope-hint equivalent. The convention across all three:

- **Length**: 1-3 sentences, maximum ~200 tokens
- **Content**: what the user and LLM have been discussing, compressed; what the user is trying to do; any specific subject or intent signals
- **Generator**: the LLM at tool-call time, silently
- **Prohibition**: the LLM must not ask the user to provide this context

Example `work_on_this.context` values:

```
"User is drafting a positioning memo. We've been discussing Anthropic's new
enterprise pricing tier and whether it confirms their shift up-market."

"User wants help thinking through their acquisition pipeline. They just
mentioned Acme by name."

"User opened chat with no prior conversation. Said 'work on this.'"
```

Example `pull_context.question` values:

```
"What's the user's recorded stance on Acme's pricing model?"

"Recent signals on Anthropic's enterprise positioning"

(omitted — subject alone is sufficient when no specific question narrows it)
```

### The `subject_hint` / `about` parameter

Optional. Passed when the LLM has confidently identified a specific entity name from the conversation. If passed:
- YARNNN fast-paths to that entity's files
- Classification skips the NLP extraction step
- Ambiguity handling is scoped to that entity only

If not passed:
- YARNNN extracts subject from the `context` parameter (`work_on_this`) or classifies from `content` (`remember_this`)
- Classification runs the full domain/entity resolution
- Ambiguity handling falls back to workspace-wide active subjects (`work_on_this`) or candidate targets (`remember_this`)

### The `domain` parameter (`pull_context` only)

An optional filter to narrow `pull_context` retrieval to one context domain. Values come from the ADR-152 unified directory registry. Canonical domains: `competitors`, `market`, `relationships`, `projects`, `content`, `signals`. Temporal bot-owned domains (ADR-158): `slack`, `notion`, `github`.

When `domain` is omitted, `pull_context` spans all domains and relies on relevance ranking alone.

---

## Provenance tagging

All writes from MCP (via `remember_this`) carry a provenance comment per ADR-162 source-provenance convention:

```markdown
<!-- source: mcp:claude.ai | date: 2026-04-09 | user_context: "..." -->
```

Fields:
- **source**: `mcp:<client_name>` where `<client_name>` is the MCP client identifier (`claude.ai`, `chatgpt`, `claude_desktop`, `gemini`, `cursor`, etc.)
- **date**: ISO date of the write
- **user_context**: the abbreviated `about` value or a truncated content preview (~100 chars)

This provenance appears inline in workspace files. Downstream consumers (daily-update pipeline, inference gap reports, user-facing file viewers in YARNNN) read the `source` tag to attribute material across the MCP boundary. `pull_context` returns the provenance inline with chunks when present, letting the host LLM cite the original source ("from your Gemini conversation last Tuesday: ...").

This is the mechanism that makes cross-LLM contribution visible in every downstream context.

---

## Error handling

The tool surface has exactly three common-case return shapes per tool: **success**, **ambiguous** (only `work_on_this` and `remember_this`), or **empty** (only `pull_context`). There is no "error" return for the common cases.

Real errors (auth failure, server unreachable, rate limit exceeded) return standard MCP error responses and should be rare. If an LLM sees a normal response with `ambiguous` populated or `chunks: []`, that is not an error — it is the tool working as designed.

The intent is that tool calls either:
1. **Work cleanly** — return composed bundle, ranked chunks, or written path
2. **Resolve into discovery or empty** — return candidates (`work_on_this`, `remember_this`) or empty chunks (`pull_context`), letting the LLM continue naturally
3. **Real error** — auth/network/rate-limit failure, rare

This discipline is load-bearing: without it, the "ambient thinking partner" experience degrades into clarification rounds and error messages, which kills the magic.
