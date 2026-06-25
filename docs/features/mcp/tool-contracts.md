# MCP Tool Contracts — the memory verbs

> **Parent**: [README.md](README.md)
> **Audience**: engineers implementing the MCP server tools, and LLM hosts (Claude, GPT, Gemini) that consume them
> **Scope**: exact signatures, parameter schemas, return shapes, tool-description text
> **Governing**: **ADR-368** (memory-first surface — the verbs) + **ADR-310** (judged substrate — the framing). Supersedes ADR-311's pure-primitive surface and ADR-169's original three intent tools. The implementation is `api/services/mcp_composition.py` + `api/mcp_server/server.py`.

---

## The surface in one screen

Three verbs, shaped on the user's memory mental model (ADR-368 D1): **put in · get out · trace history.**

| Verb | User says | Nature | Composes (server-side) |
|---|---|---|---|
| `remember` | "remember this" | write · sync | `WriteFile(operation/…)` + integrity wake |
| `recall` | "what do I know about X" | read · sync | `QueryKnowledge` → rank |
| `trace` | "how did my thinking on X change" | read · sync | resolve → `ListRevisions` → `DiffRevisions` |

Each verb returns a reason-ready result in **one round** from the host's perspective — the multi-step composition lives server-side (inside YARNNN, an agentic context), not in the round-limited consumer host (ADR-368 Correction 1). The raw kernel primitives (`ReadFile`/`SearchFiles`/`WriteFile`/`ListRevisions`/`DiffRevisions`) remain available `defer_loading` for agentic hosts that genuinely chain.

---

## Design invariants

1. **Memory-model names, kernel internals.** The verbs mirror how a person thinks about their own memory. The dispatch composes kernel primitives; that never surfaces.
2. **Free-form context, silently filled.** Each verb's description tells the host LLM to compress the recent conversation into the parameters (`content`/`about`/`subject`/`question`) at call time, and never to ask the user for it.
3. **`recall` returns; it does not synthesize.** The bright memory-vs-delegation line (ADR-368 D1): YARNNN returns material; the host LLM explains. A verb that composed an answer would be the deferred delegation nature leaking in.
4. **`remember` captures a dump; the Reviewer places it** (ADR-368 D3 + D5). The MCP layer writes the memory inbox (`operation/memory/`) only — it does not route content to a home, because placement is a judgment the foreign caller lacks the workspace knowledge to make. The `mcp` caller is locked from `governance/`/`contract/`/`constitution/`/`persona/`/`system/` by `CALLER_WRITE_POLICY` (ADR-320/366); the gate is the backstop.
5. **Every dump is placed, judged + attributed.** `remember` commits to the inbox stamped `authored_by="yarnnn:mcp"` (ADR-288) + ADR-162 provenance, then invokes the Reviewer (substrate_event wake) to file it where it belongs and check it against ground-truth — a separate `reviewer:<id>` revision. `trace` surfaces the full chain.
6. **Operator-visibility is session-independent** (ADR-368 D4). Every call emits a narrative entry even when no session is active, so the cross-room operator sees what entered.

### Zero LLM calls inside MCP

No verb makes an LLM call internally. `remember` is a gated write. `recall` is composed retrieval over `QueryKnowledge`. `trace` is composed revision-reads. Per-call cost ≈ $0, cross-LLM consistency preserved (no composition drift), the host LLM is the sole synthesizer.

---

## Verb 1: `remember`

### Purpose

Save an observation, decision, or insight from the current conversation into the user's YARNNN memory. The write commits synchronously to the `operation/` commons, is attributed to the calling LLM, and is immediately visible to any other LLM the user switches to. The Reviewer then validates the contribution against authored ground-truth in the background (ADR-368 D5) — this is *safety on a write*, not delegated work.

### Signature

```python
remember(
    content: str,        # required — the thing to remember
    about: str = None,   # optional — subject hint (company, person, project, topic)
) -> RememberResponse
```

### Response shape

```python
# Success
{
    "success": True,
    "written_to": "/workspace/operation/memory/acme-corp.md",   # the inbox — NOT final placement
    "provenance": {
        "source": "mcp:claude.ai",        # ADR-162 source-provenance tag
        "date": "2026-06-25",
        "original_context": "Q3 deck positioning…"
    },
    "captured": True                       # the seat will file + judge this (ADR-368 D5)
}

# Failure (rare — empty content)
{ "success": False, "error": "empty_content", "message": "content is required" }
```

### Capture, then placement-by-judgment (ADR-368 D3 + D5)

**`remember` does not route content to a home — it CAPTURES a dump and the Reviewer places it.** Placement is a judgment, not a deterministic route (the MCP layer doesn't understand the workspace's structure well enough to file into it, and must not corrupt a program's output tree).

`resolve_remember_path(about)` → the **memory inbox**, subject-organized only so dumps group:
- `about="Acme Corp"` → `operation/memory/acme-corp.md`
- no `about` → `operation/memory/inbox.md`

The write is attributed `yarnnn:mcp`, then `submit_foreign_write_wake` **invokes the Reviewer** (substrate_event wake) to reason about where the dump belongs and file it into its real home (a domain, an entity file, agent feedback, or left as memory) — a separate `reviewer:<id>` revision. `trace` then shows the chain: *contributed via claude.ai → filed to X by the Reviewer*.

A foreign LLM never writes `system/`, `persona/`, `constitution/`, `governance/`, or `contract/` — the surface only constructs `operation/memory/` paths, and the ADR-307 gate is the backstop. The pre-ADR-368 five-target enum (`memory|identity|brand|agent|task`) — three of whose targets pointed at locked roots — is **deleted**, along with the first-draft `operation/{domain}/` keyword router (ADR-151 domain fiction live workspaces don't use).

### Description text (what the LLM reads)

```
Save something into the user's YARNNN memory so it follows them across every
LLM. Call whenever the user shares something worth keeping — a decision,
insight, fact, preference, or observation about something they track. Don't
wait for "remember this": if they reach a conclusion they'll want later, save
it. Pass the thing as `content` (their words or a faithful summary); pass the
subject as `about` if clear. The write is synchronous and immediately visible
to any other LLM. You are saving to a shared memory — not asking YARNNN to do
work.
```

---

## Verb 2: `recall`

### Purpose

Return what the user already knows about a subject from their accumulated YARNNN memory. Composed server-side (`QueryKnowledge` → rank) into ranked excerpts with paths, timestamps, and the contributing source. **YARNNN returns the material; the host LLM explains it** — preserving cross-LLM consistency (every LLM sees the same substrate) and letting the host synthesize with the conversation in hand.

### Signature

```python
recall(
    subject: str,           # required — what to recall
    question: str = None,   # optional — focus the retrieval on a question
    domain: str = None,     # optional — narrow to one domain
    limit: int = 10         # max excerpts (hard cap 30)
) -> RecallResponse
```

### Response shape

```python
# Found
{
    "success": True,
    "subject": "Acme Corp",
    "chunks": [
        {
            "path": "/workspace/operation/competitors/acme/notes.md",
            "excerpt": "2026-06-20: announced seat-based enterprise pricing…",
            "last_updated": "2026-06-20T10:12:00Z",
            "domain": "competitors",
            "source_tag": "mcp:claude.ai"   # who contributed this, if attributed
        }
    ],
    "total_matches": 17,
    "returned": 10,
    "citations": ["/workspace/operation/competitors/acme/notes.md", …]
}

# Empty (a clean signal, not an error)
{
    "success": True, "subject": "Quantum cryptography",
    "chunks": [], "total_matches": 0, "returned": 0, "citations": [],
    "explanation": "YARNNN has no accumulated memory about this subject. "
                   "Answer from your own knowledge if you can."
}
```

### Description text

```
Pull what the user already knows about a subject from their YARNNN memory. Call
whenever they reference something that might live there — a person, company,
market, project, or topic they track — and you need the material to reason well.
Don't wait to be asked. Pass the subject as `subject`; optionally `question` to
focus, `domain` to narrow. YARNNN RETURNS ranked excerpts with paths and the LLM
that contributed each — it does NOT write an answer for you. Reason over what it
returns and explain in your own voice. Every LLM sees the same memory, so the
user's thinking stays coherent across rooms. If nothing matches, say so and
answer from your own knowledge.
```

---

## Verb 3: `trace`

### Purpose

Return the **authored revision history** of a recorded fact — who changed it, when, and what the change was. This is YARNNN's distinguishing capability (ADR-311 §3, preserved): the attributed, walkable revision chain (ADR-209) surfaced across the boundary. A plain storage connector returns whatever is stored, no provenance, no history-with-authorship. YARNNN returns content + *who* + *when* + *what changed*.

### Signature

```python
trace(
    subject: str,     # required — what to trace the history of
    limit: int = 10   # max revisions (hard cap 30)
) -> TraceResponse
```

### Response shape

```python
# Found
{
    "success": True,
    "subject": "Acme pricing stance",
    "path": "/workspace/operation/competitors/acme/notes.md",
    "history": [                              # newest first
        {
            "authored_by": "reviewer:simons",  # operator | yarnnn:mcp | reviewer:<id> | agent:<slug> | system:<actor>
            "when": "2026-06-22T09:00:00Z",
            "change": "revised stance after Q2 earnings",
            "revision_id": "…"
        },
        {
            "authored_by": "yarnnn:claude.ai",
            "when": "2026-06-20T10:12:00Z",
            "change": "remember → operation commons",
            "revision_id": "…"
        }
    ],
    "returned": 2,
    "citations": ["/workspace/operation/competitors/acme/notes.md"],
    "explanation": "The authored history of 'Acme pricing stance' — 2 revisions, "
                   "each attributed to who changed it and when."
}

# No history
{
    "success": True, "subject": "…", "path": None, "history": [],
    "explanation": "YARNNN has no recorded material about this subject to trace."
}
```

### Description text

```
Show how the user's recorded thinking on a subject changed over time. Call when
they ask about the HISTORY of something they track — "when did I decide that,"
"how has my view on X changed," "who added this," "what did this used to say."
YARNNN returns the authored revision chain — who changed it, when, and what the
change was — newest first. This is YARNNN's distinguishing capability; a plain
storage connector cannot show it. Reason over the chain and narrate the
evolution in your own voice.
```

---

## Shared conventions

### The `context` / scope parameters

`remember` takes `about`; `recall` takes `question`; all take a `subject`/`content` the LLM fills by compressing the recent conversation. Convention across all three:
- **Length**: 1–3 sentences, ≤ ~200 tokens
- **Generator**: the host LLM at call time, silently
- **Prohibition**: never ask the user to provide it

### Provenance tagging

Every `remember` write carries an ADR-162 provenance comment:

```markdown
<!-- source: mcp:claude.ai | date: 2026-06-25 | user_context: "…" -->
```

- **source**: `mcp:<client_name>` (`claude.ai`, `chatgpt`, `claude_desktop`, `gemini`, `cursor`)
- **date**: ISO date of the write
- **user_context**: abbreviated `about` or a content preview (~100 chars)

`recall` returns the `source_tag` inline with each chunk; `trace` returns `authored_by` per revision. This is the mechanism that makes cross-LLM contribution visible — and lets the host attribute it ("from your ChatGPT conversation last Tuesday: …").

### Error handling

Three common-case shapes per verb: **success**, **empty** (`recall`/`trace` — a clean signal, not an error), and rare real errors (auth/network/rate-limit, standard MCP error responses). An empty `recall` or a no-history `trace` is the tool working as designed — the host LLM continues naturally. This discipline is load-bearing: without it the ambient experience degrades into clarification rounds and error messages.

---

## Deferred (ADR-368 §6)

- **Delegation-from-foreign-LLM** — a `work_on_this`-equivalent reframed as an addressed wake into the operation (YARNNN does work, reports back). Deferred pending the sync-vs-stream tool-return hinge + demonstrated demand. Additive when it lands; these three verbs are untouched.
- **Richer operator-visibility tiers** — a batchable `external_contribution` notification; a Management-Plane "what entered from outside" lane.
- **Second protocol bindings** (A2A, direct-API) of the same three-verb contract.
