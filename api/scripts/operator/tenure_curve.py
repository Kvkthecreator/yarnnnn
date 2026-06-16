"""TENURE-READ Read-1 curve extractor — the mechanized "curve view".

Hat-B developer-surface tooling (NOT system canon). Closes the gap
`docs/evaluations/LONGITUDINAL-TRACKING.md` §4 and `TENURE-READ.md` Read 1
both name explicitly: *"the curve view does not exist yet."*

WHAT THIS IS
------------
TENURE-READ Read 1 asks: *does the program's declared ground-truth measurand
move the right way over tenure?* The trajectory is fully reconstructable from
the ground-truth file's revision chain (ADR-209 retains every revision), but
until now it was hand-extracted — diffing N revisions' YAML frontmatter by
eye. That hand work is what this script removes.

It is the demand-pull promotion of the **curve view only** (Read 1's numeric
trajectory). Reads 2 (self-amendment trail) and 3 (intent coherence) stay
manual prose reads per TENURE-READ §2 — they are forensic, not tabular.

WHAT THIS IS NOT
----------------
It RENDERS the curve; it does NOT classify the tenure verdict. The
`SURVIVING + COHERENT` vs `IMPROVING` judgment is the human's, written into
the soak's TRACKING-LOG.md (TENURE-READ §3). The only verdict this script
emits is the *mechanical, deterministic* ledger-state fact — e.g.
"BOOTSTRAP-EMPTY → INCONCLUSIVE-on-improvement" when the ground-truth file has
zero samples — which TENURE-READ Read 1 explicitly instructs the reader to
state. That is a substrate fact (sample count == 0), not a judgment.

PROGRAM-AGNOSTIC BY CONSTRUCTION
--------------------------------
Per ADR-188 + ADR-330 + TENURE-READ §1, the measurand path is resolved from
the active bundle's `substrate_abi.ground_truth` declaration via the canonical
`services.bundle_reader.get_ground_truth_for_workspace` — not hardcoded. The
numeric trajectory is extracted by flattening each revision's frontmatter to
its numeric leaves, so no per-program field names are baked in. alpha-trader's
`_money_truth.md` (by-signal expectancy) and yarnnn-author's `_signal.md`
(voice adherence) both render through the same path.

USAGE
-----
    # by persona slug (resolves user_id from docs/alpha/personas.yaml):
    python api/scripts/operator/tenure_curve.py --persona alpha-trader-2

    # by explicit workspace:
    python api/scripts/operator/tenure_curve.py \
        --user-id 29a74c63-0c9c-4998-b8bb-56dd0d810a4e

    # override the measurand path (generic workspace / testing):
    python api/scripts/operator/tenure_curve.py --user-id <uuid> \
        --ground-truth operation/trading/_money_truth.md

    # write the scaffold into the soak dir instead of stdout:
    python api/scripts/operator/tenure_curve.py --persona alpha-trader-2 --emit

The DB layer needs network reach to Supabase (same constraint as the whole
operator harness). The pure-core functions (frontmatter → trajectory) need no
DB and are exercised by `api/test_tenure_curve.py`.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

# --- path bootstrap so `from services...` resolves when run as a script ------
_API_ROOT = Path(__file__).resolve().parents[2]  # .../api
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

_REPO_ROOT = _API_ROOT.parent
_PERSONAS_YAML = _REPO_ROOT / "docs" / "alpha" / "personas.yaml"

# Keys whose values count as "ledger size" — the presence of real samples is
# what distinguishes a primed-but-empty ground truth from an accumulating one.
_SAMPLE_KEY_RE = re.compile(
    r"(?i)(sample|count|\bn_|num_|trades|reconciled|fills|pieces|wakes|audited)"
)


# ===========================================================================
# Pure core — no DB, fully unit-testable (see api/test_tenure_curve.py)
# ===========================================================================

def extract_frontmatter(content: str) -> dict[str, Any]:
    """Parse the leading YAML frontmatter block from a `.md` body.

    Uses the sanctioned extraction shape (CLAUDE.md §9): regex the `---`
    fenced block, then `yaml.safe_load`. Returns {} when there is no
    frontmatter or it is not a mapping. Never raises on malformed YAML — a
    corrupt revision should degrade to "no metrics", not crash the curve.
    """
    if not content:
        return {}
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    try:
        loaded = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _coerce_number(value: Any) -> Optional[float]:
    """Return a float for numeric values (and numeric strings); None otherwise.

    Booleans are explicitly excluded — `bool` is an `int` subclass but is not a
    measurand on a curve.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except (ValueError, AttributeError):
            return None
    return None


def flatten_numeric(data: Any, prefix: str = "") -> dict[str, float]:
    """Flatten a frontmatter dict to its numeric leaves, dotted-key keyed.

    Dicts recurse by key; lists recurse by index. Non-numeric leaves (strings,
    timestamps, narrative) are dropped — they are read by the human, not
    plotted. This is what keeps the extractor program-agnostic: it never names
    a field, it harvests whatever numbers the program's ground truth carries.
    """
    out: dict[str, float] = {}
    if isinstance(data, dict):
        for key, val in data.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            out.update(flatten_numeric(val, child))
    elif isinstance(data, list):
        for idx, val in enumerate(data):
            child = f"{prefix}[{idx}]"
            out.update(flatten_numeric(val, child))
    else:
        num = _coerce_number(data)
        if num is not None and prefix:
            out[prefix] = num
    return out


def ledger_size(flat: dict[str, float]) -> float:
    """The max value among sample-shaped keys — the proxy for "how much real
    history has accumulated". Zero (or no sample keys) == bootstrap-empty."""
    matched = [v for k, v in flat.items() if _SAMPLE_KEY_RE.search(k)]
    return max(matched) if matched else 0.0


class CurvePoint:
    """One revision of the ground-truth file, reduced to its numeric leaves."""

    def __init__(self, created_at: str, authored_by: str, message: str,
                 flat: dict[str, float]):
        self.created_at = created_at
        self.authored_by = authored_by
        self.message = message
        self.flat = flat
        self.ledger = ledger_size(flat)


def build_trajectory(points: list[CurvePoint]) -> tuple[list[str], list[list[str]]]:
    """Assemble the curve table: union of all metric keys (rows) across
    revisions (columns), oldest→newest. Returns (ordered_metric_keys, rows)
    where each row is [metric_key, val_at_rev_0, val_at_rev_1, ...].

    A metric absent at a given revision renders as "·" (did not exist yet).
    """
    keys: list[str] = []
    seen: set[str] = set()
    for p in points:
        for k in p.flat:
            if k not in seen:
                seen.add(k)
                keys.append(k)
    keys.sort()
    rows: list[list[str]] = []
    for k in keys:
        row = [k]
        for p in points:
            row.append(_fmt(p.flat[k]) if k in p.flat else "·")
        rows.append(row)
    return keys, rows


def _fmt(v: float) -> str:
    """Render a metric value compactly: ints without decimals, floats to 4 sig."""
    if v == int(v):
        return str(int(v))
    return f"{v:.4g}"


def mechanical_verdict(points: list[CurvePoint]) -> str:
    """The deterministic ledger-state fact (NOT the tenure quality verdict).

    TENURE-READ Read 1 instructs the reader to state this honestly; it is a
    substrate fact, so the script may compute it. The IMPROVING / COHERENT
    judgment remains the human's.
    """
    if not points:
        return ("NO SUBSTRATE — the ground-truth file has no revision chain "
                "(path wrong, or never written). Read 1 cannot run.")
    sampled = [p for p in points if p.ledger > 0]
    if not sampled:
        return ("BOOTSTRAP-EMPTY → INCONCLUSIVE-on-improvement — ground truth "
                "primed (revisions exist) but zero samples accumulated. No "
                "curve yet; survival may still be SURVIVING.")
    if len(sampled) == 1:
        return ("SINGLE DATAPOINT → no curve yet — one sampled revision "
                f"(ledger≈{_fmt(sampled[0].ledger)}). Direction unreadable "
                "until a second sampled revision lands.")
    return (f"CURVE PRESENT — {len(sampled)} sampled revisions "
            f"(ledger {_fmt(sampled[0].ledger)} → {_fmt(sampled[-1].ledger)}). "
            "Human reads direction in the trajectory table below.")


def render_read1(*, subject: str, user_id: str, ground_truth_path: str,
                 deploy_marker: str, points: list[CurvePoint]) -> str:
    """Emit the deploy-marker-stamped TENURE-READ Read-1 scaffold (markdown).

    Shape mirrors TENURE-READ §3's tracking-log entry. The mechanical curve +
    receipts are filled; the prose verdict is left blank for the human (the
    same discipline as run_eval_suite.py's SESSION.md scaffold)."""
    now = datetime.now(timezone.utc).isoformat()
    keys, rows = build_trajectory(points)
    out: list[str] = []
    out.append(f"## {now} — TENURE-READ Read 1 (ground-truth curve) — {subject}")
    out.append("")
    out.append(f"**Deploy-marker**: `{deploy_marker}` "
               "(local checkout HEAD — confirm against the commit Render ran under for this segment)")
    out.append(f"**Workspace**: `{user_id}`")
    out.append(f"**Measurand**: `{ground_truth_path}` (the program's `substrate_abi.ground_truth`)")
    out.append(f"**Revisions on the chain**: {len(points)}")
    out.append("")
    out.append(f"**Ledger state (mechanical)**: {mechanical_verdict(points)}")
    out.append("")

    if not points:
        out.append("_No revision chain — nothing to plot._")
        return "\n".join(out) + "\n"

    # Revision legend (the receipts under the curve).
    out.append("### Revision chain (oldest → newest)")
    out.append("")
    out.append("| # | created_at | authored_by | ledger | message |")
    out.append("|---|---|---|---|---|")
    for i, p in enumerate(points):
        msg = (p.message or "").replace("|", "\\|")[:70]
        out.append(f"| r{i} | {p.created_at} | `{p.authored_by}` | {_fmt(p.ledger)} | {msg} |")
    out.append("")

    # The curve table.
    if keys:
        out.append("### Trajectory (numeric leaves of the frontmatter, per revision)")
        out.append("")
        header = "| metric | " + " | ".join(f"r{i}" for i in range(len(points))) + " |"
        sep = "|---|" + "|".join("---" for _ in points) + "|"
        out.append(header)
        out.append(sep)
        for row in rows:
            metric = row[0].replace("|", "\\|")
            out.append("| `" + metric + "` | " + " | ".join(row[1:]) + " |")
        out.append("")
    else:
        out.append("_Revisions exist but carry no numeric frontmatter leaves — "
                   "the ground truth is narrative-only so far._")
        out.append("")

    # The human read — left blank (script renders, human classifies).
    out.append("### The read — ground-truth curve  ← human writes this")
    out.append("")
    out.append("_Does the measurand move the right way over tenure? Name the by-signal / "
               "by-piece direction, any decay-threshold crossings, and whether the curve is "
               "real or still bootstrapping. If BOOTSTRAP-EMPTY above, say so and stop — there "
               "is no improvement to read yet. Every load-bearing claim carries a receipt "
               "(revision_id / reproducible query)._")
    out.append("")
    out.append("**Tenure verdict (Read-1 contribution)**: _SURVIVING + COHERENT (no curve yet) "
               "| IMPROVING (curve bends right) | FINDING: <class>_ — the script never fills this.")
    out.append("")
    return "\n".join(out) + "\n"


# ===========================================================================
# DB layer — needs Supabase reach (runs where the harness runs)
# ===========================================================================

def resolve_persona_user_id(slug: str) -> str:
    """Map a persona slug → user_id via docs/alpha/personas.yaml."""
    if not _PERSONAS_YAML.exists():
        raise SystemExit(f"personas.yaml not found at {_PERSONAS_YAML}")
    with _PERSONAS_YAML.open() as f:
        registry = yaml.safe_load(f) or {}
    for p in registry.get("personas", []) or []:
        if p.get("slug") == slug:
            uid = p.get("user_id")
            if not uid:
                raise SystemExit(f"persona '{slug}' has no user_id in personas.yaml")
            return uid
    raise SystemExit(f"persona '{slug}' not found in personas.yaml")


def resolve_ground_truth_path(client: Any, user_id: str,
                              override: Optional[str]) -> str:
    """Return the workspace-absolute ground-truth path.

    Override wins (for generic workspaces / testing); otherwise resolve via the
    canonical `bundle_reader.get_ground_truth_for_workspace` (the same helper
    the kernel calibration mirror uses — Singular Implementation)."""
    rel = override
    if rel is None:
        from services.bundle_reader import get_ground_truth_for_workspace
        rel = get_ground_truth_for_workspace(user_id, client)
        if rel is None:
            raise SystemExit(
                "no active bundle declares substrate_abi.ground_truth for this "
                "workspace — pass --ground-truth explicitly, or activate a program."
            )
    rel = rel.lstrip("/")
    return rel if rel.startswith("workspace/") else f"/workspace/{rel}"


def fetch_curve_points(client: Any, user_id: str, path: str,
                       max_points: int = 500) -> list[CurvePoint]:
    """Walk the ground-truth revision chain oldest→newest, reduce each revision
    to its numeric frontmatter leaves. Reuses the canonical Authored-Substrate
    read helpers (no re-derived blob join)."""
    from services.authored_substrate import list_revisions, read_revision

    revs = list_revisions(client, user_id=user_id, path=path, limit=max_points)
    revs = list(reversed(revs))  # list_revisions is newest-first
    points: list[CurvePoint] = []
    for r in revs:
        rev = read_revision(client, user_id=user_id, path=path, revision_id=r["id"])
        content = rev.content if rev else None
        flat = flatten_numeric(extract_frontmatter(content or ""))
        created = r.get("created_at")
        created = created.isoformat() if hasattr(created, "isoformat") else str(created)
        points.append(CurvePoint(
            created_at=created,
            authored_by=r.get("authored_by", "?"),
            message=r.get("message", "") or "",
            flat=flat,
        ))
    return points


def _deploy_marker() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(_REPO_ROOT)
        ).decode().strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description="TENURE-READ Read-1 curve extractor")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--persona", help="persona slug (resolves user_id via personas.yaml)")
    g.add_argument("--user-id", help="explicit workspace user_id")
    ap.add_argument("--ground-truth", help="override the measurand path (workspace-relative)")
    ap.add_argument("--max-points", type=int, default=500, help="cap on revisions fetched")
    ap.add_argument("--emit", action="store_true",
                    help="write into the soak dir instead of stdout")
    ap.add_argument("--out", help="explicit output file path (implies write)")
    args = ap.parse_args()

    subject = args.persona or args.user_id
    user_id = resolve_persona_user_id(args.persona) if args.persona else args.user_id

    from services.supabase import get_service_client
    client = get_service_client()

    path = resolve_ground_truth_path(client, user_id, args.ground_truth)
    points = fetch_curve_points(client, user_id, path, max_points=args.max_points)
    scaffold = render_read1(
        subject=subject, user_id=user_id, ground_truth_path=path,
        deploy_marker=_deploy_marker(), points=points,
    )

    out_path: Optional[Path] = None
    if args.out:
        out_path = Path(args.out)
    elif args.emit:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        soak_dir = _REPO_ROOT / "docs" / "evaluations" / f"longitudinal-soak-{subject}"
        soak_dir.mkdir(parents=True, exist_ok=True)
        out_path = soak_dir / f"READ1-curve-{date}.md"

    if out_path:
        out_path.write_text(scaffold)
        print(f"wrote {out_path}")
    else:
        print(scaffold)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
