# What Are Agents?

Agents are persistent work specialists inside YARNNN.

They are not one-off prompts. They keep their own instructions, sources, run history, and accumulated feedback over time.

## What makes an agent useful

Each agent combines four things:

1. **A job**: what it is supposed to produce
2. **Coverage**: which sources it should draw from
3. **A schedule**: when and how often it runs
4. **Feedback history**: what it has learned from prior runs

That is why the tenth run of an agent should be better than the first.

## Common agent jobs

Most users begin with one of these:

- **Weekly update**: summarize Slack channels or Notion pages on a schedule
- **Competitor watch**: monitor topics or competitors with web research
- **Research tracker**: investigate a topic and deepen findings over time
- **Status report**: synthesize activity across platforms into a polished deliverable

## How agents run

Every agent has a **pulse** — an autonomous sense-and-decide cycle that runs on cadence.

When the pulse fires, the agent checks whether it has fresh context and enough signal to produce useful work. If it does, it generates. If not, it waits. Either way, the pulse is visible — you can see what your agents are doing even when they decide not to generate.

New agents pulse on their schedule. As agents gain tenure and trust, their pulse becomes more sophisticated — they self-assess before generating and can act off-schedule when something warrants it.

## Agents work together

For bigger jobs, multiple agents can collaborate on a single deliverable.

One agent pulls from Slack, another from Notion, another does research — then a coordinator (the Project Manager agent) assembles their contributions into one polished output. You get a finished product, not fragments.

This is how [projects](projects.md) work: a team of agents with a shared objective, coordinated by a PM.

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
- talk to the agent directly in its [meeting room](projects.md) to redirect its focus

That feedback becomes part of the agent's future behavior. Instructions you give in conversation persist across sessions — agents remember what you told them.

## Why persistence matters

The point of an agent is not just automation. It is accumulated attention.

A good agent remembers:

- what sources usually matter
- what structure you prefer
- what you keep editing out
- what level of detail is useful for a specific audience

That is what turns a generic summary into work that actually feels tailored.
