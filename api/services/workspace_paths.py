"""
Workspace path constants + permission topology (ADR-320, 2026-06-05).

Single source of truth for canonical workspace file paths AND the write-permission
policy. Callers pass these to UserMemory (AgentWorkspace is agent-scoped; these are
workspace-scoped). The permission gate `_is_path_locked(caller_class, path)` in
`services/primitives/workspace.py` reads `CALLER_WRITE_POLICY` from this module.

ADR-320 — FIVE-ROOT PERMISSION TOPOLOGY (FOUNDATIONS Derived Principle 25):
the directory a file lives in determines who may write it, for every caller class,
derivable from the path prefix alone with no file enumeration. The workspace root
IS the permission taxonomy — `access(2)` for the agent OS (Derived Principle 16).

    /workspace/
      ├── governance/    OPERATOR-ONLY ceilings the seat runs under but cannot set.
      │     AUTONOMY.md + _autonomy.yaml (delegation), _budget.yaml (spend
      │     envelope — ADR-327, collapsed _token_budget + _pace),
      │     _preferences.yaml (deliverable cadence).
      │     OS analog: /etc/security/limits.conf + cgroup/ulimits.
      ├── constitution/  OPERATOR intent the seat AMENDS; read by ALL agents.
      │     MANDATE.md (Primary Action), PRECEDENT.md (durable interpretations).
      │     OS analog: the app's own ~/.config/{app}/ it may rewrite.
      │     NOTE (ADR-320, operator-identity collapse): the operator's
      │     operating-posture file (legacy context/_shared/IDENTITY.md) is NOT
      │     here — it is reasoning-character, the same KIND as the persona, so it
      │     collapses INTO persona/IDENTITY.md (singular reasoning-character per
      │     Axiom 2 two-embodiments). constitution/ is pure intent: MANDATE +
      │     PRECEDENT, no IDENTITY.
      ├── persona/       THE SEAT — how it reasons + its trail. Occupant-agnostic.
      │     IDENTITY.md (the operator's judgment, embodied — absorbs the legacy
      │       operator operating-posture file), principles.md (+_principles.yaml),
      │       judgment_log.md,
      │     OCCUPANT.md, handoffs.md, standing_intent.md.
      │     OS analog: the process's own address space / working set.
      ├── operation/     THE WORK the agent operates on / produces. Many writers.
      │     BRAND.md, CONVENTIONS.md, _voice.md-class style files, specs/, reports/,
      │     operations/, {domain}/ accumulated context (_money_truth.md, _risk.md,
      │     _operator_profile.md, _universe.yaml, etc.).
      │     OS analog: ~/Documents/ + project working dirs (the commons).
      └── system/        ORCHESTRATION runtime accumulation. Not Identity-bearing.
            awareness.md, _playbook.md, style.md, notes.md, _schedule_index.md,
            _recent_execution.md.
            OS analog: /var/lib/{service} + /tmp.

Plus agent substrate at `/workspace/agents/{slug}/`, ephemeral `/workspace/working/`,
and user uploads at `/workspace/uploads/` — unchanged by ADR-320 (not part of the
constitution/operation/governance cut; agents/ is per-agent, working/ ephemeral,
uploads/ user-contributed reference material).

constitution/ + persona/ are the REQUIRED region (ADR-320 D4 hard-gate, generalizing
ADR-207's MANDATE gate): the workspace cannot dispatch work until MANDATE.md +
persona IDENTITY.md + persona principles.md are non-skeleton. governance/ defaults
are kernel/bundle-seeded. operation/ empty is legal — it signals the bare-workspace
"agent authored, no operation attached" state.
"""

# =============================================================================
# Root prefixes (ADR-320) — the five semantic-class roots
# =============================================================================
GOVERNANCE_ROOT = "governance/"
CONSTITUTION_ROOT = "constitution/"
PERSONA_ROOT = "persona/"
OPERATION_ROOT = "operation/"
SYSTEM_ROOT = "system/"

# Per-agent + ephemeral + upload roots (not part of the constitution/operation cut)
AGENTS_ROOT = "agents/"
WORKING_ROOT = "working/"
UPLOADS_ROOT = "uploads/"


# =============================================================================
# governance/ — operator-only ceilings (locked from every LLM writer)
# =============================================================================
# AUTONOMY: prose doc (LLM/human reads) + machine-parsed yaml (yaml.safe_load).
GOVERNANCE_AUTONOMY_PATH = "governance/AUTONOMY.md"
GOVERNANCE_AUTONOMY_YAML_PATH = "governance/_autonomy.yaml"
# The operation's spend envelope (ADR-327): one dollar budget over a timeframe.
# Reviewer reads, never authors (Reviewer-edit could raise its own ceiling —
# authority the operator did not delegate). Collapses the retired _pace.yaml +
# _token_budget.yaml into one file (both constants deleted by ADR-327).
GOVERNANCE_BUDGET_PATH = "governance/_budget.yaml"
# Operator's deliverable-cadence preferences (ADR-275). Reviewer reads + reconciles
# via Schedule; operator owns the content.
GOVERNANCE_PREFERENCES_PATH = "governance/_preferences.yaml"


# =============================================================================
# constitution/ — operator intent the seat amends; read by all agents
# =============================================================================
# PURE INTENT only (ADR-320 operator-identity collapse): MANDATE + PRECEDENT.
# The operator's operating-posture (legacy context/_shared/IDENTITY.md) is NOT
# here — it is reasoning-character and collapses into PERSONA_IDENTITY_PATH.
CONSTITUTION_MANDATE_PATH = "constitution/MANDATE.md"
# Durable interpretations that survive seat rotation; read by YARNNN, the seat, and
# domain Agents alike. ADR-320 D2: PRECEDENT is constitution (survives rotation;
# distinct from persona which rotates with the occupant).
CONSTITUTION_PRECEDENT_PATH = "constitution/PRECEDENT.md"

# Files the kernel seeds at every workspace init (constitution skeletons).
CONSTITUTION_FILES = (
    CONSTITUTION_MANDATE_PATH,
    CONSTITUTION_PRECEDENT_PATH,
)


# =============================================================================
# persona/ — the judgment seat itself (occupant-agnostic)
# =============================================================================
# The singular reasoning-character file (ADR-320 operator-identity collapse):
# the operator's judgment, embodied. Absorbs BOTH the legacy persona file
# (review/IDENTITY.md) AND the legacy operator operating-posture file
# (context/_shared/IDENTITY.md) — two embodiments of one principal (Axiom 2),
# one substrate home. Operator-authored; occupant-agnostic.
PERSONA_IDENTITY_PATH = "persona/IDENTITY.md"
PERSONA_PRINCIPLES_PATH = "persona/principles.md"         # prose (LLM reads)
PERSONA_PRINCIPLES_YAML_PATH = "persona/_principles.yaml"  # machine-parsed thresholds (ADR-254)
PERSONA_JUDGMENT_LOG_PATH = "persona/judgment_log.md"     # append-only judgment lineage
PERSONA_OCCUPANT_PATH = "persona/OCCUPANT.md"             # who currently fills the seat
PERSONA_HANDOFFS_PATH = "persona/handoffs.md"             # append-only rotation log
PERSONA_STANDING_INTENT_PATH = "persona/standing_intent.md"  # forward-looking working state (ADR-284)

PERSONA_FILES = (
    PERSONA_IDENTITY_PATH,
    PERSONA_PRINCIPLES_PATH,
    PERSONA_JUDGMENT_LOG_PATH,
    PERSONA_OCCUPANT_PATH,
    PERSONA_HANDOFFS_PATH,
    PERSONA_STANDING_INTENT_PATH,
)


# =============================================================================
# operation/ — the work the agent operates on / produces
# =============================================================================
OPERATION_BRAND_PATH = "operation/BRAND.md"
# CONVENTIONS.md: program-scoped (NOT kernel-seeded); bundle forks it.
OPERATION_CONVENTIONS_PATH = "operation/CONVENTIONS.md"
# Program-bundle capability library (Claude Code skills.md analog, ADR-261 D6).
SPECS_PREFIX = "/workspace/operation/specs/"
# Deliverable + action recurrence substrate (ADR-231).
REPORTS_PREFIX = "operation/reports/"
OPERATIONS_PREFIX = "operation/operations/"
# Accumulated domain context lives at operation/{domain}/ (ADR-151 relocated by ADR-320).
OPERATION_DOMAINS_PREFIX = "operation/"


# =============================================================================
# system/ — orchestration runtime accumulation (not Identity-bearing)
# =============================================================================
SYSTEM_AWARENESS_PATH = "system/awareness.md"
SYSTEM_PLAYBOOK_PATH = "system/_playbook.md"
SYSTEM_STYLE_PATH = "system/style.md"
SYSTEM_NOTES_PATH = "system/notes.md"
# ADR-301: Reviewer Pulse envelope substrate — mechanically-mirrored per scheduler
# tick; the Reviewer reads them at every wake, never writes them.
SYSTEM_SCHEDULE_INDEX_PATH = "system/_schedule_index.md"
SYSTEM_RECENT_EXECUTION_PATH = "system/_recent_execution.md"
# ADR-327 D6: calibration evidence for the self-improving loop — correlates
# the Reviewer's cadence-authoring history against ground-truth outcome
# quality. Mechanically-mirrored per scheduler tick (sibling of the ADR-301
# pulse files); the Reviewer reads it before reasoning about cadence.
SYSTEM_CALIBRATION_PATH = "system/_calibration.md"

SYSTEM_FILES = (
    SYSTEM_AWARENESS_PATH,
    SYSTEM_PLAYBOOK_PATH,
    SYSTEM_STYLE_PATH,
    SYSTEM_NOTES_PATH,
)


# =============================================================================
# Permission topology — `access(2)` for the agent OS (ADR-320 D3)
# =============================================================================
# One per-caller prefix policy. `_is_path_locked(caller_class, path)` in
# services/primitives/workspace.py reads CALLER_WRITE_POLICY: a caller is
# LOCKED from writing `path` iff `path` starts with any prefix in its locked set.
# No filename appears here — permission derives from (caller_class, root) alone.
# This is the SINGULAR lock source: it replaces the pre-ADR-320 pair
# (DEFAULT_REVIEWER_WRITE_LOCKS flat-list + DEFAULT_MCP_WRITE_LOCK_PREFIXES).
#
# Caller classes (matched by authored_by prefix in the gate):
#   - "reviewer"  — the seat occupant. Amends constitution/ + persona/ +
#                   operation/; locked from governance/ (its own ceilings) and
#                   system/ (orchestration's, not the seat's).
#   - "mcp"       — foreign LLM (yarnnn:mcp). Lowest trust. Writes ONLY the
#                   operation/ commons; locked from everything else.
#   - "agent"     — domain agent / specialist. Writes operation/ (domain-scoped
#                   enforcement is the dispatcher's job); locked from governance/
#                   constitution/ persona/ system/.
#   - "operator"  — the human. Writes everything except system/ (orchestration
#                   runtime state is not hand-edited).
#   - "system"    — deterministic actors (reconciler, mirrors, cleanup). Write
#                   system/ + operation/ only; locked from governance/
#                   constitution/ persona/. (No persona/ exception: calibration
#                   evidence lives in system/_calibration.md per ADR-327, not in
#                   persona/ — ADR-320 D6 cross-class write retired 2026-06-16.)
#                   Enforced by named-path discipline at each system writer.
CALLER_WRITE_POLICY: dict[str, tuple[str, ...]] = {
    "reviewer": (GOVERNANCE_ROOT, SYSTEM_ROOT),
    "mcp": (GOVERNANCE_ROOT, CONSTITUTION_ROOT, PERSONA_ROOT, SYSTEM_ROOT),
    "agent": (GOVERNANCE_ROOT, CONSTITUTION_ROOT, PERSONA_ROOT, SYSTEM_ROOT),
    "operator": (SYSTEM_ROOT,),
    # system: governed by named-path discipline at each writer, not a prefix lock.
    "system": (),
}
