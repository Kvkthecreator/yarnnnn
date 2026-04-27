# Reference Workspace — alpha-trader

> The bundled starter substrate operators fork on activation. Per ADR-223 §5: templates with prompts, not authored content the operator must accept.

## What's here

- `context/_shared/` — workspace-level authored substrate operators populate (IDENTITY, BRAND, CONVENTIONS, MANDATE, AUTONOMY)
- `review/` — Reviewer seat substrate (IDENTITY persona + principles framework)
- `memory/` — YARNNN orchestration accumulation files (empty placeholders)

## What's NOT here

- **No tasks.** Tasks are operator-created post-activation via the CreateTask modal or YARNNN chat. The reference doesn't pre-author tasks; it ships the substrate context tasks will reference.
- **No agents.** Per ADR-205, signup scaffolds exactly one agent (YARNNN). User-authored Agents are operator-authored post-activation.
- **No real numbers.** Reference workspaces are public — they ship as part of the repo. No P&L numbers, no real customer data, no API keys. Per ADR-223 §5 redaction discipline.
- **No specific positions, signals, or universes.** Those are persona-layer (operator-authored) content, not program-layer (platform-authored) content.

## Activation

Per the forthcoming Reference-Workspace Activation Flow ADR (ADR-222 roadmap ADR 5): when an operator selects alpha-trader at signup, `workspace_init.py` copies these files into the operator's `/workspace/`. The chat agent then walks the operator through differential-authoring — *"this is the reference. Walk me through how your discipline differs."*
