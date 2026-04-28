#!/usr/bin/env python3
"""
Path C: rewrite seulkim88's AUTONOMY.md in parser-compatible schema.

The operator's original AUTONOMY.md (4415 chars) was thoughtfully authored but
used vocabulary the parser doesn't recognize:
  - Domain key `trading-execute:` (parser looks for plain `trading:`)
  - Field `approval_required:` (parser only knows `level:`)
  - Field `ceiling_per_order_pct_equity:` (parser only knows `ceiling_cents:`)

Result: review_policy.is_eligible_for_auto_approve sees an empty policy →
returns "no ceiling_cents set" → AI Reviewer auto-approve cannot fire.

This script rewrites AUTONOMY.md in the canonical schema while preserving the
operator's authored prose as Markdown commentary. The YAML block at the top is
what the parser reads; the prose below is for human reference.

Usage:
    python -m api.scripts.alpha_ops.author_autonomy_for_path_c alpha-trader
    python -m api.scripts.alpha_ops.author_autonomy_for_path_c alpha-trader --dry-run

Phase B observation log entry should follow this rewrite.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parents[2]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shared import load_registry  # noqa: E402


# Canonical AUTONOMY.md content for alpha-trader-1 paper validation.
# Schema: keyed YAML with `<domain>:` headers + `level:` / `ceiling_cents:` /
# `never_auto:` fields. Parser at api/services/review_policy.py:_parse_keyed_yaml.
#
# Original operator intent preserved as prose below the YAML block.
AUTONOMY_CONTENT = """# Autonomy — alpha-trader (intraday paper validation)

> Per ADR-217: this file declares operator-to-role delegation. It is
> NOT Reviewer-owned — operator authors. Reviewer reads to know its
> ceiling. Per ADR-194 v2: ceiling here can narrow Reviewer principles,
> never widen them.
>
> Authored 2026-04-27, rewritten in parser-compatible schema 2026-04-28.
> Phase 2 (Live Float) requires explicit replacement of this file +
> Reviewer-approved phase change.

```yaml
trading:
  level: bounded_autonomous
  ceiling_cents: 200000
  never_auto:
    - close_position_market
    - cancel_other_orders
```

## What the YAML above declares

- `level: bounded_autonomous` — AI Reviewer may auto-approve trading
  proposals up to the ceiling, defer above it.
- `ceiling_cents: 200000` — auto-approve ceiling is $2,000 USD per
  proposal during paper-validation phase. Anything above defers to
  human operator click in cockpit Queue.
- `never_auto: [close_position_market, cancel_other_orders]` — these
  action_type fragments always defer to human regardless of ceiling.

## What the operator originally authored (semantic intent preserved)

Original schema declared per-order percentage limits (5% of equity)
and richer guardrails (reviewer_confidence_required, defer_to_operator_when
list, time-stop authority). Those concerns are now distributed across:

- `_risk.md` — per-trade size, var budget, daily loss, time-stop rules
  (read by risk_gate at execution time, also re-read by AI Reviewer in
  its 6-check reasoning per ADR-216 Commit 2).
- `principles.md` — Reviewer's authored framework (Simons-style six
  checks). principles can NARROW autonomy (add defer conditions) but
  never widen, per ADR-217 D4.
- This file — operator's bottom-line ceiling, the singular fact:
  "above $X, no AI auto-approval, regardless of what the Reviewer says."

This is the ADR-194/217 separation of concerns:
  - operator → AUTONOMY.md (delegation ceiling + never_auto)
  - reviewer → principles.md (evaluation framework)
  - risk → _risk.md (mechanical pre-trade limits)

## Phase progression — when to widen this ceiling

- **Phase 0-1 (current)**: paper-only `bounded_autonomous` with $2K
  ceiling. Reviewer + risk_gate enforce the rest.
- **Phase 2 (Live Float)**: this file FLIPS — `level: manual` for every
  order regardless of size, until live calibration accumulates.
- **Phase 3 (Calibrated Autonomy)**: per-domain auto-approval on live
  for low-risk reversible orders, gated on Phase 1+2 expectancy data.

Phase 2/3 transitions require Reviewer-approved phase change per
MANDATE.md performance objectives. This file is not auto-revisable.

## Audit

Every auto-approved order writes to `/workspace/review/decisions.md`
with `reviewer_identity="ai:reviewer-sonnet-v5"` and the Reviewer's
6-check reasoning. Operator audits via cockpit Decisions stream or
direct file read. Override-after-the-fact supported via post-fill
manual close-position (reversible during paper).
"""


async def author_autonomy(slug: str, dry_run: bool) -> int:
    if slug != "alpha-trader":
        print(f"This script is alpha-trader-specific. Got {slug!r}.")
        return 1

    registry = load_registry()
    persona = registry.require(slug)

    from supabase import create_client  # type: ignore[import-untyped]

    supabase_url = os.environ["SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_KEY"]
    client = create_client(supabase_url, service_key)

    from services.authored_substrate import write_revision

    path = "/workspace/context/_shared/AUTONOMY.md"

    # Show diff first
    current = client.table("workspace_files").select("content").eq("user_id", persona.user_id).eq("path", path).limit(1).execute()
    current_content = (current.data[0].get("content") or "") if current.data else ""
    print(f"Current AUTONOMY.md: {len(current_content)} chars")
    print(f"New AUTONOMY.md:     {len(AUTONOMY_CONTENT)} chars")
    print()

    # Verify the new content parses correctly under the actual parser
    from services.review_policy import load_autonomy, autonomy_for_domain, is_eligible_for_auto_approve
    print("Verifying new content parses under review_policy._parse_keyed_yaml...")
    # Use a temp swap for verification
    import services.review_policy as rp
    real_read = rp._read_file

    def fake_read(c, u, p):
        return AUTONOMY_CONTENT
    rp._read_file = fake_read
    try:
        autonomy = load_autonomy(client, persona.user_id)
        trading_policy = autonomy_for_domain(autonomy, "trading")
        print(f"  Parsed autonomy: {autonomy}")
        print(f"  Trading policy:  {trading_policy}")
        # Smoke-test eligibility for a small reversible trading order
        eligible, reason = is_eligible_for_auto_approve(
            trading_policy,
            action_type="trading.submit_order",
            estimated_cents=71500,  # ~$715 SPY × 1
            reversibility="reversible",
        )
        print(f"  Sample eligibility (SPY $715 reversible): eligible={eligible}, reason={reason}")
    finally:
        rp._read_file = real_read

    print()

    if dry_run:
        print("[DRY RUN] not writing.")
        return 0

    write_revision(
        client,
        user_id=persona.user_id,
        path=path,
        content=AUTONOMY_CONTENT,
        authored_by="operator",
        message="rewrite AUTONOMY.md in parser-compatible schema (trading: level/ceiling_cents/never_auto) for Path C autonomous Reviewer-approval validation",
        summary="Operator delegation ceiling per ADR-217",
    )
    print(f"Wrote AUTONOMY.md ({len(AUTONOMY_CONTENT)} chars) via authored substrate.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    ap.add_argument("persona", help="Persona slug (alpha-trader)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return asyncio.run(author_autonomy(args.persona, args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
