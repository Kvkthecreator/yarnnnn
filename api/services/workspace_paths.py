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
      │     OCCUPANT.md, handoffs.md, calibration.md, standing_intent.md.
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

constitution/ + persona/ are the semantic-class roots for a workspace-level
constitution — BUT under ADR-414 (pure genesis) + ADR-419 they are NO LONGER
workspace-level concepts: mandate/identity/principles are PER-AGENT (they live in
a hired agent's home `agents/{slug}/`, ADR-414 D6), and the steward's versions are
KERNEL CONSTANTS riding the wake envelope (ADR-414 D2), never seeded files. So the
old ADR-320 D4 / ADR-207 "the workspace cannot dispatch until MANDATE.md +
IDENTITY.md + principles.md are non-skeleton" hard-gate is RETIRED at the workspace
level (ADR-414 D4) — a bare workspace is a complete commons (files/members/grants/
balance) with no constitution of its own. These root paths persist as the
STEWARD-ERA layout for legacy (pre-ADR-414) workspaces and as the region-lock
prefixes; genesis writes none of them. governance/ dials (autonomy/budget) are the
only seeded files. operation/ empty is legal — the bare-workspace state.
"""

# =============================================================================
# Root prefixes (ADR-320 + the grant/contract split) — semantic-class roots
# =============================================================================
# ADR (autonomy-mode-as-execution-breadth, 2026-06-25): governance/ is split by
# the "should the agent be able to write its own X?" test into two roots:
#   - governance/ = the GRANT (authority + spend the agent runs under) — the
#     irreducible lock. A grant the grantee can rewrite is not a grant: the
#     agent cannot author the declaration of its own breadth (_autonomy) or its
#     own spend authorization (_budget). Locked-always, every mode, every caller.
#   - contract/   = the operating CONTRACT (what the operator declares the agent
#     OWES + PREFERS — _expected_output, _preferences). NOT an authority grant:
#     editing it grants the agent no new power; it changes what the agent is
#     measured against. So it is MODE-GOVERNED, not locked — the existing ADR-307
#     witness gate routes a Reviewer write to it (QUEUE under bounded/supervised,
#     APPLY under autonomous). Breadth = AUTONOMY mode, not a capability lock.
GOVERNANCE_ROOT = "governance/"
CONTRACT_ROOT = "contract/"
CONSTITUTION_ROOT = "constitution/"
PERSONA_ROOT = "persona/"
OPERATION_ROOT = "operation/"
SYSTEM_ROOT = "system/"

# Per-agent + ephemeral + upload roots (not part of the constitution/operation cut)
AGENTS_ROOT = "agents/"
WORKING_ROOT = "working/"
UPLOADS_ROOT = "uploads/"


# =============================================================================
# Per-agent homes (ADR-414 D5/D6 — program-as-hire, the Altitude-3 substrate)
# =============================================================================
# A hired agent's file set lives in agents/{slug}/ — its persona, purpose,
# rules, dials, contract, and working trail. The workspace-root seat paths
# (persona/, constitution/, contract/) are the LEGACY steward-era layout: they
# survive as the steward's interim working set (standing_intent/judgment_log
# on a no-hire workspace) and on pre-ADR-414 workspaces; a hire never writes
# them. Layout (ADR-414 §9a):
#
#   agents/{slug}/
#     IDENTITY.md          — the persona
#     MANDATE.md           — the agent's purpose (ADR-207 gate, per-agent)
#     principles.md        — rules of judgment (prose)
#     _principles.yaml     — machine thresholds
#     AUTONOMY.md          — witness-dial prose
#     _autonomy.yaml       — witness dial (GRANT SIDECAR — locked, ADR-366 per-agent)
#     _budget.yaml         — ADR-391 allocation (GRANT SIDECAR — reserved, not yet shipped)
#     _preferences.yaml    — deliverable-cadence preferences
#     _expected_output.yaml— output contract (ADR-345)
#     standing_intent.md   — forward working state
#     judgment_log.md      — judgment lineage
#     reflection.md        — interpreted learning
#
# No OCCUPANT.md: the occupant fact is kernel data (ADR-414 D2).

#: Grant-sidecar leaves within an agent home — the per-agent dials the agent
#: itself must never author (a grant the grantee can rewrite is not a grant —
#: ADR-366's logic applied per-agent). `_is_path_locked` in
#: services/primitives/workspace.py enforces this for freddie/mcp/agent callers.
AGENT_GRANT_SIDECAR_LEAVES = ("_autonomy.yaml", "_budget.yaml")


def agent_home(slug: str) -> str:
    """The hired agent's substrate home prefix (workspace-relative)."""
    return f"{AGENTS_ROOT}{slug}/"


def is_agent_grant_sidecar(path: str) -> bool:
    """True iff `path` is a per-agent grant sidecar (agents/{slug}/_autonomy.yaml
    or agents/{slug}/_budget.yaml) — locked for every non-operator caller."""
    rel = path.strip().lstrip("/")
    if rel.startswith("workspace/"):
        rel = rel[len("workspace/"):]
    if not rel.startswith(AGENTS_ROOT):
        return False
    leaf = rel.rsplit("/", 1)[-1]
    return leaf in AGENT_GRANT_SIDECAR_LEAVES
# The RAW intake lane (ADR-376 / FOUNDATIONS DP32 — the ledger-intake axiom).
# Machine/external contributions land here as IMMUTABLE attributed raw
# observations: inbound/{transport}/{principal}/{slug}.md. Sibling to uploads/
# (the human raw root) — both OUTSIDE the constitution/operation/governance cut,
# both reasoned-against-never-rewritten. The DERIVED understanding the seat
# builds from a raw observation lands in operation/ carrying a `derived_from`
# citation back to its inbound/ source. uploads/ is the N=human case of the same
# raw-lane shape. The per-{transport}/{principal} sublane is single-writer by
# construction today (a convention ADR-373's per-principal grant later enforces).
INBOUND_ROOT = "inbound/"


# =============================================================================
# WORKSPACE_ROOTS — the UI source-of-truth for the Files surface (ADR-388 D1)
# =============================================================================
# The Files explorer DERIVES its tree from the actual filesystem roots
# (GET /workspace/roots), not a hardcoded list — so every directory shows and
# no future root can go missing (the ADR-388 root-cause kill). This dict gives
# each KNOWN root a friendly display label + icon hint + one-line description +
# its ADR-320 semantic class. The explorer is filesystem-LITERAL: it renders
# whatever roots exist; a root NOT in this map still renders, using its raw
# directory name (forward-compatible with the re-founding re-homing roots —
# ADR-388 §6). `order` is the at-rest sort (lower = higher in the tree);
# unknown roots sort after all known ones, alphabetically.
#
# `icon` is a lucide-react icon NAME (resolved FE-side, mirroring the
# surface-icons pattern) — the kernel names the glyph, the FE maps it.
#
# `group` (ADR-423 follow-on / the Files-model note, 2026-07-09) is the SINGULAR
# source for the Finder-vocabulary tree reshape. It sorts each root into one of
# three operator-facing zones — the three category-kinds from the note:
#   "work"    → Documents (kind ①): what the operator + agents author + keep.
#   "arrival" → Downloads (kind ①): what ARRIVED (didn't author) — the raw lanes.
#   "system"  → System files (kind ③): kernel-bootstrap residue, collapsed + hidden.
# This is a DISPLAY grouping only — no substrate path moves (the labels rename
# what the operator SEES; `operation/` etc. stay the canonical paths the kernel,
# gate, and every writer depend on). The FE renders work + arrival at the top and
# folds every "system" root under one collapsed "System files" disclosure.
# `semantic_class` (the ADR-320 lock class) is UNCHANGED — group is the operator
# zone, semantic_class is the permission class; two orthogonal facts.
WORKSPACE_ROOTS: dict[str, dict] = {
    # ── work → Documents (kind ①: authored) ──────────────────────────────────
    "operation": {
        "display_name": "Documents",
        "semantic_class": "work",
        "group": "work",
        "description": "What you and your agents author and keep — your work, context, reports.",
        "icon": "folder-cog",
        "order": 10,
    },
    # ── arrival → Downloads (kind ①: what arrived) ───────────────────────────
    # inbound/ is the unified arrival lane (ADR-395: uploads land in inbound/uploads/
    # too). Both render under "Downloads"; an arrival is marked by its ADR-423
    # revision_kind='observation' badge, not by which lane-root it sits in.
    "inbound": {
        "display_name": "Downloads",
        "semantic_class": "raw-lane",
        "group": "arrival",
        "description": "What arrived in your workspace — uploads and observations from connected apps. Kept as received.",
        "icon": "arrow-down-to-line",
        "order": 20,
    },
    "uploads": {
        # Legacy root — only shows when it holds pre-ADR-395 files. Grouped with
        # inbound/ under Downloads so the operator sees one "arrivals" zone.
        "display_name": "Downloads",
        "semantic_class": "raw-lane",
        "group": "arrival",
        "description": "Files you uploaded (legacy location — new uploads land under Downloads).",
        "icon": "upload",
        "order": 21,
    },
    # ── system → System files (kind ③: kernel residue, collapsed) ────────────
    # The ADR-320 semantic-class roots + runtime + agent homes. Present, reachable,
    # deep-linkable — but folded under one "System files" disclosure (the OS
    # "Show system files" model), NOT peers of the operator's work.
    "constitution": {
        "display_name": "Constitution",
        "semantic_class": "operator-intent",
        "group": "system",
        "description": "Operator intent the agent amends against ground truth — MANDATE, PRECEDENT.",
        "icon": "scroll-text",
        "order": 50,
    },
    "governance": {
        "display_name": "Governance",
        "semantic_class": "grant",
        "group": "system",
        "description": "The grant — authority + spend the agent runs under. Operator-only, locked.",
        "icon": "shield",
        "order": 51,
    },
    "contract": {
        "display_name": "Contract",
        "semantic_class": "contract",
        "group": "system",
        "description": "What the operator declares the agent owes and prefers — mode-governed.",
        "icon": "file-signature",
        "order": 52,
    },
    "persona": {
        "display_name": "Persona",
        "semantic_class": "seat",
        "group": "system",
        "description": "How the agent reasons — IDENTITY, principles, the seat's working files.",
        "icon": "brain",
        "order": 53,
    },
    "agents": {
        "display_name": "Agents",
        "semantic_class": "agents",
        "group": "system",
        "description": "Per-agent homes (the Rung-2 judgment seats, when present).",
        "icon": "users",
        "order": 54,
    },
    "system": {
        "display_name": "System",
        "semantic_class": "runtime",
        "group": "system",
        "description": "Orchestration runtime — awareness, notes, style, system ledger.",
        "icon": "settings",
        "order": 55,
    },
    "working": {
        "display_name": "Working",
        "semantic_class": "ephemeral",
        "group": "system",
        "description": "Ephemeral scratch — transient working files.",
        "icon": "file-clock",
        "order": 56,
    },
}


def root_metadata(root_name: str) -> dict:
    """ADR-388 D1 — UI metadata for a workspace root.

    `root_name` is the bare top-level segment (e.g. "constitution", "inbound").
    Returns the WORKSPACE_ROOTS entry for a known root, or a filesystem-literal
    fallback for an unknown/new root (display = the raw name title-cased, a
    generic folder icon, sorted after all known roots). This is what makes the
    derived tree forward-compatible: a root the kernel has never heard of still
    renders with its real directory name.
    """
    known = WORKSPACE_ROOTS.get(root_name)
    if known is not None:
        return {"name": root_name, **known}
    return {
        "name": root_name,
        "display_name": root_name.replace("_", " ").replace("-", " ").title(),
        "semantic_class": "unknown",
        # An unknown/new root defaults to the operator's "work" zone (Documents),
        # NOT hidden under System — a re-founding meaning-folder (the-acme-deal/)
        # is the operator's work and must surface, not fold into the residue.
        "group": "work",
        "description": "",
        "icon": "folder",
        "order": 1000,
    }


# =============================================================================
# governance/ — the GRANT: authority + spend the agent runs under (locked-always)
# =============================================================================
# These two are the irreducible lock set (re-ratifies ADR-293's "two governance
# instruments"): the agent reads them to know its own breadth + budget, and can
# NEVER author them — a gate the gated party can open is not a gate.
# AUTONOMY: prose doc (LLM/human reads) + machine-parsed yaml (yaml.safe_load).
GOVERNANCE_AUTONOMY_PATH = "governance/AUTONOMY.md"
GOVERNANCE_AUTONOMY_YAML_PATH = "governance/_autonomy.yaml"
# The operation's spend envelope (ADR-327): one dollar budget over a timeframe.
# The agent should not author its own spend AUTHORIZATION (the operator's grant
# of capital to the operation — upstream of the work, not a judgment within it).
# Collapses the retired _pace.yaml + _token_budget.yaml (both deleted by ADR-327).
GOVERNANCE_BUDGET_PATH = "governance/_budget.yaml"

# =============================================================================
# contract/ — the operating CONTRACT: operator-declared, agent-honored,
#             MODE-GOVERNED (not locked — the witness dial governs writes)
# =============================================================================
# Operator's deliverable-cadence preferences (ADR-275). Reviewer reads + reconciles
# via Schedule; operator owns the content but the agent MAY revise it against
# ground truth — a write QUEUES under bounded/supervised, APPLIES under autonomous.
CONTRACT_PREFERENCES_PATH = "contract/_preferences.yaml"
# The operation's output contract (ADR-345) — what the workspace owes:
# kind + delivery-cadence + bar. The machine face of MANDATE ## Expected Output.
# Operator-declared; mode-governed for the agent (ADR-319 stewardship — the
# installed judgment revises its own operating contract against ground truth,
# witness-gated). The standing-obligation check (DP30) reads it declared-then-derive.
CONTRACT_EXPECTED_OUTPUT_PATH = "contract/_expected_output.yaml"


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
PERSONA_REFLECTION_PATH = "persona/reflection.md"         # interpreted learning from the closed intent→outcome loop (ADR-364; supersedes calibration.md)
PERSONA_STANDING_INTENT_PATH = "persona/standing_intent.md"  # forward-looking working state (ADR-284)

PERSONA_FILES = (
    PERSONA_IDENTITY_PATH,
    PERSONA_PRINCIPLES_PATH,
    PERSONA_JUDGMENT_LOG_PATH,
    PERSONA_OCCUPANT_PATH,
    PERSONA_HANDOFFS_PATH,
    PERSONA_REFLECTION_PATH,
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
# (DEFAULT_FREDDIE_WRITE_LOCKS flat-list + DEFAULT_MCP_WRITE_LOCK_PREFIXES).
#
# Caller classes (matched by authored_by prefix in the gate):
#   - "reviewer"  — the seat occupant. Amends constitution/ + persona/ +
#                   operation/ + contract/; locked ONLY from governance/ (the
#                   GRANT it runs under — authority + spend it cannot self-author)
#                   and system/ (orchestration's, not the seat's). Writes ALL of
#                   persona/ including reflection.md (ADR-364). contract/ is NOT
#                   locked: a Reviewer write to _preferences/_expected_output is
#                   MODE-GOVERNED by the ADR-307 witness gate (QUEUE under
#                   bounded/supervised, APPLY under autonomous) — breadth = the
#                   AUTONOMY dial, not a capability lock (the grant/contract-split
#                   ADR, 2026-06-25). The pre-ADR-364 cross-class exception
#                   (reconciler → persona/calibration.md) is RETIRED.
#   - "mcp"       — foreign LLM (yarnnn:mcp). Lowest trust. Writes the operation/
#                   commons + the inbound/ RAW LANE (its raw observations, ADR-376
#                   / DP32); locked from everything else (incl. contract/ — a
#                   foreign LLM does not revise the operator's operating contract,
#                   and never writes governance/constitution/persona/system).
#                   inbound/ is intentionally NOT locked (it is the foreign
#                   caller's attributed raw-intake home), and is outside the
#                   topology cut so it carries no semantic-class authority.
#   - "agent"     — domain agent / specialist. Writes operation/ (domain-scoped
#                   enforcement is the dispatcher's job); locked from governance/
#                   contract/ constitution/ persona/ system/.
#   - "operator"  — the human. Writes everything except system/ (orchestration
#                   runtime state is not hand-edited) — including governance/ (the
#                   grant is the operator's to set) + contract/ (the operator's
#                   own operating contract).
#   - "system"    — deterministic actors (reconciler, mirrors, cleanup). Write
#                   system/ + operation/; locked from governance/ contract/
#                   constitution/ + ALL of persona/.
#                   (Enforced by the named-path discipline at each system writer,
#                   not by a prefix — system writers target specific paths.)
CALLER_WRITE_POLICY: dict[str, tuple[str, ...]] = {
    "freddie": (GOVERNANCE_ROOT, SYSTEM_ROOT),  # contract/ NOT here → mode-governed
    "mcp": (GOVERNANCE_ROOT, CONTRACT_ROOT, CONSTITUTION_ROOT, PERSONA_ROOT, SYSTEM_ROOT),
    "agent": (GOVERNANCE_ROOT, CONTRACT_ROOT, CONSTITUTION_ROOT, PERSONA_ROOT, SYSTEM_ROOT),
    "operator": (SYSTEM_ROOT,),
    # system: governed by named-path discipline at each writer, not a prefix lock.
    "system": (),
}


# ADR-400 Amendment 1 (2026-07-02): the operator's ORGANIZE reach (move/rename/
# trash), the SINGULAR source both the Files routes and the FE mirror. The
# operator organizes their whole workspace EXCEPT three carves:
#
#   1. system/  — runtime orchestration state, not hand-organized. This IS the
#      declared operator write-lock (CALLER_WRITE_POLICY['operator'] = SYSTEM_ROOT).
#   2. _*.yaml / _*.json machine-config — code reads these at an EXACT path (the
#      scheduler reads _budget.yaml, the gate reads _principles.yaml); renaming or
#      moving one breaks the reader. This is a FILESYSTEM-INTEGRITY rule (don't
#      rename a file another program finds by path), NOT a permission hierarchy —
#      the operator "owns" it, but the machine depends on its exact location.
#   3. inbound/  — the RAW INTAKE LANE (ADR-376 / DP32). Every file here is an
#      immutable attributed observation of what arrived from the outside: raw is
#      RETAINED and reasoned-against, NEVER rewritten. Moving/renaming/trashing a
#      record of what came in is a category error — the operator reads the raw and
#      corrects the DERIVED understanding, not the observation. Added by ADR-422
#      D2: the FE previously believed intake was organizable (no carve), so the
#      surface and this gate disagreed; this closes that (uploads/ is the HUMAN
#      raw lane and stays organizable — the operator owns what they uploaded).
#
# Everything else — constitution/, persona/, operation/, uploads/, all prose — is
# the operator's to reorganize. Delete is trash-not-erase (reversible), so this is
# safe. NOT a topology lock against the human: it's their filesystem.
_MACHINE_CONFIG_EXTS = (".yaml", ".yml", ".json")


def operator_can_organize(path: str) -> bool:
    """True iff the operator may move/rename/trash `path` (ADR-400 Amendment 1
    + ADR-422 D2).

    The three carves on top of the operator's near-total workspace reach:
      - under system/ → False (runtime state, the declared operator lock)
      - a _*.yaml/_*.json machine-config file → False (read by exact path)
      - under inbound/ → False (immutable raw intake, ADR-376 — retained, never
        rewritten; uploads/ is the human raw lane and stays organizable)
      - everything else → True (constitution/persona/operation/uploads/... prose)
    """
    rel = path.strip().lstrip("/")
    if rel.startswith("workspace/"):
        rel = rel[len("workspace/"):]
    if rel.startswith(SYSTEM_ROOT):
        return False
    if rel.startswith(INBOUND_ROOT):
        return False
    leaf = rel.rsplit("/", 1)[-1]
    if leaf.startswith("_") and leaf.lower().endswith(_MACHINE_CONFIG_EXTS):
        return False
    return True
