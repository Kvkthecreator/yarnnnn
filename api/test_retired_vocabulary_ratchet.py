"""Retired-vocabulary ratchet (2026-09-12).

ADR-632 retired the steward / Reviewer / Freddie seat, its wake stack and queue;
ADR-603 D5 retired recurrences; ADR-231 dissolved ManageRecurrence/FireInvocation.
The code went. The CANON did not follow: on 2026-09-12 the documents CLAUDE.md
sends every session to still described that machinery as live in 752 lines
across 29 files (FOUNDATIONS 144, GLOSSARY 109), and 327 non-comment
lines across 75 live modules still name it (orchestration.py carries a kernel-default
MANDATE addressed to "Freddie, the system agent").

This gate freezes every count as a per-file CEILING that only moves down:
  - a file may not gain a retired-vocabulary line (a new one is a reintroduction);
  - when a rewrite drops a file's count, the ceiling must follow within SLACK lines
    (a ceiling nobody approaches is decorative) — lower the table in the same commit;
  - a file at zero leaves the table and must stay at zero.

Two counts never reach zero by design and simply freeze: the `freddie:` attribution
prefix survives on historical revisions, display-resolved (principal_display.py,
principals.py, narrative.py). Everything else is debt with the ADR as its spec.

Run: python3 -m pytest api/test_retired_vocabulary_ratchet.py -q
"""
from __future__ import annotations

import glob
import os
import re

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLACK = 3

CANON_TERMS = re.compile(r"\bReviewer\b|\bFreddie\b|\bsteward\b|wake_queue|wake queue|ManageRecurrence|FireInvocation|\brecurrences?\b", re.I)
CODE_TERMS = re.compile(r"\bReviewer\b|\bFreddie\b|\bsteward\b|wake_queue|ManageRecurrence|FireInvocation", re.I)

CANON_CEILINGS = {
    "docs/architecture/FOUNDATIONS.md": 144,
    "docs/architecture/GLOSSARY.md": 109,
    "docs/design/WORKSPACE.md": 82,
    "docs/architecture/agent-composition.md": 69,
    "docs/architecture/WORKSPACE.md": 67,
    "docs/architecture/SERVICE-MODEL.md": 57,
    "docs/architecture/ADR-LEDGER.md": 48,
    "docs/architecture/primitives-matrix.md": 33,
    "docs/architecture/THESIS.md": 27,
    "docs/ESSENCE.md": 21,
    "docs/architecture/bare-kernel-product-floor-2026-06-01.md": 17,
    "docs/architecture/authored-substrate.md": 12,
    "docs/features/data-privacy.md": 9,
    "docs/architecture/YARNNN-DESIGN-PRINCIPLES.md": 8,
    "docs/features/mcp/SUBMISSION.md": 7,
    "docs/architecture/LAYER-MAPPING.md": 6,
    "docs/features/sessions.md": 5,
    "docs/architecture/README.md": 4,
    "docs/architecture/compositor.md": 4,
    "docs/architecture/lane-frame.md": 4,
    "docs/architecture/DOMAIN-STRESS-MATRIX.md": 3,
    "docs/architecture/propagation-discipline.md": 3,
    "docs/architecture/AGENT-TAXONOMY.md": 2,
    "docs/architecture/connectors.md": 2,
    "docs/architecture/observability.md": 2,
    "docs/architecture/os-framing-implementation-roadmap.md": 2,
    "docs/features/context.md": 2,
    "docs/features/mcp/presentation.md": 2,
    "docs/architecture/connector-reach-and-the-commons.md": 1,
}

CODE_CEILINGS = {
    "api/services/orchestration.py": 66,
    "api/services/judgment_log.py": 17,
    "api/services/review_policy.py": 15,
    "api/services/primitives/workspace.py": 11,
    "api/routes/account.py": 10,
    "api/services/narrative.py": 10,
    "api/services/primitives/propose_action.py": 10,
    "api/services/operator_proxy/client.py": 9,
    "api/services/primitives/registry.py": 9,
    "api/services/primitives/permission.py": 7,
    "api/services/operator_proxy/draft_templates.py": 6,
    "api/services/principal_display.py": 6,
    "api/services/workspace_guide.py": 6,
    "api/services/daily_pnl_email.py": 5,
    "api/services/workspace_init.py": 5,
    "api/jobs/unified_scheduler.py": 4,
    "api/routes/alpha_trader.py": 4,
    "api/routes/proposals.py": 4,
    "api/services/anthropic.py": 4,
    "api/services/capture/declarations.py": 4,
    "api/services/lane_runner.py": 4,
    "api/services/operator_proxy/capture.py": 4,
    "api/services/operator_proxy/scenarios.py": 4,
    "api/services/primitives/sync_platform_state.py": 4,
    "api/services/primitives/track_regime.py": 4,
    "api/services/principals.py": 4,
    "api/services/supabase.py": 4,
    "api/services/system_calls.py": 4,
    "api/services/telemetry.py": 4,
    "api/services/workspace_context.py": 4,
    "api/services/workspace_purge.py": 4,
    "api/routes/admin.py": 3,
    "api/routes/lanes.py": 3,
    "api/services/conventions.py": 3,
    "api/services/outcomes/ledger.py": 3,
    "api/services/primitives/__init__.py": 3,
    "api/services/primitives/revisions.py": 3,
    "api/services/substrate_reapply.py": 3,
    "api/services/workspace_paths.py": 3,
    "api/services/workspace_utils.py": 3,
    "api/routes/authored.py": 2,
    "api/routes/system.py": 2,
    "api/services/budget.py": 2,
    "api/services/kernel_surfaces.py": 2,
    "api/services/mentions.py": 2,
    "api/services/model_router.py": 2,
    "api/services/operator_proxy/proposal_templates.py": 2,
    "api/services/primitives/track_universe.py": 2,
    "api/services/primitives/trading_emit_contract.py": 2,
    "api/mcp_server/auth.py": 1,
    "api/mcp_server/server.py": 1,
    "api/routes/documents.py": 1,
    "api/routes/workspace.py": 1,
    "api/services/ask_builder.py": 1,
    "api/services/attached_connectors.py": 1,
    "api/services/authored_substrate.py": 1,
    "api/services/authoring.py": 1,
    "api/services/bundle_reader.py": 1,
    "api/services/byok.py": 1,
    "api/services/capture/__init__.py": 1,
    "api/services/capture/drainer.py": 1,
    "api/services/connector_retention.py": 1,
    "api/services/conversation_cast.py": 1,
    "api/services/deep_links.py": 1,
    "api/services/directory_registry.py": 1,
    "api/services/falsifiers.py": 1,
    "api/services/operator_proxy/__init__.py": 1,
    "api/services/outcomes/__init__.py": 1,
    "api/services/outcomes/trading.py": 1,
    "api/services/platform_tools.py": 1,
    "api/services/primitives/embed.py": 1,
    "api/services/programs.py": 1,
    "api/services/scheduling.py": 1,
    "api/services/upload_tickets.py": 1,
    "api/services/workspace_delete.py": 1,
}


def _canon_files() -> list[str]:
    g = lambda p: glob.glob(os.path.join(_REPO, p), recursive=True)
    return sorted(set(g("docs/architecture/*.md") + g("docs/ESSENCE.md") + g("docs/design/WORKSPACE.md") + g("docs/features/**/*.md")))


def _code_files() -> list[str]:
    g = lambda p: glob.glob(os.path.join(_REPO, p), recursive=True)
    return sorted(g("api/services/**/*.py") + g("api/routes/*.py") + g("api/jobs/*.py") + g("api/mcp_server/*.py"))


def _count(path: str, rx: re.Pattern, skip_comments: bool) -> int:
    n = 0
    for line in open(path, encoding="utf-8"):
        if skip_comments and line.lstrip().startswith("#"):
            continue
        if rx.search(line):
            n += 1
    return n


def _check(files: list[str], rx: re.Pattern, ceilings: dict[str, int], skip_comments: bool, label: str) -> None:
    assert len(files) >= 20, f"{label}: only {len(files)} files globbed — the scope stopped matching, not the repo"
    over, slack, missing = [], [], []
    seen = set()
    for path in files:
        rel = os.path.relpath(path, _REPO)
        seen.add(rel)
        n = _count(path, rx, skip_comments)
        cap = ceilings.get(rel, 0)
        if n > cap:
            over.append(f"{rel}: {n} > {cap}")
        elif cap - n > SLACK:
            slack.append(f"{rel}: {n} but ceiling {cap} — lower it")
    for rel in ceilings:
        if rel not in seen:
            missing.append(rel)
    assert not over, f"{label}: retired vocabulary reintroduced (ADR-632/603) — " + "; ".join(over)
    assert not slack, f"{label}: ratchet the ceiling down — " + "; ".join(slack)
    assert not missing, f"{label}: ceiling rows for files that no longer exist (delete the row): {missing}"


def test_canon_does_not_regrow_retired_vocabulary():
    _check(_canon_files(), CANON_TERMS, CANON_CEILINGS, False, "canon")


def test_code_does_not_regrow_retired_vocabulary():
    _check(_code_files(), CODE_TERMS, CODE_CEILINGS, True, "code")
