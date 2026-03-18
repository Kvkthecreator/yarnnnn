# What Are Agents?

Agents are persistent work specialists inside YARNNN.

They are not one-off prompts. They keep their own instructions, sources, run history, and accumulated feedback over time.

## What makes an agent useful

Each agent combines four things:

1. **A job**: what it is supposed to produce
2. **Coverage**: which sources it should draw from
3. **A mode**: when it should act
4. **Feedback history**: what it has learned from prior runs

That is why the tenth run of an agent should be better than the first.

## Common agent patterns

Most users begin with one of these:

- **Recap / Digest**: summarize activity in a source or domain
- **Meeting Prep**: prepare context before a meeting
- **Status Update**: synthesize updates for a stakeholder or team
- **Watch**: monitor a topic and surface meaningful signal
- **Research**: investigate a bounded question and return a structured result

## Modes

Modes describe how an agent decides when to act.

| Mode | What it means |
|---|---|
| `recurring` | Runs on a schedule |
| `goal` | Runs toward a specific objective |
| `reactive` | Runs when event-driven conditions are met |
| `proactive` | Reviews a domain periodically and acts when warranted |
| `coordinator` | Participates in a supervisory review loop managed by the system |

## What supervision looks like

Every run gives you something concrete to evaluate.

- review the work
- edit it if needed
- refine the instructions through TP

That feedback becomes part of the agent's future behavior.

## Why persistence matters

The point of an agent is not just automation. It is accumulated attention.

A good agent remembers:

- what sources usually matter
- what structure you prefer
- what you keep editing out
- what level of detail is useful for a specific audience

That is what turns a generic summary into work that actually feels tailored.
