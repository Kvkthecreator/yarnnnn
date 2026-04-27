"""ADR-226 — Reference-Workspace Activation Flow tests.

Phase 7 fork helper (`_fork_reference_workspace`) + frontmatter parser
(`_strip_tier_frontmatter`) + activation state classifier
(`_classify_activation_state`).

Test strategy: pure-function tests for the parser + classifier.
Integration tests for the fork + activate endpoint require a real
Supabase client and operator workspace, validated via a separate
smoke test against kvk's user_id (BOOTSTRAP.md Step 1).

The frontmatter parser is the hottest correctness path — operators
must never see bundle metadata in their workspace files.
"""

from __future__ import annotations

import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))


# =============================================================================
# Frontmatter parser tests
# =============================================================================


def test_strip_frontmatter_with_no_frontmatter_returns_unchanged():
    from services.workspace_init import _strip_tier_frontmatter
    raw = "# Mandate\n\nSome body content.\n"
    body, meta = _strip_tier_frontmatter(raw)
    assert body == raw
    assert meta == {}


def test_strip_frontmatter_extracts_tier_and_strips_block():
    from services.workspace_init import _strip_tier_frontmatter
    raw = (
        "---\n"
        "tier: authored\n"
        'prompt: "What is your edge?"\n'
        "---\n"
        "\n"
        "# Mandate (template)\n"
        "\n"
        "Body content.\n"
    )
    body, meta = _strip_tier_frontmatter(raw)
    assert meta.get("tier") == "authored"
    assert "What is your edge?" in (meta.get("prompt") or "")
    assert "tier:" not in body
    assert "prompt:" not in body
    assert "# Mandate (template)" in body
    assert "Body content." in body


def test_strip_frontmatter_handles_canon_tier():
    from services.workspace_init import _strip_tier_frontmatter
    raw = (
        "---\n"
        "tier: canon\n"
        'note: "Operator typically does not edit."\n'
        "---\n"
        "\n"
        "# Conventions\n"
    )
    body, meta = _strip_tier_frontmatter(raw)
    assert meta.get("tier") == "canon"
    assert "tier:" not in body
    assert "# Conventions" in body


def test_strip_frontmatter_handles_optional_field():
    from services.workspace_init import _strip_tier_frontmatter
    raw = (
        "---\n"
        "tier: authored\n"
        "optional: true\n"
        'prompt: "Brand-related prompt"\n'
        "---\n"
        "\n"
        "# Brand (template)\n"
    )
    body, meta = _strip_tier_frontmatter(raw)
    assert meta.get("tier") == "authored"
    assert meta.get("optional") is True
    assert "tier:" not in body


def test_strip_frontmatter_malformed_returns_text_unchanged():
    from services.workspace_init import _strip_tier_frontmatter
    # Opens frontmatter but never closes — treat as no frontmatter
    raw = "---\ntier: canon\n# No closing fence\n\n# Body\n"
    body, meta = _strip_tier_frontmatter(raw)
    # Defensive: don't lose data; return as-is if parse fails
    assert "---" in body
    assert meta == {}


# =============================================================================
# Skeleton-content detection tests
# =============================================================================


def test_skeleton_detection_empty_content_is_skeleton():
    from services.workspace_init import _is_skeleton_content
    assert _is_skeleton_content("", "# bundle template") is True
    assert _is_skeleton_content("   ", "# bundle template") is True


def test_skeleton_detection_matches_bundle_body():
    from services.workspace_init import _is_skeleton_content
    body = "# Mandate (template)\nAuthor here:\n"
    assert _is_skeleton_content(body, body) is True
    # Whitespace-only difference still counts as skeleton
    assert _is_skeleton_content(f"\n{body}\n", body) is True


def test_skeleton_detection_kernel_default_is_skeleton():
    from services.workspace_init import _is_skeleton_content
    kernel_default = (
        "# Mandate\n\n"
        "## Primary Action\n"
        "_<not yet declared — talk to YARNNN to author your mandate>_\n\n"
        "## Success Criteria\n\n"
        "## Boundary Conditions\n"
    )
    bundle_body = "# Mandate (template)\nAuthor your edge here.\n"
    assert _is_skeleton_content(kernel_default, bundle_body) is True


def test_skeleton_detection_authored_content_is_not_skeleton():
    from services.workspace_init import _is_skeleton_content
    operator_authored = (
        "# Mandate\n\n"
        "## Primary Action\n"
        "Submit equity orders to Alpaca matching one of 5-8 declared signals "
        "in _operator_profile.md, passing every rule in _risk.md.\n\n"
        "## Success Criteria\n"
        "Signal attribution on every proposal. Mechanical rule evaluation. "
        "Formula-based sizing. Expectancy decay honored.\n"
    )
    bundle_body = "# Mandate (template)\nAuthor your edge here.\n"
    assert _is_skeleton_content(operator_authored, bundle_body) is False


# =============================================================================
# Activation-state classifier tests
# =============================================================================


class _StubResult:
    def __init__(self, data):
        self.data = data


class _StubSelect:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, _col, _val):
        return self

    def execute(self):
        return _StubResult(self._rows)


class _StubClient:
    def __init__(self, platform_connections_rows):
        self._rows = platform_connections_rows

    def table(self, name):
        if name == "platform_connections":
            return _StubSelect(self._rows)
        raise NotImplementedError


def _bust_caches():
    from services.bundle_reader import _load_manifest, _all_slugs
    _load_manifest.cache_clear()
    _all_slugs.cache_clear()


def test_activation_state_none_when_no_bundles_active():
    """No platform connections → no bundle is active for this workspace →
    activation_state == 'none'."""
    _bust_caches()
    from services.working_memory import _classify_activation_state

    def make_client():
        return _StubClient([])

    state = _classify_activation_state("user", "any mandate content", make_client)
    assert state == "none"


def test_activation_state_post_fork_pre_author_when_skeleton_mandate():
    """alpaca connected → alpha-trader bundle active. MANDATE.md skeleton
    → state is 'post_fork_pre_author' — YARNNN activation overlay engages."""
    _bust_caches()
    from services.working_memory import _classify_activation_state

    def make_client():
        return _StubClient([
            {"platform": "trading", "status": "active", "created_at": "2026-04-01T00:00:00Z"},
        ])

    skeleton_mandate = (
        "# Mandate\n\n"
        "## Primary Action\n"
        "_<not yet declared — talk to YARNNN to author your mandate>_\n"
    )
    state = _classify_activation_state("user", skeleton_mandate, make_client)
    assert state == "post_fork_pre_author"


def test_activation_state_post_fork_pre_author_with_bundle_template():
    """Bundle's MANDATE.md template (with '(template)' marker) is treated
    as skeleton — the operator hasn't authored their edge yet."""
    _bust_caches()
    from services.working_memory import _classify_activation_state

    def make_client():
        return _StubClient([
            {"platform": "trading", "status": "active", "created_at": "2026-04-01T00:00:00Z"},
        ])

    bundle_template_mandate = (
        "# Mandate — alpha-trader (template)\n\n"
        "## Primary Action\n\n"
        "## Edge hypothesis (one paragraph)\n"
        "Author here: in 2-4 sentences, name the edge.\n"
    )
    state = _classify_activation_state("user", bundle_template_mandate, make_client)
    assert state == "post_fork_pre_author"


def test_activation_state_operational_when_mandate_authored():
    """alpaca connected + MANDATE.md authored → state is 'operational'.
    Activation overlay does NOT engage."""
    _bust_caches()
    from services.working_memory import _classify_activation_state

    def make_client():
        return _StubClient([
            {"platform": "trading", "status": "active", "created_at": "2026-04-01T00:00:00Z"},
        ])

    operator_authored = (
        "# Mandate — alpha-trader\n\n"
        "## Primary Action\n"
        "Submit equity orders to the Alpaca API that match one of the 5-8 "
        "declared signals in _operator_profile.md, passing every rule in "
        "_risk.md and every Reviewer check in principles.md.\n\n"
        "## Success Criteria\n"
        "Signal attribution on every proposal. Mechanical rule evaluation. "
        "Formula-based sizing. Expectancy decay honored. Var budget never "
        "exceeded. Discretionary vocabulary blocked at Reviewer.\n"
    )
    state = _classify_activation_state("user", operator_authored, make_client)
    assert state == "operational"


# =============================================================================
# Frontmatter integration with shipped bundle files
# =============================================================================


def test_alpha_trader_reference_workspace_files_have_valid_tier_frontmatter():
    """Every alpha-trader reference-workspace/*.md file must declare
    `tier:` per ADR-223 §5 amendment. Validates the bundle is real."""
    from pathlib import Path
    from services.workspace_init import _strip_tier_frontmatter

    bundle_root = (
        Path(__file__).resolve().parent.parent
        / "docs" / "programs" / "alpha-trader" / "reference-workspace"
    )
    md_files = sorted(bundle_root.rglob("*.md"))
    assert len(md_files) > 0, "alpha-trader reference-workspace/ has no .md files"

    valid_tiers = {"canon", "authored", "placeholder"}
    files_without_tier = []
    for src in md_files:
        if src.name == "README.md" and src.parent == bundle_root:
            continue  # bundle-meta, not a workspace file
        raw = src.read_text(encoding="utf-8")
        _, meta = _strip_tier_frontmatter(raw)
        tier = (meta.get("tier") or "").lower()
        if tier not in valid_tiers:
            files_without_tier.append(str(src.relative_to(bundle_root)))

    assert not files_without_tier, (
        f"alpha-trader reference-workspace files without valid tier "
        f"frontmatter: {files_without_tier}"
    )


def test_alpha_trader_authored_files_carry_prompts():
    """Every `tier: authored` file should carry a `prompt:` frontmatter
    field — that's the question YARNNN surfaces during the activation
    conversation."""
    from pathlib import Path
    from services.workspace_init import _strip_tier_frontmatter

    bundle_root = (
        Path(__file__).resolve().parent.parent
        / "docs" / "programs" / "alpha-trader" / "reference-workspace"
    )
    md_files = sorted(bundle_root.rglob("*.md"))

    for src in md_files:
        if src.name == "README.md" and src.parent == bundle_root:
            continue
        raw = src.read_text(encoding="utf-8")
        _, meta = _strip_tier_frontmatter(raw)
        if (meta.get("tier") or "").lower() == "authored":
            assert meta.get("prompt"), (
                f"`authored` tier file {src.relative_to(bundle_root)} "
                f"has no `prompt:` frontmatter — YARNNN won't have a "
                f"question to surface during activation walk."
            )
