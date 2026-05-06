# Git For AI: Why Every Memory Edit Should Be Attributed

Every AI memory layer I've used eventually has the same conversation: "Wait, who wrote this?"

The model wrote it, the user edited it, the model overwrote, and now there's no way to recover the original or tell what changed when. The fix isn't better UX. It's the discipline git brought to source code thirty years ago — content-addressed storage, parent-pointed revisions, required authorship on every mutation.

I shipped this in my own product six weeks ago. I'd put it in the top three architectural decisions of the year.

**The three disciplines git brought to source code**

Before git, source control was a coordination problem. Files got overwritten. Branches diverged silently. Authorship was ambiguous. The fix wasn't better commit UI. It was three architectural choices:

→ Content-addressed storage. Every blob keyed by its hash. Identical content reuses storage.
→ Parent-pointed revisions. Every commit knows its parent. The chain is walkable.
→ Required authorship. Every commit has an author. Anonymous commits don't exist.

These three together gave source code the trust model that allowed every modern collaboration pattern — branches, pull requests, blame, bisect — to exist downstream.

**What this looks like for AI memory**

In our system, every file in every workspace is backed by:

→ Content-addressed blob table (sha256-keyed, deduplicated)
→ Revision chain (every mutation produces a new row with parent_version_id)
→ Required write path (one function, takes content + author identity + message)

Author identity is a typed taxonomy: operator, ai:claude-sonnet-4-5, agent:competitor-analyst, reviewer:simons, system:initialization. Every revision belongs to exactly one.

**What this enables**

→ Trustable AI mutation — the operator can see who wrote what, with what message
→ Multi-AI coordination — agents can see what other agents wrote, when, with what message
→ Reviewable AI behavior over time — operator can audit "every AI reviewer edit to my principles last month"
→ Provenance-aware reading — AI weights AI-edited content less than operator-authored content
→ Survival of mistakes — every prior version is recoverable

**Why this becomes table-stakes**

The agent products that win the persistent-collaborator slot will have provenance. The ones that don't will keep losing operators to "I gave up and copied my notes into Apple Notes where the AI can't touch them."

This isn't a prediction. It's already happening.

The next wave of AI workspace products will all claim to have "version history" and "audit logs." A few will actually have provenance. Look for the difference: can you read any file and see who wrote each section, when, why?

Full essay: yarnnn.com/blog/git-for-ai-why-every-memory-edit-should-be-attributed

#AIAgents #AIMemory #VersionControl #Git #AITrust #AuthoredSubstrate

---

Kevin is the founder of YARNNN, an agent-native operating system for autonomous knowledge work.
