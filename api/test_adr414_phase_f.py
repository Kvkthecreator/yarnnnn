"""ADR-414 Phase F regression gate — internal vocabulary never reaches the operator.

ADR-410 D4: "Internal enums (`wake_source` values, 'Reviewer', 'ADDRESSED',
family slugs as titles) are banned from operator-facing strings." This is
the ADR-414 CI ratchet #4: the word "Reviewer" may survive in code
comments, identifiers (ReviewerDetail, reviewer_identity — API contract),
and docs — never in operator-visible copy.

Heuristic: a display-copy violation is the standalone word `Reviewer` on a
non-comment line of a web/ source file, excluding identifier forms.
"""

import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"

WORD = re.compile(r"(?<![\w'\"/])Reviewer(?![A-Za-z_])")
COMMENT = re.compile(r"^\s*(//|\*|/\*|\{/\*)")

SCAN_DIRS = ("components", "app", "lib")

# Data literals that must MATCH substrate/backend-produced content — they
# are pattern-matchers, not display copy. Each carries its removal
# condition (D+E-2 file re-homing / narrative-string rename).
ALLOWLIST = {
    "lib/freddie-persona.ts",   # skeleton-detection literal matching legacy '# Reviewer Identity' file content
    "lib/feed-grouping.ts",     # regex matching backend narrative strings ("on Reviewer's direction")
    # app/admin/accounts/page.tsx — REMOVED (ADR-414 F2): the "Reviewer 7d"
    # label became "Agent 7d"; the doc line names the freddie:/reviewer:
    # data prefixes inside <code> spans (identifier form, not display copy),
    # so the standalone-word heuristic no longer fires.
}


def _violations():
    offenders = []
    for sub in SCAN_DIRS:
        root = WEB / sub
        if not root.exists():
            continue
        for f in root.rglob("*.ts*"):
            if "node_modules" in f.parts:
                continue
            rel = str(f.relative_to(WEB))
            if rel in ALLOWLIST:
                continue
            in_block_comment = False
            for i, line in enumerate(f.read_text().splitlines(), 1):
                stripped = line.strip()
                if in_block_comment:
                    if "*/" in stripped:
                        in_block_comment = False
                    continue
                if stripped.startswith(("/*", "{/*")) and "*/" not in stripped:
                    in_block_comment = True
                    continue
                if COMMENT.match(line):
                    continue
                # strip trailing // comments before matching (inline
                # code-comments may cite historical ADR vocabulary)
                code = line.split("//", 1)[0]
                if WORD.search(code):
                    offenders.append(f"{rel}:{i}: {stripped[:100]}")
    return offenders


def test_no_operator_facing_reviewer_vocabulary():
    offenders = _violations()
    assert not offenders, (
        "operator-facing 'Reviewer' vocabulary reappeared (ADR-410 D4 / "
        "ADR-414 ratchet #4) — use 'agent', 'Freddie', or the agent's own "
        "name:\n" + "\n".join(offenders)
    )
