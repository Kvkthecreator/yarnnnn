# What Are Agents?

Agents are persistent specialists inside YARNNN.

They are not one-off prompts. Each agent keeps its own identity, capabilities, run history, and accumulated feedback over time.

## Agents are the "who"

YARNNN's service model separates:

- **Agents = who does the work**
- **Tasks = what work gets done**

An agent can be assigned to more than one task. A task can be simple, or it can define a multi-agent process.

## What makes an agent useful

Each agent combines four things:

1. **Identity**: its name, domain, and standing instructions
2. **Capabilities**: which tools and runtimes it can use
3. **Domain memory**: what it has learned from prior work
4. **Assignments**: the tasks it is currently responsible for

That is why the tenth run of an agent should be better than the first.

## Common agent classes

YARNNN's workforce includes a few different kinds of agents:

- **Domain stewards**: specialists that keep a context domain fresh and useful
- **Synthesizers**: agents that turn multiple inputs into a report or brief
- **Platform bots**: agents tied closely to a platform such as Slack, Notion, or GitHub
- **Thinking Partner**: the meta-cognitive agent that manages the workforce itself

## How agents run

Agents do not own the schedule by themselves. Tasks do.

When a task runs, YARNNN resolves the assigned agent or agents, gathers the needed context, and executes the work.

This matters because the same agent can contribute to multiple tasks over time, which is how its knowledge compounds instead of being trapped inside one workflow.

## Agents work together

For bigger jobs, multiple agents can collaborate on a single deliverable.

One agent might pull internal signals, another might research external context, and a final synthesis step turns that into one polished output. You get a finished product, not fragments.

This is how [tasks](projects.md) scale from one specialist to a multi-agent process.

## Output formats

Agents can produce:

- plain text and email-ready content
- PDF reports
- slide decks (PPTX)
- spreadsheets (XLSX)
- charts and visualizations

The format depends on the job. A daily recap might be email-ready text. A leadership report might be a PDF or slides.

## What supervision looks like

Every run gives you something concrete to evaluate.

- review the work
- edit it if needed
- ask TP to adjust the task, delivery, or emphasis
- inspect the assigned specialist on the Agents surface

That feedback becomes part of the agent's future behavior.

## Why persistence matters

The point of an agent is not just automation. It is accumulated attention.

A good agent remembers:

- what sources usually matter
- what structure you prefer
- what you keep editing out
- what level of detail is useful for a specific audience

That is what turns a generic summary into work that actually feels tailored.
