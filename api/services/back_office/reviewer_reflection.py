"""Back Office: Reviewer Reflection — ADR-218 + persona-reflection.md.

Phase A of the Reviewer self-evolution pipeline. Runs on cadence as an
essential YARNNN-owned back-office task. Reads the Reviewer's own
track record + operator-declared triggers, decides whether a
reflection is warranted.

Zero LLM cost in this module — Phase A is deterministic substrate
scan + trigger evaluation. If a trigger crosses, this module returns
a structured "reflect now" signal plus the substrate snapshot the
reflection-mode LLM will need. Phase B (LLM invocation — Commit 3 of
ADR-218) lives in `reviewer_agent.run_reflection()`. Phase C
(write-back + visibility — Commit 4) lives in `reflection_writer`.

This module's `run()` returns the Phase A verdict. When Commits 3+4
land, this module will call them on trigger crossing. For V1 (this
commit), crossing a trigger logs + returns a "would-reflect" marker;
the actual LLM invocation is stubbed behind a feature-off flag so
Commit 2 ships independently green without accidentally firing
real reflections before the invocation + write-back code exists.

Scope ceiling per persona-reflection.md §4:
  - Reviewer's own directory (/workspace/review/) is reflection target.
  - Everything else is untouchable.
  - This module only reads substrate; actual writes happen in Commit 4's
    reflection_writer.

Trigger YAML shape (lives in principles.md under `## Reflection triggers`):

    ---
    triggers:
      - name: cold_start_threshold_crossed
        description: "_performance.md transitioned from empty to non-empty"
        when: performance_md_first_populated
        min_days_between: 1
      - name: twenty_trade_calibration
        description: "Reviewer has rendered >=20 verdicts since last reflection"
        when: verdicts_since_last_reflection >= 20
        min_days_between: 7
      - name: sharpe_drift
        description: "..."
        when: sharpe_delta_vs_baseline >= 1.5
        min_days_between: 14
      - name: defer_rate_anomaly
        description: "Defer rate on last 50 verdicts high or low"
        when: defer_rate_last_50 >= 0.8 OR defer_rate_last_50 <= 0.1
        min_days_between: 7
    ---

`when` expressions are restricted: left-hand side is a known metric
key (see _METRIC_KEYS); comparator is one of `>= > <= < == !=`;
right-hand side is a numeric literal; expressions can be joined with
`AND` / `OR` (left-to-right, no precedence — keep it simple). Anything
outside this shape fails the parser and the trigger is skipped with a
warning. Operator-authored triggers are trusted content but the parser
is not eval() — it's a tiny recursive-descent restricted to the grammar.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from services.workspace_paths import (
    REVIEW_DECISIONS_PATH,
    REVIEW_PRINCIPLES_PATH,
)

logger = logging.getLogger(__name__)


# Feature flag: Phase B (LLM invocation) + Phase C (write-back) haven't
# landed yet (Commits 3 + 4). When True, a trigger crossing logs + returns
# "would-reflect" but does not invoke the LLM or write any files.
#
# Flip to False once Commits 3 + 4 land — the back-office task will then
# complete the full loop (A → B → C) on every crossing.
_PHASE_B_STUBBED = True


# Metric keys the trigger `when` expression can reference. Any other
# identifier in the expression fails the parser → trigger skipped.
_METRIC_KEYS = {
    # Boolean metrics (treated as 1.0 when True, 0.0 when False)
    "performance_md_first_populated",
    "performance_md_exists",
    # Counters (int)
    "verdicts_since_last_reflection",
    "approvals_last_30d",
    "rejections_last_30d",
    "defers_last_30d",
    # Rates (float 0.0..1.0)
    "defer_rate_last_50",
    "approve_rate_last_50",
    "reject_rate_last_50",
    # Deltas (float, dimensionless)
    "sharpe_delta_vs_baseline",
    "expectancy_delta_vs_baseline",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run(client: Any, user_id: str, task_slug: str) -> dict:
    """Phase A: evaluate reflection triggers against substrate.

    Returns the standard back-office executor shape:
      {
          "content": "<markdown report>",
          "structured": {
              "triggered": bool,
              "winning_trigger": dict | None,
              "reason": str,
              "substrate_snapshot": dict,
              "phase_b_invoked": bool,
          },
      }

    Idempotent within a task cadence — calling multiple times on the
    same day produces the same verdict (triggers respect
    `min_days_between` against the last reflection timestamp, not the
    last invocation).
    """
    started_at = datetime.now(timezone.utc)
    result_structured: dict = {
        "triggered": False,
        "winning_trigger": None,
        "reason": "",
        "substrate_snapshot": {},
        "phase_b_invoked": False,
    }

    try:
        # 1. Load operator-declared triggers from principles.md
        principles_md = await _read_file(client, user_id, REVIEW_PRINCIPLES_PATH)
        triggers = _parse_triggers(principles_md)
        if not triggers:
            result_structured["reason"] = "no triggers declared in principles.md"
            return _shape_result(started_at, result_structured, trigger_count=0)

        # 2. Snapshot substrate into metric values
        substrate = await _snapshot_substrate(client, user_id, started_at)
        result_structured["substrate_snapshot"] = _public_snapshot(substrate)

        # 3. Check last-reflection timestamp for min_days_between gating
        last_reflection_ts = await _read_last_reflection_ts(client, user_id)

        # 4. Evaluate each trigger in declared order. First one whose
        #    `when` crosses AND whose `min_days_between` has elapsed wins.
        winning: dict | None = None
        for trig in triggers:
            verdict, reason = _evaluate_trigger(trig, substrate, last_reflection_ts, started_at)
            logger.info(
                "[REFLECTION] trigger=%s verdict=%s reason=%s",
                trig.get("name", "?"), verdict, reason,
            )
            if verdict is True:
                winning = trig
                break

        if not winning:
            result_structured["reason"] = "no trigger crossed"
            return _shape_result(started_at, result_structured, trigger_count=len(triggers))

        result_structured["triggered"] = True
        result_structured["winning_trigger"] = _public_trigger(winning)

        # 5. Phase B (LLM invocation) + Phase C (write-back). Stubbed in this
        #    commit — Commits 3 + 4 of ADR-218 flip `_PHASE_B_STUBBED` off
        #    and wire `reviewer_agent.run_reflection()` + `reflection_writer`.
        if _PHASE_B_STUBBED:
            result_structured["reason"] = (
                f"trigger '{winning.get('name', '?')}' crossed; "
                "Phase B invocation stubbed (ADR-218 Commits 3+4 pending)"
            )
            logger.info(
                "[REFLECTION] would reflect for user=%s trigger=%s (stubbed)",
                user_id[:8], winning.get("name", "?"),
            )
            return _shape_result(started_at, result_structured, trigger_count=len(triggers))

        # Commit 3+4 wiring target (not live yet):
        # from agents.reviewer_agent import run_reflection
        # from services.reflection_writer import apply_reflection_writes
        # proposals = await run_reflection(client, user_id, substrate, winning)
        # write_summary = await apply_reflection_writes(client, user_id, proposals)
        # result_structured["phase_b_invoked"] = True
        # result_structured["write_summary"] = write_summary
        return _shape_result(started_at, result_structured, trigger_count=len(triggers))

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[REFLECTION] Phase A failed for user=%s: %s",
            user_id[:8], exc,
        )
        result_structured["reason"] = f"Phase A exception: {exc}"
        return _shape_result(started_at, result_structured, trigger_count=0)


# ---------------------------------------------------------------------------
# Substrate snapshot
# ---------------------------------------------------------------------------

async def _snapshot_substrate(
    client: Any, user_id: str, now: datetime
) -> dict:
    """Build the metric dict the trigger evaluator reads against.

    All reads are substrate-only (zero LLM). Reuses parsers from
    `reviewer_calibration` for decisions.md + _performance.md
    aggregates — singular implementation, no duplicated parsing.
    """
    from services.back_office.reviewer_calibration import (
        _read_decisions,
        _read_domain_outcome_totals,
    )

    decisions = await _read_decisions(client, user_id)
    outcome_totals = await _read_domain_outcome_totals(client, user_id)

    # Filter to verdicts since the last reflection timestamp (if any)
    last_reflection_ts = await _read_last_reflection_ts(client, user_id)
    if last_reflection_ts is not None:
        decisions_since_last = [
            d for d in decisions if d.get("ts") and d["ts"] > last_reflection_ts
        ]
    else:
        decisions_since_last = decisions

    # Count last-50 verdict distribution
    last_50 = decisions[-50:] if len(decisions) >= 50 else decisions
    last_50_total = len(last_50)
    approvals_50 = sum(1 for d in last_50 if d.get("verdict") == "approve")
    rejects_50 = sum(1 for d in last_50 if d.get("verdict") == "reject")
    defers_50 = sum(1 for d in last_50 if d.get("verdict") == "defer")

    # Last-30d counts (rolling window)
    thirty_days_ago = now - timedelta(days=30)
    decisions_30d = [d for d in decisions if d.get("ts") and d["ts"] >= thirty_days_ago]
    approvals_30d = sum(1 for d in decisions_30d if d.get("verdict") == "approve")
    rejects_30d = sum(1 for d in decisions_30d if d.get("verdict") == "reject")
    defers_30d = sum(1 for d in decisions_30d if d.get("verdict") == "defer")

    # Performance-md state — per persona-reflection.md cold-start discussion,
    # "first populated" means at least one domain has a non-zero total now AND
    # no reflection has occurred yet (first-populated is a one-shot event).
    performance_md_exists = any(
        v.get("has_performance_md") for v in outcome_totals.values()
    )
    performance_md_first_populated = (
        performance_md_exists and last_reflection_ts is None
    )

    # Sharpe + expectancy deltas — aggregates across domains if present.
    # Stubbed as None for V1 — the reconciler exposes per-domain rolling
    # Sharpe/expectancy in _performance.md frontmatter; wiring through
    # _read_domain_outcome_totals returns them but baseline comparison
    # needs an operator-declared baseline per domain, which lives in
    # _operator_profile.md (future enhancement). For V1 these metrics
    # return 0.0 if no baseline available → trigger won't cross by
    # default on a fresh workspace.
    sharpe_delta = 0.0
    expectancy_delta = 0.0

    return {
        "now": now,
        "last_reflection_ts": last_reflection_ts,
        # Boolean metrics (1.0 / 0.0 for the expression evaluator)
        "performance_md_first_populated": 1.0 if performance_md_first_populated else 0.0,
        "performance_md_exists": 1.0 if performance_md_exists else 0.0,
        # Counters
        "verdicts_since_last_reflection": float(len(decisions_since_last)),
        "approvals_last_30d": float(approvals_30d),
        "rejections_last_30d": float(rejects_30d),
        "defers_last_30d": float(defers_30d),
        # Rates
        "defer_rate_last_50": (defers_50 / last_50_total) if last_50_total else 0.0,
        "approve_rate_last_50": (approvals_50 / last_50_total) if last_50_total else 0.0,
        "reject_rate_last_50": (rejects_50 / last_50_total) if last_50_total else 0.0,
        # Deltas (V1 stubbed — future enhancement with operator-baseline wiring)
        "sharpe_delta_vs_baseline": sharpe_delta,
        "expectancy_delta_vs_baseline": expectancy_delta,
    }


def _public_snapshot(substrate: dict) -> dict:
    """Filter internal fields (datetime objects, raw lists) before returning
    the structured output — back-office executor results serialize to JSON.
    """
    return {
        k: v for k, v in substrate.items()
        if k in _METRIC_KEYS
    }


# ---------------------------------------------------------------------------
# Trigger parsing (reads principles.md `## Reflection triggers` YAML block)
# ---------------------------------------------------------------------------

# Header that introduces the triggers block inside principles.md
_TRIGGERS_HEADER_RE = re.compile(
    r"^##\s+Reflection\s+triggers\s*$", re.IGNORECASE | re.MULTILINE
)
# Opening fence `---` begins the YAML; closing `---` ends it
_YAML_FENCE = "---"


def _parse_triggers(principles_md: str) -> list[dict]:
    """Extract the `triggers:` list from the `## Reflection triggers`
    YAML block in principles.md. Returns [] if the section is absent or
    malformed.

    Tolerant: missing section, empty block, or a parse error logs a
    warning and returns [] — the back-office task then reports
    "no triggers declared" without crashing.
    """
    if not principles_md:
        return []

    # Find the Reflection-triggers header
    header_match = _TRIGGERS_HEADER_RE.search(principles_md)
    if not header_match:
        return []

    after_header = principles_md[header_match.end():]

    # Find the opening YAML fence (must be on its own line, leading
    # whitespace tolerated)
    fence_start = _find_fence(after_header, start=0)
    if fence_start is None:
        return []

    fence_end = _find_fence(after_header, start=fence_start + len(_YAML_FENCE))
    if fence_end is None:
        return []

    yaml_text = after_header[fence_start + len(_YAML_FENCE):fence_end].strip()
    if not yaml_text:
        return []

    # Try PyYAML; fall back to minimal custom parser for robustness
    try:
        import yaml  # type: ignore[import-untyped]
        parsed = yaml.safe_load(yaml_text)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REFLECTION] triggers YAML parse failed: %s — triggers skipped", exc
        )
        return []

    if not isinstance(parsed, dict):
        return []
    triggers = parsed.get("triggers")
    if not isinstance(triggers, list):
        return []

    # Validate each trigger has the required fields
    valid: list[dict] = []
    for t in triggers:
        if not isinstance(t, dict):
            continue
        if not t.get("name") or not t.get("when"):
            continue
        t.setdefault("description", "")
        t.setdefault("min_days_between", 1)
        valid.append(t)

    return valid


def _find_fence(text: str, start: int) -> int | None:
    """Return the index of the next `---` at line-start, or None."""
    idx = start
    while idx < len(text):
        # Either at beginning of string or preceded by newline
        if idx == 0 or text[idx - 1] == "\n":
            if text.startswith(_YAML_FENCE, idx):
                # Allow trailing whitespace before the newline
                eol = text.find("\n", idx)
                if eol == -1:
                    eol = len(text)
                between = text[idx + len(_YAML_FENCE):eol].strip()
                if not between:
                    return idx
        idx += 1
    return None


# ---------------------------------------------------------------------------
# Trigger evaluation (restricted expression language)
# ---------------------------------------------------------------------------

# Comparators supported in trigger `when` expressions
_COMPARATORS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}
# Sort longest-first so `>=` matches before `>` during tokenization
_COMPARATOR_KEYS_SORTED = sorted(_COMPARATORS.keys(), key=len, reverse=True)

# Atomic clause regex: <identifier> <op> <number>
# Also accepts a bare identifier (treated as `<identifier> == 1`, useful
# for boolean metrics like `performance_md_first_populated`)
_CLAUSE_RE = re.compile(
    r"^\s*(?P<ident>[a-z][a-z0-9_]*)\s*"
    r"(?:(?P<op>>=|<=|==|!=|>|<)\s*(?P<num>-?\d+(?:\.\d+)?))?\s*$"
)


def _evaluate_trigger(
    trigger: dict,
    substrate: dict,
    last_reflection_ts: datetime | None,
    now: datetime,
) -> tuple[bool, str]:
    """Evaluate a single trigger. Returns (crossed: bool, reason: str).

    Checks `min_days_between` first — if not enough time has elapsed
    since the last reflection, the trigger cannot cross regardless of
    its `when` expression. This is the rate-limit invariant.
    """
    # Rate-limit gate
    min_days = trigger.get("min_days_between", 1)
    try:
        min_days = int(min_days)
    except (TypeError, ValueError):
        min_days = 1
    if last_reflection_ts is not None:
        elapsed_days = (now - last_reflection_ts).total_seconds() / 86400.0
        if elapsed_days < min_days:
            return False, (
                f"rate-limited: {elapsed_days:.1f}d since last reflection "
                f"(min_days_between={min_days})"
            )

    # `when` expression
    when_expr = trigger.get("when", "")
    if not isinstance(when_expr, str) or not when_expr.strip():
        return False, "empty `when` expression"

    try:
        crossed = _eval_expr(when_expr, substrate)
    except _TriggerParseError as exc:
        return False, f"expression parse error: {exc}"

    if crossed:
        return True, f"`{when_expr.strip()}` evaluated True"
    return False, f"`{when_expr.strip()}` evaluated False"


class _TriggerParseError(Exception):
    pass


def _eval_expr(expr: str, substrate: dict) -> bool:
    """Evaluate a restricted boolean expression.

    Grammar:
        expr       := clause (('AND'|'OR') clause)*
        clause     := ident [comparator number]
        ident      := known metric key
        comparator := '>=' | '<=' | '==' | '!=' | '>' | '<'
        number     := -?\\d+(.\\d+)?

    Left-to-right evaluation, no precedence. Whitespace tolerated.
    Case-sensitive keywords ('AND'/'OR'); identifier match is exact.
    """
    # Tokenize on AND / OR boundaries (case-sensitive per spec)
    # Use a regex that preserves the operators
    tokens = re.split(r"\s+(AND|OR)\s+", expr.strip())
    if not tokens:
        raise _TriggerParseError("empty expression")

    # tokens alternates: clause, op, clause, op, ...
    result = _eval_clause(tokens[0], substrate)
    i = 1
    while i < len(tokens) - 1:
        op = tokens[i]
        rhs = _eval_clause(tokens[i + 1], substrate)
        if op == "AND":
            result = result and rhs
        elif op == "OR":
            result = result or rhs
        else:
            raise _TriggerParseError(f"unknown boolean operator: {op}")
        i += 2
    return result


def _eval_clause(clause: str, substrate: dict) -> bool:
    """Evaluate a single atomic clause."""
    m = _CLAUSE_RE.match(clause.strip())
    if not m:
        raise _TriggerParseError(f"malformed clause: '{clause.strip()}'")
    ident = m.group("ident")
    op = m.group("op")
    num_str = m.group("num")

    if ident not in _METRIC_KEYS:
        raise _TriggerParseError(f"unknown metric: '{ident}'")
    lhs = substrate.get(ident, 0.0)
    # Normalize boolean-ish values to float
    try:
        lhs = float(lhs)
    except (TypeError, ValueError):
        lhs = 0.0

    # Bare identifier → treat as "lhs >= 1.0" (boolean-true semantics)
    if op is None:
        return lhs >= 1.0

    try:
        rhs = float(num_str)
    except (TypeError, ValueError) as exc:
        raise _TriggerParseError(f"invalid number: '{num_str}'") from exc

    comparator = _COMPARATORS.get(op)
    if comparator is None:
        raise _TriggerParseError(f"unknown comparator: '{op}'")
    return comparator(lhs, rhs)


# ---------------------------------------------------------------------------
# Last-reflection timestamp (read reflections.md if it exists)
# ---------------------------------------------------------------------------

_REFLECTION_TS_RE = re.compile(
    r"^timestamp:\s*(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s*$",
    re.MULTILINE,
)


async def _read_last_reflection_ts(
    client: Any, user_id: str
) -> datetime | None:
    """Return the timestamp of the most recent reflection run, or None
    if reflections.md is absent or empty.

    reflections.md format (append-only, latest entry last):

        --- reflection ---
        timestamp: 2026-05-15T04:00:00+00:00
        trigger: twenty_trade_calibration
        reviewer_identity: ai:reviewer-sonnet-v4
        ...
        ---
    """
    content = await _read_file(client, user_id, "review/reflections.md")
    if not content:
        return None

    timestamps: list[datetime] = []
    for m in _REFLECTION_TS_RE.finditer(content):
        ts_str = m.group("ts")
        try:
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            timestamps.append(datetime.fromisoformat(ts_str))
        except ValueError:
            continue

    if not timestamps:
        return None
    return max(timestamps)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _read_file(client: Any, user_id: str, path: str) -> str:
    """Read a workspace_files row's content. Empty string on any failure.

    Tolerates both leading-slash and relative forms since
    workspace_paths.py stores relative paths but substrate reads
    commonly pass the leading-slash form.
    """
    full_path = path if path.startswith("/workspace/") else f"/workspace/{path.lstrip('/')}"
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", full_path)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REFLECTION] read failed path=%s user=%s: %s",
            full_path, user_id[:8], exc,
        )
        return ""
    rows = result.data or []
    if not rows:
        return ""
    return rows[0].get("content") or ""


def _public_trigger(trig: dict) -> dict:
    """Strip the trigger down to a JSON-safe public summary."""
    return {
        "name": trig.get("name", ""),
        "description": trig.get("description", ""),
        "when": trig.get("when", ""),
        "min_days_between": trig.get("min_days_between", 1),
    }


def _shape_result(
    started_at: datetime,
    structured: dict,
    *,
    trigger_count: int,
) -> dict:
    """Produce the back-office executor return shape."""
    report_lines = [
        "# Reviewer Reflection — Phase A",
        "",
        f"**Ran**: {started_at.isoformat(timespec='seconds')}",
        f"**Triggers declared**: {trigger_count}",
        f"**Triggered**: {structured.get('triggered')}",
        f"**Reason**: {structured.get('reason', '')}",
    ]
    winning = structured.get("winning_trigger")
    if winning:
        report_lines += [
            "",
            "## Winning trigger",
            "",
            f"- **name**: `{winning.get('name', '?')}`",
            f"- **when**: `{winning.get('when', '?')}`",
            f"- **description**: {winning.get('description', '')}",
        ]
    report_lines += [
        "",
        "## Substrate snapshot",
        "",
    ]
    snap = structured.get("substrate_snapshot") or {}
    for k in sorted(snap.keys()):
        report_lines.append(f"- `{k}`: {snap[k]}")
    report_lines += [
        "",
        "_Phase B (LLM invocation) + Phase C (write-back) land in ADR-218 Commits 3 + 4. "
        "This report is Phase A only (zero-LLM trigger evaluation)._",
    ]
    return {
        "content": "\n".join(report_lines) + "\n",
        "structured": structured,
    }
