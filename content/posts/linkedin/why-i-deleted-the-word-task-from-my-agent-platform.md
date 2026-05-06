# Why I Deleted The Word "Task" From My Agent Platform

Last month I deleted 9,200 lines of task-management code from my agent platform.

That number feels like a brag. It's actually an embarrassment. Those lines should never have been there. The word "task" had been the central abstraction since day one, and it was wrong from day one.

What operators actually wanted wasn't a task manager. It was an autonomous operation governed by their standing intent.

**What I built first (and why it was wrong)**

The first version of the platform had `tasks` as a first-class table — id, title, schedule, status, mode, output_kind. The UI had a /tasks page. The API had POST /api/tasks. Operators created tasks. Agents executed tasks.

This felt natural because every productivity tool works this way. Asana, Linear, Trello, Jira. Plug in agents instead of humans and you have an agent platform. Right?

Wrong, in the way that took six months to see.

The task abstraction encodes an assumption: work is composed of discrete units, defined upfront, executed once, completed. That assumption is true for human labor. It is not true for what operators want autonomous AI to do.

**The symptoms I should have listened to**

→ Every alpha operator ended up with 8-14 fragmented tasks for what was conceptually one operation
→ My own conversational agent kept defaulting to "let me create a task for that" for every operator request
→ The substrate layout was schizophrenic — some artifacts under /workspace/context/, others under /tasks/{slug}/outputs/

I dismissed each of these for months as "we'll clean it up later." Eventually I noticed the cleanup would never come because the underlying abstraction was wrong.

**The replacement: Mandate, Recurrence, Invocation**

The new architecture doesn't have tasks. It has three things:

→ Mandate: the operator's standing intent, authored at /workspace/context/_shared/MANDATE.md
→ Recurrence: a YAML file describing what should happen on what cadence
→ Invocation: one cycle of execution

The user-facing vocabulary diverges from the storage vocabulary on purpose. Operators talk about reports, trackers, actions, system. The substrate stores them in shape-appropriate locations.

The thing that's gone: the word "task."

**What I'd tell past me**

Pick the abstraction by listening to what operators actually say, not by reaching for the productivity-tool metaphor.

Operators don't ask for "tasks." They ask for "watch this," "tell me when," "every morning," "do that for me until I say stop." Those words describe standing intent and recurrence, not discrete work units.

Build mandate-driven from the start. The architecture is shaped by the abstraction you choose for the first few weeks.

Full essay: yarnnn.com/blog/why-i-deleted-the-word-task-from-my-agent-platform

#AIAgents #BuildInPublic #AgentArchitecture #MandateDrivenAI #AutonomousAgents

---

Kevin is the founder of YARNNN, an agent-native operating system for autonomous knowledge work.
