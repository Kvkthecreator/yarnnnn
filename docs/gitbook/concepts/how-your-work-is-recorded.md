# How Your Work Is Recorded

This is the part of YARNNN you mostly don't look at, and the reason the rest of it works.

## Every change is an attributed revision

Files in YARNNN aren't overwritten. Each change writes a new **revision** that points back at the one before it, carrying:

- **who** made the change — you, a named agent, an external AI reaching in over MCP, or the system
- **when** it happened
- **a message** describing it
- **the content itself**, stored so identical content is never duplicated

The result is a walkable chain. You can read a file's whole life, not just its current state.

## Three things this buys you

### 1. `trace` — "why is this here?"

Open any file's history and you see the chain: `r7`, authored by you, "tightened the pricing section," two days ago. Click a revision to diff it against the current version.

This is the capability a memory feature can't offer. An inferred-memory system can tell you what it thinks it knows; it can't tell you who told it, when, or what it used to think instead.

You can also ask for this from outside YARNNN — the `trace` tool over MCP returns the same history to ChatGPT or Claude.

### 2. Corrections compound

Fix a source file once, and everything made from it afterwards starts from the corrected version. You aren't re-explaining the same thing every session.

The reverse also holds: when a file was **made from** other files, that relationship is recorded. So when you trash a source, you're told what depended on it.

### 3. Nothing is silently lost

Deleting moves a file to Trash, and Trash has no timer. Reverting writes the old content forward as a new revision rather than erasing what happened. Even permanent delete removes the bytes while keeping the record that they existed and who authored them.

## Who can write where

Every participant in a workspace — you, your teammates, an agent, a connected ChatGPT — holds a **grant**: a record of what they're allowed to write.

- **You (the owner)** hold full access, and it can't be revoked out from under you
- **Teammates** hold member access, which you can narrow to specific regions
- **External AIs** get a grant automatically when you connect them, and it's revocable at any time

There's one rule that never bends: **no permission is ever based on whether the participant is a human or an AI.** A grant is a grant. What differs is what each one is allowed to write, which is something you set.

You can see the whole roster and adjust it at **Workspace Settings → Access**.

## Where to see it in the app

- **Files → any file → Get Info** — the revision history and contributors
- **Files → Recents** — the most recent revisions across the workspace
- **Launcher → Activity** — the log of runs and system events (this is machinery, not file history)
