# MCP Workflows — How the File-Native Verbs Resolve Intent

> **Parent**: [README.md](README.md) · **Contracts**: [tool-contracts.md](tool-contracts.md)
> **Governing**: ADR-543 (file-native surface) over ADR-512 (the file is the unit
> of interop). Rewritten 2026-08-10 — the prior version walked the ADR-169-era
> intent tools (`work_on_this` / `pull_context`), two verb generations stale.

The host LLM (Claude, ChatGPT, Gemini) is the one in the conversation; YARNNN
is the workspace it works in. Every walkthrough below follows the same shape:
the user speaks naturally, the host picks verbs, YARNNN returns files and
receipts, the host explains in its own voice.

---

## Case 1 — Orientation: "what do I have?"

**User (Claude.ai):** "What's in my yarnnn workspace for the acquisition work?"

The host calls `list()` (no reference — the whole tree), sees a
`deals/meridian/` folder among the results, then `list(reference="deals/meridian")`:

```json
{
  "files": [
    {"path": "deals/meridian/thesis.md", "authored_by": "operator",
     "last_updated": "2026-08-07T…", "reference": "yarnnn://workspace/deals/meridian/thesis.md"},
    {"path": "deals/meridian/diligence-notes.md", "authored_by": "yarnnn:mcp:chatgpt", …}
  ],
  "count": 2,
  "explanation": "2 file(s) under `deals/meridian`, each with who last changed it and when…"
}
```

The host narrates: *"Two files — your thesis (you edited it Thursday) and
diligence notes ChatGPT contributed. Want me to open either?"* The listing is
real enumeration — what it returns is what exists. Before ADR-543 there was no
enumeration verb, and a connected LLM had to reconstruct the tree from search
hits ("it's inferred, not listed" — the external audit that precipitated the
re-cut).

## Case 2 — Exact read → reasoned edit → attributed save

**User:** "Tighten the risks section of the thesis and save it back."

1. `open(reference="deals/meridian/thesis.md")` → exact content +
   `history[0].revision_id` (the head).
2. The host rewrites the section **in its own reasoning** — YARNNN does no
   generation.
3. `save(reference=…, content=<full new content>, base_revision=<head id>,
   message="tightened risks section")`.

If someone changed the file in between, `save` returns `stale_write` **with
who holds the head** — the host re-opens, merges their change with its own,
and saves against the new base. Never a blind overwrite; the exact-version
guarantee runs both ways (ADR-512 §8a).

## Case 3 — Cross-LLM continuity (the load-bearing case)

**Tuesday, ChatGPT:** the user concludes the Meridian earn-out should be
structured as revenue-gated, not EBITDA-gated. Nothing is "delegated" — the
host is taught (connector instructions) to capture conclusions worth keeping:

```
save(reference="deals/meridian/earn-out-structure.md",
     content="Decision 2026-08-11: revenue-gated earn-out…",
     derived_from=["deals/meridian/diligence-notes.md"])
```

The write lands signed `yarnnn:mcp:chatgpt`, citing what it was built on.

**Wednesday, Gemini** (fresh session, different vendor): "Where did we land on
the Meridian earn-out?" → `search(query="meridian earn-out")` →
`confidence: "high"`, one dominant hit → `open` it → the host answers **with
attribution**: *"Decided yesterday (recorded from your ChatGPT session):
revenue-gated, because…"*

**Thursday, the operator** asks Claude: "How did the earn-out thinking
evolve?" → `history(reference="deals/meridian/earn-out-structure.md")` → the
chain: ChatGPT's creation, the operator's Wednesday edit, each with diffs —
plus the cited diligence-notes chain appended (`cited_source: true`). No flat
memory can answer this question.

## Case 4 — Ambiguity stays honest

**User (new session):** "Pull up my notes on the pricing work."

`search(query="pricing")` returns three files with close scores →
`confidence: "ambiguous"`. The host does NOT crown the top hit; it asks:
*"You have pricing notes in three places — the GTM folder, the alpha-program
specs, and a July scratch file. Which do you mean?"* Then `open`s the answer.

The division of labor is the [honest-state contract](honest-state-contract.md):
YARNNN reports the honest state; the clarify act belongs to the host, which is
the only party that can see the conversation.

## Case 5 — Letting someone in

**User:** "Share the thesis with Alex — read-only."

`share(reference="deals/meridian/thesis.md", access="viewer")` → a link the
host relays. Whoever opens it sees the document *and who changed it*; joining
the workspace requires sign-in. The host sends nothing itself (ADR-404 —
models come IN).

---

## The through-line

1. **Exact when you hold a reference, fuzzy only when you don't.**
   `open`/`history` never guess; `search` says how sure it is; `list` shows
   what exists. The host is taught the escalation: reference → `open`; topic →
   `search`; orientation → `list`.
2. **Every write is a signed revision.** No anonymous contributions, no silent
   overwrites, and `derived_from` records what content was made from.
3. **YARNNN never synthesizes.** Every narration above is the host's own — the
   connector returns files, receipts, and honest signals, in one round each.
4. **Empties are clean signals.** `found: false` / `confidence: "none"` /
   `count: 0` are the tool working as designed; the host continues naturally.

## What these workflows imply for testing

Drive a real host against a live workspace and assert the *gesture*, not the
plumbing: enumerate a tree you've never seen (Case 1), lose a save race and
recover (Case 2), read back another host's attributed write (Case 3), get an
ambiguous search to produce a clarifying question rather than a wrong answer
(Case 4). The ADR-543 phase-5 criterion is Case 1: an external principal can
enumerate the tree it previously had to infer.
