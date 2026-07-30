# Prompt engineering principles

**Date**: 2026-07-30
**Status**: Reference. A neutral statement of the principles — no YARNNN-specific application, no recommendations.
**Source**: Boris Cherny, "We Cut 80% of Claude Code's Prompt" (https://www.youtube.com/watch?v=qyPCVqFUyDo&t=1713s), as captured in operator-supplied notes.

> **Sourcing note.** YouTube did not serve the transcript to the fetch tool; only the title and speaker were recoverable. The principles below are transcribed from operator-supplied notes, not verified against the recording.

This document states the principles as they are. Applying them is separate work.

---

## 1. Prompt ablation

Treat prompts like production code: every instruction should justify its existence.

- Delete aggressively.
- Don't guess that an instruction is helpful — test it.
- Run prompt ablation regularly.
- Remove instructions that don't produce measurable improvements.
- Only introduce new instructions to solve **repeated** failure modes.
- Refine iteratively through observation and testing.
- Prefer the shortest prompt that consistently achieves the desired outcome.

**Rule of thumb:** every instruction is guilty until it proves its value.

---

## 2. Prompt bloat and LLM hobbling

Adding more instructions does not necessarily improve model performance. Excessive prompts can:

- Compete with the user's actual request.
- Create conflicting objectives.
- Reduce flexibility and adaptability.
- Increase latency and token cost.
- Make prompts harder to maintain.

Instead of continuously patching prompts with new rules, periodically perform prompt ablation to ensure every remaining instruction still provides value.

---

## 3. Prompt structure

A simple, reusable framework.

**Describe** — provide the necessary context.
- What is the project?
- What background is relevant?
- What environment does the model operate in?

**Task** — clearly define the work.
- What should be accomplished?
- What inputs are available?
- What output is expected?

**Guardrails** — specify constraints.
- What should not happen?
- What assumptions are prohibited?
- What existing patterns or standards should be followed?
- When should the model ask instead of guessing?

**Exit criteria** — define success.
- What deliverables are required?
- What conditions must be met?
- How should completion be verified?

---

## 4. Coding agent best practices

For repository-aware coding agents:

- Inspect the existing codebase before making changes.
- Follow existing architecture and conventions.
- Modify the minimum number of files necessary.
- Reuse existing components and abstractions.
- Avoid unnecessary refactors.
- Explain what changed and why.
- Verify the project builds or tests successfully before considering the task complete.

**Operating principle:** inspect before acting. Plan before editing. Edit the minimum. Verify before finishing.

---

## 5. General philosophy

Good prompt engineering isn't about writing longer prompts — it's about writing better ones.

Optimize through:

- Simplicity
- Measurable improvements
- Repeated testing
- Iterative refinement
- Minimal but sufficient instructions

The prompt should contain only the information that demonstrably improves the model's ability to complete the task reliably.
