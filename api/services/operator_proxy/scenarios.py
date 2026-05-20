"""ADR-294 D6 — Scenario YAML parser + runner.

Scenarios are first-class versioned eval artifacts under
docs/observations/scenarios/. Assertion-light, observation-heavy —
the runner logs what happened and lets capture.py snapshot the
artifact. `expect:` clauses are interpretation hints, not pass/fail gates.

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
    turns:
      - send_message: "..."                 # operator-voice chat
        expect:                              # interpretation hints (logged, never fail-hard)
          - reviewer_responded
          - no_substrate_writes
      - emit_proposal:
          template: signal-2-nvda          # uses existing emit_test_proposal logic
        expect:
          - reviewer_verdict_in: [approve, reject]
      - if_approved:
          expect:
            - alpaca_order_submitted
    capture:
      - revision_chain
      - decisions_md
      - action_proposals
      - token_usage_by_caller
      - all_session_messages
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
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

    Discipline: every observation is logged, never fail-hard on expect:
    mismatches. Scenarios validate behavior shape; humans interpret.
    """

    def __init__(self, scenario: Scenario, *, caller: str = "scenario-runner"):
        self.scenario = scenario
        self.caller = caller
        self.observations: list[dict] = []   # ordered log of {turn, expect, observed}

    async def run(self, observation_folder: Path) -> dict:
        """Execute scenario. Returns summary dict + writes capture artifacts."""
        from .client import OperatorProxy
        from .capture import CaptureSession

        observation_folder.mkdir(parents=True, exist_ok=True)
        proxy = OperatorProxy.from_persona(self.scenario.persona, caller=self.caller)
        # Mint JWT + fetch user_id resolution via the proxy's config.
        user_id = proxy.config.user_id

        capture = await CaptureSession.start(
            user_id,
            observation_folder,
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
                self.observations.append(obs)

        capture.metadata["observations"] = self.observations
        await capture.snapshot()

        return {
            "scenario": self.scenario.slug,
            "persona": self.scenario.persona,
            "turns_executed": len(self.observations),
            "observation_folder": str(observation_folder),
        }

    # ----- step executors -----

    async def _execute_setup_step(self, proxy: Any, step: dict) -> None:
        """Setup steps: fire | write_substrate. Logged but not turn-counted."""
        if "fire" in step:
            slug = step["fire"]
            # Invoke manual_fire path directly via dispatch.
            await _manual_fire(proxy.config.user_id, slug)
            self.observations.append({
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
            self.observations.append({
                "phase": "setup",
                "action": "write_substrate",
                "path": path,
                "authored_by": authored_by,
                "revision_id": result.get("revision_id"),
            })
            return

        # Unknown setup step — log and continue (assertion-light).
        self.observations.append({
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
