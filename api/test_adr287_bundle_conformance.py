"""ADR-287 — Bundle Conformance Discipline.

Per ADR-287 D1: every kernel ADR that introduces a bundle-side
requirement must extend THIS test in the same commit as the ADR ships.
The test is the single source of truth for "what every active/deferred
bundle must provide." Adding a requirement without extending the test is
a process violation surfaced at code review.

Per ADR-287 D2: each test function walks every active/deferred bundle in
docs/programs/{slug}/ and asserts conformance to one ADR's bundle-side
requirement. Failure messages point at the specific bundle + ADR + the
missing surface, so the gap is operator-actionable.

Per ADR-287 D4: tests organized by ADR. New ADR with bundle requirements
→ new section in this file. Future ADRs add `# ADR-XXX — ...` sections
with new test functions following the same pattern.

Pure-fs assertions. No DB, no network, no LLM. Fast (sub-second).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PROGRAMS_ROOT = REPO_ROOT / "docs" / "programs"
PERSONAS_YAML = REPO_ROOT / "docs" / "alpha" / "personas.yaml"


# =============================================================================
# Helpers — walk active/deferred bundles + personas
# =============================================================================


def _all_active_or_deferred_bundles() -> Iterator[Path]:
    """Walk every bundle with status in (active, deferred). reference and
    archived bundles are excluded — they don't ship live or pending-live,
    so conformance doesn't apply."""
    if not PROGRAMS_ROOT.is_dir():
        return
    for program_dir in sorted(PROGRAMS_ROOT.iterdir()):
        manifest_path = program_dir / "MANIFEST.yaml"
        if not manifest_path.exists():
            continue
        try:
            data = yaml.safe_load(manifest_path.read_text()) or {}
        except yaml.YAMLError:
            continue
        if data.get("status") in ("active", "deferred"):
            yield program_dir


def _personas_for_active_or_deferred_bundles() -> Iterator[dict]:
    """Walk every persona row whose declared program is active or deferred.
    Returns the raw persona dict (not Persona dataclass) so this test stays
    independent of the Persona schema (which itself is mutable across ADRs)."""
    raw = yaml.safe_load(PERSONAS_YAML.read_text()) or {}
    active_or_deferred_programs = {b.name for b in _all_active_or_deferred_bundles()}
    for p in raw.get("personas", []):
        if p.get("program") in active_or_deferred_programs:
            yield p


def _load_recurrences(bundle_dir: Path) -> list[dict]:
    """Load _recurrences.yaml entries from a bundle's reference-workspace."""
    rec_path = bundle_dir / "reference-workspace" / "_recurrences.yaml"
    if not rec_path.exists():
        return []
    try:
        data = yaml.safe_load(rec_path.read_text()) or {}
    except yaml.YAMLError:
        return []
    return data.get("recurrences", []) or []


def _load_captures(bundle_dir: Path) -> list[dict]:
    """Load _captures.yaml entries from a bundle's reference-workspace (ADR-393).

    Captures are the deterministic-intake declarations the capture lane runs
    outside the wake funnel. A watch's Trigger (cadence) may live on a capture
    (a standing web/repo watch — track-sources/track-repo) or, historically, a
    recurrence; both are valid Trigger homes for a watch declaration."""
    cap_path = bundle_dir / "reference-workspace" / "_captures.yaml"
    if not cap_path.exists():
        return []
    try:
        data = yaml.safe_load(cap_path.read_text()) or {}
    except yaml.YAMLError:
        return []
    return data.get("captures", []) or []


# =============================================================================
# ADR-284 — Standing Intent + OCCUPANT runtime-alignment
# =============================================================================
#
# Per ADR-284 D6 + D8: every bundle's persona/IDENTITY.md + persona/principles.md
# references standing_intent.md; judgment-mode recurrences pair stand-down
# with a standing-intent update directive; persona rows declare
# expected.occupant_attribution + include persona/OCCUPANT.md in core_files.


def test_adr284_d8_bundle_identity_references_standing_intent():
    """ADR-284 D8: every active/deferred bundle's persona/IDENTITY.md must
    reference standing_intent.md. Without it the Reviewer persona prompt
    references a substrate file the bundle never tells operators about."""
    bundles = list(_all_active_or_deferred_bundles())
    assert bundles, "no active/deferred bundles found in docs/programs/"

    for bundle in bundles:
        identity_md = bundle / "reference-workspace" / "review" / "IDENTITY.md"
        if not identity_md.exists():
            continue  # bundle doesn't ship persona/IDENTITY.md at all; out of ADR-284 scope
        content = identity_md.read_text()
        assert "standing_intent" in content, (
            f"bundle '{bundle.name}' persona/IDENTITY.md does not reference "
            f"standing_intent.md. ADR-284 D8 requires every bundle's "
            f"IDENTITY.md to name the standing-intent substrate so the "
            f"Reviewer persona prompt aligns with bundle-shipped substrate. "
            f"Add a section like '## Standing intent — my forward-looking "
            f"substrate (ADR-284)' citing /workspace/persona/standing_intent.md."
        )


def test_adr284_d8_bundle_principles_references_standing_intent():
    """ADR-284 D8: every active/deferred bundle's persona/principles.md must
    reference standing_intent.md, typically under the 'default posture'
    framing where the no-fire / no-findings cycle's standing-intent update
    is the substrate counterpart to action."""
    for bundle in _all_active_or_deferred_bundles():
        principles_md = bundle / "reference-workspace" / "review" / "principles.md"
        if not principles_md.exists():
            continue
        content = principles_md.read_text()
        assert "standing_intent" in content, (
            f"bundle '{bundle.name}' persona/principles.md does not reference "
            f"standing_intent.md. ADR-284 D8 requires every bundle's "
            f"principles.md to name standing-intent as the substrate "
            f"counterpart to default-posture-action. Add a paragraph under "
            f"the default-posture section."
        )


def test_adr354_judgment_recurrences_do_not_rescript_the_close():
    """ADR-354 (supersedes ADR-284 D6's prompt-string assertion): a judgment-mode
    recurrence prompt must NOT re-script cycle-closing. ADR-284 D6's intent —
    no-fire cycles leave forward-looking evidence — is now owned by the KERNEL
    FRAME ("close every cycle with a verdict or a standing_intent write",
    freddie_agent.py::_compute_minimal_frame), not the prompt. A prompt that
    re-scripts a terminal "else → WriteFile standing_intent THEN
    ReturnVerdict(stand_down)" pre-empts the standing-obligation (DP30)
    reasoning the frame owns: the concrete procedure beats the thin frame
    (the 2026-06-22 full-autonomy probe). So the conformance direction INVERTS:
    the close-scripting markers must be ABSENT.

    Singular Implementation: ADR-284 D6's evidence guarantee is preserved (the
    frame still mandates the standing_intent write on a no-fire cycle); only its
    ENFORCEMENT HOME moved from prompt-string to frame. This test guards the new
    home's invariant — prompts stay operator-instruction-only."""
    # Markers of a re-scripted close (the anti-pattern ADR-354 deletes).
    RESCRIPT_MARKERS = [
        'returnverdict(verdict="stand_down',
        "then returnverdict",
        "required even when",
        "text-only response without returnverdict is\n      forbidden",
    ]
    for bundle in _all_active_or_deferred_bundles():
        for entry in _load_recurrences(bundle):
            mode = entry.get("mode", "judgment")
            if mode != "judgment":
                continue
            prompt = (entry.get("prompt", "") or "").lower()
            slug = entry.get("slug", "<unknown>")
            hit = [m for m in RESCRIPT_MARKERS if m in prompt]
            assert not hit, (
                f"bundle '{bundle.name}' recurrence '{slug}' re-scripts the "
                f"cycle close in its prompt ({hit}). ADR-354: the frame owns "
                f"cycle-closing; the prompt carries only the operator's "
                f"instruction. Delete the terminal stand-down script — the "
                f"frame's 'close every cycle with a verdict or a standing_intent "
                f"write' already guarantees the no-fire evidence."
            )


def test_adr284_d3_persona_rows_have_occupant_attribution():
    """ADR-284 D3: every persona row whose bundle is active/deferred must
    declare expected.occupant_attribution with expected_occupant_class +
    expected_occupant_prefix fields. Without these, verify.py cannot
    detect substrate-runtime drift where OCCUPANT.md's declared occupant
    disagrees with the runtime occupant."""
    personas = list(_personas_for_active_or_deferred_bundles())
    assert personas, "no personas found whose program is active/deferred"

    for p in personas:
        slug = p.get("slug", "<unknown>")
        expected = p.get("expected", {}) or {}
        occ_attr = expected.get("occupant_attribution")
        assert occ_attr, (
            f"persona '{slug}' missing expected.occupant_attribution block. "
            f"ADR-284 D3 requires every persona row whose bundle is "
            f"active/deferred to declare expected_occupant_class + "
            f"expected_occupant_prefix so verify.py can detect "
            f"substrate-runtime drift."
        )
        assert "expected_occupant_class" in occ_attr, (
            f"persona '{slug}' expected.occupant_attribution missing "
            f"expected_occupant_class field."
        )
        assert "expected_occupant_prefix" in occ_attr, (
            f"persona '{slug}' expected.occupant_attribution missing "
            f"expected_occupant_prefix field."
        )


def test_adr284_d3_persona_core_files_includes_occupant_md():
    """ADR-284 D3: every persona row whose bundle is active/deferred must
    list /workspace/persona/OCCUPANT.md in expected.core_files. OCCUPANT.md
    is kernel-scaffolded (workspace_init Phase 5) and bundle-fork-populated
    with the runtime occupant identity; verify.py asserts presence at
    activation time."""
    for p in _personas_for_active_or_deferred_bundles():
        slug = p.get("slug", "<unknown>")
        core_files = (p.get("expected", {}) or {}).get("core_files", []) or []
        assert "/workspace/persona/OCCUPANT.md" in core_files, (
            f"persona '{slug}' expected.core_files does not include "
            f"/workspace/persona/OCCUPANT.md. ADR-284 D3 requires every "
            f"persona row whose bundle is active/deferred to declare "
            f"OCCUPANT.md as a core file so verify.py asserts presence "
            f"after activation."
        )


# =============================================================================
# ADR-285 — Holistic Wake Envelope
# =============================================================================
#
# Per ADR-285 D2: bundle MANIFEST reviewer_wake_envelope entries gain an
# optional `role:` tag. Backward-compatible — entries without explicit
# role default to `operator-canon`. The conformance check asserts that
# when role IS declared, it's one of the six valid taxonomy values.


def test_adr285_d2_envelope_role_tags_are_valid_when_present():
    """ADR-285 D2: when a bundle's reviewer_wake_envelope entry declares
    a `role:` field, it must be one of the six valid substrate roles per
    ADR-281 §3 taxonomy. Missing role tags fall through to the
    operator-canon default and pass (backward-compatible)."""
    valid_roles = {
        "operator-canon",
        "reviewer-workbench",
        "system-ledger",
        "world-mirror",
        "running-narrative",
        "kernel-index",
    }
    for bundle in _all_active_or_deferred_bundles():
        manifest = yaml.safe_load((bundle / "MANIFEST.yaml").read_text()) or {}
        envelope = (
            (manifest.get("substrate_abi") or {}).get("reviewer_wake_envelope") or []
        )
        for entry in envelope:
            if "role" not in entry:
                continue  # backward-compat default
            role = entry["role"]
            assert role in valid_roles, (
                f"bundle '{bundle.name}' reviewer_wake_envelope entry "
                f"'{entry.get('key', '<unknown>')}' declares role='{role}' "
                f"which is not one of the six valid roles "
                f"({sorted(valid_roles)}). Per ADR-285 D2 + ADR-281 §3."
            )


# =============================================================================
# ADR-286 — Kernel/Program Substrate Single-Writer Boundary
# =============================================================================
#
# Per ADR-286 D3: every active bundle ships 13 program-owned substrate
# files. (Deferred bundles ship the same set when they activate.) The
# conformance check asserts these files exist in each active bundle's
# reference-workspace.


# The 13 paths declared bundle-owned by ADR-286 D3.
_ADR286_D3_BUNDLE_OWNED_PATHS = [
    "constitution/MANDATE.md",
    "persona/IDENTITY.md",
    "operation/BRAND.md",
    "operation/CONVENTIONS.md",
    "governance/AUTONOMY.md",
    "governance/_autonomy.yaml",
    "governance/_preferences.yaml",
    "system/awareness.md",
    "persona/IDENTITY.md",
    "persona/principles.md",
    "persona/_principles.yaml",
    "_recurrences.yaml",
    "_workspace_guide.md",
]


def _active_bundles() -> Iterator[Path]:
    """Walk active-only bundles. ADR-286 D3 conformance scopes to bundles
    that ship live; deferred placeholders (e.g., alpha-commerce parking
    lot per ADR-224) are exempt until they graduate to active."""
    for bundle in _all_active_or_deferred_bundles():
        manifest = yaml.safe_load((bundle / "MANIFEST.yaml").read_text()) or {}
        if manifest.get("status") == "active":
            yield bundle


def test_adr286_d3_active_bundle_ships_all_program_owned_paths():
    """ADR-286 D3: every active bundle must ship the 13 program-owned
    substrate files in its reference-workspace/. The kernel stops
    scaffolding these (the kernel only writes for no-program workspaces);
    bundle-fork is the singular writer for active-program workspaces.

    Scoped to active bundles only per the ADR-286 D3 letter ("every active
    bundle"). Deferred bundles (e.g., alpha-commerce parking lot per
    ADR-224) are exempt until they graduate to active; activation-time
    conformance is the gate then. alpha-author is deferred today but the
    paths are already shipped — when it graduates this assertion will
    pass without backfill."""
    for bundle in _active_bundles():
        ref_root = bundle / "reference-workspace"
        for path in _ADR286_D3_BUNDLE_OWNED_PATHS:
            full = ref_root / path
            assert full.exists(), (
                f"bundle '{bundle.name}' (status: active) missing program-"
                f"owned substrate file '{path}'. ADR-286 D3 lists 13 paths "
                f"every active bundle must ship; the kernel no longer "
                f"scaffolds these. Missing file means activation will "
                f"produce a workspace with an incomplete substrate."
            )


# =============================================================================
# ADR-330 — Ground-Truth Intake (the consequence pipe)
# =============================================================================
#
# Per ADR-330 D4: every active/deferred bundle must declare its ground-truth
# file via substrate_abi.ground_truth, and that path must fall within a
# declared path zone (per ADR-287 discipline — no ground-truth file outside
# the program's owned substrate topology). The ground-truth file is what the
# kernel calibration mirror (ADR-327 D6) reads to light the self-improving
# loop; a bundle that omits it leaves its loop structurally dark.


def test_adr330_d4_bundle_declares_ground_truth():
    """ADR-330 D4: every active/deferred bundle must declare
    substrate_abi.ground_truth pointing at its per-domain ground-truth file.
    Without it, bundle_reader.get_ground_truth_for_workspace returns None and
    the calibration mirror omits the ground-truth section — the program's
    self-improving loop runs on cadence-history alone, no outcome basis."""
    bundles = list(_all_active_or_deferred_bundles())
    assert bundles, "no active/deferred bundles found in docs/programs/"

    for bundle in bundles:
        manifest = yaml.safe_load((bundle / "MANIFEST.yaml").read_text()) or {}
        abi = manifest.get("substrate_abi") or {}
        gt = abi.get("ground_truth")
        assert isinstance(gt, str) and gt.strip(), (
            f"bundle '{bundle.name}' does not declare substrate_abi.ground_truth. "
            f"ADR-330 D4 requires every active/deferred bundle to point at its "
            f"per-domain ground-truth file (e.g. operation/trading/_money_truth.md "
            f"for alpha-trader, operation/authored/_signal.md for alpha-author). "
            f"Without it the calibration mirror (ADR-327 D6) omits the "
            f"ground-truth section and the self-improving loop is dark."
        )


def test_adr335_derived_tier_connection_capabilities_declare_feeds():
    """ADR-335 derived-trust-tier (ratified 2026-06-19): every bundle capability
    that requires a connection must declare `feeds: ground_truth|action|context`.

    `feeds` is the DECLARED flow-role the derived-tier gate reads to compute
    `required_tier` (never inferred — inference would reintroduce the proxy the
    head/tail retirement killed). A connection-gated capability without `feeds`
    would silently default to OPEN tier (orchestration._normalize_bundle_capability),
    admitting a weaker-grade transport to serve a possibly-constitutive read.
    The gate must fail loud at conformance time, not silently downgrade."""
    valid = {"ground_truth", "action", "context"}
    for bundle in _all_active_or_deferred_bundles():
        manifest = yaml.safe_load((bundle / "MANIFEST.yaml").read_text()) or {}
        for cap in manifest.get("capabilities") or []:
            if not isinstance(cap, dict):
                continue
            if not cap.get("requires_connection"):
                continue  # connectionless capabilities never reach the tier gate
            feeds = cap.get("feeds")
            assert feeds in valid, (
                f"bundle '{bundle.name}' capability '{cap.get('key')}' requires a "
                f"connection but declares feeds={feeds!r}. ADR-335 derived-trust-tier "
                f"requires every connection-gated capability to declare its flow-role "
                f"(ground_truth|action|context) so required_tier is derived from a "
                f"declared fact, not inferred. A write/act -> 'action'; a read that "
                f"reconciles ground_truth -> 'ground_truth'; an attention-only read "
                f"-> 'context'."
            )


def test_adr330_d4_ground_truth_within_declared_path_zone():
    """ADR-330 D4 + ADR-287 discipline: the declared ground_truth path must
    fall within one of the bundle's declared substrate_abi.path_zones. A
    ground-truth file outside the program's owned substrate topology would
    be an un-owned write target — the same discipline that governs every
    other program substrate path."""
    for bundle in _all_active_or_deferred_bundles():
        manifest = yaml.safe_load((bundle / "MANIFEST.yaml").read_text()) or {}
        abi = manifest.get("substrate_abi") or {}
        gt = (abi.get("ground_truth") or "").strip()
        if not gt:
            continue  # the declaration test above already fails this case
        zone_paths = [
            (z.get("path") or "").strip()
            for z in (abi.get("path_zones") or [])
            if isinstance(z, dict)
        ]
        assert any(gt.startswith(zp) for zp in zone_paths if zp), (
            f"bundle '{bundle.name}' declares ground_truth='{gt}' which is not "
            f"under any declared path_zone ({zone_paths}). ADR-330 D4 + ADR-287: "
            f"the ground-truth file must live within the program's owned "
            f"substrate topology. Add the file's zone to substrate_abi.path_zones "
            f"or correct the ground_truth path."
        )


def test_adr330_d4_ground_truth_is_accumulating_file():
    """ADR-330 D4 (companion): the ground-truth file should be declared in its
    path zone's `accumulating_files` — it is written by judgment-mode
    recurrences (reconciliation / coherence-check) at runtime, not authored at
    activation. This catches the alpha-author class of gap where the file
    accumulates but the ground_truth pointer was never wired. Soft companion:
    asserts the file's basename appears in some zone's accumulating_files."""
    for bundle in _all_active_or_deferred_bundles():
        manifest = yaml.safe_load((bundle / "MANIFEST.yaml").read_text()) or {}
        abi = manifest.get("substrate_abi") or {}
        gt = (abi.get("ground_truth") or "").strip()
        if not gt:
            continue
        gt_basename = gt.rsplit("/", 1)[-1]
        accumulating = []
        for z in (abi.get("path_zones") or []):
            if isinstance(z, dict):
                accumulating.extend(z.get("accumulating_files") or [])
        assert gt_basename in accumulating, (
            f"bundle '{bundle.name}' ground_truth='{gt}' but its basename "
            f"'{gt_basename}' is not in any path zone's accumulating_files "
            f"({accumulating}). The ground-truth file is accumulated by runtime "
            f"recurrences, not authored at activation — declare it under "
            f"accumulating_files so the substrate contract is complete."
        )


def test_adr286_d3_deferred_bundle_path_readiness():
    """Companion to the active-bundle test: deferred bundles are exempt
    from full conformance, but pin a count so we know what state each
    deferred bundle is in. A deferred bundle with 0 of the 13 paths is a
    placeholder; one with all 13 is ready to flip to active. Surfacing
    this as a test makes the readiness state legible without forcing
    backfill on deferred bundles."""
    deferred_bundles = [
        b for b in _all_active_or_deferred_bundles()
        if (yaml.safe_load((b / "MANIFEST.yaml").read_text()) or {}).get("status") == "deferred"
    ]
    for bundle in deferred_bundles:
        ref_root = bundle / "reference-workspace"
        present = [p for p in _ADR286_D3_BUNDLE_OWNED_PATHS if (ref_root / p).exists()]
        # No assertion on count — this test always passes for deferred
        # bundles. Its job is to be a present-but-passing test so a future
        # operator running pytest -v sees the readiness state at a glance.
        # When a deferred bundle's count reaches 13 it's ready to graduate;
        # the activation step would flip status to active and the assertion
        # in test_adr286_d3_active_bundle_ships_all_program_owned_paths
        # would then enforce.
        print(
            f"\nADR-286 D3 readiness for deferred bundle '{bundle.name}': "
            f"{len(present)}/13 program-owned paths shipped"
        )


# =============================================================================
# ADR-335 — Perception Field: watches + the general four-flow conformance gate
# =============================================================================
#
# Per ADR-335 D9 (enacting ADR-332 D4, deferred from ADR-330 D4's
# first-instance): every ACTIVE program declares all four flows — context-in
# (substrate_abi.watches OR an explicit flows_na.perception rationale),
# work-out (capabilities), outcomes-in (substrate_abi.ground_truth), the loop
# (>=1 judgment-mode recurrence) — or explicitly marks a flow N/A with
# rationale via `substrate_abi.flows_na.{perception|work_out|outcomes|loop}`.
# Deferred bundles get the readiness-print pattern (ADR-286 precedent), not
# the strict gate. Per ADR-335 D2: watch declarations are well-formed and
# their recurrence pointers resolve.

_FOUR_FLOW_NA_KEYS = ("perception", "work_out", "outcomes", "loop")


def _manifest(bundle_dir: Path) -> dict:
    return yaml.safe_load((bundle_dir / "MANIFEST.yaml").read_text()) or {}


def _four_flow_state(bundle_dir: Path) -> dict[str, bool]:
    """Compute each flow's declared-or-NA state for a bundle. Derivation-first
    (singular declarations — the gate reads the canonical slot for each flow),
    with flows_na as the explicit escape hatch."""
    data = _manifest(bundle_dir)
    abi = data.get("substrate_abi") or {}
    flows_na = abi.get("flows_na") or {}

    def _na(key: str) -> bool:
        rationale = flows_na.get(key)
        return isinstance(rationale, str) and bool(rationale.strip())

    watches = abi.get("watches") or []
    judgment_recurrences = [
        r for r in _load_recurrences(bundle_dir)
        if (r.get("mode") or "judgment") == "judgment"
    ]
    return {
        "perception": (isinstance(watches, list) and len(watches) > 0) or _na("perception"),
        "work_out": bool(data.get("capabilities")) or _na("work_out"),
        "outcomes": bool((abi.get("ground_truth") or "").strip()) or _na("outcomes"),
        "loop": len(judgment_recurrences) > 0 or _na("loop"),
    }


def test_adr335_d9_active_bundles_declare_four_flows():
    """ADR-335 D9: every ACTIVE bundle declares all four flows or marks the
    absent flow N/A with rationale. Perception is a flow, never a gate
    (ADR-332 §2) — the lean uploads+websearch shape satisfies flow 1 via
    flows_na.perception, never by silence."""
    active = [
        b for b in _all_active_or_deferred_bundles()
        if _manifest(b).get("status") == "active"
    ]
    assert active, "no active bundles found in docs/programs/"
    for bundle in active:
        state = _four_flow_state(bundle)
        missing = [flow for flow, ok in state.items() if not ok]
        assert not missing, (
            f"bundle '{bundle.name}' is flow-incomplete: {missing} neither "
            f"declared nor marked N/A-with-rationale in substrate_abi.flows_na. "
            f"Per ADR-335 D9 + ADR-332 D4, every active program declares all "
            f"four flows (context-in / work-out / outcomes-in / the loop) or "
            f"explicitly marks a flow N/A with rationale."
        )


def test_adr335_d9_flows_na_keys_are_valid():
    """flows_na declarations use only the four canonical flow keys with
    non-empty string rationales — no freehand flow vocabulary."""
    for bundle in _all_active_or_deferred_bundles():
        abi = _manifest(bundle).get("substrate_abi") or {}
        flows_na = abi.get("flows_na") or {}
        for key, rationale in flows_na.items():
            assert key in _FOUR_FLOW_NA_KEYS, (
                f"bundle '{bundle.name}' declares flows_na.{key} — not a "
                f"canonical flow key {_FOUR_FLOW_NA_KEYS}"
            )
            assert isinstance(rationale, str) and rationale.strip(), (
                f"bundle '{bundle.name}' flows_na.{key} must carry a non-empty "
                f"rationale string (an N/A without rationale is silence, not "
                f"a declaration)"
            )


def test_adr335_d2_watch_declarations_well_formed():
    """ADR-335 D2: every declared watch carries id + shape + distills_to;
    when a recurrence pointer is present it resolves to a Trigger slug in the
    bundle. ADR-393: a watch's cadence (Trigger) lives on a CAPTURE (a standing
    web/repo watch is deterministic intake — track-sources/track-repo moved to
    _captures.yaml) OR, historically, a recurrence. The pointer must resolve to
    one of them — a dangling pointer means a watch with no Trigger."""
    for bundle in _all_active_or_deferred_bundles():
        abi = _manifest(bundle).get("substrate_abi") or {}
        watches = abi.get("watches") or []
        if not watches:
            continue
        trigger_slugs = {r.get("slug") for r in _load_recurrences(bundle)} | {
            c.get("slug") for c in _load_captures(bundle)
        }
        for watch in watches:
            assert isinstance(watch, dict), (
                f"bundle '{bundle.name}' has a non-dict watches entry: {watch!r}"
            )
            for field in ("id", "shape", "distills_to"):
                value = watch.get(field)
                assert isinstance(value, str) and value.strip(), (
                    f"bundle '{bundle.name}' watch {watch.get('id')!r} missing "
                    f"required field '{field}' (ADR-335 D2 declaration shape)"
                )
            rec = watch.get("recurrence")
            if rec is not None:
                assert rec in trigger_slugs, (
                    f"bundle '{bundle.name}' watch '{watch['id']}' points at "
                    f"Trigger '{rec}' which is neither a recurrence nor a capture "
                    f"in the bundle — a watch with no Trigger never fires"
                )


def test_adr335_d2_trader_universe_is_kernel_declared_watch():
    """The migration receipt: alpha-trader's _universe.yaml is a
    kernel-declared watch (declaration field) enacted by track-universe,
    not trader-private vocabulary. This is the third trader-private pattern
    promoted to a kernel slot (ground_truth per ADR-330, /setup per ADR-331,
    watches per ADR-335)."""
    trader = PROGRAMS_ROOT / "alpha-trader"
    abi = _manifest(trader).get("substrate_abi") or {}
    watches = abi.get("watches") or []
    universe = [w for w in watches if w.get("id") == "universe"]
    assert universe, "alpha-trader does not declare the 'universe' watch"
    assert universe[0].get("declaration") == "operation/trading/_universe.yaml"
    assert universe[0].get("recurrence") == "track-universe"


def test_adr335_d9_deferred_bundles_four_flow_readiness():
    """Deferred bundles are exempt from the strict four-flow gate (D9 reads
    'every active program'); print readiness per the ADR-286 D3 pattern so
    the graduation gap is legible without forcing backfill."""
    deferred = [
        b for b in _all_active_or_deferred_bundles()
        if _manifest(b).get("status") == "deferred"
    ]
    for bundle in deferred:
        state = _four_flow_state(bundle)
        declared = [flow for flow, ok in state.items() if ok]
        print(
            f"\nADR-335 D9 four-flow readiness for deferred bundle "
            f"'{bundle.name}': {len(declared)}/4 flows declared ({declared})"
        )


# ── ADR-354 D3 — perception-field discipline (generalized across bundles) ────
# A signal/quality rule a recurrence prompt asks the Reviewer to evaluate may
# reference ONLY fields the program's perception field emits (DP27 / ADR-335).
# A rule naming an absent field is structurally unevaluable, and the occupant
# rationalizes the gap rather than recognizing it (the 2026-06-22 probe: Signal 1
# keyed on "20-day high" + current-bar volume — fields track-universe never
# emits). This lifts the trader-specific check (test_trading_pipeline_architecture.py
# §5) to the bundle-conformance layer so EVERY program inherits it.
#
# Mechanism: a bundle whose reference-workspace ships an _operator_profile.md with
# field-keyed "### Signal N:" triggers gets checked; the emitted vocabulary is the
# snapshot-schema fields (from operation/specs/ticker-snapshot.md or equivalent) +
# regime fields. Programs without field-keyed rules (e.g. alpha-author, whose
# quality bar is prose) are a clean no-op. DORMANT-marked signals are skipped.

# Field-shaped tokens that, if present in a non-dormant trigger, name data the
# perception field does NOT emit. Program-neutral: each is a known absent-field
# pattern. Extend as new programs add field-keyed rules.
_ABSENT_FIELD_MARKERS = {
    "20-day high": "no period-high field in the snapshot schema",
    "20 day high": "no period-high field in the snapshot schema",
    "volume > 1.5": "no current-bar volume field (only volume_20d_avg)",
    "earnings surprise": "no earnings feed in the perception field",
    "price gap": "no gap field in the perception field",
    "relative-strength rank": "no cross-ticker RS field in the perception field",
}


def test_adr354_signal_rules_reference_only_emitted_perception_fields():
    """ADR-354 D3 (generalized): in every active/deferred bundle, a NON-DORMANT
    signal trigger in operation/trading/_operator_profile.md (or equivalent
    field-keyed rule file) references only fields the perception field emits.
    DORMANT-marked signals are exempt (their feed is declared absent). Bundles
    without a field-keyed rule file are a clean no-op."""
    import re
    for bundle in _all_active_or_deferred_bundles():
        profile = (
            bundle / "reference-workspace" / "operation" / "trading"
            / "_operator_profile.md"
        )
        if not profile.is_file():
            continue  # program has no field-keyed signal rules (e.g. alpha-author)
        text = profile.read_text()
        headers = re.findall(r"^### Signal \d+:[^\n]*", text, flags=re.MULTILINE)
        blocks = re.split(r"^### Signal \d+:", text, flags=re.MULTILINE)[1:]
        for hdr, blk in zip(headers, blocks):
            if "DORMANT" in hdr:
                continue
            trig_m = re.search(r"\*\*Trigger:\*\*([^\n]*)", blk)
            trig = (trig_m.group(1) if trig_m else "").lower()
            absent = [why for marker, why in _ABSENT_FIELD_MARKERS.items() if marker in trig]
            assert not absent, (
                f"bundle '{bundle.name}' {hdr.strip()[:40]}… non-dormant trigger "
                f"references absent perception field(s): {absent}. ADR-354 D3: a "
                f"signal rule may reference only emitted perception fields, or be "
                f"marked DORMANT. Rewrite the rule to emitted fields, or mark the "
                f"signal DORMANT if its feed does not exist."
            )
