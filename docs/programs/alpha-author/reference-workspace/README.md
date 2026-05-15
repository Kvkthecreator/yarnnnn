# Reference Workspace — alpha-author

> The bundled starter substrate operators fork on activation. Per ADR-223 §5: templates with prompts, not authored content the operator must accept.

## What's here

- `context/_shared/` — workspace-level authored substrate operators populate (IDENTITY, BRAND, CONVENTIONS, MANDATE, AUTONOMY) plus machine-parsed siblings (`_autonomy.yaml`, `_preferences.yaml`)
- `context/authored/` — operator-authored substrate for the authored domain (`_voice.md` voice fingerprint, `_editorial.md` editorial principles)
- `review/` — Reviewer seat substrate (IDENTITY editor persona, principles.md framework, `_principles.yaml` machine-parsed thresholds)
- `memory/` — YARNNN orchestration accumulation files (empty placeholders)
- `specs/` — capability specs (Claude Code skills.md analog; six specs: voice-audit, continuity-audit, corpus-coherence-rollup, pre-ship-check, weekly-corpus-review, quarterly-voice-audit)
- `_recurrences.yaml` — bundle's scheduled work declaration (mechanical mirrors + judgment recurrences)
- `_workspace_guide.md` — ADR-280 path-zone declarations + Reviewer wake envelope merge of kernel-universal + alpha-author program-specific paths

## What's NOT here

- **No tasks.** Tasks are operator-created post-activation via the CreateTask modal or YARNNN chat. The reference doesn't pre-author tasks; it ships the substrate context tasks will reference.
- **No agents.** Per ADR-205, signup scaffolds exactly one agent (YARNNN). User-authored Agents are operator-authored post-activation.
- **No specific drafts, voice fingerprints, or audience platforms.** Those are persona-layer (operator-authored) content, not program-layer (platform-authored) content.
- **No real audience or revenue numbers.** Reference workspaces are public — they ship as part of the repo. No subscriber counts, MRR data, customer information, or API keys. Per ADR-223 §5 redaction discipline.

## Activation

Per [ADR-226 (Reference-Workspace Activation Flow)](../../../adr/ADR-226-reference-workspace-activation-flow.md): when an operator selects alpha-author at signup or via `/api/programs/activate`, `workspace_init.py::fork_reference_workspace` copies these files into the operator's `/workspace/`. The chat agent then walks the operator through differential-authoring — *"this is the reference. Walk me through your voice. Walk me through what you ship vs hold."*

Per [ADR-283](../../../adr/ADR-283-alpha-author-bundle.md): full bundle activation requires roadmap step 2 (capability extensions — Notion page-write + publishing-platform writes) and step 3 (program-specific cockpit faces). Pre-step-2, activation produces a knowledge-only workspace (reads + drafts + comments-only Notion + lived-attention via uploads + websearch). Audience-bearing capabilities unlock the audience signal slice of `_signal.md` once step 2 ships.
