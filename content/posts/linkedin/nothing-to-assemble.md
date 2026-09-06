---
source: https://www.yarnnn.com/blog/nothing-to-assemble
platform: linkedin
account: yarnnn company page
series: Inside the workspace (6/8)
status: ready
---

Most AI tooling asks you to build the workspace before you can use one.

Pick an orchestration framework. Connect a vector store. Add the connectors for the tools you already pay for. Write the agent definitions. Decide how files are persisted, then discover that decision was load-bearing and revisit it.

Every step is reasonable. The sum is a small infrastructure project standing between a person and the work they wanted to do — and the people with the most to gain from AI colleagues are exactly the people with the least appetite for a small infrastructure project.

There is a subtler cost too. When you assemble the workspace yourself, the pieces do not share a record. They share a bus.

Chat holds conversations. The store holds embeddings. Files sit somewhere else. Nothing has a common notion of this artifact, and who changed it, because you wired transports rather than a substrate.

If chat has its own store and the deck editor has another, the same fact ends up in two places with no relationship between them. Fix it in one and the other is now quietly wrong. Nothing tells you.

That is exactly the failure a record is supposed to catch, reintroduced by the architecture of the tool meant to catch it.

One file system means a correction is made once and is true everywhere, because there is only one place for it to be true.

It is a fair suspicion that assembled means closed — batteries-included has historically been how products make leaving expensive. So the boundary matters: connect the assistants you already use, and take the whole workspace out as a plain git repo with its history intact.

An assembled product with a plain-text exit is a convenience. Without one it is a trap.

Full argument: https://www.yarnnn.com/blog/nothing-to-assemble

#AI #FutureOfWork
