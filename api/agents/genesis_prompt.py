"""Genesis-by-Reviewer prompt assembly (ADR-280 §2.D4 + §3).

The genesis wake is the one-shot Reviewer wake that authors a workspace's
canonical `_workspace_guide.md` from kernel-universal "how" template +
active bundle's `substrate_abi` declaration. Fires once per workspace
lifetime, synchronously after `workspace_init.py`'s deterministic scaffold
completes.

This module provides:
  - `KERNEL_TEMPLATE` constants (universal "how" content — same for every workspace)
  - `assemble_genesis_prompt(substrate_abi)` — composes the full directive the
    Reviewer reads at the genesis wake (kernel template + bundle ABI + author-
    the-guide instructions)

The Reviewer reads the genesis prompt as a recurrence-fire trigger
(`recurrence_prompt` shape per `ReviewerContext`), runs its tool loop,
calls `WriteFile(/workspace/_workspace_guide.md, ...)` with `authored_by=
"reviewer:{occupant}/genesis"` per ADR-209 §D8.

After genesis, every subsequent Reviewer wake reads `_workspace_guide.md`
as canon — like principles.md or MANDATE.md. The genesis-wake persona
prose is structurally distinct from steady-state persona prose (which
references the workspace guide rather than carrying its content).

Companion:
  - `services/workspace_guide.py` — kernel-side reader
  - `services/bundle_reader.py::get_substrate_abi_for_workspace` — bundle data source
  - `services/workspace_init.py` — invoker
"""

from __future__ import annotations

from typing import Any


#: Stable slug for the genesis recurrence-fire shape — surfaced in
#: `ReviewerContext.recurrence_slug` so the Reviewer's audit trail attributes
#: substrate writes during genesis to `reviewer:{occupant}/genesis` per ADR-209 D8.
GENESIS_RECURRENCE_SLUG = "workspace-genesis"


#: Universal kernel-shipped path-zone declarations — present in every
#: workspace regardless of program. Per ADR-280 §3 + §D5. The Reviewer
#: composes these into the workspace guide alongside bundle-declared zones.
#:
#: Each entry is shaped like the bundle MANIFEST's substrate_abi.path_zones
#: schema (per ADR-223 §3.bis) — keeps composition uniform.
KERNEL_PATH_ZONES = [
    # operator-canon — operator-authored library, locked from Reviewer
    {"path": "context/_shared", "role": "operator-canon",
     "purpose": "operator's standing intent — MANDATE, IDENTITY, BRAND, AUTONOMY, PRECEDENT, _preferences"},
    {"path": "context/_shared/_locks.yaml", "role": "operator-canon",
     "purpose": "operator-authored lock policy"},
    {"path": "uploads", "role": "operator-canon",
     "purpose": "operator-contributed reference material"},
    # operator-canon — Reviewer seat identity files
    {"path": "review/IDENTITY.md", "role": "operator-canon",
     "purpose": "Reviewer seat persona declaration"},
    {"path": "review/principles.md", "role": "operator-canon",
     "purpose": "Reviewer's declared judgment framework"},
    {"path": "review/_principles.yaml", "role": "operator-canon",
     "purpose": "machine-parsed Reviewer thresholds"},
    # system-ledger — infrastructure-rendered append-only, locked from LLM
    {"path": "review/OCCUPANT.md", "role": "system-ledger",
     "purpose": "current Reviewer seat occupant (rotation primitive writes)"},
    {"path": "review/handoffs.md", "role": "system-ledger",
     "purpose": "append-only seat-occupant rotation log"},
    {"path": "review/calibration.md", "role": "system-ledger",
     "purpose": "per-occupant judgment-vs-outcome rolling windows"},
    {"path": "review/decisions.md", "role": "system-ledger",
     "purpose": "Reviewer's judgment lineage (proposal verdicts, operation-shaping decisions)"},
    {"path": "memory/recent.md", "role": "system-ledger",
     "purpose": "back-office narrative digest (24h rollup)"},
    # reviewer-workbench — Reviewer-authored, no lock
    {"path": "review/notes.md", "role": "reviewer-workbench",
     "purpose": "Reviewer's working scratch across wakes"},
    {"path": "working", "role": "reviewer-workbench",
     "purpose": "ephemeral scratch (24h TTL)"},
    # running-narrative — append-shape, mechanical or judgment-fed
    {"path": "memory", "role": "running-narrative",
     "purpose": "YARNNN orchestration accumulation (awareness, _playbook, style, notes)"},
    {"path": "agents", "role": "running-narrative",
     "purpose": "per-agent substrate (AGENT.md + memory + outputs)"},
    {"path": "reports", "role": "running-narrative",
     "purpose": "per-recurrence deliverable outputs"},
    {"path": "operations", "role": "running-narrative",
     "purpose": "per-recurrence action state"},
    # kernel-index — kernel-managed, regenerable
    {"path": "_recurrences.yaml", "role": "kernel-index",
     "purpose": "scheduling-index source of truth (kernel reads, Schedule primitive writes)"},
]


#: Universal envelope inputs the Reviewer needs at every wake regardless of
#: program. Per ADR-280 §D5 — bundles only declare additions to this base.
KERNEL_REVIEWER_WAKE_ENVELOPE = [
    {"key": "identity_md", "path": "review/IDENTITY.md", "optional": False},
    {"key": "principles_md", "path": "review/principles.md", "optional": False},
    {"key": "precedent_md", "path": "context/_shared/PRECEDENT.md", "optional": True},
    {"key": "mandate_md", "path": "context/_shared/MANDATE.md", "optional": False},
    {"key": "autonomy_md", "path": "context/_shared/AUTONOMY.md", "optional": False},
    {"key": "preferences_yaml", "path": "context/_shared/_preferences.yaml", "optional": True},
]


#: Universal prose body template — sections the Reviewer authors at genesis.
#: Per ADR-280 §3 + §D5 — three required sections; the Reviewer narrates the
#: program-specific "What this workspace contains" content from the bundle's
#: substrate_abi declaration.
PROSE_TEMPLATE = """\
# Workspace Guide

This is your workspace guide. You (the Reviewer) read it at every wake to
understand what substrate exists in this workspace and how to navigate it.
The frontmatter (machine-parsed) declares path zones and their roles plus
the substrate you need pre-loaded at every wake; the prose body (which you
read) narrates the contract.

## How this workspace works

Substrate is the persistence layer (FOUNDATIONS Axiom 1) — every piece of
state that survives between invocations lives in `/workspace/` files.
Computation (the scheduler, you the Reviewer, mechanical primitives) is
stateless: read substrate, act, write substrate, terminate. Substrate is
the bus over which the runtime operates (Axiom 1 fourth sub-clause); there
is no parallel control-flow channel between you and the System Agent —
substrate revisions are the channel.

Every write to substrate is **attributed and retained** (Authored Substrate,
ADR-209). Every revision carries an `authored_by` identity (`operator`,
`reviewer:{occupant}`, `system:{actor}`, etc.) and a short message.
Revisions accumulate; nothing is destructively overwritten. You can inspect
prior revisions of any path via `ListRevisions` / `ReadRevision` /
`DiffRevisions` — substrate carries history natively, no sibling audit
table.

The path zones declared in this guide's frontmatter are guaranteed to be
the substrate topology — you do not need to `ListFiles` defensively before
writing within them.

**Six roles classify every path zone** (each role implies its writer +
reader + lock + retention; see frontmatter `path_zones[*].role`):

- **`operator-canon`** — operator-authored library (MANDATE, IDENTITY,
  BRAND, AUTONOMY, principles, declared strategy + risk floors, etc.).
  You can read; you cannot write directly. To propose changes, use
  `Clarify` to ask the operator or `ProposeAction` to file a structured
  proposal.
- **`reviewer-workbench`** — your working substrate (notes.md, working/).
  You can read and write freely. Use this for patterns, observations, and
  scratch you want to retain across wakes that aren't yet operation-shaping.
- **`system-ledger`** — infrastructure-rendered append-only logs
  (decisions.md, calibration.md, handoffs.md, OCCUPANT.md, memory/recent.md).
  You supply the content (via your `ReturnVerdict` for decisions.md);
  infrastructure renders the entries. You do not WriteFile directly.
- **`world-mirror`** — external state mirrored into substrate by mechanical
  primitives (broker positions, account balances, etc.). You read; you
  never write. Mechanical primitives keep these fresh between your wakes.
- **`running-narrative`** — append-shape substrate fed by mechanical or
  judgment work. The declared writer (named per zone) writes; you can read
  + append when explicitly authorized.
- **`kernel-index`** — kernel-managed regenerable indexes. The kernel
  writes; you read but do not write outside the kernel's primitive surface
  (e.g., the Schedule primitive writes to `_recurrences.yaml`, not your
  `WriteFile` directly).

## What NOT to write to operator-canon

Even when you have insights about the operator's intent or framework, do
NOT write to `operator-canon` paths directly. The lock policy will reject
the write, but the discipline is upstream of the lock — the operator
authors their own canon, and your role is to surface insight via Clarify
/ ProposeAction so the operator authors the change with their own
attribution. Specifically:

- Do not "tighten" a MANDATE because outcomes suggest a tighter scope.
  Instead: `Clarify` proposing the tightening; let the operator author it.
- Do not adjust `principles.md` thresholds because calibration suggests a
  shift. Instead: `ProposeAction` with the structured threshold change.
- Do not synthesize an `IDENTITY.md` revision based on observed operator
  behavior. The persona is the operator's authored character; do not
  paraphrase it.

The right home for your own evolving understanding is your
`reviewer-workbench` substrate (notes.md). The right channel for proposed
changes to operator canon is the operator's approval surface (Clarify or
ProposeAction).

## When things diverge

This guide describes the substrate topology; it does not enforce it. When
you encounter substrate the guide doesn't classify (operator dropped files
in an undeclared zone, a future Agent wrote somewhere new, a bundle update
declares paths your guide doesn't yet know about):

- Treat unclassified substrate as `running-narrative` for your own reading
  purposes (most permissive role — won't break your perception).
- Surface the drift to the operator through normal authoring channels:
  `Clarify` if it's worth their immediate attention, or note it in your
  `notes.md` workbench and let it surface on the daily-update pointer.
- Never silently classify or relocate substrate to enforce this guide.
  Like Claude Code refusing to silently restructure a codebase, your role
  is to surface drift, not erase it.

The same discipline applies to bundle ABI updates: if an active bundle
declares paths or envelope inputs your guide doesn't yet reflect, surface
the drift via `Clarify` proposing the merge — operator chooses.
"""


def assemble_genesis_prompt(
    program_slug: str | None,
    substrate_abi: dict[str, Any] | None,
) -> str:
    """Compose the full genesis directive the Reviewer reads at the genesis wake.

    Combines:
      - Universal kernel "how" content (KERNEL_PATH_ZONES + KERNEL_REVIEWER_WAKE_ENVELOPE
        + PROSE_TEMPLATE — same for every workspace)
      - Program-specific "what" content from the active bundle's substrate_abi
        declaration (path zones + envelope inputs unique to this program)
      - Author-the-guide instructions (the Reviewer's directive — what to write,
        where, with what attribution)

    The output is a single prose directive intended for `ReviewerContext.recurrence_prompt`.
    The Reviewer reads it, runs its tool loop, calls `WriteFile` to author
    `/workspace/_workspace_guide.md`, returns a verdict.

    Args:
        program_slug: Active program slug (e.g., "alpha-trader"), or None for
            generic workspaces (no program activated).
        substrate_abi: The aggregated substrate_abi from
            `bundle_reader.get_substrate_abi_for_workspace` —
            `{path_zones: [...], reviewer_wake_envelope: [...]}`. Empty
            (`{"path_zones": [], "reviewer_wake_envelope": []}`) for generic
            workspaces.

    Returns:
        A single prose directive string.
    """
    abi = substrate_abi or {"path_zones": [], "reviewer_wake_envelope": []}
    bundle_zones = abi.get("path_zones", [])
    bundle_envelope = abi.get("reviewer_wake_envelope", [])

    program_section = ""
    if program_slug and bundle_zones:
        zones_yaml = "\n".join(
            f"      - path: {z['path']}\n"
            f"        role: {z['role']}\n"
            f"        purpose: {z.get('purpose', '(see bundle)')}"
            + (f"\n        bundle: {program_slug}" if z.get("_program_slug") else "")
            for z in bundle_zones
        )
        envelope_yaml = ""
        if bundle_envelope:
            envelope_lines = []
            for e in bundle_envelope:
                line = f"      - key: {e['key']}"
                if "path" in e:
                    line += f"\n        path: {e['path']}"
                elif "path_glob" in e:
                    line += f"\n        path_glob: {e['path_glob']}"
                    if "summarizer" in e:
                        line += f"\n        summarizer: {e['summarizer']}"
                line += f"\n        optional: {str(e.get('optional', False)).lower()}"
                envelope_lines.append(line)
            envelope_yaml = "\n".join(envelope_lines)

        program_section = f"""

## Program-specific declarations (from the active program bundle)

This workspace runs the **{program_slug}** program. The bundle declares
the following program-shaped path zones and envelope inputs, in addition
to the universal kernel-shipped declarations above. Compose these into
the workspace guide's frontmatter alongside the universal entries.

Bundle path zones:
{zones_yaml}

Bundle envelope inputs:
{envelope_yaml or '      (none)'}

When you author the workspace guide's prose body's `## What this workspace
contains` section, narrate these program-specific zones — name them, give
their purpose, explain how the operator interacts with them. Use the
`purpose` field above as your starting point but write the narration in
your own voice (operator will read this; make it operator-legible).
"""

    return f"""\
You are the Reviewer for this workspace at its genesis wake — the very
first time you wake into this workspace's substrate. Your one and only
task at this wake is to author the workspace's canonical workspace guide
at `/workspace/_workspace_guide.md`. After this wake completes, every
subsequent wake of yours (whether reactive or addressed) will read this
guide as canon — like you read MANDATE.md, IDENTITY.md, and principles.md
at every wake.

The workspace guide is the singular operator-and-Reviewer-readable doc
declaring this workspace's substrate topology. It has YAML frontmatter
(structured, machine-parsed by the kernel for lock policy and wake
envelope assembly) plus a prose body (LLM and operator readable, narrating
the contract). One file, two consumers, no sync problem.

# Universal kernel template (the "how" — same for every workspace)

These path zones are universal — present in every workspace regardless
of program. Compose them into the workspace guide's frontmatter alongside
any program-specific zones.

Universal path zones:
{_format_zones_for_prompt(KERNEL_PATH_ZONES)}

Universal Reviewer wake envelope inputs:
{_format_envelope_for_prompt(KERNEL_REVIEWER_WAKE_ENVELOPE)}
{program_section}
# Author the guide

Use `WriteFile` to author `/workspace/_workspace_guide.md`. The file
structure is:

1. **YAML frontmatter** at the top (between `---` delimiters) declaring:
   - `schema_version: 1`
   - `path_zones`: a list combining the universal entries above with the
     program-specific entries (if any). Each entry: `path`, `role`,
     `purpose`, optionally `bundle` (program slug attribution).
   - `reviewer_wake_envelope`: a list combining the universal entries
     above with the program-specific entries. Each entry: `key`, `path`
     or `path_glob` (with `summarizer` for globs), `optional`.
   - `locks`: an empty `{{add: [], remove: []}}` block (operator extends
     later if they want to override role-derived defaults).

2. **Prose body** below the closing `---`. Use the following template
   verbatim as the canonical "how" content (it teaches you and the
   operator how this workspace works), then add a `## What this workspace
   contains` section narrating the path zones (universal + program-specific)
   in operator-legible prose:

```
{PROSE_TEMPLATE}
```

When you call `WriteFile`, the kernel will record your authorship with
`authored_by="reviewer:{{occupant}}/genesis"` per ADR-209 §D8 — this
attribution stays in the revision chain so future readers know the guide
originated at genesis. Subsequent revisions you make will carry the
standard `reviewer:{{occupant}}` attribution; the operator's revisions
will carry `operator`.

After authoring the guide, return a verdict via `ReturnVerdict` with
`verdict: "stand_down"` and `reasoning` briefly noting that genesis
completed successfully. Do not call any other primitives; this wake is
exclusively for genesis. Subsequent wakes will read the guide you just
authored and operate over the workspace normally."""


def _format_zones_for_prompt(zones: list[dict[str, Any]]) -> str:
    """Render path zones as YAML-shape prose for the genesis directive."""
    return "\n".join(
        f"  - path: {z['path']}\n"
        f"    role: {z['role']}\n"
        f"    purpose: {z.get('purpose', '')}"
        for z in zones
    )


def _format_envelope_for_prompt(envelope: list[dict[str, Any]]) -> str:
    """Render envelope entries as YAML-shape prose for the genesis directive."""
    lines = []
    for e in envelope:
        line = f"  - key: {e['key']}"
        if "path" in e:
            line += f"\n    path: {e['path']}"
        elif "path_glob" in e:
            line += f"\n    path_glob: {e['path_glob']}"
            if "summarizer" in e:
                line += f"\n    summarizer: {e['summarizer']}"
        line += f"\n    optional: {str(e.get('optional', False)).lower()}"
        lines.append(line)
    return "\n".join(lines)
