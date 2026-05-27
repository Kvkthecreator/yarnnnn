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
        """Setup steps: fire | write_substrate. Logged but not turn-counted."""
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

    profile_path = f"/workspace/context/authored/{slug}/profile.md"
    content_path = f"/workspace/context/authored/{slug}/content.md"

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
