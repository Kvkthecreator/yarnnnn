---
name: mermaid
description: "Create diagrams from Mermaid syntax. Produces PNG or SVG flowcharts, sequence diagrams, org charts, and more."
type: local
tools: ["mermaid-cli"]
input_format: "JSON with mermaid syntax string"
output_formats: [".png", ".svg"]
---

# Mermaid Diagram Skill

Creates diagrams from Mermaid syntax using mermaid-cli (mmdc).

## Input Spec

The input is a JSON object:

```json
{
  "mermaid": "graph TD\n    A[Start] --> B[Process]\n    B --> C[End]",
  "title": "Optional title (not rendered in diagram)"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mermaid` | string | yes | Mermaid diagram syntax |
| `title` | string | no | Metadata title (not rendered) |

### Supported Diagram Types

- **Flowchart** — `graph TD`, `graph LR` (top-down, left-right)
- **Sequence** — `sequenceDiagram`
- **Class** — `classDiagram`
- **State** — `stateDiagram-v2`
- **ER** — `erDiagram`
- **Gantt** — `gantt`
- **Pie** — `pie`
- **Mindmap** — `mindmap`
- **Timeline** — `timeline`

## Output Formats

- `png` — Raster image. Best for embedding in presentations and emails.
- `svg` — Vector image. Best for web display and scaling.

## Examples

### Process flow
```json
{
  "type": "diagram",
  "input": {
    "mermaid": "graph TD\n    A[User Request] --> B{Composer}\n    B -->|Create| C[New Agent]\n    B -->|Adjust| D[Update Agent]\n    B -->|Dissolve| E[Archive Agent]\n    C --> F[First Run]\n    D --> F\n    F --> G[Deliver Output]"
  },
  "output_format": "png"
}
```

### Sequence diagram
```json
{
  "type": "diagram",
  "input": {
    "mermaid": "sequenceDiagram\n    participant U as User\n    participant TP as Orchestrator\n    participant A as Agent\n    participant R as Render\n    U->>TP: Create report\n    TP->>A: Execute\n    A->>R: RuntimeDispatch\n    R-->>A: output_url\n    A-->>TP: Done\n    TP-->>U: Report ready"
  },
  "output_format": "svg"
}
```

## Constraints

- Maximum mermaid syntax: ~50KB
- Rendering timeout: 30 seconds
- No custom themes — uses mermaid default theme
- Puppeteer runs headless in container (no GPU)
