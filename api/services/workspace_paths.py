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
      │     CONVENTIONS.md, _voice.md-class style files, specs/, reports/,
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

from typing import Optional

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
# observations: inbound/{lane}/{selector}/{stamp}.{ext} — see
# docs/architecture/intake-pipeline.md, the binding grammar.
#   lane     = HOW it arrived (web · slack · uploads · mcp)
#   selector = WHICH slice (a feed slug, a channel id, or — for uploads/mcp —
#              a principal; `{principal}` is the SPECIAL CASE, not the general
#              form, which this comment previously stated as though general)
# Sibling to uploads/
# (the human raw root) — both OUTSIDE the constitution/operation/governance cut,
# both reasoned-against-never-rewritten. The DERIVED understanding the seat
# builds from a raw observation lands in operation/ carrying a `derived_from`
# citation back to its inbound/ source. uploads/ is the N=human case of the same
# raw-lane shape. The per-{lane}/{selector} sublane is single-writer by
# construction today (a convention ADR-373's per-principal grant later enforces).
INBOUND_ROOT = "inbound/"

# The HUMAN upload sublane of the raw arrival lane (ADR-395: uploads land at
# inbound/uploads/{principal}/{slug}.{ext}). It is the N=human case of the raw
# lane — but unlike machine/external observations, the operator OWNS what they
# uploaded and may reorganize it (rename/move/trash). So this sublane is carved
# BACK OUT of the inbound/ immutability rule (ADR-422 D2's stated invariant:
# "uploads/ is the HUMAN raw lane and stays organizable"). When ADR-395 relocated
# uploads from the top-level uploads/ root INTO inbound/uploads/, the blanket
# inbound/ carve started swallowing them, contradicting that invariant; this
# constant restores it.
INBOUND_UPLOADS_ROOT = "inbound/uploads/"


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
# PARTICIPANT_FILESYSTEM_MODEL — the SINGULAR pure-OS home-directory prose
# (ADR-424 D1). The one place the filesystem's mental model is authored for an
# LLM participant. Every envelope that needs to teach the filesystem imports
# THIS — it never re-authors a root list (the four pre-ADR-424 inline
# enumerations disagreed; this is their singular replacement, DP33).
#
# The model is PURE OS: the workspace is a home directory; write by meaning; the
# grant governs; attribution records who. No participant is told "your work goes
# to root X." `operation/` is the path of the Documents home — the participant
# is told "Documents," not the kernel root (permission still derives from the
# path root at the gate, ADR-320 — unchanged; this is what the participant is
# TOLD, not what is ENFORCED).
#
# Kernel-universal (true on every workspace) → a constant, not per-workspace
# data. Program-specific substrate structure layers on top via
# `_workspace_guide.md` (ADR-281), which this does not replace.
PARTICIPANT_FILESYSTEM_MODEL = """\
## The filesystem

Your workspace is a home directory. You write files into it by meaning — the
same way any participant (the operator, other agents, connected apps) does.
Three things you always know:

- **Where** — a file's path is its meaning, chosen by what the file is *about*.
  Two homes are provided: **Documents** (where authored work lives when it has
  no more specific home) and **Downloads** (what arrived from outside — uploads,
  observations from connected apps). Everything else at the top level is a
  meaning-named folder someone created (e.g. a folder for a specific deal,
  project, or topic). You may create one by writing a file into it — you don't
  ask permission to name a new folder for your work.
- **Whether** — a grant decides if you may write a given path. Most of the home
  is yours; a few regions (the system's own settings + runtime state) are not
  yours to author. If a write isn't permitted, you'll be told; write elsewhere.
- **Who** — every write is attributed to you and versioned. Nothing is silently
  overwritten; the history is walkable.

Write by meaning, honor the grant, and your work accumulates as an attributed
part of the shared workspace."""


# =============================================================================
# The participant commons contract (ADR-533 D1) — the SINGULAR clauses
# =============================================================================
# The etiquette every LLM participant needs to behave correctly in the commons,
# authored ONCE here and composed per surface. Same DP33 "collapse to data" move
# PARTICIPANT_FILESYSTEM_MODEL made for the filesystem model (ADR-424 D1),
# extended to the rest of the contract.
#
# WHO COMPOSES THESE: the lane frame (`services/lane_runner.py`) and the interop
# binding (`api/mcp_server/server.py`). The wake spine is Altitude 1 and is out of
# ADR-533's scope. A surface COMPOSES these constants — it never restates a clause
# inline. That is the whole point, and `test_adr533_participant_contract.py`
# ratchets it (it asserts the composed OUTPUT carries each clause verbatim).
#
# WHAT DOES *NOT* LIVE HERE (ADR-533 D6): workspace-SPECIFIC intent (the MANDATE
# head the lane injects). These constants are kernel-universal — true of every
# workspace, therefore data. Workspace intent is per-workspace and stays on the
# surfaces that already carry it. The distinction is the ADR's boundary: the
# commons contract is HOW THE WORKSPACE WORKS; the mandate is WHAT IT IS FOR.
#
# EDITING RULE: these are prose clauses, deliberately not pinned by any gate's
# assertion (ADR-533 D5 — the ratchet asserts a constant is IMPORTED and composed,
# never what it says). Edit the wording freely; the gates stay green.

#: How the shared, versioned commons behaves — and the transcript's non-role in it.
#: The "through files, never through your transcript" clause is load-bearing: it is
#: what makes a participant leave durable work instead of conversational residue
#: (ADR-457 D2 — the transcript is never the system of record).
PARTICIPANT_COMMONS_CONTRACT = """\
This workspace is a SHARED, versioned filesystem (the commons) that several
humans and AIs work through. Your conversation is private to this session, but
everything you write to files is shared, attributed, and visible to every member
on the workspace timeline. The durable output of your work belongs in FILES —
the transcript is not shared memory. Other members and other AI sessions
collaborate with you THROUGH these files, never through your transcript; leave
files other actors can pick up."""

#: What a write RECORDS. Kept separate from the commons clause because the
#: attribution SUBJECT is surface-specific ("{member} via {model}" on a lane, the
#: connector identity on interop) — the RULE is universal, the rendering is not.
#:
#: DELIBERATE SENTENCE FRAGMENT — it begins mid-clause ("and versioned with…").
#: Each surface supplies the subject it can name honestly and appends this:
#:   lane:    'Every write attributes as "Kevin via Claude Sonnet", ' + RULE
#:   interop: 'Every write is signed as you, ' + RULE
#: A surface that restated the whole sentence would re-fork the clause — which is
#: what ADR-533 D1 exists to prevent. Keep it a fragment.
PARTICIPANT_ATTRIBUTION_RULE = """\
and versioned with full history — writes are revertible, never silently
destructive, and the history is walkable."""

#: The reference edge (ADR-448). Authorable from every write-capable surface as of
#: ADR-533 D3 — before that, interop could READ the edge but never author it.
PARTICIPANT_CITATION_RULE = """\
Cite your sources: when you author a file FROM another file (something that
arrived, a shared reference, any file you read and built on), pass
derived_from=[its path(s)] on the write. The workspace uses that edge to show
what was made from what and to warn before a source is deleted."""

#: Read-before-write. Its own clause because the VERBS differ per surface (a lane
#: names SearchFiles/ListFiles/ReadFile; interop names open/recall) — the surface
#: appends its own verb list to this stem.
PARTICIPANT_READ_BEFORE_WRITE = """\
Read before writing: check what already exists before creating or overwriting."""

#: Format discipline (ADR-254). The narrow, high-value half: a participant that
#: hand-authors machine config breaks the parsers that read it.
PARTICIPANT_FORMAT_DISCIPLINE = """\
Prose documents are .md. Machine config is _*.yaml (don't author these unless
asked)."""


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
# ADR-445 §7 Phase 4 — per-member spend caps (the owner's abuse lever; ADR-391
# Layer ②). One ceiling per principal on their draw from the shared workspace pool.
# Owner-authored only (the owner bounds a member); the member cannot lift their own
# cap. Machine-parsed yaml (a map of principal_id → cap_usd). Read by the balance
# gate to block a capped member while the pool is non-zero for others.
GOVERNANCE_MEMBER_CAPS_PATH = "governance/_member_caps.yaml"

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
# ADR-432 D1c: OPERATION_BRAND_PATH removed — Brand retired (no producing path
# read operation/BRAND.md; brand voice homes per-agent when load-bearing).
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
#   3. inbound/  — the RAW INTAKE LANE (ADR-376 / DP32), EXCEPT inbound/uploads/.
#      Every machine/external file here is an immutable attributed observation of
#      what arrived from the outside: raw is RETAINED and reasoned-against, NEVER
#      rewritten. Moving/renaming/trashing a record of what came in is a category
#      error — the operator reads the raw and corrects the DERIVED understanding,
#      not the observation. Added by ADR-422 D2. The exception: inbound/uploads/
#      is the HUMAN raw lane (ADR-395 relocated uploads here from the top-level
#      uploads/ root) and STAYS organizable — the operator owns what they
#      uploaded. Only NON-upload inbound/ (connector/MCP/web observations) carves.
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
      - under inbound/ (EXCEPT inbound/uploads/) → False (immutable raw intake,
        ADR-376 — retained, never rewritten). inbound/uploads/ is the HUMAN raw
        lane (ADR-395) and stays organizable — the operator owns what they
        uploaded.
      - everything else → True (constitution/persona/operation/uploads/... prose)
    """
    rel = path.strip().lstrip("/")
    if rel.startswith("workspace/"):
        rel = rel[len("workspace/"):]
    if rel.startswith(SYSTEM_ROOT):
        return False
    if rel.startswith(INBOUND_ROOT) and not rel.startswith(INBOUND_UPLOADS_ROOT):
        return False
    leaf = rel.rsplit("/", 1)[-1]
    if leaf.startswith("_") and leaf.lower().endswith(_MACHINE_CONFIG_EXTS):
        return False
    return True


# ADR-570 D4: the prose text class — the substrate's prose currency as a
# FORMAT class. Membership here answers "is this the kind of file a member
# may edit as text"; WHERE a given principal may write is always
# `_is_path_locked_for_principal` (class ceiling + grants), and placement
# integrity (system/, raw inbound/, machine-config leaves) is
# `operator_can_organize` — the door composes all three, this predicate
# never re-derives them.
_PROSE_DOCUMENT_EXTS = (".md", ".markdown", ".txt")


def is_prose_document(path: str) -> bool:
    """True iff `path` is a prose text document (ADR-570 D4).

    Format class only: `.md`/`.markdown`/`.txt`, excluding `_`-prefixed
    leaves (the underscore marks machine-tended state per ADR-254 — those
    keep their existing narrow doors) and any traversal-shaped path.
    """
    if ".." in path:
        return False
    leaf = path.rsplit("/", 1)[-1]
    if leaf.startswith("_"):
        return False
    return leaf.lower().endswith(_PROSE_DOCUMENT_EXTS)


# =============================================================================
# FOLDER MARKERS — an empty folder is expressible (ADR-588 D1)
# =============================================================================
# Folders do not exist in the substrate: a folder exists iff a file exists under
# its path prefix, and the tree is DERIVED from paths (`_build_tree`). That made
# an EMPTY folder inexpressible, and the pre-ADR-588 `create_folder` worked
# around it by seeding a `README.md` attributed to "operator" — a signed revision
# the operator never authored, in the one ledger whose whole value is that its
# attribution is true.
#
# The marker replaces the seed. It is a real `workspace_files` row at the
# FOLDER's own path, carrying the filesystem's own directory MIME type:
#
#     path         = "/workspace/deals/acme/"     ← TRAILING SLASH, always
#     content_type = "inode/directory"
#     content      = ""                            (a directory has no body)
#
# THE TRAILING SLASH IS LOAD-BEARING, not cosmetic. It is what makes the marker
# unambiguously not-a-file at every path-shaped consumer, including ones that
# never learn the content_type:
#   · `git_export._repo_rel` already returns None for `rel.endswith("/")` — the
#     export excludes markers for free, and can never write a zero-byte blob
#     that collides with a real directory of the same name.
#   · `UserMemory.list` (non-recursive) already yields "acme/" for such a row —
#     it reads as a directory, which is exactly what it is.
#   · A file and its folder can never collide on the unique (workspace_id, path)
#     index: "…/acme" and "…/acme/" are distinct keys.
# Consumers that DO see the row filter on `is_folder_marker`, below — one
# predicate, the ADR-424/ADR-395 `is_upload_projection` precedent.
#
# A marker is a CONVENIENCE, not a requirement: a folder holding files still
# exists through those files with no marker row, exactly as before. The marker
# only carries the empty case. Deleting the last file in a marked folder leaves
# the folder — which is Finder/Explorer grammar, and the point.
FOLDER_MARKER_CONTENT_TYPE = "inode/directory"


def folder_marker_path(folder_path: str) -> str:
    """The marker row's path for a folder — absolute, trailing-slash (ADR-588).

    Accepts any spelling of the folder ("deals/acme", "/workspace/deals/acme",
    "workspace/deals/acme/") and returns the single canonical marker key
    "/workspace/deals/acme/".
    """
    rel = (folder_path or "").strip().lstrip("/")
    if rel.startswith("workspace/"):
        rel = rel[len("workspace/"):]
    rel = rel.strip("/")
    return f"/workspace/{rel}/" if rel else "/workspace/"


def is_folder_marker(path: str, content_type: Optional[str] = None) -> bool:
    """True iff this row is a folder marker, not a document (ADR-588 D1).

    The SINGULAR predicate every listing / search / export / embed consumer
    filters on, so a marker never renders as a file to an operator, an LLM
    participant, or an export. Follows the `is_upload_projection` precedent
    (services/documents.py): hide at PRESENTATION, never at authorization.

    Path-shape alone is sufficient and is the primary test — a trailing slash
    is not a legal file path anywhere in the substrate (`write_revision` writes
    leaf paths; `_repo_rel` already rejects it). `content_type` is accepted as a
    corroborating signal for the callers that already select the column, so a
    consumer holding only one of the two facts can still answer correctly.
    """
    if content_type == FOLDER_MARKER_CONTENT_TYPE:
        return True
    return (path or "").rstrip().endswith("/")


# =============================================================================
# Reserved top-level folder names (ADR-588 D3)
# =============================================================================
# PARTICIPANT_FILESYSTEM_MODEL *tells* every participant that two homes are
# provided, by their DISPLAY names: "Documents" and "Downloads". Those names are
# addresses the participant was handed. A second TOP-LEVEL root literally named
# `Documents/` is an exact visual twin of the real home (`root_metadata` title-
# cases an unknown root, so `/workspace/Documents/` renders as "Documents" beside
# `operation/`'s "Documents"), and an operator cannot tell which one their work
# landed in. Refuse it at the create door with the honest reason.
#
# Only DEPTH 1 collides. A nested `Projects/Documents/` is an ordinary folder
# and is allowed — the same way ~/Projects/Documents collides with nothing.
#
# Derived from WORKSPACE_ROOTS, never hand-listed: a new home added there is
# reserved automatically. Both the display label ("Documents") and the kernel
# root name ("operation") are reserved — creating `operation/` by hand would
# merge a new folder into the real home invisibly.


def _folder_name_key(name: str) -> str:
    """Fold a folder name to its comparison key (case/space/dash-insensitive)."""
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())


def reserved_top_level_folder_reason(name: str) -> Optional[str]:
    """The operator-facing refusal for a reserved TOP-LEVEL folder name, or None.

    ADR-588 D3. Returns a sentence naming what already holds the name and what
    it is for — never a bare "invalid name", which would leave the operator
    guessing why a perfectly ordinary word was refused.
    """
    key = _folder_name_key(name)
    if not key:
        return None
    for root_name, meta in WORKSPACE_ROOTS.items():
        display = meta.get("display_name") or root_name
        if key in (_folder_name_key(root_name), _folder_name_key(display)):
            return (
                f"{display} already exists — {meta.get('description') or 'it is one of your workspace homes.'} "
                f"Pick another name, or put this folder inside {display}."
            )
    return None


# =============================================================================
# HOME ALIASES — the told-name is an accepted address (ADR-588 D2)
# =============================================================================
# PARTICIPANT_FILESYSTEM_MODEL (above) tells EVERY LLM participant, verbatim:
#
#     Two homes are provided: **Documents** (where authored work lives when it
#     has no more specific home) and **Downloads** (what arrived from outside…)
#
# Those are DISPLAY names. The kernel paths are `operation/` and `inbound/`, and
# before ADR-588 nothing translated between them at any door. A participant that
# used the vocabulary we handed it therefore wrote to a path that did not mean
# what it was told it meant. Production ledger, before the fix:
#
#     yarnnn:mcp:claude.ai | save via interop: Documents/adr572-clickpass-brief.md
#     yarnnn:mcp:claude.ai | save via interop: Documents/adr373-d6-roundtrip.md
#
# The write returned 200. It was attributed. And it created a REAL top-level
# root `/workspace/Documents/`, which `root_metadata()` title-cases back into
# the display name "Documents" — an exact visual twin of `operation/`'s. That is
# the ADR-373 D6 INCORRECT-SUCCESS class: success, attribution, wrong place, no
# signal. `Downloads` → `inbound/` had the identical hole; it just had not been
# hit yet.
#
# THE DECISION IS TO RESOLVE, NOT REFUSE. Refusing would break live connectors
# mid-flight, and it would be the wrong answer besides: the participant used the
# exact vocabulary this codebase handed it, so honoring that name is correct.
# The resolution is not silent — the write lands at the real path, and the real
# path is what the response, the ledger, and the tree all show.
#
# SCOPE: the FIRST path segment only. A nested `operation/Documents/notes.md` is
# an ordinary folder someone named, exactly as ~/Projects/Documents is on any
# real machine — aliasing it would be the same category of silent misroute this
# exists to close.
#
# This map's keys must stay in sync with what PARTICIPANT_FILESYSTEM_MODEL
# actually says; `test_adr588_folder_markers_and_home_aliases.py` asserts each
# key appears in that prose, so renaming a home in the model without updating
# this map fails the gate rather than silently re-opening the hole.
HOME_ALIASES: dict[str, str] = {
    "Documents": OPERATION_ROOT.rstrip("/"),   # → "operation"
    "Downloads": INBOUND_ROOT.rstrip("/"),     # → "inbound"
}

_HOME_ALIAS_LOOKUP = {k.lower(): v for k, v in HOME_ALIASES.items()}


def resolve_home_alias(rel_path: str) -> str:
    """Resolve a told-name home in the FIRST segment to its kernel path.

    ADR-588 D2. `Documents/q3.md` → `operation/q3.md`; `Downloads/x` →
    `inbound/x`; case-insensitive. Any other path is returned byte-identical,
    so every existing caller is unchanged.

    Takes and returns a WORKSPACE-RELATIVE path (no leading slash, no
    `/workspace/` prefix) — the form the write door already normalizes to.
    """
    rel = rel_path or ""
    if not rel or rel.startswith("/"):
        return rel
    head, sep, tail = rel.partition("/")
    real = _HOME_ALIAS_LOOKUP.get(head.lower())
    if real is None:
        return rel
    return f"{real}{sep}{tail}" if sep else real
