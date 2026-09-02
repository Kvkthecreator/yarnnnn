---
name: writing-a-spec
description: Writes a grounded product or feature spec (PRD shape) from workspace sources, with every requirement traceable to a source and inferences marked. Use when asked for a spec, PRD, requirements, a feature definition, or to turn notes and research into something a team could build from.
metadata:
  target: One spec (.md) in the product's meaning-folder with the conventional sections, grounded in the source, inferences marked.
  apps: [text]
---
# Writing a spec

Produce a spec a teammate, or another agent, could act on, derived from the source.

## Steps

1. Read the source fully. Separate what it STATES from what you INFER.
2. Write ONE markdown file into the product's meaning-folder (create one if none fits), named for the product or feature, with `derived_from` naming the source.
3. Sections, in order: Problem · Users · Goals · Non-goals · Requirements (functional, then non-functional) · Success metrics · Open questions.

## Quality bar

- Grounded: every requirement traceable to the source. Where you infer, mark it "(inferred)" so readers can challenge it.
- Non-goals and Open questions are mandatory. An empty one means you have not thought about scope; say what the source leaves undecided.
- Requirements are testable statements, not themes.

## Anti-patterns

Solution language in the Problem section. Requirements the source never supports. Omitting Open questions to look complete.
