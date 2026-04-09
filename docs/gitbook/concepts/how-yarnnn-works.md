# How YARNNN Works

YARNNN runs on a simple loop:

`connect → accumulate context → define tasks → agents execute → supervise → compound`

## 1. Connect

You connect Slack or Notion through OAuth.

YARNNN gets read-only access so it can understand your work context, not act inside those tools.

## 2. Accumulate context

After connection, YARNNN discovers the available sources and syncs the selected coverage into a shared workspace.

That workspace holds the material the whole system reasons over:

- Slack messages
- Notion pages and databases
- uploaded files and documents

This is what keeps later work grounded instead of starting cold every time.

## 3. Assign persistent agents

YARNNN uses persistent agents rather than session-only chat threads.

Agents are the specialists that keep getting better with use. They hold identity, capabilities, memory, and prior work history.

Different agents play different roles:

- domain specialists deepen knowledge in a subject area
- platform bots bridge specific systems such as Slack or Notion
- Thinking Partner manages the system itself

## 4. Define tasks

Tasks are the work units.

Each task defines:

- what should be produced
- how often it should run
- where it should be delivered
- which agent or multi-agent process should handle it

This is the key split in the service model:

- **Agents = who**
- **Tasks = what**

## 5. Execute and deliver

When a task is due, YARNNN reads the task definition, gathers the right context, generates the output, composes it, and delivers it.

Simple tasks can be handled by one agent. Larger tasks can define a process where multiple agents contribute in sequence to one deliverable.

Outputs can be:

- email-ready digests
- status reports
- research briefs
- PDFs, slides, spreadsheets, and other richer artifacts

## 6. Supervise and improve

You review what the system produces and redirect it when needed.

That supervision can include:

- refining coverage
- changing task objectives
- adjusting tone or structure
- adding or removing recurring work

This is the trust model. YARNNN starts supervised and improves from real feedback.

## Two layers of intelligence

YARNNN has two kinds of intelligence running on the same agent substrate:

- **Thinking Partner (TP)** manages the workforce, creates and adjusts tasks, explains system behavior, and keeps the whole workspace coherent.
- **Domain agents** execute the recurring work and deepen domain-specific knowledge over time.

TP is not a separate chat product bolted on top. It is a meta-cognitive agent inside the same system.

## Multi-agent work

For bigger jobs, multiple agents can collaborate on one task.

One agent might gather internal signals, another might research external context, and a final step might synthesize the deliverable. The task defines that process. TP orchestrates it.

The result is one finished output, not a pile of fragments.
