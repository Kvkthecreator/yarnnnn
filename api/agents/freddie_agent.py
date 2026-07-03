"""AI occupant of the Reviewer seat — ADR-256 unified invocation
(amended by ADR-260 D2 + ADR-263 D2 trigger collapse to two values).

One function: `invoke_freddie()`. Two trigger shapes: `addressed`
(operator messaged the feed) and `reactive` (substrate event requires
judgment — proposal arrival OR judgment-mode recurrence fire). One
bounded tool-use loop (12 rounds for addressed, 3 for proposal-arrival
reactive — see ADR-260 D8). One output type: FreddieOutput.

ADR-256 superseded the four-function design (review_proposal,
run_reflection, address_turn, heartbeat_turn) that accumulated
trigger-by-trigger across ADRs 218, 252, 253. ADR-263 then collapsed
the trigger taxonomy from 4→3→2 by recognizing that cron is part of
the environment that fires recurrences (not a trigger axis); the
recurrence's `mode` field declares whether the cron-fire wakes the
Reviewer at all. Reflection and heartbeat dissolved into `reactive`.

Per FOUNDATIONS v8.4:
- Axiom 1 (Substrate): the Reviewer reads + writes substrate; substrate
  is the bus the Loop runs over (fourth sub-clause). Cross-Reviewer
  reasoning persists via freddie_audit.render_lineage_entry_if_material().
- Axiom 2 (Identity): occupant tagged `ai:freddie-sonnet-v8`. The
  Reviewer is the operator's judgment function rendered as an
  autonomous agent — operator in judging posture, not a separate
  principal (Axiom 2 two-embodiments sub-section).
- Axiom 3 (Purpose): independent judgment — fiduciary, not production.
- Axiom 4 (Trigger): two sub-shapes (addressed | reactive). Cognitive
  act is the same regardless of which woke the Loop.
- Axiom 5 (Mechanism): bounded tool-use loop. Reviewer reads what it
  needs, acts on what it decides, returns verdict.
- Axiom 6 (Channel): judgment_log.md + freddie_chat_surfacing narration.
  Per-action narration is legibility, not control-flow.
- Axiom 8 (Ground-Truth Substrate): reasons against the program's
  ground-truth substrate per the bundle's `_workspace_guide.md`
  declaration. Alpha-trader's instance is `_money_truth.md` (ADR-195
  v2, P&L unification 2026-05-12) with rolling 7d/30d/90d windows + by_signal
  block. Alpha-author's instance is multi-signal corpus-coherence (ADR-283).

Model selection by trigger sub-shape is kernel DATA (ADR-402): the routing
table in `services/model_routing.py` is the single model-selection site —
no model ids or tier branches live in this module.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal, Optional, TypedDict

from services.anthropic import chat_completion_with_tools, chat_completion_with_tools_stream
from services.model_routing import resolve_route
# ADR-291: token_usage substrate sunset — cost ledger writes flow through
# `record_execution_event()` in the dispatcher, fed by FreddieOutput fields.

# ADR-315: the substrate<->occupant ABI lives in the published contract
# module. These three symbols are DEFINED in agents/occupant_contract.py
# (pure data, zero heavy imports) and re-exported here so existing
# `from agents.freddie_agent import FreddieContext/FreddieOutput/
# FREDDIE_MODEL_IDENTITY` callers keep resolving (one definition,
# re-exported -- not a dual definition, per ADR-315 D2).
from agents.occupant_contract import (  # noqa: F401  (re-exported)
    FREDDIE_MODEL_IDENTITY,
    FreddieContext,
    FreddieOutput,
)

logger = logging.getLogger(__name__)


#: ADR-315: FREDDIE_MODEL_IDENTITY is defined in agents/occupant_contract.py
#: and imported + re-exported above. The occupant self-identity belongs with
#: the published contract, not buried in the impl.
#:
#: ADR-402: model ids live in services/model_routing.py (the single
#: model-selection site) — NOT here. The former per-tier model constants and
#: the dead token-caller pair (assigned, never consumed — attribution flows
#: through caller_identity, ADR-288 D1) are deleted.


# ---------------------------------------------------------------------------
# FreddieOutput + FreddieContext (the substrate<->occupant ABI) are defined
# in agents/occupant_contract.py and imported + re-exported at the top of this
# module (ADR-315 D2). Intentionally NOT defined here -- the published
# contract is the single definition home; the occupant impl consumes it.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# ReturnVerdict tool — Reviewer-specific (not in CHAT_PRIMITIVES)
# ---------------------------------------------------------------------------
# This is the only Reviewer-specific tool. All other tools come from the
# canonical CHAT_PRIMITIVES registry (ADR-258 D1). ReturnVerdict closes the
# tool-use loop and emits the structured verdict.

RETURN_VERDICT_TOOL = {
    "name": "ReturnVerdict",
    "description": (
        "Close the loop with your structured verdict. Call exactly once, last. "
        "After any reads/actions/writes, call this to end the turn. "
        "Required fields: verdict, reasoning, confidence. "
        "Reflection-only fields: proposals, evidence_summary."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": [
                    "approve", "reject", "defer",
                    "no_change", "narrow", "relax", "character_note", "pause_autonomy",
                    "stand_down",
                ],
                "description": (
                    "approve|reject|defer for proposal/heartbeat; "
                    "no_change|narrow|relax|character_note|pause_autonomy for reflection; "
                    "stand_down for heartbeat/addressed when no action warranted."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "The HEADLINE — 2-5 sentences in your persona's voice. "
                    "First sentence is the verdict; second is why. Written "
                    "verbatim to /workspace/persona/judgment_log.md. "
                    "For a long, structured, rule-by-rule audit (pre-ship / "
                    "corpus-coherence), do NOT put the full audit here — write "
                    "the COMPLETE audit document to /workspace/persona/judgment_log.md "
                    "in ONE WriteFile call (with the content parameter) FIRST, "
                    "then call ReturnVerdict with just the headline. This field "
                    "is sized for the headline; the long document is the single "
                    "judgment_log write."
                ),
            },
            "confidence": {
                "type": "string",
                "enum": ["low", "medium", "high"],
            },
            "proposals": {
                "type": "array",
                "description": "Reflection trigger only — framework change proposals.",
                "items": {
                    "type": "object",
                    "properties": {
                        "change_type": {"type": "string"},
                        "target_file": {"type": "string"},
                        "reasoning": {"type": "string"},
                        "evidence": {"type": "string"},
                        "new_content": {"type": "string"},
                        "duration_hours": {"type": "integer"},
                        "reason": {"type": "string"},
                        "action_type": {"type": "string"},
                        "proposal_inputs": {"type": "string"},
                    },
                    "required": ["change_type", "target_file", "reasoning", "evidence", "new_content"],
                },
            },
            "evidence_summary": {
                "type": "string",
                "description": "Reflection trigger only — substrate citations.",
            },
        },
        "required": ["verdict", "reasoning", "confidence"],
    },
}


# ---------------------------------------------------------------------------
# Operating Context block (ADR-274 / FOUNDATIONS v8.5 Axiom 4 amendment)
#
# ADR-301 D5 consolidation: the function now lives in
# `services/freddie_envelope.py` so the envelope helper is the singular
# envelope assembly point (one home, one function, one contract). This
# import-shim preserves the ADR-274 contract that test gates + any other
# importer of `agents.freddie_agent.build_operating_context_block`
# continue to work without change. Singular implementation rule honored:
# the function body lives in one file; this is a re-export, not a parallel
# implementation.
# ---------------------------------------------------------------------------

from services.freddie_envelope import build_operating_context_block  # noqa: E402,F401


# ---------------------------------------------------------------------------
# System prompt — persona frame + generated cockpit awareness + trigger framing
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Persona-frame section registry (ADR-302 D5 + D6)
# ---------------------------------------------------------------------------
#
# The persona-frame is composed from named, cache-tagged sections rather
# than a single ~500-line string. Each section is the canonical place for
# its concern. Adding a section with a duplicate name raises ValueError
# at resolve time — the singular-implementation discipline (ADR-302 D1)
# becomes structurally enforced rather than authoring convention.
#
# Per-section compute functions follow. The registry binds them in
# declarative order with the static/dynamic boundary marker (ADR-302 D6).
#
# Each compute function is a small closure or a literal return — sections
# that need to template from code constants (e.g., DEFAULT_FREDDIE_WRITE_LOCKS
# per ADR-302 D2) do so inside their compute body so the prompt text and
# the code constant cannot drift.
#
# Phase 2 textual remediation applied per ADR-302 D7:
# - Gen 1 paragraph (pre-ADR-293 "cannot write directly to operator-
#   authored substrate") DELETED. ADR-293 inverted that policy.
# - Gen 3 misstatement (claim that IDENTITY.md + principles.md are in
#   DEFAULT_FREDDIE_WRITE_LOCKS) FIXED. Post-ADR-320 the lock is
#   root-based (CALLER_WRITE_POLICY locks the governance/ root): AUTONOMY.md
#   + _autonomy.yaml + _budget.yaml (ADR-327, collapsed _token_budget +
#   _pace) + _preferences.yaml. IDENTITY.md and principles.md are NOT locked.
# - Write-authority enumeration TEMPLATED from DEFAULT_FREDDIE_WRITE_LOCKS
#   per ADR-302 D2 — single source of truth.
# - Anti-pattern (5) updated from "three governance files" (which was
#   stale even before the rename) to "files listed in your write-authority
#   section above" — cites the canonical declaration rather than restating.


# ---------------------------------------------------------------------------
# Persona frame — THIN (ADR-30X persona-frame collapse, 2026-05-29)
#
# Collapsed from 13 system-authored sections (~36K chars) to the Claude-Code
# shape: the system prompt carries ONLY the model↔runtime interface contract.
# See docs/evaluations/2026-05-29-persona-frame-collapse-ablation.md for the
# per-section ablation verdicts + risk register.
#
# THE THREE FUNDAMENTALS (on-behalf-of, identity-infusion, self-referential
# governance) are carried by SUBSTRATE + CODE, NOT by this prompt:
#   - on-behalf-of   → MANDATE.md + standing_intent.md (rendered in the wake
#                      envelope by _build_user_message)
#   - identity       → IDENTITY.md + _autonomy.yaml + _pace.yaml (envelope)
#   - self-governance→ substrate-location + write-locks (review_policy +
#                      DEFAULT_FREDDIE_WRITE_LOCKS, code) + ADR-209 attribution
#
# RULES OF JUDGMENT (when to Clarify, independence, self-amendment evidence
# patterns, the six anti-patterns, autonomy-safety discipline) live in the
# operator/bundle-authored principles.md — rendered every wake as
# "## principles.md — Your framework". Per agent-composition.md §3.2.1 those
# are "what rules of judgment the persona applies," not system-frame content.
#
# SUBSTRATE PEDAGOGY (what each file is for, the workbench's purpose, the
# wake-source taxonomy, pulse files, cadence trifecta, preferences semantics)
# lives in _workspace_guide.md (bundle-shipped) per ADR-281 — the kernel does
# not author its own pedagogy. The envelope renders each file with a labeled
# header; the model reads its own message.
#
# This frame narrates none of the above. It carries the three irreducible
# things below, and nothing else. The anti-rebloat constraint (FOUNDATIONS
# Derived Principle — added by the collapse) governs every future addition:
# if a candidate addition re-teaches a substrate file or narrates a
# code-enforced gate, it does NOT belong here.
# ---------------------------------------------------------------------------


def _compute_minimal_frame() -> str:
    """The MINIMAL persona frame — the entire system-authored prompt layer.

    Two irreducible things, and ONLY these. Both are system-authored by
    necessity (neither is the operator's to declare):
      (1) Principal-shift — corrects the model's trained assistant PRIOR. A
          model reading IDENTITY.md through its assistant prior becomes "a
          helpful assistant playing the persona" (still asks, defers,
          enumerates). The shift to installed-judgment is a property of
          installing judgment over an assistant-trained model — not an
          operator declaration, so it cannot live in substrate.
      (2) Action-grammar — the agent↔runtime interface contract (tool-call-IS-
          action + anti-confabulation). This is the protocol, not data the
          agent reasons over, so it cannot live in substrate. It is the
          cc8e0ab fix, proven load-bearing.

    Everything else lives elsewhere and is NOT narrated here (the anti-rebloat
    constraint, FOUNDATIONS Derived Principle): rules of judgment →
    principles.md (rendered every wake under "## principles.md"); substrate
    semantics → _workspace_guide.md (ADR-281); governance files → the wake
    envelope's own labeled headers (the model reads its own message). See
    docs/evaluations/2026-05-29-persona-frame-collapse-ablation.md.

    ADR-314 (2026-06-02): the principal-shift INDEXES the operator's intent
    ("read your governing files; act on what they declare") — it never ASSERTS
    that intent exists ("the operator already told you what to do" — deleted).
    Index-not-assert makes the same frame coherent across states without a
    substrate-conditional branch: present headers direct behavior; absent
    headers are reasoned about honestly.

    ADR-383 (2026-06-29): the two-order re-carve. The systemic self-model is the
    STEWARD (the system agent / Freddie), not "the operator's installed
    judgment" — under the two-order collapse (FOUNDATIONS DP33) judgment is the
    program-activated role (the persona agent), while the systemic occupant of a
    bare workspace is the steward whose MANDATE is stewardship. The Variant-F
    sentence (DP21) survives as the SEAT's structure (occupant-agnostic — true
    of steward and judgment alike); the frame's self-model leads steward and
    routes to judgment via the MANDATE/principles.md the envelope renders. The
    capital-judgment posture (standing-obligation, aperture/floor, capital-EV)
    is REMOVED from the frame — it is each agent's `principles.md`'s content
    (already present in the alpha-trader/alpha-author bundles, migrated there by
    the 2026-05-29 collapse); the frame keeps only the rung-agnostic pointer
    ("apply what your principles.md declares about what you owe"). Per ADR-383 §4
    every agent's MANDATE is populated (steward default for the bare workspace),
    so the frame reasons from a present MANDATE rather than an absent one.

    ADR-397 (2026-07-02, Rung 2): the wake LITURGY (situation-not-task
    forward reasoning + verdict-taxonomy/standing_intent/reflection close
    pedagogy) moved OUT of this cached frame into the `reactive` trigger
    framing — it is the unattended-cycle discipline, and prompting it on
    every addressed chat turn produced the measured ceremony tax (Rung-0
    baseline). ReturnVerdict remains the uniform close on every trigger
    (ADR-360); the addressed framing carries its own one-line close."""
    return """\
**What you are (FOUNDATIONS Derived Principle 21):**

You are this workspace's installed agent — the operator's, acting on their
behalf while they are away, NOT an assistant awaiting instruction. Structurally
you are a full-substrate-authoring persona-bearing judgment seat —
filesystem-native, single-lane queue-serialized, wake-fired, paced by
operator-declared pace + autonomy, driven by operator-authored mandate. That
structure is the same whatever you are doing; what your MANDATE declares is what
sets your purpose.

Read your MANDATE to know which you are. When it declares **stewardship of this
workspace's substrate** — keeping the files, context, attributions, intake, and
connections coherent, well-placed, and legible — you are the **system agent**:
you tend the substrate, you do not move capital or send irreversible messages.
When a program has declared an **operation** (a mandate with a value-moving
primary action) and your `principles.md` carries that operation's judgment
rules, you reason and judge against it as that operation's installed judgment.
Either way the move is the same: act from what your governing files declare.

Your governing files are pre-loaded in the message below, each under its own
labeled header. They are authoritative; read them there. This prompt does not
restate them — it tells you only who you are and how you act.

You decide and direct from what your governing files declare — you do not ask
the operator what to do. (Asking is governed by the witness dial, not your
discretion: under `autonomous` it is unavailable except to surface a structural
gap only the operator can close; the runtime enforces this — ADR-352.) When a
header is present, act on its content. When a header
is absent or empty, reason honestly about that absence rather than inventing
intent. Embody your IDENTITY.md; speak first person as that character. If
IDENTITY.md is empty, reason as a careful, independent steward.

**Read fresh substrate; never reason from cached memory.** Each file's current
content is in the envelope below. When the envelope carries a file, read it
from the message — do not ask whether it exists, and do not reason from a
remembered earlier state when the envelope shows current content. Your
`principles.md` (in the envelope) is your rulebook; apply every rule it declares.

**How you act (FOUNDATIONS Axiom 1 §4 + Axiom 2):**
You act by *making a tool call*. A tool call IS your action — there is no
separate "you perform a write and then watch a gate intercept it" step. When
you call a tool, that call is your directing intent; the runtime executes it
and the *result comes back to you as the tool result*. You direct; the
substrate revision is the channel; the next wake reads what this wake wrote.
You are the judgment that decides and directs — the runtime is the hands that
execute. The AUTONOMY ceiling is code-enforced — you cannot bind a
consequential action beyond it regardless of what you write; reason on the
merits before that filter, and let the tool result tell you what bound. (As the
system agent over reversible substrate there is no consequential external write
to bind — the ceiling has nothing to bite on; it binds only once an operation's
value-moving action is in play.) Your write boundary
is topological (ADR-320): you may author everything EXCEPT two roots —
`governance/` (the ceilings you run under but cannot set) and `system/`
(orchestration's runtime state). Everything in `constitution/`, `persona/`,
and `operation/` is yours; the gate decides by the path's root, not a list.

**Close the turn by calling ReturnVerdict** — its reasoning is your report,
first person, leading with what you did. A turn without a ReturnVerdict
records as unanswered. (This is the interface contract; what a verdict means
per trigger is your envelope's business.)

**Anti-confabulation rule (load-bearing).** Describe only what your tool
calls actually returned. If you did not call a tool, do not narrate its
outcome. Do not say "I attempted the write" / "it was gated" / "it queued as
a proposal" unless a tool call actually returned that. If a call returned an
error or a lock, report *that*. The substrate record (revision chain,
action_proposals) is the truth; your narration must match it exactly. A tidy
"I tried X and the gate caught it" story that no tool call produced is a
fabrication, not a report.

**Narrate in first person, and write for the operator — someone who never read
your files and didn't watch you work, picking it up cold.** This governs your
narration AND every document you leave behind. Three rules, each with the
failure it fixes:
- Lead with the takeaway, not your process. NOT "I read the workspace state: 36
  days post-bootstrap, full framework, zero corpus" → "There's nothing to review
  yet — no pieces written, everything set up and ready."
- Expand or drop codenames. The operator doesn't know `corpus-coherence-check`
  or `cadence-drift` → "the scheduled checks run on time but have nothing to look
  at."
- Flowing sentences read once. NOT "recurrences firing and failing on empty
  substrate" → "the checks run on schedule but have nothing to review yet."
Your reasoning keeps its vocabulary; what you write for the operator does not.

**Cite your sources so the operator can trace your reasoning.** When a MANDATE
clause is the authority your verdict rests on, name it ("per the MANDATE's
anti-slop floor, I'm deferring"). When a claim rests on something you perceived,
cite the observation's `source_ref` (the real external origin — a repo path,
URL, channel), not the workspace file holding the distilled copy and not
`authored_by`. A claim with no resolvable source does not ship."""


# Section registry — ADR-302 D5 declarative ordering + D6 boundary marker.
# All sections below are cached (static across wakes within a deploy).
# Future per-wake content (e.g., operating-context block currently injected
# via _build_user_message) would land below the boundary marker using
# DANGEROUS_uncached_persona_frame_section.
from agents.freddie_agent_sections import (  # noqa: E402
    PersonaFrameSection,
    persona_frame_section,
    resolve_persona_frame_sections,
)

_PERSONA_FRAME_SECTIONS: list[PersonaFrameSection] = [
    # --- Static content (cached across wakes within a deploy) ---
    # MINIMAL frame (persona-frame collapse 2026-05-29): ONE section carrying
    # the two irreducible things — principal-shift (corrects the model's
    # assistant prior) + action-grammar (agent↔runtime interface contract).
    # Rules-of-judgment live in principles.md (envelope-rendered every wake);
    # substrate pedagogy in _workspace_guide.md (ADR-281); governance files in
    # the envelope's own labeled headers. The frame narrates none of those —
    # that is the anti-rebloat constraint (FOUNDATIONS Derived Principle).
    # See docs/evaluations/2026-05-29-persona-frame-collapse-ablation.md.
    persona_frame_section("minimal_frame", _compute_minimal_frame),
    # === BOUNDARY MARKER (ADR-302 D6) - DO NOT MOVE OR REMOVE ===
    # All sections above are cached (cache_break=False) and stable across
    # wakes. All sections below (when added) MUST use
    # DANGEROUS_uncached_persona_frame_section with a documented reason —
    # they recompute per wake and bust the prompt cache. Currently empty;
    # per-wake content lives in _build_user_message (operating-context
    # block per ADR-274), which is its own envelope, not the persona-frame.
]


# _TRIGGER_FRAMING DELETED (ADR-400): per-trigger coaching retired. The
# close CONTRACT lives in the minimal frame (DP22, Rung-3 finding); the
# per-trigger INTERFACE rules (verdict-early on proposals, one-WriteFile
# for long documents) live in the ask branches of _ask_for_trigger.


# Composed once at module import; refreshes on deploy when canonical sources change.
def _build_system_prompt() -> list[dict]:
    """Compose the Reviewer system prompt as cache-marked content blocks.

    The frame + cockpit-awareness section are static across every Reviewer
    wake within a deploy — marking them ephemeral lets Anthropic's prompt
    cache short-circuit re-billing on every round of every Reviewer loop.
    Without cache markers each Reviewer wake re-bills 15-23K input tokens
    of system prompt; with them, rounds 2..N (and subsequent waves within
    the cache TTL) pay ~10% of base input rate.

    ADR-171/172 pricing model assumes caching is firing — the user-facing
    2× markup is computed against full input rate, the cache discount
    accrues as platform margin. Same shape as the dispatch_specialist fix
    in commit cf5bb69. ADR-258 D5 (cockpit awareness drift-resistance) is
    preserved: section is still generated from path constants + primitive
    registry, just wrapped in a content-block with cache_control.
    """
    from agents.cockpit_awareness import build_cockpit_section
    # ADR-302 Phase 2: persona-frame resolved from the typed section
    # registry. Duplicate section names raise ValueError at resolve time
    # (singular-implementation discipline enforced structurally per ADR-302
    # D1). Sections in _PERSONA_FRAME_SECTIONS are all cached (cache_break=
    # False); future per-wake content lives below the boundary marker via
    # DANGEROUS_uncached_persona_frame_section.
    persona_body = resolve_persona_frame_sections(_PERSONA_FRAME_SECTIONS)
    body = "\n\n".join([persona_body, build_cockpit_section()])
    return [
        {
            "type": "text",
            "text": body,
            "cache_control": {"type": "ephemeral"},
        }
    ]


_SYSTEM_PROMPT_CACHE: list[dict] | None = None


def _system_prompt() -> list[dict]:
    """Lazy-cached system prompt (composed once per process)."""
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        _SYSTEM_PROMPT_CACHE = _build_system_prompt()
    return _SYSTEM_PROMPT_CACHE


# ---------------------------------------------------------------------------
# User message builder — trigger-specific pre-loaded substrate
# ---------------------------------------------------------------------------

def _ask_for_trigger(trigger: str, ctx: FreddieContext) -> str:
    """Extract THE ASK (the user-message-analogue) for a given trigger shape.

    ENVELOPE COLLAPSE (the-envelope-collapse-2026-06-24.md): the ask is the
    one part of the CC turn that is the user message. For Arm B it is delivered
    bare — no _TRIGGER_FRAMING coaching wrapped around it. The ask-shaped wake
    (ADR-360) already made the imperative the ask; the framing was the prosthetic.
    """
    import json as _json
    parts: list[str] = []
    if trigger == "reactive":
        if ctx.get("recurrence_prompt") or ctx.get("recurrence_slug"):
            slug = ctx.get("recurrence_slug")
            if slug:
                parts += [f"## Recurrence: `{slug}`", ""]
            prompt_text = (ctx.get("recurrence_prompt") or "").strip()
            if prompt_text:
                parts += ["## The ask", "", prompt_text, ""]
            rrc = ctx.get("recurrence_required_capabilities") or []
            if rrc and isinstance(rrc, list):
                parts += [
                    f"_Required specialist capabilities if you dispatch: "
                    f"`{', '.join(rrc)}`._", "",
                ]
            # ADR-400: round-budget interface rule for document-producing
            # recurrences (audits, reports).
            parts += [
                "_If this prompt directs a long structured document: compose "
                "it whole, write it with ONE WriteFile (always include "
                "`content`), then close with ONE ReturnVerdict carrying a "
                "one-line headline — never the full document._", "",
            ]
        else:
            row = ctx.get("proposal_row") or {}
            if row:
                parts += [
                    "## Proposed action (judge this)",
                    "",
                    f"**action_type:** `{row.get('action_type', '?')}`",
                    f"**reversibility:** {row.get('reversibility', '?')}",
                ]
                if row.get("rationale"):
                    parts.append(f"**rationale:** {row['rationale']}")
                if row.get("expected_effect"):
                    parts.append(f"**expected_effect:** {row['expected_effect']}")
                inputs = row.get("inputs") or {}
                parts += [
                    "**inputs:**", "```json",
                    _json.dumps(inputs, indent=2, default=str), "```", "",
                    # ADR-400: round-budget interface rule (proposal wakes run
                    # a short budget — the ADR-294 mid-write truncation class).
                    "_Call ReturnVerdict with approve | reject | defer + "
                    "reasoning EARLY — before any substrate writes; the round "
                    "budget on proposal wakes is short._", "",
                ]
    elif trigger == "addressed":
        if ctx.get("conversation_window"):
            parts += ["## Recent conversation", "", ctx["conversation_window"], ""]
        msg = (ctx.get("user_message") or "").strip()
        parts += ["## The ask (operator message)", "", msg, ""]
        # ADR-398 D2: the operator locator — where they are writing from.
        # One situational line; shell-composed, opaque here.
        locator = (ctx.get("operator_locator") or "").strip()
        if locator:
            parts += [f"_The operator is writing from: {locator}_", ""]
    return "\n".join(parts)


def _governance_prefix(ctx: FreddieContext) -> str:
    """The cacheable governance block — the CLAUDE.md-analogue (ADR-400).

    The authored governing files, verbatim under labeled headers. Stable
    across wakes; its bytes change only when a governing file is revised,
    which is exactly what lets the prompt cache key on it.
    """
    parts: list[str] = [
        "## IDENTITY.md — Your persona", "",
        ctx.get("identity_md") or "_(empty — reason as a neutral skeptical judgment seat)_", "",
        "## principles.md — Your framework (your rulebook; apply every rule)", "",
        ctx.get("principles_md") or "_(empty — no declared framework)_", "",
    ]
    if ctx.get("precedent_md"):
        parts += ["## PRECEDENT.md — Operator's durable interpretations (overrides principles)", "", ctx["precedent_md"], ""]
    if ctx.get("mandate_md"):
        parts += ["## MANDATE.md — Operation's primary intent", "", ctx["mandate_md"], ""]
    if ctx.get("autonomy_md"):
        parts += ["## AUTONOMY.md — Delegation ceiling", "", ctx["autonomy_md"], ""]
    if ctx.get("budget_yaml"):
        parts += ["## _budget.yaml — Spend envelope (allocate wakes within it)", "", ctx["budget_yaml"], ""]
    if ctx.get("expected_output_yaml"):
        parts += ["## _expected_output.yaml — Output contract (what you owe; floor-gated cadence, NOT a quota)", "", ctx["expected_output_yaml"], ""]
    if ctx.get("preferences_yaml"):
        parts += ["## _preferences.yaml — Operator cadence preferences", "", ctx["preferences_yaml"], ""]
    if ctx.get("occupant_md"):
        parts += ["## OCCUPANT.md — Your current seat", "", ctx["occupant_md"], ""]
    # Governing domain constants (program-shaped, declared strategy + floors).
    if ctx.get("operator_profile_md"):
        parts += ["## _operator_profile.md — Declared strategy", "", ctx["operator_profile_md"], ""]
    if ctx.get("risk_md"):
        parts += ["## _risk.md — Hard floors", "", ctx["risk_md"], ""]
    return "\n".join(parts)


def _volatile_suffix(trigger: str, ctx: FreddieContext) -> str:
    """The per-wake suffix (ADR-400): operating-context (clock) + wake-context
    + standing-intent + substrate snapshot (heads, never bodies) + THE ASK.
    Changes every wake — sits AFTER the governance cache breakpoint by
    construction. Everything else is read on demand from authored substrate.
    """
    from services.substrate_snapshot import build_substrate_snapshot

    parts: list[str] = []
    op_ctx = ctx.get("operating_context_block")
    if op_ctx:
        parts += [op_ctx, ""]
    wake_source = ctx.get("wake_source")
    if wake_source:
        wl = ["## Wake context", "", f"- wake_source: {wake_source}"]
        if ctx.get("triggering_path"):
            wl.append(f"- triggering_path: {ctx['triggering_path']}")
        if ctx.get("triggering_revision_id"):
            wl.append(f"- triggering_revision_id: {ctx['triggering_revision_id']}")
        parts += wl + [""]
    # ADR-284: standing intent has a substrate home; the envelope renders it
    # every wake (the agent's own forward working state).
    si = ctx.get("standing_intent_md")
    if si:
        parts += ["## persona/standing_intent.md — What you were watching for last cycle", "", si, ""]
    else:
        parts += ["## persona/standing_intent.md — (empty — first cycle, author it as part of this judgment)", ""]
    snapshot = build_substrate_snapshot(
        ctx.get("_snapshot_client"),
        ctx.get("_snapshot_user_id") or "",
        since_iso=ctx.get("_snapshot_since_iso"),
        schedule_index_md=ctx.get("schedule_index_md") or "",
        recent_execution_md=ctx.get("recent_execution_md") or "",
        calibration_md=ctx.get("calibration_md") or "",
        ground_truth_md=ctx.get("ground_truth_md") or "",
    ) if ctx.get("_snapshot_client") else ""
    if snapshot:
        parts += [snapshot, ""]
    # Kernel perception facts — RETAINED per ADR-400 §correction: the ADR-390
    # commons surface (the validated attribution catch-fix, leads verbatim) +
    # the ADR-364 reflection gap are ratified, gate-covered arcs. Each is
    # empty-graceful (silent on a quiet workspace), so the bare-steward
    # envelope matches the measured Arm-B shape.
    _commons_parts = [
        ("principal_commons_fact",
         "**Principals — who may write, the referent for every attribution.** A "
         "PRINCIPAL is an intent-bearing, grant-backed identity that attributes as "
         "itself (the human operator writes as `operator`; a foreign LLM as "
         "`yarnnn:mcp:…`). Check every stamp below against this roster: AI-voiced "
         "content stamped `operator` IS a violation — the `operator` principal is "
         "a specific human and this is not their writing."),
        ("attribution_fact",
         "**Recent revisions and who authored them.** For each line, read the "
         "file's content against its `authored_by` AND against the roster above. "
         "Voice that doesn't match the stamp (an external LLM's voice stamped "
         "`operator`) is an attribution-integrity violation — fix where you "
         "authored it, flag where another principal did. A raw `remember`/inbound "
         "dump with no deriving revision is an intake-placement situation."),
        ("peripheral_field_fact",
         "**Perimeter health (peripherals).** Connections and sources are "
         "driver-class transports with no intent — you tend their HEALTH (live? "
         "current?), not their honesty. Their `system:` attribution is honest by "
         "construction, NEVER a violation. Surface a transport gone dark if your "
         "mandate depends on it."),
    ]
    _present = [(k, lead) for (k, lead) in _commons_parts if ctx.get(k)]
    if _present:
        parts += ["## The commons — who writes here, is it honest, is the perimeter sound", ""]
        for key, lead in _present:
            parts += [lead, "", ctx[key], ""]
    if ctx.get("reflection_gap_fact"):
        parts += ["## Reflection gap-fact (a closed intent→outcome loop to learn from)", "", ctx["reflection_gap_fact"], ""]
    if ctx.get("specs_inventory"):
        parts += ["## Specs inventory (discovery surface — read spec bodies on demand)", "", ctx["specs_inventory"], ""]
    # ADR-281 D2 / ADR-336: program-DECLARED wake-envelope substrate renders
    # generically — the bundle ABI is the program's ratified prerogative; the
    # kernel is thin, a program may declare what its judgment needs.
    for key in ctx.get("_program_envelope_keys") or []:
        if key in ("operator_profile_md", "risk_md", "ground_truth_md"):
            continue  # bespoke homes: governance prefix / snapshot head
        val = ctx.get(key)
        if val and isinstance(val, str) and val.strip():
            parts += [f"## {key} (program-declared substrate)", "", val, ""]
    parts += [_ask_for_trigger(trigger, ctx)]
    return "\n".join(parts)


def _build_user_message_content(trigger: str, ctx: FreddieContext) -> list[dict]:
    """THE envelope builder (ADR-400) — the thin CC-shape as cache-marked blocks.

      [0] governance prefix — cache_control: ephemeral. Bytes change only on a
          governing-file revision; rounds 2..N of every wake AND subsequent
          wakes within the TTL pay ~10% of base input rate on it.
      [1] volatile suffix — clock + wake-context + standing-intent + snapshot
          + the ask. Changes every wake; sits after the breakpoint.

    The fat partitioned envelope, the Arm A/B probe toggle, the per-trigger
    framing, and the fact sections are DELETED (ADR-400 deletion inventory).
    Evidence the thin shape holds on the weak model:
    docs/evaluations/2026-07-02-freddie-envelope-rung3-armB-v2/.
    """
    governance = _governance_prefix(ctx)
    volatile = _volatile_suffix(trigger, ctx)
    blocks: list[dict] = []
    if governance.strip():
        blocks.append({
            "type": "text",
            "text": governance,
            "cache_control": {"type": "ephemeral"},
        })
    blocks.append({"type": "text", "text": volatile})
    return blocks


def _build_user_message(trigger: str, ctx: FreddieContext) -> str:
    """String form of the same envelope (probe harnesses + logging)."""
    governance = _governance_prefix(ctx)
    volatile = _volatile_suffix(trigger, ctx)
    if governance.strip():
        return f"{governance}\n{volatile}"
    return volatile


# ---------------------------------------------------------------------------
# Context shape validation (2026-05-13 — Problem B fix)
# ---------------------------------------------------------------------------

def _validate_context_shape(
    trigger: str, context: Any, user_id: str
) -> str | None:
    """Validate that the context bag matches one of three valid shapes.

    Returns None when valid; returns a short reason string when invalid.
    Callers (i.e., invoke_freddie) log the reason and return None instead
    of waking the Reviewer with an empty user message.

    Why this exists. Python dicts are stringly-typed; the dispatcher and
    the Reviewer historically named the same data with different keys
    (commit e55d201 fixed `prompt`/`slug` vs `recurrence_prompt`/`recurrence_slug`
    mismatch). The bug surfaced because nothing asserted the shape —
    the model was forgiving, fires logged, costs accrued, the system
    looked healthy from the audit-log layer. This validator fails loudly
    on shape violation so the next instance of the same bug class
    surfaces immediately.

    The three valid shapes are derived from the three trigger sub-shapes
    `_build_user_message` knows how to construct:

      1. proposal-arrival (trigger="reactive"):
         REQUIRES proposal_row to be a non-empty dict.
      2. recurrence-fire (trigger="reactive"):
         REQUIRES BOTH recurrence_prompt (non-empty str) AND
         recurrence_slug (non-empty str).
      3. addressed (trigger="addressed"):
         REQUIRES user_message (non-empty str).

    A context that satisfies neither (1) nor (2) when trigger=reactive,
    or doesn't satisfy (3) when trigger=addressed, is rejected.
    """
    if not isinstance(context, dict):
        return f"context must be a dict, got {type(context).__name__}"

    if trigger == "reactive":
        # Shape 1: proposal-arrival
        proposal_row = context.get("proposal_row")
        has_proposal = isinstance(proposal_row, dict) and bool(proposal_row)
        # Shape 2: recurrence-fire
        rec_prompt = context.get("recurrence_prompt")
        rec_slug = context.get("recurrence_slug")
        has_recurrence = (
            isinstance(rec_prompt, str) and bool(rec_prompt.strip())
            and isinstance(rec_slug, str) and bool(rec_slug.strip())
        )

        if has_proposal and has_recurrence:
            return (
                "ambiguous reactive context: both proposal_row and "
                "recurrence_prompt/recurrence_slug present. Callers must "
                "choose exactly one sub-shape."
            )
        if not has_proposal and not has_recurrence:
            return (
                "reactive trigger requires either proposal_row (proposal-"
                "arrival) or recurrence_prompt+recurrence_slug (recurrence-"
                f"fire). Got context keys: {sorted(context.keys())}"
            )
        return None

    if trigger == "addressed":
        msg = context.get("user_message")
        if not (isinstance(msg, str) and msg.strip()):
            return (
                "addressed trigger requires non-empty user_message. "
                f"Got context keys: {sorted(context.keys())}"
            )
        return None

    return f"unknown trigger value: {trigger!r}"


# ---------------------------------------------------------------------------
# Public entry point — invoke_freddie (ADR-258)
# ---------------------------------------------------------------------------

async def invoke_freddie(
    client: Any,
    user_id: str,
    *,
    trigger: Literal["addressed", "reactive"],
    context: FreddieContext,
    invocation_id: str,
    event_callback: Any = None,
) -> FreddieOutput | None:
    """Unified Reviewer invocation — ADR-258 (revised) + ADR-260 D2 + ADR-263.

    Reviewer is a chat-mode caller of the canonical primitive registry.
    Tool surface = curated FREDDIE_PRIMITIVES + ReturnVerdict. Tool-use loop
    bounded at 12 rounds for addressed, 3 for reactive (ADR-260 D8).

    Safety story (ADR-293): attribution (ADR-209 authored substrate) +
    revision chain + uniform AUTONOMY-mode gating (capital + substrate via
    should_auto_apply) + root-based governance lock (the governance/ root —
    AUTONOMY.md / _autonomy.yaml / _budget.yaml / _preferences.yaml — paths
    the Reviewer cannot author because editing them would grant the Reviewer
    unauthorized authority). Not access control; not blanket lock. Everything
    else operational + revertable.

    Two triggers (ADR-260 D2 amended by ADR-263 D2):
    - `addressed` — operator addressed the Reviewer (chat turn).
    - `reactive`  — substrate event requires judgment. Two sub-shapes,
                    differentiated by context-bag contents:
                      • Proposal arrival (proposal_row in context).
                      • Judgment-mode recurrence fire (recurrence_prompt in context;
                        per ADR-263, mechanical-mode recurrences do NOT invoke
                        the Reviewer — they execute deterministic primitives).

    Cron is part of the environment that fires recurrences; the recurrence's
    `mode` field declares whether the fire wakes the Reviewer (judgment) or
    runs as deterministic Python (mechanical). The Reviewer never sees the
    `scheduled` trigger value because cron-fired Reviewer wakes are now
    `reactive` (ADR-263 D2 amendment).

    Model selection by trigger:
    - Sonnet (capital decisions): reactive proposals
    - Haiku  (reasoning):         addressed + reactive recurrences

    Optional `event_callback`: an async callable `(event_dict) -> None` that
    fires progressively as the loop advances — once per round_start, once
    per tool_call, once per round_end. Used by chat.py to stream live
    progress to the operator (so the UI doesn't go silent during the loop).

    Never raises. Returns None on total failure.
    """
    # Contract enforcement (2026-05-13 — Problem B fix).
    # The dispatcher↔Reviewer key-drift bug (commit e55d201) lived for days
    # because nothing asserted the context shape — silent fallback turned a
    # malformed call into an inert stand_down. Reject malformed shapes
    # loudly at the boundary instead of waking the LLM with an empty
    # user message and burning tokens to produce a useless verdict.
    shape_error = _validate_context_shape(trigger, context, user_id)
    if shape_error:
        logger.error(
            "[REVIEWER] context shape violation user=%s trigger=%s: %s",
            user_id[:8] if user_id else "?", trigger, shape_error,
        )
        return None

    from services.primitives.registry import FREDDIE_PRIMITIVES, execute_primitive
    from types import SimpleNamespace

    # ADR-402: model + round-ceiling selection is kernel data — the routing
    # table in services/model_routing.py (single model-selection site,
    # env-overridable per deployment). Shape key: addressed | proposal |
    # recurrence. Sub-shape detection mirrors the pattern in
    # `_build_user_message`: presence of `recurrence_prompt`/`recurrence_slug`
    # keys = recurrence fire.
    is_recurrence_fire = bool(
        context.get("recurrence_prompt") or context.get("recurrence_slug")
    ) if isinstance(context, dict) else False

    route = resolve_route(trigger, is_recurrence_fire)
    model = route.model

    # Build auth namespace with freddie_caller flag — handlers consult this
    # for ADR-258 D9 lock enforcement on operator-shared substrate.
    # `recurrence_options` carries the recurrence YAML's `options` block
    # (whatever the operator declared) through to downstream primitives.
    # Specifically `handle_dispatch_specialist` reads `max_rounds` from
    # here to honor per-recurrence round budgets (heavy work like
    # falsify-signals or 5-ticker track-universe needs > the global
    # default of 5).
    recurrence_options = {}
    if isinstance(context, dict):
        raw = context.get("options")
        if isinstance(raw, dict):
            recurrence_options = raw
    # ADR-288 D1: caller_identity is the canonical attribution source for
    # every substrate write made during this Reviewer wake. The Schedule
    # primitive's per-call injection at the dispatch loop (pre-ADR-288) is
    # superseded — substrate primitives default authored_by from
    # auth.caller_identity (ADR-288 D2). freddie_caller=True is preserved
    # for ADR-258 D9 lock enforcement (separate concern: locks read paths
    # against the caller-class flag, not the attribution string).
    auth = SimpleNamespace(
        client=client,
        user_id=user_id,
        caller_identity=f"freddie:{FREDDIE_MODEL_IDENTITY}",
        freddie_caller=True,
        agent=None,
        agent_slug=None,
        task_slug=None,
        recurrence_options=recurrence_options,
    )

    # Tool list = curated reviewer primitives + ReturnVerdict (ADR-258 revised)
    tools = list(FREDDIE_PRIMITIVES) + [RETURN_VERDICT_TOOL]

    async def _emit(event: dict) -> None:
        """Best-effort progress emit — never raises, never blocks the loop.
        Callers can inspect events to surface progress in the UI without
        blocking the LLM cycle."""
        if event_callback is None:
            return
        try:
            await event_callback(event)
        except Exception as cb_exc:
            logger.debug("[REVIEWER] event_callback raised: %s", cb_exc)

    try:
        # ADR-400: the substrate snapshot is a first-class envelope input —
        # the collapse landed; the Arm A/B toggle is deleted.
        if isinstance(context, dict):
            context.setdefault("_snapshot_client", client)
            context.setdefault("_snapshot_user_id", user_id)
        user_message: str | list[dict] = _build_user_message_content(trigger, context)
        messages: list[dict] = [{"role": "user", "content": user_message}]
        actions_taken: list[dict] = []
        verdict_raw: dict | None = None
        # ADR-360 Stage 4: the verdict-in-prose recovery nudge + silent-exit
        # synthesizer are deleted. A no-tool-call round breaks to the honest
        # terminal (return None → caller records `failed`); `verdict_raw` is only
        # ever set by a real model-authored ReturnVerdict now.

        # ADR-402: the round ceiling comes from the routing table alongside the
        # model — a COST CEILING, not a behavioral constraint (trust-the-model:
        # the model decides when it's done via ReturnVerdict; the budget caps
        # cost-per-wake). Per-shape values + their population-audit history
        # live with the table in services/model_routing.py. The fallback below
        # (verdict_raw is None) is the safety net for the rare case the model
        # truly can't synthesize within budget.
        max_rounds = route.max_rounds

        # ADR-363 D3 (PROBE-GATED): context-editing for the within-wake tool-loop.
        # Off by default — gated on YARNNN_CONTEXT_EDIT so the cross-wake floor is
        # never assumed-on before a funded measurement proves it relieves the
        # max_rounds ceiling (verdict=None / truncation) OR gives equal behavior at
        # lower cost. The two probe variables are tunable by env (defaults match the
        # safety analysis, NOT the API defaults):
        #   - TRIGGER (YARNNN_CONTEXT_EDIT_TRIGGER, default 24000): the API default
        #     of 100k would never fire on a wake whose governance prefix is ~16k +
        #     a bounded loop — exactly the wakes D3 targets. 24k fires once the loop
        #     has accumulated meaningful tool-result bloat past the governance block.
        #   - KEEP (YARNNN_CONTEXT_EDIT_KEEP, default 6): retain the N most-recent
        #     tool_use/result pairs. The read-heavy pattern (pre-ship-audit reads 8+
        #     files before writing) means keep:3 (the API default) could evaporate
        #     file contents the verdict still rests on; 6 is the conservative start.
        # Pure within-call prune — the durable record is the substrate the agent
        # already wrote (ADR-209), untouched. Moat-neutral by construction.
        # (import was owned by the deleted Arm-B toggle block — ADR-400)
        import os as _os_probe
        _ctx_edit: dict | None = None
        if _os_probe.environ.get("YARNNN_CONTEXT_EDIT", "").strip().lower() in ("1", "true", "on"):
            try:
                _ce_trigger = int(_os_probe.environ.get("YARNNN_CONTEXT_EDIT_TRIGGER", "24000"))
            except ValueError:
                _ce_trigger = 24000
            try:
                _ce_keep = int(_os_probe.environ.get("YARNNN_CONTEXT_EDIT_KEEP", "6"))
            except ValueError:
                _ce_keep = 6
            _ctx_edit = {
                "edits": [{
                    "type": "clear_tool_uses_20250919",
                    "trigger": {"type": "input_tokens", "value": _ce_trigger},
                    "keep": {"type": "tool_uses", "value": _ce_keep},
                }]
            }
            logger.info(
                "[REVIEWER] ADR-363 D3 context-editing ON trigger=%d keep=%d trigger_kind=%s user=%s",
                _ce_trigger, _ce_keep, trigger, user_id[:8],
            )

        total_input = 0
        total_output = 0
        total_cache_read = 0
        total_cache_create = 0
        rounds_used = 0

        for _round in range(max_rounds):
            rounds_used = _round + 1
            # Commit H (2026-05-11): cooperative cancellation check between
            # rounds. When the operator clicks Stop in the feed composer,
            # the FE POSTs /api/feed/cancel which sets
            # chat_sessions.cancellation_requested=true on the workspace's
            # active session. We check it here at the top of every round
            # (not inside a single LLM call — that's not interruptible).
            # On cancel: exit early with stand_down verdict; the caller
            # then resets the flag for the next session.
            if _check_session_cancellation(client, user_id):
                # This is a DISTINCT stand_down — the operator pressed Stop, an
                # explicit operator-authored close. It is NOT the inaction-default
                # recovery net that ADR-360 Stage 4 deleted (a silent no-tool-call
                # exit now returns None → recorded `failed`, the honest-unanswered
                # path). Operator-Stop is a real, intended stand_down and survives.
                # Kept inline (not extracted) because it reads 8 loop-local
                # accumulators; a module-level helper would need all 8 as params.
                logger.info(
                    "[REVIEWER] cancellation_requested honored at round %d/%d trigger=%s user=%s",
                    rounds_used, max_rounds, trigger, user_id[:8],
                )
                _clear_session_cancellation(client, user_id)
                return FreddieOutput(
                    verdict="stand_down",
                    reasoning="Operator interrupted the in-flight Loop via the Stop affordance. No further actions taken in this session.",
                    confidence="high",
                    actions_taken=actions_taken,
                    invocation_id=invocation_id,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    cache_read_tokens=total_cache_read,
                    cache_create_tokens=total_cache_create,
                    model=model,
                    tool_rounds=rounds_used,
                )
            tool_choice = {"type": "any"} if _round == 0 else {"type": "auto"}
            await _emit({"phase": "round_start", "round": rounds_used, "trigger": trigger})

            # 8192 (raised from 2048, 2026-06-11): composed deliverables
            # (weekly-performance-review output.md, _signal.md rollups) are
            # 5-10KB of markdown — JSON-escaped tool input for a single
            # WriteFile regularly exceeded 2048 output tokens, truncating the
            # call mid-input. max_tokens is a ceiling, not a cost — only
            # generated tokens bill.
            # ADR-351 Phase 1: the addressed trigger (operator chat turn over
            # the SSE-streamed wake) uses the tool-aware STREAMING call so the
            # Reviewer's reasoning reaches the operator token-by-token as it
            # generates — fulfilling ADR-260 §D6 (its streaming half was never
            # built; the blocking call buffered the whole block to cycle-end).
            # reactive/scheduled wakes have no live operator listening and keep
            # the blocking call (ADR-351 §4 + §6 Phase 3 deferral). The
            # returned ChatResponse is identical in both branches, so the
            # downstream loop (truncation guard, usage, tool dispatch) is
            # untouched.
            if trigger == "addressed":
                async def _on_text_delta(chunk: str) -> None:
                    await _emit({
                        "phase": "text_delta",
                        "round": rounds_used,
                        "trigger": trigger,
                        "text": chunk,
                    })

                response = await chat_completion_with_tools_stream(
                    messages=messages,
                    system=_system_prompt(),
                    tools=tools,
                    model=model,
                    max_tokens=8192,
                    tool_choice=tool_choice,
                    on_text_delta=_on_text_delta,
                    context_management=_ctx_edit,  # ADR-363 D3 (probe-gated, None when off)
                )
            else:
                response = await chat_completion_with_tools(
                    messages=messages,
                    system=_system_prompt(),
                    tools=tools,
                    model=model,
                    max_tokens=8192,
                    tool_choice=tool_choice,
                    context_management=_ctx_edit,  # ADR-363 D3 (probe-gated, None when off)
                )

            usage = response.usage or {}
            total_input += int(usage.get("input_tokens", 0) or 0)
            total_output += int(usage.get("output_tokens", 0) or 0)
            # Anthropic native names — same shape as services/anthropic.py
            # surfaces. F1 (2026-05-17): denormalize into execution_events
            # via FreddieOutput so slug-indexed reads see cache discount.
            total_cache_read += int(usage.get("cache_read_input_tokens", 0) or 0)
            total_cache_create += int(usage.get("cache_creation_input_tokens", 0) or 0)

            tool_uses = response.tool_uses or []

            # Truncation guard (2026-06-11): when generation hits the
            # max_tokens ceiling mid-tool-call, the final tool_use block's
            # input is INCOMPLETE — the API salvages partial JSON, so a
            # WriteFile arrives with `path` set and `content` missing.
            # Executing it writes a 0-byte revision over real substrate
            # (observed: weekly-performance-review output.md ×12 empty
            # writes; yarnnn-author _signal.md ground truth wiped to 0
            # bytes on 2026-06-09). The truncated block must NOT execute;
            # the model gets an is_error tool_result instructing it to
            # re-issue in smaller parts.
            response_truncated = getattr(response, "stop_reason", None) == "max_tokens"

            # Append assistant turn for multi-round history
            assistant_content: list[dict] = []
            for block in (response.content or []):
                btype = getattr(block, "type", None)
                if btype == "text":
                    assistant_content.append({"type": "text", "text": getattr(block, "text", "")})
                elif btype == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": getattr(block, "id", ""),
                        "name": getattr(block, "name", ""),
                        "input": getattr(block, "input", {}),
                    })
            if assistant_content:
                messages.append({"role": "assistant", "content": assistant_content})

            if not tool_uses:
                # ADR-360 Stage 4: the silent-exit RECOVERY NET is deleted. A
                # round that yields no tool call means the model did not close
                # with ReturnVerdict. We no longer fabricate a verdict or write a
                # dispatcher-attributed standing_intent to launder that into a
                # clean `stand_down`. `verdict_raw` stays as-is (None unless an
                # earlier ReturnVerdict set it), so the loop falls through to the
                # honest terminal: invoke_freddie returns None, which the caller
                # (wake.py SILENT-WAKE path) records as a visible `failed`
                # execution_event + a material "produced no judgment" narrative.
                # An unanswered ask is visible AS unanswered (ADR-360 DP32) — not
                # masked as a deliberate stand-down. The model's last prose, if
                # any, is preserved in the log line for diagnosis.
                _last_prose = (response.text or "").strip()
                logger.warning(
                    "[REVIEWER] no-tool-call exit round %d/%d trigger=%s user=%s "
                    "(no recovery net — returns None → recorded failed). last_prose=%r",
                    rounds_used, max_rounds, trigger, user_id[:8], _last_prose[:200],
                )
                break

            tool_results: list[dict] = []
            clarify_called_this_round = False
            for _tu_idx, tu in enumerate(tool_uses):
                name = tu.name
                inp = tu.input or {}
                tu_id = tu.id

                # Truncation guard: the FINAL tool_use of a max_tokens-cut
                # response carries incomplete input — never execute it (and
                # never record a truncated ReturnVerdict). Earlier blocks in
                # the same response completed before the cut and run normally.
                if response_truncated and _tu_idx == len(tool_uses) - 1:
                    logger.warning(
                        "[REVIEWER] truncated tool call NOT executed: tool=%s "
                        "trigger=%s user=%s round=%d — max_tokens ceiling hit "
                        "mid-input",
                        name, trigger, user_id[:8], rounds_used,
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu_id,
                        "is_error": True,
                        "content": (
                            f"TRUNCATED — this {name} call hit the output-token "
                            "ceiling mid-generation and was NOT executed (its "
                            "input arrived incomplete). Re-issue it in smaller "
                            "parts: for a large WriteFile, write the file across "
                            "multiple calls using mode='append'."
                        ),
                    })
                    continue

                if name == "ReturnVerdict":
                    verdict_raw = inp
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu_id,
                        "content": "Verdict recorded.",
                    })
                    break

                # Emit tool_start for UI progress before dispatch
                await _emit({
                    "phase": "tool_start",
                    "round": rounds_used,
                    "tool": name,
                    "input": inp,
                })

                # ADR-288 D3: Schedule-specific authored_by injection DELETED.
                # auth.caller_identity (set at construction time per D1)
                # propagates through execute_primitive → Schedule's
                # `authored_by or auth.caller_identity` default-resolution
                # (parallel pattern to handle_write_file ADR-288 D2). One
                # canonical declaration replaces three compensating sites.
                # LLM-supplied authored_by still wins when explicitly passed.

                # Dispatch through canonical primitive registry
                try:
                    result = await execute_primitive(auth, name, inp)
                except Exception as exc:
                    result = {"success": False, "error": "execution_error", "message": str(exc)}

                # Capture proposal_id from ProposeAction results so the
                # downstream narration emit (surface_freddie_actions) can
                # render an inline ProposalCard chip per Audit-pass-2 DD-4.
                # Pre-2026-05-11, narration was plain-text and operators had
                # to mentally stitch from the feed entry to the cockpit Queue
                # to find the proposal — mental-thread broken.
                # ADR-303 D3 (2026-05-26): capture failure_reason on the
                # action record so the visibility-first surfacing layer
                # (services/freddie_chat_surfacing.py::surface_freddie_actions)
                # can apply its denylist (SILENCE_FAILURE_REASONS) without
                # re-parsing the result dict. Primitives uniformly carry
                # `error` keys on failure (see grep across api/services/
                # primitives/); we surface that as `failure_reason` on the
                # action record. `None` when success is True or when
                # the primitive didn't set an error code — both flow to
                # default-surface per the visibility-first invert.
                _success = bool(result.get("success", True)) if isinstance(result, dict) else True
                _failure_reason: Optional[str] = None
                if not _success and isinstance(result, dict):
                    err = result.get("error")
                    if isinstance(err, str) and err.strip():
                        _failure_reason = err.strip()
                action_record: dict = {
                    "tool": name,
                    "input": inp,
                    "success": _success,
                    "failure_reason": _failure_reason,
                    "summary": _summarize_result(result),
                    # ADR-289 D4: stamp the invocation atom id on every
                    # action record. Downstream surfacing (surface_freddie_actions)
                    # reads this to propagate metadata.invocation_id onto every
                    # narrative entry produced during this cycle. One invocation,
                    # one shared id, N grouped narrative rows on the Feed surface.
                    "invocation_id": invocation_id,
                }
                if name == "ProposeAction" and isinstance(result, dict):
                    pid = result.get("proposal_id") or (
                        result.get("proposal", {}) or {}
                    ).get("id")
                    if pid:
                        action_record["proposal_id"] = pid
                actions_taken.append(action_record)

                await _emit({
                    "phase": "tool_end",
                    "round": rounds_used,
                    "tool": name,
                    "input": inp,  # ADR-289 Phase 2a: needed by the live
                                   # narration site in routes/feed.py to
                                   # classify mirror-refresh SyncPlatformState
                                   # calls via is_mirror_refresh_action.
                                   # ADR-296 v2 D3: the FireInvocation branch
                                   # of that classifier dissolved when
                                   # FireInvocation left FREDDIE_PRIMITIVES.
                    "success": actions_taken[-1]["success"],
                    "summary": actions_taken[-1]["summary"],
                })

                # Compact result for the model — limit size
                result_text = _compact_result_for_model(result)
                logger.info(
                    "[REVIEWER] tool=%s trigger=%s user=%s success=%s",
                    name, trigger, user_id[:8],
                    actions_taken[-1]["success"],
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu_id,
                    "content": result_text,
                })

                # ADR-352: only a Clarify the ask-gate ALLOWED surfaces a
                # question and closes the turn. A DENIED Clarify (autonomous,
                # no structural_gap) returned an `ask_denied` result — the loop
                # must NOT treat it as "question surfaced / close now"; it lets
                # the occupant read the deny guidance and act this same wake.
                if name == "Clarify" and actions_taken[-1]["success"]:
                    clarify_called_this_round = True

            if verdict_raw is not None:
                break

            # Loop-shape nudge (signal-based, not counter-based per 2026-05-21
            # population audit docs/evaluations/2026-05-21-014009-reviewer-
            # round-budget-population-audit/):
            #
            # After Clarify the operator's question has been surfaced and the
            # turn should close so the operator can respond. This nudge fires
            # only after the Reviewer has called Clarify in the current round
            # — it's a signal-based stop condition, parallel to Claude Code's
            # "repeated identical action" pattern.
            #
            # The previous round-counter-based nudge (`elif _round >= 4`) was
            # DELETED 2026-05-21 because population data showed it was solving
            # a problem we don't have (zero wakes reached round 11+ in N=28
            # history) while causing the problem we do have (70% silent rate
            # at round 6 due to its "stand_down is correct" invitation). Trust-
            # the-model philosophy: the budget is the cost ceiling, the
            # ReturnVerdict tool is the model's voluntary completion signal,
            # the fallback at `if verdict_raw is None` (line ~1530) is the
            # safety net for the rare in-budget-but-can't-synthesize case.
            nudge: str | None = None
            if clarify_called_this_round:
                nudge = (
                    "Your Clarify question has been surfaced to the operator. "
                    "Now call ReturnVerdict(verdict='stand_down', reasoning='[your "
                    "persona-voice summary including the question you asked]', "
                    "confidence='medium') to close this turn. The operator will "
                    "respond on a subsequent turn."
                )

            if tool_results:
                # Append nudge as a text block alongside tool_result blocks so the
                # model sees it as part of the user turn. tool_use_id cannot be
                # synthesized — must reference a real tool_use block — so the
                # nudge rides as a separate text block in the same user message.
                content_blocks: list[dict] = list(tool_results)
                if nudge:
                    content_blocks.append({"type": "text", "text": nudge})
                messages.append({"role": "user", "content": content_blocks})

        # ADR-291: cost ledger write happens downstream in the dispatcher via
        # `record_execution_event()`, fed by the cost/token fields on
        # `FreddieOutput` (below). Removing the duplicate `token_usage` write
        # collapses the dual-ledger architecture; the dispatcher's slug-indexed
        # `execution_events` row is now the sole authoritative record.

        if verdict_raw is None:
            # ADR-360 Stage 4: budget-exhausted with no ReturnVerdict. The
            # RECOVERY NET is deleted — we no longer fabricate a `stand_down`
            # verdict + dispatcher standing_intent to mask a non-judging wake as
            # a clean close. Return None: the caller (wake.py SILENT-WAKE path)
            # records a visible `failed` execution_event + a material "produced
            # no judgment" narrative. An unanswered ask is visible AS unanswered
            # (ADR-360 DP32). The model's last prose is logged for diagnosis.
            last_text = ""
            for m in reversed(messages):
                if m.get("role") != "assistant":
                    continue
                for block in (m.get("content") or []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        last_text = block.get("text", "")
                        if last_text:
                            break
                if last_text:
                    break
            logger.warning(
                "[REVIEWER] no ReturnVerdict after %d rounds trigger=%s user=%s "
                "(no recovery net — returns None → recorded failed). last_prose=%r",
                max_rounds, trigger, user_id[:8], last_text[:200],
            )
            return None

        verdict = verdict_raw.get("verdict", "")
        reasoning = (verdict_raw.get("reasoning") or "").strip()
        confidence = verdict_raw.get("confidence") or "low"

        _VALID_VERDICTS = {
            "approve", "reject", "defer",
            "no_change", "narrow", "relax", "character_note", "pause_autonomy",
            "stand_down",
        }
        if verdict not in _VALID_VERDICTS:
            logger.warning(
                "[REVIEWER] invalid verdict=%r trigger=%s user=%s", verdict, trigger, user_id[:8],
            )
            return None
        if not reasoning:
            logger.warning(
                "[REVIEWER] empty reasoning trigger=%s user=%s", trigger, user_id[:8],
            )
            return None

        output: FreddieOutput = {
            "verdict": verdict,
            "reasoning": reasoning,
            "confidence": confidence,
            "actions_taken": actions_taken,
            # ADR-289 D4: invocation atom id, propagated from caller, surfaced
            # so the dispatcher can stamp the same id on the verdict-row write
            # (write_freddie_message) and the FE can group every row produced
            # by this cycle under one invocation card.
            "invocation_id": invocation_id,
            # ADR-291: telemetry pass-through (single-ledger). The dispatcher
            # reads these off and forwards into `record_execution_event` — the
            # sole authoritative cost ledger write per the unified-cost-ledger
            # decision (replaces the prior dual write to `token_usage`).
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cache_read_tokens": total_cache_read,
            "cache_create_tokens": total_cache_create,
            "model": model,
            "tool_rounds": rounds_used,
        }

        # Under ADR-263's two-trigger model, reflection-shaped output fields
        # (`proposals`, `evidence_summary`) may appear on any reactive
        # invocation whose recurrence prompt directs the Reviewer to author
        # proposals or summarize evidence. The gate is "model returned the
        # field," not "trigger == reflection" (which is a dead enum value
        # post-collapse). Older callers relying on field-presence to detect
        # reflection-shaped output continue to work.
        if verdict_raw.get("proposals") or verdict_raw.get("evidence_summary"):
            from agents.freddie_agent_compat import _normalize_reflection_proposals
            if verdict_raw.get("proposals"):
                output["proposals"] = _normalize_reflection_proposals(verdict_raw.get("proposals") or [])
            if verdict_raw.get("evidence_summary"):
                output["evidence_summary"] = (verdict_raw.get("evidence_summary") or "").strip()

        return output

    except Exception as exc:
        # SILENT-WAKE diagnosis (2026-06-04): this swallow-to-None is the
        # in-process half of the silent-wake bug — an exception anywhere in the
        # round loop (a malformed _build_user_message, a fast-failing
        # chat_completion_with_tools, a primitive dispatch error) returns None,
        # and the dispatcher (wake.py) now records that as status="failed"
        # rather than the prior status="success". Capture the FULL traceback at
        # error level so the cause is diagnosable from logs — "[REVIEWER]
        # invoke_freddie failed: <one-line>" with no stack was what made every
        # prior silent-wake investigation hit a dead end.
        logger.exception(
            "[REVIEWER] invoke_freddie raised (→ None → dispatcher records "
            "failed) trigger=%s user=%s: %s",
            trigger, user_id[:8] if user_id else "?", exc,
        )
        return None


def _summarize_result(result: Any) -> str:
    """One-line summary of a primitive result for actions_taken audit log.

    Field-preference order is semantic-first: when a result carries multiple
    discriminators, prefer the one that distinguishes this action from a
    sibling action of the same tool.

      1. action + slug     (Schedule / ManageHook — two writes to the same
                            file with distinct recurrence/hook slugs look
                            identical when summarized by path alone)
      2. proposal_id       (ProposeAction — every proposal is a distinct
                            decision; prefer the proposal identity)
      3. slug              (any slug-bearing result without an action
                            verb — e.g. FireInvocation in CHAT_PRIMITIVES
                            per ADR-296 v2 D3, no longer in FREDDIE_PRIMITIVES)
      4. path              (WriteFile etc. — terminal fallback)

    Closes Pattern 3 of docs/evaluations/2026-05-21-005856-wake-duplication-
    audit/findings.md — pre-fix the helper checked `path` first, collapsing
    distinct Schedule calls (weekly-corpus-review vs quarterly-voice-audit)
    to identical `path=/workspace/_recurrences.yaml` summaries that looked
    like duplicate actions in the feed.
    """
    if not isinstance(result, dict):
        return "ok"
    if result.get("success") is False:
        return f"error: {result.get('error') or 'unknown'}"
    # 2026-05-25 Clarify branch (per
    # docs/evaluations/2026-05-25-042827-clarify-silenced-from-feed/):
    # Clarify returns {success, question, options, ui_action}. The
    # question is the operator-facing payload — it becomes the narration
    # body for the Reviewer-bubble Feed entry. Without this branch the
    # helper falls through to "ok" and the question is lost.
    if "question" in result:
        question = (result.get("question") or "").strip()
        options = result.get("options") or []
        if question:
            if options:
                opts_str = ", ".join(str(o) for o in options if o)
                return f"{question} [{opts_str}]"
            return question
    # Slug + action verb together — the strongest discriminator for
    # lifecycle primitives (Schedule / ManageHook). Two distinct slugs
    # at the same path render with distinct summaries.
    if "slug" in result and "action" in result:
        return f"action={result['action']} slug={result['slug']}"
    if "proposal_id" in result:
        return f"proposal_id={result['proposal_id'][:8]}..."
    if "slug" in result:
        return f"slug={result['slug']}"
    if "path" in result:
        return f"path={result['path']}"
    return "ok"


def _compact_result_for_model(result: Any) -> str:
    """Compact a primitive result for tool_result content sent back to the model.
    Limits content size so a large file read doesn't blow the round budget."""
    import json as _json
    if isinstance(result, dict):
        # If there's a 'content' field (from ReadFile), truncate generously
        if "content" in result and isinstance(result["content"], str):
            content = result["content"]
            if len(content) > 6000:
                content = content[:6000] + f"\n\n_(truncated from {len(result['content'])} chars)_"
            shaped = {**result, "content": content}
            return _json.dumps(shaped, default=str)[:8000]
        return _json.dumps(result, default=str)[:8000]
    return str(result)[:8000]


# ---------------------------------------------------------------------------
# Cooperative cancellation (Commit H.1, 2026-05-11)
# ---------------------------------------------------------------------------
#
# Two helpers used by invoke_freddie's per-round cancellation check (Mode 1
# of the interruption surface). The flag lives on chat_sessions
# (migration 173); operator's POST /api/feed/cancel sets it; the Reviewer
# checks + clears it.
#
# Design choice: we look up the operator's *active workspace session* (same
# function freddie_chat_surfacing uses) rather than threading a session_id
# parameter through every Reviewer call site. The Reviewer doesn't know
# which session it's running on behalf of — that's the orchestration
# context. Looking up the active session at check time matches how
# narration emits work too.
#
# Failure discipline: any exception (Supabase blip, no active session, etc.)
# → returns False (no cancellation). Cancellation is best-effort safety,
# never blocks the Loop on errors.

def _check_session_cancellation(client: Any, user_id: str) -> bool:
    """Return True iff the operator's active session has cancellation_requested=true."""
    if not user_id:
        return False
    try:
        from services.narrative import find_active_workspace_session
        session_id = find_active_workspace_session(client, user_id)
        if not session_id:
            return False
        result = (
            client.table("chat_sessions")
            .select("cancellation_requested")
            .eq("id", session_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return False
        return bool(rows[0].get("cancellation_requested", False))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[REVIEWER] cancellation check failed: %s", exc)
        return False


def _clear_session_cancellation(client: Any, user_id: str) -> None:
    """Reset the cancellation flag after honoring it. Best-effort; never raises."""
    if not user_id:
        return
    try:
        from services.narrative import find_active_workspace_session
        session_id = find_active_workspace_session(client, user_id)
        if not session_id:
            return
        client.table("chat_sessions").update(
            {"cancellation_requested": False}
        ).eq("id", session_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[REVIEWER] cancellation clear failed: %s", exc)


# read_signal_files() relocated to services/freddie_envelope.py per ADR-280
# Stream A. The function is kernel-internal envelope-summarizer infrastructure
# — bundles reference it by name in their MANIFEST `substrate_abi.reviewer_wake_envelope`
# declarations; the kernel hosts the implementation. New name + module:
# `services.freddie_envelope.ENVELOPE_SUMMARIZERS["signal_files"]` (a.k.a.
# `_summarize_signal_files`). The relocation makes path_glob parametric so
# the summarizer is no longer alpha-trader-hardcoded; bundles declare their
# own glob (e.g., `operation/trading/signals/*.yaml`).
