"""Orchestration — the capability registry and its gates.

What survives here after ADR-632 (the steward retires) and the 2026-09-12 residue
sweep: `CAPABILITIES` (the capability → platform/tier table read by
`platform_tools`, `bundle_reader` and `storage_backend`), the tier/attestation
helpers (`required_tier`, `capability_available`, `unavailable_capabilities`),
`KERNEL_VERSION` + the four substrate constants `substrate_reapply` still propagates
(`TP_ORCHESTRATION_PLAYBOOK`, `DEFAULT_PRECEDENT_MD`, `DEFAULT_REVIEW_PRINCIPLES_MD`,
`DEFAULT_REVIEW_REFLECTION_MD` — ADR-292), and `DEFAULT_AUTONOMY_YAML` (the one dial
`workspace_init` seeds on the reset paths — ADR-414 D2).

DELETED 2026-09-12 (zero live callers, all describing the retired steward or the
pre-ADR-596 agent model): the role registries (`PRODUCTION_ROLES`, `SYSTEMIC_AGENTS`,
`ALL_ROLES`, `LEGACY_ROLE_MAP`, `resolve_role`, `get_agent_class_and_domain`,
`RUNTIMES`, `has_capability`, `get_type_skill_docs`, `get_type_display`,
`list_agent_types`, `get_agent_domain`) and the steward's kernel-default files
(`DEFAULT_IDENTITY_MD`, `DEFAULT_AWARENESS_MD`, `DEFAULT_REVIEW_IDENTITY_MD`,
`DEFAULT_AUTONOMY_MD`, `DEFAULT_STEWARD_{MANDATE,IDENTITY,PRINCIPLES}_MD`,
`STEWARD_DEFAULT_MARKER(_YAML)`, `DEFAULT_WORKSPACE_GUIDE_MD`). Do not reintroduce:
an agent is identity ⊕ character ⊕ engine (ADR-596 D1); a kernel-default MANDATE for
a systemic agent is a file the kernel never legitimately seeds (ADR-414 D2).
"""

from __future__ import annotations
from typing import Any, Optional
# =============================================================================
# TP Orchestration Playbook — workspace-level (/workspace/_playbook.md)
# =============================================================================
# TP is infrastructure, not workforce. Its playbook lives at workspace scope,
# not under /agents/. Seeded at roster creation, evolves through user feedback.

TP_ORCHESTRATION_PLAYBOOK = """\
# Orchestration Playbook

## Work-First Principle (ADR-176)
Work exists first. Agents serve work. When a user states what they want to accomplish,
resolve team composition from the work intent — not the other way around.

## Task Decomposition
- Simple requests (single deliverable, clear audience) → assign to one or two specialists
- Complex requests (multi-source, multi-format) → Researcher first, then Analyst or Writer
- Recurring work → create task with schedule, not one-off run
- Bounded investigation → create goal-mode task with clear completion criteria

## Production-role Assignment (ADR-176 Decision 1 + ADR-212)
Work requires finding info?        → Researcher
Work requires synthesizing patterns? → Analyst
Work requires a polished deliverable? → Writer
Work requires monitoring over time? → Tracker
Work requires visual assets?        → Designer
Cross-domain summary?               → Reporting (synthesizer)

Platform access (ADR-207 P4a — capabilities, not bots):
- Platform reads/writes are capabilities on specialists — `read_slack`, `write_slack`,
  `read_notion`, `write_notion`, `read_github`, `read_commerce`, `write_commerce`,
  `read_trading`, `write_trading`. Declared on the recurrence YAML via `required_capabilities:` field.
- Gate: `capability_available(user_id, cap, client)` checks the matching
  `platform_connections` row at dispatch. Missing = fail fast with "connect X first".

## Team Composition (ADR-176 Decision 2)
TP owns full composition authority. Registry provides suggested defaults — apply judgment.

Composition criteria:
- Research task → Researcher [+ Analyst if synthesis needed]
- Recurring deliverable → Researcher + Writer [+ Analyst, Designer optional]
- Monitoring task → Tracker [+ Analyst optional]
- One-time deliverable → Researcher + Writer
- Visual output needed → add Designer
- Cross-domain synthesis → Reporting

Write team decisions into the `team:` field of the recurrence YAML declaration. Document reasoning briefly.

## Capability Discipline
- Researcher and Analyst: text and knowledge files only.
- Writer: text deliverables only.
- Designer: composes substrate into HTML (ADR-417: asset generation retired — yarnnn hosts no generation engine).
- Reporting: reads all domains, produces synthesis. Do NOT assign platform-specific research.

## Feedback Routing
- When user comments on output quality → WriteFile(scope="workspace", path="agents/{slug}/memory/feedback.md", content="...", mode="append") for the producing agent (ADR-235)
- When user says "too long" / "more detail" / "different format" → feedback to agent
- When user corrects orchestration → update this playbook
- Positive feedback matters too — "great charts" confirms the agent's approach

## Quality Oversight
- After task completion, check if output matches what was asked
- If user edits frequently, note patterns in agent feedback
- When an agent consistently underperforms, suggest task reassignment or team restructure
"""

# =============================================================================
# Kernel Version (ADR-292)
# =============================================================================
#
# Single version stamp for the kernel-universal seed set (the DEFAULT_*_MD
# constants below + the seed-paths map in workspace_init.py Phase 2).
#
# Bump this string whenever any kernel-universal seed constant changes
# meaningfully — e.g., tightened safety language in DEFAULT_REVIEW_PRINCIPLES_MD,
# revised TP_ORCHESTRATION_PLAYBOOK, etc. The operator-facing update flow
# (ADR-292) compares this against the workspace's recorded
# `activated_kernel_version` (MANDATE.md frontmatter) and surfaces "Kernel
# update available" when the strings differ.
#
# Format: date-stamped `YYYY-MM-DD[.N]` aligning with api/prompts/CHANGELOG.md.
# Operator-driven, not auto-computed — discipline cost is one line per kernel
# substrate change, identical to the CHANGELOG entry the change already needs.
#
# Update flow (operator-initiated, like Claude Code's `claude --update`):
#   1. Operator sees notification on Settings → Workspace surface
#   2. Operator clicks "Update kernel substrate" — invokes
#      services.substrate_reapply.reapply_platform_substrate(source="operator")
#   3. Re-apply runs against kernel-universal paths only (bundle layer
#      handled by separate per-bundle version stamp in MANIFEST.yaml)
#   4. On success, MANDATE.md frontmatter `activated_kernel_version` advances
KERNEL_VERSION = "2026-05-18.1"

DEFAULT_REVIEW_PRINCIPLES_MD = """\
# Review — Principles

This is the declared review framework for this workspace. The Reviewer
reads this alongside `_risk.md` and the program's ground-truth substrate
(per FOUNDATIONS Axiom 8 — `/workspace/_workspace_guide.md` declares the
instance for your bundle). Edit to tune how the Reviewer reasons and what
it does when it defers.

---

## Default posture: skeptical over permissive

When in doubt, defer. Asymmetric losses deserve more scrutiny than
asymmetric gains. A proposal that looks marginal defers; one that is
clearly positive and within declared edge can approve.

## Decision categories

- **approve** — EV clearly positive AND within declared edge AND
  `auto_approve_below_cents` threshold met (see below).
- **reject** — EV clearly negative OR violates `_risk.md` OR outside
  declared strategy. Rejection is unconditional — AUTONOMY does not
  gate it.
- **defer** — EV ambiguous, high stakes, or edge case not yet in the
  ground-truth substrate. Defer always commissions missing substrate
  (see Defer posture below).

## Auto-approve threshold (ADR-253 D1)

Controls whether the Reviewer's approve verdict auto-executes.
Without this field set, every approve requires operator Queue click
regardless of AUTONOMY level.

```yaml
# auto_approve_below_cents: 0   # uncomment + set to enable AI auto-action
```

## Defer posture — what I commission when I defer for evidence gap (ADR-253 D2 amended by ADR-296 v2 D3)

When I defer because evidence is insufficient, I author cadence + standing
intent. I do not re-propose to myself, and per ADR-296 v2 D3 I do not
fire upstream recurrences by name — that is operator + cron territory.

```
# Example (override for your domain):
# When deferring because a signal has < 20 closed-loop samples:
#   directive: write_file(path="/workspace/persona/standing_intent.md",
#                          content="I want to be woken when this signal
#                                   crosses 20 closed-loop samples.")
#   AND
#   Schedule(action="create", slug="reviewer-next-cycle", schedule=...,
#            prompt="Re-assess <signal> after upstream accumulation.")
#
# When deferring because ground-truth substrate is empty:
#   directive: clarify("No closed-loop outcomes exist. Approve a
#                       minimum-size seed action to begin calibration.")
```

## Directive posture — what I can instruct directly (ADR-253 D2 amended by ADR-296 v2 D3)

The Reviewer issues directives for self-substrate work (write to own
substrate, clarify to operator). Per ADR-296 v2 D3, the historical
`fire_invocation` directive is removed — Reviewer authors cadence via
Schedule, not via directive-fire of upstream recurrences. It does NOT
issue directives for external platform writes (those are proposals),
infrastructure changes, or operator configuration.

## Per-domain high-impact thresholds (ADR-195 Phase 5)

Outcomes above these amounts route to the originating task's feedback.md.
This is a principle (what you consider significant), not an autonomy gate.

<!--
commerce:
  high_impact_threshold_cents: 100000

trading:
  high_impact_threshold_cents: 50000
-->

## What the Reviewer does NOT do

- Does not enforce unstated rules.
- Does not override explicit operator approvals.
- Does not accumulate style preference (that is production-role calibration).
"""

DEFAULT_AUTONOMY_YAML = """\
# yarnnn:steward-default
# _autonomy.yaml — delegation declaration (ADR-254 machine-parsed governance).
# Read by review_policy + working_memory. See AUTONOMY.md for the prose docs.
#
# Kernel-default (steward) posture, ADR-408 D3: the system agent is HANDS,
# not a gatekeeper. `substrate` (reversible workspace writes — revision chain
# + revert-as-write make every one of them undoable) runs AUTONOMOUS: the
# steward's file work applies immediately, attributed and after-witness
# emitted, like any member's act. `default` (which governs capital / external
# consequential actions) stays MANUAL — fail-closed, every binding decision
# queues for the operator. Activating a program overwrites this file with the
# operation's tuned delegation.
#
# Schema:
#   default:
#     delegation: manual | bounded | autonomous   (canonical 3-value enum)
#     ceiling_cents: <int>  (required when delegation=bounded)
#     never_auto: [<action_type>, ...]  (always route to operator)
#   substrate:                          (ADR-408 D3 per-class override)
#     delegation: manual | bounded | autonomous
#     never_auto: ["path:<prefix>", ...]  (paths that always queue)
#   paused_until: <ISO timestamp>  (set by operator, ADR-248 D3)
default:
  delegation: manual
  # ceiling_cents: 0       # uncomment + set when promoting to bounded
  # never_auto: []         # action types that always require operator click
substrate:
  delegation: autonomous   # ADR-408 D3 — reversible file work is the steward's hands
"""

DEFAULT_PRECEDENT_MD = """\
# Precedent

This file records durable interpretations and boundary-case decisions
that should shape future behavior across the workspace.

Use it for decisions that are:
- broader than one task run
- narrower than a mandate or autonomy rewrite
- likely to recur
- valuable for YARNNN, the Reviewer, and domain Agents to read the same way

Do not use it for:
- one-off execution instructions
- raw notes or scratch thinking
- operator identity or brand rules
- Reviewer persona/framework content that belongs in `/workspace/persona/`

## Active precedents

<!--
Create one block per durable interpretation.

### <slug>
- Scope:
- Rule:
- Why:
- Source:
- Review trigger:
- Status: active
-->

## Notes

Promote a chat decision here when it should compound.
If the decision changes what the workspace is trying to do, edit
`MANDATE.md` instead.
If it changes how much authority the AI has, edit `AUTONOMY.md` instead.
If it changes how the Reviewer reasons, edit `/workspace/persona/principles.md`.
"""

# DEFAULT_REVIEW_HANDOFFS_MD DELETED — the rotation primitive
# (services/review_rotation.py::_render_handoff_entry) is the single source
# of truth for handoffs.md entries. Per ADR-211 D4 singular-implementation,
# every append to handoffs.md flows through rotate_occupant().


# ADR-364: the persona seat's reflection file — the agent's interpreted
# learning from the closed intent→outcome loop. Supersedes the prior
# DEFAULT_REVIEW_CALIBRATION_MD (the auto-generated aggregate-windows file,
# whose back-office-reviewer-calibration writer is retired separately). Unlike
# calibration, reflection is REVIEWER-AUTHORED (not machine-generated) from the
# envelope gap-fact (judgment_log verdicts joined to ground-truth outcomes by
# proposal_id), so the seed is an empty-state stub the Reviewer fills — the
# same shape as standing_intent's empty-state, not a machine template.
DEFAULT_REVIEW_REFLECTION_MD = """\
# Reflection — what I've learned from how my judgments turned out

This file is **mine to author** (the seat occupant), not machine-generated.
Each cycle, the wake envelope presents a *gap-fact*: my recent verdicts joined
to their ground-truth outcomes (value + attestation) by proposal_id — the loop
my `standing_intent.md` opened (what I watched for), my `judgment_log.md`
recorded (what I decided), now closed by what actually happened.

I read that gap and write here what it teaches: which of my calls worked, which
didn't, what I'd watch for or decide differently. I reflect only when the gap
teaches something — silence is fine when it doesn't. The outcomes I reflect on
are attested (platform / operator / agent), so I cannot flatter myself; I learn
from a record I cannot edit.

## Initial state

No reflections yet — no verdict↔outcome pairs have closed. The first entry lands
once a decision I made has produced a reconciled, attested outcome.
"""

# =============================================================================
# Registry 2: Capabilities — what each capability resolves to
# =============================================================================

#
# ADR-207 P3: each entry declares `platform_connection_requirement`. `None`
# means the capability is always available (internal runtime). A dict with
# `{platform, status}` means the capability only fires when a matching
# `platform_connections` row exists for the user. `capability_available()`
# enforces this at task dispatch; callers should surface a clear
# "connect {platform} first" error to the operator.
#
# ADR-335 derived-trust-tier (ratified 2026-06-19): each entry also declares
# `feeds` — the capability's flow-role, the DECLARED fact `required_tier` reads
# (never inferred — that would reintroduce the proxy the head/tail retirement
# killed). Three values:
#   "action"       — a consequential write/act (write_*). Constitutive of a
#                    primary action ⇒ required_tier HIGH.
#   "ground_truth" — a read whose correctness is constitutive of the program's
#                    ground-truth (the money-truth read) ⇒ required_tier HIGH.
#   "context"      — a read that feeds attention only; a wrong/missing read
#                    degrades a watch, never an act or ground-truth ⇒ OPEN.
# Kernel platform-integration reads (read_slack/notion/github) are generic
# context reads — `feeds: context`. A program that needs one of them at
# ground-truth tier declares a watch (ADR-335 D5), it does not re-grade the
# kernel capability. Internal/cognitive/asset capabilities are gradeless
# (`feeds: context`) — they carry no platform_connection_requirement so the
# tier is never consulted (the gate returns available before reaching it).

CAPABILITIES: dict[str, dict[str, Any]] = {
    # -- Cognitive (prompt-driven, no dedicated tool) --
    "summarize":         {"category": "cognitive", "runtime": "internal", "feeds": "context", "platform_connection_requirement": None},
    "detect_change":     {"category": "cognitive", "runtime": "internal", "feeds": "context", "platform_connection_requirement": None},
    "alert":             {"category": "cognitive", "runtime": "internal", "feeds": "context", "platform_connection_requirement": None},
    "cross_reference":   {"category": "cognitive", "runtime": "internal", "feeds": "context", "platform_connection_requirement": None},
    "data_analysis":     {"category": "cognitive", "runtime": "internal", "feeds": "context", "platform_connection_requirement": None},
    "investigate":       {"category": "cognitive", "runtime": "internal", "feeds": "context", "platform_connection_requirement": None},
    "produce_markdown":  {"category": "cognitive", "runtime": "internal", "feeds": "context", "platform_connection_requirement": None},

    # -- Tool-backed (internal primitives) --
    "web_search":        {"category": "tool", "runtime": "internal", "tool": "WebSearch", "feeds": "context", "platform_connection_requirement": None},
    "read_workspace":    {"category": "tool", "runtime": "internal", "tool": "ReadFile", "feeds": "context", "platform_connection_requirement": None},
    "search_knowledge":  {"category": "tool", "runtime": "internal", "tool": "QueryKnowledge", "feeds": "context", "platform_connection_requirement": None},

    # -- Platform runtime (provider-native external capabilities) --
    "read_slack": {
        "category": "tool", "runtime": "external:slack", "feeds": "context",
        "tools": ["platform_slack_list_channels", "platform_slack_get_channel_history"],
        "platform_connection_requirement": {"platform": "slack", "status": "active"},
    },
    # ADR-304 amendment (2026-06-19): `write_slack` is KERNEL-UNIVERSAL — the
    # audience-addressing channel-send the operator confirmed as an ambient
    # capability (no per-program friction), WITH the ADR-307 uniform gate as the
    # safety floor (ambient capability, gated act; NOT ungated). This points at
    # the audience-write tool (platform_slack_send_to_channel), NOT the
    # operator-DM send (platform_slack_send_message), which stays system
    # infrastructure per ADR-304 D1 (addressee pinned to the operator's own DM).
    # `feeds: action` ⇒ required_tier=HIGH (a primary external write); a
    # platform-grade Slack connection satisfies it. Symmetric with read_slack
    # being kernel-universal: both are capability-bundle-shaped, not program-
    # shaped (ADR-224 §1). The Reviewer is excluded — it has NO platform write
    # tool in FREDDIE_PRIMITIVES; it reaches external effect only via
    # ProposeAction (ADR-299 D8 / ADR-304 D6, preserved).
    "write_slack": {
        "category": "tool", "runtime": "external:slack", "feeds": "action",
        "tools": ["platform_slack_send_to_channel"],
        "platform_connection_requirement": {"platform": "slack", "status": "active"},
    },
    "read_notion": {
        "category": "tool", "runtime": "external:notion", "feeds": "context",
        "tools": ["platform_notion_search", "platform_notion_get_page"],
        "platform_connection_requirement": {"platform": "notion", "status": "active"},
    },
    # ADR-304 amendment (2026-06-19): `write_notion` is KERNEL-UNIVERSAL —
    # audience-addressing page-create + block-append (shared-Notion drafting),
    # the ambient capability the operator confirmed, WITH the ADR-307 gate as
    # the safety floor. Points at the audience-write tools, NOT the operator-
    # designated-page comment (platform_notion_create_comment, which stays
    # system infrastructure per ADR-304 D1). `feeds: action` ⇒ HIGH tier.
    # Reviewer excluded (no platform write in FREDDIE_PRIMITIVES; ProposeAction
    # only — ADR-299 D8 / ADR-304 D6).
    "write_notion": {
        "category": "tool", "runtime": "external:notion", "feeds": "action",
        "tools": ["platform_notion_create_page", "platform_notion_append_block"],
        "platform_connection_requirement": {"platform": "notion", "status": "active"},
    },
    # ADR-576 §5 drift fix: this listed 2 tools where PLATFORM_TOOLS_BY_CAPABILITY
    # (platform_tools.py) listed 5 — the three reference reads were unreachable
    # through this declaration. GitHub ships NO write_github capability (D1).
    "read_github": {
        "category": "tool", "runtime": "external:github", "feeds": "context",
        "tools": [
            "platform_github_list_repos",
            "platform_github_get_issues",
            "platform_github_get_repo_metadata",
            "platform_github_get_readme",
            "platform_github_get_releases",
        ],
        "platform_connection_requirement": {"platform": "github", "status": "active"},
    },
    # ADR-353 §15a: Reddit publishing. KERNEL-UNIVERSAL — Reddit is a generic
    # platform integration any publishing/content program can use (not program-
    # specific like trading is to alpha-trader), so it sits with slack/notion/
    # github per the ADR-224 §1 capability-bundle-owned rule. A program declares
    # it needs these (alpha-author does, via its MANIFEST) exactly as it declares
    # read_slack. Execution is Composio-only (driver_enabled_for("reddit")); no
    # first-party reddit client exists. write_reddit feeds:action (a primary
    # external write ⇒ HIGH tier; the ADR-307 gate is the safety floor; Reviewer
    # excluded — ProposeAction only). read_reddit feeds:context (the perceive
    # read — comments → audience_signal as observation, measure-not-steer §14).
    "read_reddit": {
        "category": "tool", "runtime": "external:reddit", "feeds": "context",
        "tools": ["platform_reddit_get_post_comments"],
        "platform_connection_requirement": {"platform": "reddit", "status": "active"},
    },
    "write_reddit": {
        "category": "tool", "runtime": "external:reddit", "feeds": "action",
        "tools": ["platform_reddit_submit_post"],
        "platform_connection_requirement": {"platform": "reddit", "status": "active"},
    },
    # ADR-353 §17: Hacker News — NO_AUTH read-only perceive connector. Zero
    # credential (no platform_connection), so platform_connection_requirement is
    # None ⇒ always available (like websearch). feeds:context (the perceive read —
    # HN discourse → audience_signal / world-mirror). NO write capability (HN has
    # no public write API). Execution is Composio-ONLY (driver_enabled_for + the
    # _NO_AUTH_PROVIDERS path); no first-party HN client.
    "read_hackernews": {
        "category": "tool", "runtime": "external:hackernews", "feeds": "context",
        "tools": ["platform_hackernews_search_posts", "platform_hackernews_get_item"],
        "platform_connection_requirement": None,
    },
    # ADR-224: read/write_commerce + read/write_trading DELETED from kernel
    # CAPABILITIES. They are program-specific (commerce / trading oracle
    # shapes) and live in their respective program bundle MANIFEST.yaml
    # capabilities[] declarations:
    #   - docs/programs/alpha-trader/MANIFEST.yaml → read_trading + write_trading
    #   - docs/programs/alpha-commerce/MANIFEST.yaml → read_commerce + write_commerce
    # bundle_reader normalizes bundle capability entries to this kernel shape;
    # task_derivation._available_platform_capabilities transparently merges
    # active bundles' capabilities with the kernel set.
    #
    # NOTE: read/write_slack, read/write_notion, read_github STAY in kernel —
    # they are capability-bundle-shaped (platform integration available to
    # any program), not program-shaped. Same classification as the slack/
    # notion/ github directories per ADR-224 §1 capability-bundle-owned rule.

    # -- Asset production (RETIRED — ADR-417) --
    # The chart/mermaid/image/video_render capabilities backed by the
    # in-house render service are retired. Generation is rented, not owned:
    # yarnnn hosts no generation engine. Asset capabilities are gone, and so is
    # RuntimeDispatch — the primitive that dispatched to the render service.
    #
    # NOTE (ADR-464, 2026-07-16): this comment used to end "no SKILL.md
    # injection", which was true of THIS path and became a misreading of the
    # whole system. ADR-417 retired the ENGINE (ADR-118's third leg — the
    # compute environment it had named as the missing one). It never retired the
    # CONVENTION. Skills are back as `agents/{slug}/skills/*.md` — instructions,
    # not engines, and vendor-free by construction because prose is what every
    # model reads. (The member-skills machinery was deleted by ADR-599 D2; the
    # convention note stays for the recipes below.)

    # -- Composition (post-generation pipeline step) --
    "compose_html": {
        "category": "composition", "runtime": "python_render",
        "post_generation": True,
        "platform_connection_requirement": None,
    },

    # ADR-299 (rewrite 2026-05-27): `send_operator_email` is NOT a workspace
    # capability and is no longer registered here. It is system infrastructure
    # (the system Resend wire — same wire ADR-040 notifications + ADR-202
    # daily-update emails use), exposed as an LLM-invokable tool via
    # SYSTEM_INFRASTRUCTURE_TOOLS in services/platform_tools.py. The
    # `runtime: "kernel"` sentinel value has been deleted from this codebase;
    # `runtime` values reduce to actual workspace-work dispatch targets
    # (internal | python_render | external:slack | external:notion |
    # external:github). See docs/adr/ADR-299-*.md for the framing.

    # PM coordination capabilities removed — PM/project architecture dissolved
}

# =============================================================================
# ADR-207 P3: Capability Availability Gate
# =============================================================================

def _resolve_capability(capability_name: str) -> Optional[dict]:
    """Per ADR-224: kernel CAPABILITIES first; on miss, consult active
    program bundles. Bundle-sourced capabilities are normalized to the
    same shape via bundle_reader so dispatch helpers treat them
    identically.
    """
    cap = CAPABILITIES.get(capability_name)
    if cap is not None:
        return cap
    try:
        from services.bundle_reader import get_capability_from_bundles
        return get_capability_from_bundles(capability_name)
    except Exception:
        return None

def get_capability_requirement(capability_name: str) -> Optional[dict]:
    """Return the platform_connection_requirement for a capability, or None.

    None means: either the capability doesn't exist, or it needs no platform
    connection (internal runtime). Callers should treat unknown capabilities
    as "not available" to fail loudly on typos in the recurrence YAML.

    Per ADR-224: falls through to active program bundles' capabilities[]
    declarations for program-specific capabilities (read_trading, write_trading,
    read_commerce, write_commerce).
    """
    cap = _resolve_capability(capability_name)
    if cap is None:
        return None
    return cap.get("platform_connection_requirement")

# ADR-335 derived-trust-tier (ratified 2026-06-19): trust is a DERIVED tier, not
# a platform class. The grade order reuses the ADR-330 D2 attestation enum
# (api/services/outcomes/base.py) verbatim — platform > operator > agent.
_GRADE_ORDER = {"platform": 2, "operator": 1, "agent": 0}

def required_tier(capability: dict[str, Any]) -> str:
    """The trust tier a transport must carry to serve this capability's read.

    DERIVED from the capability's declared `feeds` flow-role (never inferred):
      feeds in (ground_truth, action) -> HIGH  (constitutive of ground-truth or
                                                 a primary action)
      feeds == context (or absent)    -> OPEN   (feeds attention only)

    HIGH admits only a platform-grade binding; OPEN admits any grade. The tier
    is computed here, stored nowhere (FOUNDATIONS DP7).
    """
    return "HIGH" if capability.get("feeds") in ("ground_truth", "action") else "OPEN"

def _grade_satisfies_tier(attestation_grade: str, tier: str) -> bool:
    """A binding's attestation grade satisfies a required tier iff:
    HIGH requires platform-grade (gold); OPEN accepts any known grade.
    """
    if tier == "OPEN":
        return attestation_grade in _GRADE_ORDER
    return _GRADE_ORDER.get(attestation_grade, -1) >= _GRADE_ORDER["platform"]

def capability_available(user_id: str, capability_name: str, client: Any) -> bool:
    """Check whether a capability can fire for this user right now.

    ADR-335 derived-trust-tier gate (the ONE gate — absorbs the prior
    `platform_connection_requirement` platform-enum match):

      - Internal capabilities (no platform requirement) are always available.
      - A connection-gated capability is available iff an active
        `platform_connections` row exists whose `attestation_grade` satisfies
        `required_tier(capability)`. HIGH (ground_truth/action reads) admits
        only a platform-grade binding; OPEN (context reads) admits any grade.

    Existing first-party connections backfill to `platform` (gold, migration
    186), so they satisfy every tier — this generalization is a strict
    superset of the prior platform-match gate and regresses nothing.

    Unknown capability names return False — callers should surface the
    mismatch so the operator can correct the recurrence YAML declaration.

    Per ADR-224: falls through to active program bundles' capabilities[]
    declarations for program-specific capabilities.
    """
    cap = _resolve_capability(capability_name)
    if cap is None:
        return False
    req = cap.get("platform_connection_requirement")
    if req is None:
        return True
    tier = required_tier(cap)
    try:
        rows = (
            client.table("platform_connections")
            .select("attestation_grade")
            .eq("user_id", user_id)
            .eq("platform", req["platform"])
            .eq("status", req["status"])
            .execute()
        )
        # Available iff at least one matching binding's grade satisfies the tier.
        return any(
            _grade_satisfies_tier(r.get("attestation_grade", "platform"), tier)
            for r in (rows.data or [])
        )
    except Exception:
        # Deterministic gate — failing a lookup reports unavailable rather
        # than masking misconfiguration.
        return False

def unavailable_capabilities(
    user_id: str, capability_names: list[str], client: Any
) -> list[dict]:
    """Return a list of {capability, reason, required_platform} for each
    capability that cannot fire right now. Empty list = all capabilities
    are available.

    `reason` is one of: "unknown_capability", "platform_not_connected".

    Per ADR-224: resolves through _resolve_capability so bundle-sourced
    program-specific capabilities (read_trading, write_trading, read_commerce,
    write_commerce) are recognized identically to kernel capabilities.
    """
    results: list[dict] = []
    for name in capability_names or []:
        cap = _resolve_capability(name)
        if cap is None:
            results.append({
                "capability": name,
                "reason": "unknown_capability",
                "required_platform": None,
            })
            continue
        req = cap.get("platform_connection_requirement")
        if req is None:
            continue
        if not capability_available(user_id, name, client):
            results.append({
                "capability": name,
                "reason": "platform_not_connected",
                "required_platform": req.get("platform"),
            })
    return results
