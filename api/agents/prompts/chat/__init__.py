"""Chat prompt profiles (ADR-186, restructured under ADR-233 Phase 1).

Two profiles for the YARNNN orchestration chat surface:
  chat/workspace — onboarding, task catalog, team composition, creation routes
  chat/entity    — feedback routing, evaluation, agent identity management

Plus shared chat-only sections:
  activation.py — ADR-226 activation overlay (workspace profile, conditional)
  onboarding.py — CONTEXT_AWARENESS for workspace profile
  task_scope.py — entity preamble template
  behaviors.py  — legacy BEHAVIORS_SECTION (no longer wired into build_system_prompt)

Imports flow through the parent package's `build_system_prompt(profile=...)`
or unified `build_prompt("chat/<profile>", ...)`.
"""
