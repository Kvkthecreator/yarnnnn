# Deliverable Types and Modes

YARNNN deliverables are configured across two independent dimensions:

- **Type** = what you're building
- **Mode** = how/when it decides to act

This separation keeps setup clear: user intent stays in the type, execution behavior stays in the mode.

## The 7 deliverable types

| Type | Use it for |
|---|---|
| `digest` | Regular synthesis of activity in a specific place (channel, label, page set) |
| `brief` | Situation-specific prep before an event or decision |
| `status` | Cross-platform updates for stakeholders, team, or leadership |
| `watch` | Ongoing intelligence on a domain you want monitored |
| `deep_research` | Bounded investigation with a clear end state |
| `coordinator` | Meta-specialist that can dispatch other deliverables |
| `custom` | Fully custom intent and structure |

## The 5 execution modes

| Mode | Behavior |
|---|---|
| `recurring` | Runs on a fixed schedule |
| `goal` | Runs toward a defined objective, then stops |
| `reactive` | Watches events and generates when threshold is reached |
| `proactive` | Periodically reviews a domain and decides whether to generate |
| `coordinator` | Proactive + can create/trigger other deliverables |

## Natural pairings

| Type | Common modes |
|---|---|
| `digest` | `recurring`, `reactive` |
| `brief` | `goal`, `proactive`, `coordinator` |
| `status` | `recurring`, `goal` |
| `watch` | `reactive`, `proactive` |
| `deep_research` | `goal` |
| `coordinator` | `coordinator` |
| `custom` | Any mode |

## Why this matters

- You can run the same type in different ways (for example, `digest` as weekly or threshold-driven).
- Each deliverable keeps its own memory and improves over time.
- Advanced autonomy stays explicit and controllable instead of hidden in infrastructure.
