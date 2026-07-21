"""
CI Ratchet — ADR-427 §8 (the read-side classification of `.content` readers)

`workspace_files.content` / `workspace_blobs.content` is a TEXT denorm that
reads '' for a binary revision (ADR-427 D4: Category-2 cache, text-only by
contract). Every live reader must therefore be CLASSIFIED — either it is
binary-aware, or empty-content flows through it harmlessly, or binary cannot
arrive at the paths it reads. A NEW reader that isn't classified fails this
gate: the text-only assumption is explicit and guarded, never silent.

Mechanics: enumerate every live module (services/routes/mcp_server/agents/jobs,
tests and __pycache__ excluded) that (a) touches the substrate tables AND
(b) selects a `content` column. Each enumerated file must appear in
CLASSIFICATION below with one of:

  binary-aware          — detects binary (storage_key / is_binary / notice)
                          and answers legibly
  safe-on-empty         — '' content flows through harmlessly (search skips,
                          embed ineligible, compose contributes nothing)
  text-only-by-contract — reads FIXED authored-text paths (governance yaml,
                          persona md, ledgers) where a binary blob cannot
                          arrive by construction
  non-substrate         — the content select is another table entirely
                          (session_messages, agent_runs) that happens to live
                          in a file also touching workspace_files

Usage:
    cd api && python3 test_adr427_reader_classification.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

API_ROOT = Path(__file__).parent
SCAN_ROOTS = ("services", "routes", "mcp_server", "agents", "jobs")

# \bcontent\b does NOT match content_type / content_url / draft_content
# ('_' is a word character), so this finds true content-column selects.
_SELECT_CONTENT = re.compile(r'select\(\s*["\'][^"\')]*\bcontent\b')
_TOUCHES_SUBSTRATE = re.compile(r"workspace_files|workspace_blobs|workspace_file_versions")

# ---------------------------------------------------------------------------
# The classification map — every enumerated reader, with its contract.
# Adding a new `.content` reader? Classify it here, deliberately.
# ---------------------------------------------------------------------------

CLASSIFICATION: dict[str, str] = {
    # -- binary-aware (this arc) --
    "services/storage_backend.py": "binary-aware",          # the seam itself — routes inline vs external by storage_key
    "services/authored_substrate.py": "binary-aware",       # read_revision surfaces is_binary; tombstone reuses head blob_sha
    "services/primitives/workspace.py": "binary-aware",     # ReadFile answers with the binary notice; exact-search snippets '' harmlessly
    "routes/workspace.py": "binary-aware",                  # GET /file mints the serving URL for a binary head (D4)
    "routes/documents.py": "binary-aware",                  # the ADR-395 raw lane; raw rows always had '' content
    # -- safe-on-empty --
    "services/workspace.py": "safe-on-empty",               # generic read layer returns ''; the primitive layer adds the notice
    "services/mcp_composition.py": "safe-on-empty",         # recall/compose: an empty body contributes nothing
    "services/wake.py": "safe-on-empty",                    # embed sweep: is_embed_eligible rejects empty
    "services/wake_sources/substrate_event.py": "safe-on-empty",  # parent-content diff guard; ''→'' fires no transition
    "services/primitives/embed.py": "safe-on-empty",        # eligibility rejects empty content
    "routes/feed.py": "safe-on-empty",                      # workspace read renders ''; session_messages selects are non-substrate
    "routes/studio.py": "safe-on-empty",                    # opens .html artifacts; a binary head renders empty, never crashes
    "routes/images.py": "safe-on-empty",                    # compose/render read the stage .html; '' fails the data-template check → 422, never a crash or a silent bad compose
    "services/connector_retention.py": "safe-on-empty",     # citation scan of capture files; '' has no citations
    "services/design_systems.py": "safe-on-empty",          # css/html text sources; '' skipped
    # -- text-only-by-contract (fixed authored-text paths) --
    "services/agents_registry.py": "text-only-by-contract",     # agents/*.md roster files
    "services/working_memory.py": "text-only-by-contract",      # compact-index md; session/agent_runs selects are non-substrate
    "services/review_policy.py": "text-only-by-contract",       # governance yaml
    "services/budget.py": "text-only-by-contract",              # governance/_budget.yaml
    "services/risk_gate.py": "text-only-by-contract",           # trader governance yaml
    "services/member_caps.py": "text-only-by-contract",         # governance yaml
    "services/daily_pnl_email.py": "text-only-by-contract",     # _performance.md
    "services/lane_runner.py": "text-only-by-contract",         # lane context md
    "services/recurrence.py": "text-only-by-contract",          # _recurrences.yaml
    "services/freddie_envelope.py": "text-only-by-contract",    # governance envelope paths
    "services/freddie_audit.py": "text-only-by-contract",       # audit md
    "services/ask_builder.py": "text-only-by-contract",         # authored md
    "services/workspace_guide.py": "text-only-by-contract",     # _workspace_guide.md
    "services/context_inference.py": "text-only-by-contract",   # identity/brand md merge
    "services/primitives/scaffold.py": "text-only-by-contract", # seed/skeleton text templates
    "services/capture/declarations.py": "text-only-by-contract",# _captures.yaml
    "services/operator_proxy/scenarios.py": "text-only-by-contract",       # Hat-B harness, authored scenario files
    "services/operator_proxy/persona_snapshot.py": "text-only-by-contract",# Hat-B harness
    "services/operator_proxy/capture.py": "text-only-by-contract",         # Hat-B harness
    "services/primitives/mirror_signal_state.py": "text-only-by-contract",
    "services/primitives/mirror_recent_execution.py": "text-only-by-contract",
    "services/primitives/mirror_calibration.py": "text-only-by-contract",
    "services/primitives/mirror_schedule_index.py": "text-only-by-contract",
    "services/primitives/track_web_sources.py": "text-only-by-contract",
    "services/primitives/track_universe.py": "text-only-by-contract",
    "services/primitives/track_foreign.py": "text-only-by-contract",
    "services/primitives/track_regime.py": "text-only-by-contract",
    "services/outcomes/ledger.py": "text-only-by-contract",
    "services/outcomes/operator.py": "text-only-by-contract",
    "routes/alpha_trader.py": "text-only-by-contract",          # trader md/yaml
    "routes/sources.py": "text-only-by-contract",               # _watch.yaml
    "routes/agents.py": "text-only-by-contract",                # agent md files
    # -- non-substrate --
    "routes/lanes.py": "non-substrate",                         # session_messages content
}

VALID = {"binary-aware", "safe-on-empty", "text-only-by-contract", "non-substrate"}


def enumerate_readers() -> list[str]:
    found: list[str] = []
    for root in SCAN_ROOTS:
        base = API_ROOT / root
        if not base.exists():
            continue
        for py in sorted(base.rglob("*.py")):
            rel = str(py.relative_to(API_ROOT))
            if "__pycache__" in rel or rel.startswith("test") or "/test" in rel:
                continue
            try:
                text = py.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if _TOUCHES_SUBSTRATE.search(text) and _SELECT_CONTENT.search(text):
                found.append(rel)
    return found


def main() -> int:
    readers = enumerate_readers()
    unclassified = [r for r in readers if r not in CLASSIFICATION]
    stale = [c for c in CLASSIFICATION if c not in readers]
    bad_class = {f: c for f, c in CLASSIFICATION.items() if c not in VALID}

    print(f"enumerated content readers: {len(readers)}")
    print(f"classified: {len(readers) - len(unclassified)}")

    ok = True
    if unclassified:
        ok = False
        print("\n✗ UNCLASSIFIED readers (new .content read sites — classify in CLASSIFICATION):")
        for r in unclassified:
            print(f"    {r}")
    if bad_class:
        ok = False
        print(f"\n✗ invalid classification values: {bad_class}")
    if stale:
        # Stale entries are a warning, not a failure — a reader that stopped
        # reading content is progress, but keep the map honest.
        print("\n⚠ stale classifications (no longer enumerate — remove):")
        for c in stale:
            print(f"    {c}")

    print(f"\n{'='*60}")
    print(f"ADR-427 reader-classification ratchet: {'PASS' if ok else 'FAIL'}")
    print(f"{'='*60}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
