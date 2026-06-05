"""ADR-294 D6 — Scenario YAML parser + runner.

Scenarios are first-class versioned eval artifacts under
docs/evaluations/scenarios/. Assertion-light, evaluation-heavy —
the runner logs what happened and lets capture.py snapshot the
artifact. `expect:` clauses are interpretation hints, not pass/fail gates.

Renamed from "observations" to "evaluations" on 2026-05-26 — see
docs/evaluations/README.md §"Why 'evaluations' and not 'observations'"
for the criterion-declaration discipline rationale.

2026-05-27 evaluation-infrastructure consolidation: turn-shape vocabulary
extended with `write_substrate`, `flip_frontmatter_field`, and `seed_draft`
(author-shape probes — formerly required pure-Python canary scripts). See
docs/analysis/evaluation-infrastructure-audit-2026-05-27.md for the
rationale + the singular-implementation discipline that motivated the
consolidation.

Schema (v1):
    scenario: <slug>
    description: |
      Free-form description of what the scenario validates.
    persona: <persona-slug>
    setup:
      - fire: <recurrence-slug>             # manual_fire a recurrence
      - write_substrate:                     # operator-voice seed write
          path: <workspace-relative>
          authored_by: operator-proxy:scenario-runner:acting-as-<persona>
          content: |
            ...
      - write_substrate_from_file:           # single-source-of-truth variant:
          path: <workspace-relative>         # load content from repo-relative file
          source: <repo-relative path>       # avoids dual-source drift when applying
          authored_by: ...                   # versioned bundle/template content
          message: "Optional revision message"
      - seed_draft:                          # convenience: author-shape probe
          slug: <piece-slug>
          template: anti-pattern-voice      # from draft_templates.TEMPLATES
          title: "Optional override title"  # otherwise derived from template
    turns:
      - send_message: "..."                 # operator-voice chat
        expect:                              # interpretation hints (logged, never fail-hard)
          - reviewer_responded
          - no_substrate_writes
      - emit_proposal:
          template: signal-2-nvda          # uses existing emit_test_proposal logic
        expect:
          - reviewer_verdict_in: [approve, reject]
      - write_substrate:                     # mid-scenario substrate write
          path: <workspace-relative>
          content: |
            ...
          message: "Optional revision message"  # defaults to scenario-derived
      - flip_frontmatter_field:              # convenience: read + regex-replace + write
          path: <workspace-relative>
          field: status                      # YAML frontmatter field name
          value: ready_for_review            # new value
          message: "Optional revision message"
      - approve_proposal:
          id: "{{previous_proposal_id}}"    # NOTE: template var resolution is operator-side
          reasoning: "..."
      - reject_proposal:
          id: "..."
          reason: "..."
    capture:
      - revision_chain
      - decisions_md
      - action_proposals
      - token_usage_by_caller
      - all_session_messages
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Scenario data
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1


class ScenarioError(Exception):
    """Raised on malformed scenario file or runner failure."""


@dataclass
class Scenario:
    """Parsed scenario file."""

    slug: str
    description: str
    persona: str
    setup: list[dict] = field(default_factory=list)
    turns: list[dict] = field(default_factory=list)
    capture: list[str] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION

    @classmethod
    def from_file(cls, path: Path) -> "Scenario":
        raw = yaml.safe_load(path.read_text())
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict) -> "Scenario":
        if not isinstance(raw, dict):
            raise ScenarioError(f"Scenario must be a YAML dict, got {type(raw).__name__}")
        schema_version = int(raw.get("scenario_schema_version", SCHEMA_VERSION))
        if schema_version != SCHEMA_VERSION:
            raise ScenarioError(
                f"Unsupported scenario_schema_version {schema_version}; "
                f"runner only supports v{SCHEMA_VERSION}"
            )
        slug = raw.get("scenario")
        if not slug:
            raise ScenarioError("Scenario missing required 'scenario' field")
        persona = raw.get("persona")
        if not persona:
            raise ScenarioError("Scenario missing required 'persona' field")
        return cls(
            slug=str(slug),
            description=str(raw.get("description", "")),
            persona=str(persona),
            setup=list(raw.get("setup") or []),
            turns=list(raw.get("turns") or []),
            capture=list(raw.get("capture") or []),
            schema_version=schema_version,
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class ScenarioRunner:
    """Executes a Scenario against a workspace via OperatorProxy + capture.

    Discipline: every evaluation is logged, never fail-hard on expect:
    mismatches. Scenarios validate behavior shape; humans interpret.
    """

    def __init__(self, scenario: Scenario, *, caller: str = "scenario-runner"):
        self.scenario = scenario
        self.caller = caller
        self.evaluations: list[dict] = []   # ordered log of {turn, expect, observed} — note: "observed" is the verb of seeing, retained per FOUNDATIONS vocabulary

    async def run(self, evaluation_folder: Path) -> dict:
        """Execute scenario. Returns summary dict + writes capture artifacts."""
        from .client import OperatorProxy
        from .capture import CaptureSession

        evaluation_folder.mkdir(parents=True, exist_ok=True)
        proxy = OperatorProxy.from_persona(self.scenario.persona, caller=self.caller)
        # Mint JWT + fetch user_id resolution via the proxy's config.
        user_id = proxy.config.user_id

        capture = await CaptureSession.start(
            user_id,
            evaluation_folder,
            scenario_name=self.scenario.slug,
        )
        capture.metadata = {
            "scenario_slug": self.scenario.slug,
            "scenario_description": self.scenario.description,
            "persona": self.scenario.persona,
            "caller": self.caller,
        }

        async with proxy:
            # Setup phase — non-turn actions
            for step in self.scenario.setup:
                await self._execute_setup_step(proxy, step)

            # Turn phase — operator-voice sequence
            for i, turn in enumerate(self.scenario.turns):
                obs = await self._execute_turn(proxy, turn, turn_index=i)
                self.evaluations.append(obs)

        capture.metadata["evaluations"] = self.evaluations
        await capture.snapshot()

        return {
            "scenario": self.scenario.slug,
            "persona": self.scenario.persona,
            "turns_executed": len(self.evaluations),
            "evaluation_folder": str(evaluation_folder),
        }

    # ----- step executors -----

    async def _execute_setup_step(self, proxy: Any, step: dict) -> None:
        """Setup steps: fire | write_substrate | delete_substrate. Logged but not turn-counted."""
        if "delete_substrate" in step:
            # Reset step: remove a workspace_files head row (revision chain
            # preserved per ADR-209). Same shape establish_substrate honors —
            # kept in lockstep so a scenario behaves identically through the
            # run_scenario path and the eval-suite pre-flight path.
            path = step["delete_substrate"]
            removed = await _delete_substrate_file(proxy.config.user_id, path)
            self.evaluations.append({
                "phase": "setup",
                "action": "delete_substrate",
                "path": path,
                "removed": removed,
            })
            return

        if "fire" in step:
            slug = step["fire"]
            # Invoke manual_fire path directly via dispatch.
            await _manual_fire(proxy.config.user_id, slug)
            self.evaluations.append({
                "phase": "setup",
                "action": "fire",
                "slug": slug,
                "result": "dispatched",
            })
            return

        if "write_substrate" in step:
            sub = step["write_substrate"]
            path = sub["path"]
            content = sub["content"]
            authored_by = sub.get("authored_by") or proxy.config.caller_identity
            result = await _write_substrate_with_author(
                proxy.config.user_id,
                path,
                content,
                authored_by=authored_by,
                message=f"Setup write for scenario {self.scenario.slug}",
            )
            self.evaluations.append({
                "phase": "setup",
                "action": "write_substrate",
                "path": path,
                "authored_by": authored_by,
                "revision_id": result.get("revision_id"),
            })
            return

        if "write_substrate_from_file" in step:
            # Single-source-of-truth variant of write_substrate: load `content`
            # from a repo-relative file path instead of embedding it inline in
            # the scenario YAML. Used when applying a bundle template file (or
            # any other versioned-in-repo artifact) as a setup step — avoids
            # the dual-source-of-truth drift hazard of duplicating bundle
            # content inside a scenario YAML. Added 2026-05-28 for ADR-305
            # Piece 3 (apply Piece 2's principles.md rewrite as substrate
            # setup before re-running the full eval suite).
            #
            # `source` is resolved as: (a) absolute path as-is, or (b)
            # repo-relative — parent of the api/ directory where scenarios.py
            # lives (so paths like `docs/programs/.../principles.md` resolve
            # regardless of the runner's invocation cwd).
            sub = step["write_substrate_from_file"]
            target_path = sub["path"]
            source_raw = sub["source"]
            authored_by = sub.get("authored_by") or proxy.config.caller_identity
            message = sub.get("message") or f"Setup write from {source_raw} for scenario {self.scenario.slug}"
            source_path = Path(source_raw)
            if not source_path.is_absolute():
                # Repo root = parent of api/ (this file is api/services/operator_proxy/scenarios.py
                # → parents[3] is the repo root).
                repo_root = Path(__file__).resolve().parents[3]
                source_path = repo_root / source_raw
            content = source_path.read_text()
            result = await _write_substrate_with_author(
                proxy.config.user_id,
                target_path,
                content,
                authored_by=authored_by,
                message=message,
            )
            self.evaluations.append({
                "phase": "setup",
                "action": "write_substrate_from_file",
                "path": target_path,
                "source": source_path,
                "authored_by": authored_by,
                "revision_id": result.get("revision_id"),
            })
            return

        if "seed_draft" in step:
            # Author-shape convenience: compose profile.md + content.md from a
            # named template under services/operator_proxy/draft_templates.py.
            # Equivalent to two write_substrate steps but reads the template
            # once + applies common boilerplate (slug, title, created_at_iso).
            sub = step["seed_draft"]
            revisions = await _seed_draft_from_template(
                proxy.config.user_id,
                slug=sub["slug"],
                template_name=sub["template"],
                title=sub.get("title"),
                authored_by=sub.get("authored_by") or proxy.config.caller_identity,
                scenario_slug=self.scenario.slug,
            )
            self.evaluations.append({
                "phase": "setup",
                "action": "seed_draft",
                "piece_slug": sub["slug"],
                "template": sub["template"],
                "profile_revision_id": revisions.get("profile_revision_id"),
                "content_revision_id": revisions.get("content_revision_id"),
            })
            return

        # Unknown setup step — log and continue (assertion-light).
        self.evaluations.append({
            "phase": "setup",
            "action": "unknown",
            "raw": step,
        })

    async def _execute_turn(self, proxy: Any, turn: dict, *, turn_index: int) -> dict:
        """Turn: send_message | emit_proposal | approve_proposal | etc."""
        obs: dict = {
            "phase": "turn",
            "turn_index": turn_index,
            "expect": turn.get("expect", []),
        }

        if "send_message" in turn:
            content = turn["send_message"]
            obs["action"] = "send_message"
            obs["content"] = content
            response = await proxy.send_message(content)
            obs["response_text_preview"] = (response.get("text") or "")[:500]
            obs["reviewer_verdict_present"] = response.get("reviewer_verdict") is not None
            return obs

        if "emit_proposal" in turn:
            template_name = turn["emit_proposal"].get("template")
            obs["action"] = "emit_proposal"
            obs["template"] = template_name
            if not template_name:
                obs["error"] = "emit_proposal turn missing required 'template' field"
                return obs
            try:
                result = await _emit_proposal_from_template(
                    proxy.config.user_id, template_name
                )
                obs["proposal_id"] = result.get("proposal_id")
                obs["proposal_status"] = (result.get("proposal") or {}).get("status")
                obs["success"] = result.get("success", False)
            except KeyError as exc:
                obs["error"] = str(exc)
            except Exception as exc:
                obs["error"] = f"{type(exc).__name__}: {exc}"
            return obs

        if "approve_proposal" in turn:
            proposal_id = turn["approve_proposal"].get("id")
            reasoning = turn["approve_proposal"].get("reasoning", "Scenario-driven approval")
            obs["action"] = "approve_proposal"
            obs["proposal_id"] = proposal_id
            result = await proxy.approve_proposal(proposal_id, reasoning=reasoning)
            obs["result"] = result
            return obs

        if "reject_proposal" in turn:
            proposal_id = turn["reject_proposal"].get("id")
            reason = turn["reject_proposal"].get("reason", "Scenario-driven rejection")
            obs["action"] = "reject_proposal"
            obs["proposal_id"] = proposal_id
            result = await proxy.reject_proposal(proposal_id, reason=reason)
            obs["result"] = result
            return obs

        if "write_substrate" in turn:
            # Mid-scenario substrate write — same shape as setup `write_substrate`
            # but executed in turn sequence so it can interleave with send_message
            # / emit_proposal / etc. Required for author-shape probes that
            # transition substrate AFTER an operator-voice nudge.
            sub = turn["write_substrate"]
            path = sub["path"]
            content = sub["content"]
            authored_by = sub.get("authored_by") or proxy.config.caller_identity
            message = sub.get("message") or f"Turn write for scenario {self.scenario.slug}"
            obs["action"] = "write_substrate"
            obs["path"] = path
            obs["authored_by"] = authored_by
            result = await _write_substrate_with_author(
                proxy.config.user_id,
                path,
                content,
                authored_by=authored_by,
                message=message,
            )
            obs["revision_id"] = result.get("revision_id")
            return obs

        if "flip_frontmatter_field" in turn:
            # Convenience: read file, replace single YAML frontmatter line via
            # regex, write back with revision message. The canary-script pattern
            # extracted from canary_phase4_v3/v4/v5 (status: draft →
            # ready_for_review). Generic over field name + value.
            sub = turn["flip_frontmatter_field"]
            path = sub["path"]
            field = sub["field"]
            new_value = sub["value"]
            message = sub.get("message") or (
                f"Scenario {self.scenario.slug} flip {field} → {new_value}"
            )
            authored_by = sub.get("authored_by") or proxy.config.caller_identity
            obs["action"] = "flip_frontmatter_field"
            obs["path"] = path
            obs["field"] = field
            obs["new_value"] = new_value
            try:
                current = await proxy.read_file(path)
                if current is None:
                    obs["error"] = f"file not found: {path}"
                    return obs
                updated = _replace_yaml_frontmatter_field(current, field, new_value)
                result = await _write_substrate_with_author(
                    proxy.config.user_id,
                    path,
                    updated,
                    authored_by=authored_by,
                    message=message,
                )
                obs["revision_id"] = result.get("revision_id")
            except Exception as exc:
                obs["error"] = f"{type(exc).__name__}: {exc}"
            return obs

        if "fire" in turn:
            # Fire a recurrence as the MEASURED turn (not setup). This is the
            # autonomous recurrence-fire path: manual_fire enqueues to wake_queue;
            # the deployed scheduler drains it and runs the Reviewer with the
            # recurrence-fire envelope (identical context shape to a real cron_tick
            # per ADR-318). The completion gate waits for the judgment-mode
            # manual_fire execution_event. Added 2026-06-04 — the first live
            # trader-suite run surfaced that _execute_turn had no `fire` handler
            # (only _execute_setup_step did), so fire-turns fell through to
            # action="unknown" and never woke the Reviewer.
            slug = turn["fire"]
            obs["action"] = "fire"
            obs["slug"] = slug
            try:
                await _manual_fire(proxy.config.user_id, slug)
                obs["result"] = "dispatched"
            except Exception as exc:
                obs["error"] = f"{type(exc).__name__}: {exc}"
            return obs

        # Unknown turn shape — log and continue.
        obs["action"] = "unknown"
        obs["raw"] = turn
        return obs


# ---------------------------------------------------------------------------
# Setup helpers (delegate to existing services, not duplicating logic)
# ---------------------------------------------------------------------------

async def _manual_fire(user_id: str, slug: str) -> None:
    """Fire a recurrence by slug via the manual-fire wake source (ADR-296 v2)."""
    from services.supabase import get_service_client
    from services.recurrence import walk_workspace_recurrences
    from services.wake_sources.manual_fire import fire as wake_manual_fire

    client = get_service_client()
    recurrences = walk_workspace_recurrences(client, user_id)
    target = next((r for r in recurrences if r.slug == slug), None)
    if target is None:
        raise ScenarioError(f"Recurrence slug={slug!r} not found in scenario user's _recurrences.yaml")
    await wake_manual_fire(client, user_id, target, context=None)


async def _emit_proposal_from_template(user_id: str, template_name: str) -> dict:
    """Emit an action_proposals row via handle_propose_action.

    Resolves a template by name from proposal_templates.TEMPLATES, then
    calls the canonical primitive that any agent would call. The
    proposal-arrival trigger fires through review_proposal_dispatch.py,
    waking the Reviewer.
    """
    from types import SimpleNamespace
    from services.supabase import get_service_client
    from services.primitives.propose_action import handle_propose_action
    from .proposal_templates import get_template

    template = get_template(template_name)
    client = get_service_client()
    auth = SimpleNamespace(client=client, user_id=user_id)
    return await handle_propose_action(auth, template)


async def _write_substrate_with_author(
    user_id: str,
    path: str,
    content: str,
    *,
    authored_by: str,
    message: str,
) -> dict:
    """Direct write_revision; the scenario runner needs control over
    authored_by independent of any proxy config."""
    from services.authored_substrate import write_revision
    from services.supabase import get_service_client

    if not path.startswith("/workspace/"):
        path = f"/workspace/{path.lstrip('/')}"

    client = get_service_client()
    loop = asyncio.get_running_loop()
    revision_id = await loop.run_in_executor(
        None,
        lambda: write_revision(
            client,
            user_id=user_id,
            path=path,
            content=content,
            authored_by=authored_by,
            message=message,
        ),
    )
    return {"revision_id": revision_id, "path": path}


async def _delete_substrate_file(user_id: str, path: str) -> bool:
    """Delete a workspace_files row (the one legitimate non-revision write
    per ADR-209 — deletion is a distinct operation; the revision chain in
    workspace_file_versions is preserved). Returns True if a row was removed.

    Used by establish_substrate to honor a `requires: [{path, absent: true}]`
    precondition or a `setup: [{delete_substrate: path}]` reset step. The
    history under the path stays walkable; only the head/denormalized row
    goes, so a subsequent read_file returns None (file absent) as the
    precondition demands.
    """
    from services.supabase import get_service_client

    if not path.startswith("/workspace/"):
        path = f"/workspace/{path.lstrip('/')}"

    client = get_service_client()
    loop = asyncio.get_running_loop()

    def _delete() -> bool:
        resp = (
            client.table("workspace_files")
            .delete()
            .eq("user_id", user_id)
            .eq("path", path)
            .execute()
        )
        return bool(resp.data)

    return await loop.run_in_executor(None, _delete)


# ---------------------------------------------------------------------------
# EVAL-SUITE-DISCIPLINE.md §3 + §8 C2/C3 — pre-flight precondition machinery
#
# A read is only trustworthy if the situation it read was the situation it
# claimed. `requires:` makes the claim checkable (check_preconditions); the
# `absent: true` delete + setup writes make the clean starting state
# establishable (establish_substrate). The c51c44f failure — firing 7 of 10
# evals against violated preconditions — becomes structurally impossible: the
# harness refuses to fire (check_preconditions) against a state it can't
# establish.
# ---------------------------------------------------------------------------


def _dotted_get(data: dict, dotted: str):
    """Resolve a dotted path (`default.delegation`) into a nested dict.

    Returns the value or a sentinel _MISSING when any segment is absent.
    """
    cur = data
    for seg in dotted.split("."):
        if not isinstance(cur, dict) or seg not in cur:
            return _MISSING
        cur = cur[seg]
    return cur


_MISSING = object()


async def check_preconditions(user_id: str, requires: list[dict]) -> dict:
    """Evaluate each `requires:` assertion against live workspace_files.

    Each assertion is one of:
      - {path, field, equals}        — dotted YAML field equals a value
      - {path, contains}             — file content contains substring
      - {path, not_contains}         — file content does NOT contain substring
      - {path, absent: true}         — file must not exist
      - {path}                       — file must exist (present)

    Returns {satisfied: bool, checks: [{assertion, ok, detail}]}. The runner
    refuses to fire an eval whose preconditions are not satisfied (§3, S2).
    No tokens are spent on a measurement that cannot honor its own contract.
    """
    from services.supabase import get_service_client

    client = get_service_client()
    loop = asyncio.get_running_loop()

    def _read_content(path: str) -> str | None:
        norm = path if path.startswith("/workspace/") else f"/workspace/{path.lstrip('/')}"
        resp = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", norm)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0]["content"] if rows else None

    checks: list[dict] = []
    for assertion in requires or []:
        path = assertion.get("path")
        if not path:
            checks.append({"assertion": assertion, "ok": False, "detail": "missing 'path'"})
            continue
        content = await loop.run_in_executor(None, _read_content, path)

        if assertion.get("absent") is True:
            ok = content is None
            detail = "absent" if ok else "file present (expected absent)"
        elif "field" in assertion and "equals" in assertion:
            if content is None:
                ok, detail = False, "file absent (expected field match)"
            else:
                # _autonomy.yaml / _pace.yaml carry a `--- tier: ... ---`
                # frontmatter header (the grandfathered machine-config-with-
                # frontmatter exception, CLAUDE.md §9). The canonical
                # frontmatter-aware, never-raises loader is load_workspace_yaml
                # in review_policy — reuse it (CLAUDE.md §9: no hand-rolled
                # frontmatter parsers). The real config lives in the BODY after
                # the frontmatter, not in the frontmatter.
                from services.review_policy import load_workspace_yaml
                parsed = load_workspace_yaml(content)
                val = _dotted_get(parsed if isinstance(parsed, dict) else {}, assertion["field"])
                ok = (val is not _MISSING) and (val == assertion["equals"])
                detail = f"{assertion['field']}={val!r} (expected {assertion['equals']!r})"
        elif "contains" in assertion:
            ok = content is not None and assertion["contains"] in content
            detail = "contains" if ok else f"missing substring {assertion['contains']!r}"
        elif "not_contains" in assertion:
            ok = content is not None and assertion["not_contains"] not in content
            detail = "absent-substring" if ok else f"unexpected substring {assertion['not_contains']!r}"
        else:
            # bare {path} → file must be present
            ok = content is not None
            detail = "present" if ok else "file absent (expected present)"

        checks.append({"assertion": assertion, "ok": ok, "detail": detail})

    return {"satisfied": all(c["ok"] for c in checks), "checks": checks}


async def establish_substrate(
    user_id: str,
    *,
    requires: list[dict],
    setup: list[dict],
    authored_by: str,
) -> dict:
    """Establish the eval's clean starting state before firing (§3, §3.1, C3).

    Two responsibilities:
      1. Honor `requires: [{path, absent: true}]` by DELETING those files
         (revision chain preserved per ADR-209) — so the precondition the
         eval claims can actually hold.
      2. Apply `setup:` steps that write substrate (`write_substrate` /
         `delete_substrate`). The richer turn-shaped setup (`seed_draft`,
         `flip_frontmatter_field`, `fire`) stays in ScenarioRunner — this
         helper covers only the substrate establishment a pre-flight reset
         needs. ScenarioRunner.run still executes the scenario's own setup.

    All writes carry the operator-proxy eval-suite-runner attribution. Returns
    {deleted: [...], wrote: [...]} for the SESSION.md precondition record.
    """
    deleted: list[str] = []
    wrote: list[dict] = []

    # 1. Delete files that must be absent.
    for assertion in requires or []:
        if assertion.get("absent") is True and assertion.get("path"):
            removed = await _delete_substrate_file(user_id, assertion["path"])
            if removed:
                deleted.append(assertion["path"])

    # 1b. Establish field/equals preconditions on dial files (§3.1 reset-to-clean).
    #     When a `requires` asserts a field value (e.g. _autonomy.yaml
    #     default.delegation == autonomous), establishing that exact state IS the
    #     clean starting state — the assertion and the establishment are the SAME
    #     declaration, so there is no out-of-band drift (the c51c44f anti-pattern).
    #     We read the current file, set the dotted body field, preserve everything
    #     else (frontmatter + other fields), and rewrite as an operator-proxy
    #     revision. The subsequent check_preconditions then reads what we wrote.
    for assertion in requires or []:
        if "field" in assertion and "equals" in assertion and assertion.get("path"):
            established = await _establish_field_equals(
                user_id,
                path=assertion["path"],
                field=assertion["field"],
                value=assertion["equals"],
                authored_by=authored_by,
            )
            if established:
                wrote.append(established)

    # 2. Apply substrate-establishment setup steps. Only the substrate-shaped
    #    steps are handled here; turn-shaped setup runs inside ScenarioRunner.
    for step in setup or []:
        if "write_substrate" in step:
            ws = step["write_substrate"]
            res = await _write_substrate_with_author(
                user_id,
                ws["path"],
                ws.get("content", ""),
                authored_by=ws.get("authored_by", authored_by),
                message=ws.get("message", "eval-suite pre-flight establish"),
            )
            wrote.append({"path": res["path"], "revision_id": res.get("revision_id")})
        elif "delete_substrate" in step:
            path = step["delete_substrate"]
            if await _delete_substrate_file(user_id, path):
                deleted.append(path)

    return {"deleted": deleted, "wrote": wrote}


async def _establish_field_equals(
    user_id: str,
    *,
    path: str,
    field: str,
    value,
    authored_by: str,
) -> dict | None:
    """Set a dotted body field on a frontmatter-bearing dial file to `value`,
    preserving the frontmatter block + all other fields, and write it as an
    operator-proxy revision. Returns the write record, or None if the field
    is already at `value` (idempotent — no wasted revision).

    Used by establish_substrate to honor a `requires: [{field, equals}]`
    precondition (§3.1). The frontmatter (`--- tier: ... ---`) is preserved
    verbatim; only the YAML body is re-serialized with the field set. Comments
    in the body are decorative on a machine-parsed dial file and are dropped on
    rewrite — the same shape a real operator dial-edit produces.
    """
    import re
    import yaml as _y

    from services.review_policy import load_workspace_yaml
    from services.supabase import get_service_client

    norm = path if path.startswith("/workspace/") else f"/workspace/{path.lstrip('/')}"
    client = get_service_client()
    loop = asyncio.get_running_loop()

    def _read() -> str | None:
        resp = (client.table("workspace_files").select("content")
                .eq("user_id", user_id).eq("path", norm).limit(1).execute())
        rows = resp.data or []
        return rows[0]["content"] if rows else None

    content = await loop.run_in_executor(None, _read)
    if content is None:
        # File absent — can't establish a field on a nonexistent dial file here.
        # (A `setup: write_substrate` step is the right tool to create one.)
        return None

    body = load_workspace_yaml(content)
    if not isinstance(body, dict):
        body = {}

    # Already at the target value → idempotent no-op (no wasted revision, ADR-209).
    cur = body
    segs = field.split(".")
    for s in segs[:-1]:
        cur = cur.get(s, {}) if isinstance(cur, dict) else {}
    if isinstance(cur, dict) and cur.get(segs[-1]) == value:
        return None

    # Set the dotted field, creating intermediate dicts as needed.
    cur = body
    for s in segs[:-1]:
        nxt = cur.get(s)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[s] = nxt
        cur = nxt
    cur[segs[-1]] = value

    # Preserve the frontmatter block verbatim; re-serialize only the body.
    fm_match = re.match(r"^(---\s*\n.*?\n---\s*\n)", content, re.DOTALL)
    frontmatter = fm_match.group(1) if fm_match else ""
    new_body = _y.safe_dump(body, default_flow_style=False, sort_keys=False)
    new_content = frontmatter + new_body

    res = await _write_substrate_with_author(
        user_id, norm, new_content,
        authored_by=authored_by,
        message=f"eval-suite pre-flight: establish {field}={value} (§3.1 reset-to-clean)",
    )
    return {"path": res["path"], "revision_id": res.get("revision_id"), "field": field, "value": value}


async def _seed_draft_from_template(
    user_id: str,
    *,
    slug: str,
    template_name: str,
    title: str | None,
    authored_by: str,
    scenario_slug: str,
) -> dict:
    """Compose profile.md + content.md from a named draft template and write
    both as setup-attributed substrate revisions.

    Returns dict with `profile_revision_id` and `content_revision_id` for
    the scenario evaluation log.
    """
    from .draft_templates import get_template

    template = get_template(template_name)
    resolved_title = title or f"Scenario {scenario_slug} — {template_name}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    profile_md = template["profile"].format(
        slug=slug,
        title=resolved_title,
        created_at_iso=now_iso,
        description=template.get("description", ""),
    )

    profile_path = f"/workspace/operation/authored/{slug}/profile.md"
    content_path = f"/workspace/operation/authored/{slug}/content.md"

    profile_result = await _write_substrate_with_author(
        user_id,
        profile_path,
        profile_md,
        authored_by=authored_by,
        message=(
            f"Scenario {scenario_slug} seed_draft: profile.md for piece "
            f"{slug!r} from template {template_name!r}"
        ),
    )
    content_result = await _write_substrate_with_author(
        user_id,
        content_path,
        template["content"],
        authored_by=authored_by,
        message=(
            f"Scenario {scenario_slug} seed_draft: content.md for piece "
            f"{slug!r} from template {template_name!r}"
        ),
    )
    return {
        "profile_revision_id": profile_result.get("revision_id"),
        "content_revision_id": content_result.get("revision_id"),
    }


def _replace_yaml_frontmatter_field(content: str, field_name: str, new_value: str) -> str:
    """Replace a single YAML frontmatter field's value on its own line.

    Operates on the standard `{field}: {value}` line shape that
    profile.md frontmatter uses. Raises ValueError if the field is not
    found — caller's intent is unambiguous, missing-field means broken
    scenario rather than no-op tolerance.
    """
    pattern = re.compile(rf"^{re.escape(field_name)}:\s*\S+", re.MULTILINE)
    if not pattern.search(content):
        raise ValueError(
            f"Field {field_name!r} not found in YAML frontmatter "
            "(expected a `{field}: {value}` line at start of line)"
        )
    return pattern.sub(f"{field_name}: {new_value}", content, count=1)
