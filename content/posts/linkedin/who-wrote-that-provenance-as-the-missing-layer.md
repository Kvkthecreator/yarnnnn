# Who Wrote That? Provenance As The Missing Layer In AI Workspaces

Open any AI workspace product and ask the simple question: who wrote this paragraph?

In almost every case, you can't tell. The model wrote some of it, the user edited some of it, the model rewrote in the next session. The file just shows the current state with no history of who did what when.

That missing layer — provenance — is the difference between a shared workspace you can trust and one you eventually copy out of into a Google Doc.

**What provenance actually means**

Typed answers to four questions about every change:

→ Who. A typed identity: operator, ai:claude-sonnet-4-5, agent:competitor-analyst, reviewer:simons. Not a free-text string.
→ When. A timestamp at write time.
→ What changed. The previous content (or pointer to it).
→ Why. A short message. Required, not optional.

With these, "who wrote this?" always has an answer. Without them, the file is just whatever the latest writer left.

**Why this doesn't exist in most AI products**

ChatGPT memories are anonymous. If you edit them, the edit replaces the original; the next time the model writes, it overwrites again.

Notion AI edits show up as user edits in version history.

Cursor and similar coding tools at least make AI edits visible as a diff before applying. But once applied, git shows the human as the author.

Each is a reasonable shipping decision in isolation. They become a problem when the AI's role grows from "occasional assistant" to "persistent collaborator." At that point, anonymous AI edits look exactly like silent corruption, and the operator stops trusting the workspace.

**What provenance enables**

→ Trustable AI mutation — operator can see what the AI wrote and roll back if needed
→ Multi-AI coordination — agents share context with knowledge of who wrote what when
→ Reviewable AI behavior over time — patterns become visible
→ Provenance-aware reading — AI weights AI-edited content less than operator-authored content
→ Survival of mistakes — every prior version recoverable, attributed

**Provenance vs audit logs**

Audit logs are external observability — separate table, expensive to query, rarely used. Provenance is internal substrate semantics — the current state IS the head of a revision chain. Walking the chain is cheap and used constantly.

The agent products that win the persistent-collaborator slot will have provenance. The ones that don't will keep hitting a coordination wall the moment AI becomes a real writer.

Provenance isn't a feature. It's the foundation everything else stands on.

Full essay: yarnnn.com/blog/who-wrote-that-provenance-as-the-missing-layer

#AIAgents #AIWorkspace #AITrust #AIProvenance #AIAttribution

---

YARNNN is an agent-native operating system for autonomous knowledge work.
