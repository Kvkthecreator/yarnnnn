"""Author-shape draft templates for scenario runner.

Author-shape probes seed a /workspace/operation/authored/{slug}/ piece with
profile.md (frontmatter + title) + content.md (prose), then transition
profile.md's `status:` field to fire the alpha-author bundle's pre-ship-
audit substrate-event hook. Each template is hand-authored to exercise
a specific Reviewer reasoning shape:

- `anti-pattern-voice` — list-of-three openers, "at the end of the day",
  "absolutely pivotal", intensifier adverbs, "in conclusion" closer.
  Reviewer should defer with directive citing the voice anti-patterns.
  Extracted from canary_phase4_v3/v4/v5 (same content; the canary arc
  varied FREDDIE_PRIMITIVES surface size as the test variable, not
  the content).

- `clean-voice` — same length + structure, no anti-patterns. Reviewer
  should approve. Provides the contrast pair for evaluating whether
  Reviewer's verdict tracks content quality vs reasoning artifacts.

Mirrors the proposal_templates.py registry pattern (named templates,
versioned in this file, get_template() resolver). Singular-implementation
discipline: don't fork templates across files. New templates added here.

Use from a scenario YAML:
    setup:
      - seed_draft:
          slug: my-test-piece
          template: anti-pattern-voice

Or from a canary script:
    from services.operator_proxy.draft_templates import get_template
    template = get_template("anti-pattern-voice")
    profile_content = template["profile"].format(
        slug="my-canary-v6", title="My Canary Test"
    )
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


# Profile.md frontmatter template — caller formats with {slug} + {title} +
# {created_at_iso}. status starts as `draft`; canary or scenario flips it
# to ready_for_review to fire the pre-ship-audit hook.
_PROFILE_TEMPLATE = """---
title: "{title}"
slug: {slug}
type: essay
status: draft
voice: founder-prose
created_at: {created_at_iso}
ship_self_check: pending
---

# {title}

{description}
"""


# Anti-pattern voice content — extracted from canary_phase4_v4 (identical
# in v3 + v5; only the wrapping canary arc differed). Reviewer's expected
# verdict: DEFER with directive citing voice anti-patterns.
_ANTI_PATTERN_VOICE_CONTENT = """# The Future of Autonomous Agents Will Be Truly Revolutionary

There are several factors, several key drivers, several fundamental
forces that will inevitably shape the future of autonomous agent
systems. At the end of the day, we need to recognize that we're at
an absolutely pivotal moment in the evolution of how machines
collaborate with humans.

Let's dive into what makes this so transformative. It's worth noting,
I believe, that perhaps the most game-changing aspect of modern
agentic systems is their unprecedented capacity to genuinely
understand context in ways that traditional software simply cannot.

The implications are truly mind-blowing. These systems will
fundamentally revolutionize how we think about productivity,
collaboration, and indeed the very nature of work itself. They
absolutely represent a paradigm shift of monumental proportions.

In conclusion, we stand at the dawn of an entirely new era. The
question is not whether autonomous agents will transform every
industry — it's how quickly we can leverage their incredible
potential to unlock value at scale.
"""


# Clean-voice content — same length + structure, no anti-patterns.
# Reviewer's expected verdict: APPROVE (no material defects).
_CLEAN_VOICE_CONTENT = """# What Autonomous Agents Actually Change About Knowledge Work

A persistent agent that runs every day on the same operator's mandate
becomes something different from a request-response chatbot. The
substrate it accumulates — feedback, decisions, what the operator
corrected last week — is the entire point. Without persistence, every
interaction starts cold; with persistence, the agent's judgment matures.

That maturation is the operator's investment. An operator who spent
six weeks teaching an agent the tolerances of their pricing model
doesn't switch vendors lightly. The switching cost isn't the contract;
it's the six weeks. This is where the moat lives.

The architecture follows: filesystem-native substrate, attribution on
every revision, the operator can read what the agent has been doing
without log-diving. Substrate is the audit trail and the agent's mind
in the same surface.

The thesis is testable. An operator-installed agent should produce
materially better decisions in month three than month one, measurable
against declared success criteria. If it doesn't, the architecture
isn't doing its job.
"""


TEMPLATES: dict[str, dict[str, Any]] = {
    "anti-pattern-voice": {
        "profile": _PROFILE_TEMPLATE,
        "content": _ANTI_PATTERN_VOICE_CONTENT,
        "expected_verdict": "defer",
        "description": (
            "Voice anti-patterns: list-of-three openers, 'at the end of the day', "
            "'absolutely pivotal', intensifier adverbs, 'in conclusion' closer. "
            "Reviewer should defer with directive citing the anti-patterns."
        ),
    },
    "clean-voice": {
        "profile": _PROFILE_TEMPLATE,
        "content": _CLEAN_VOICE_CONTENT,
        "expected_verdict": "approve",
        "description": (
            "Same length + structural shape as anti-pattern-voice, no anti-patterns. "
            "Reviewer should approve (no material defects). Contrast pair for "
            "evaluating verdict-tracks-content-quality."
        ),
    },
}


def get_template(name: str) -> dict[str, Any]:
    """Resolve a draft template by name. Raises KeyError on unknown."""
    if name not in TEMPLATES:
        raise KeyError(
            f"Unknown draft template {name!r}. Available: {list(TEMPLATES)}. "
            "Add new templates to services/operator_proxy/draft_templates.py."
        )
    return dict(TEMPLATES[name])  # defensive copy
