# Onboarding Legacy-Framing Audit — derivation record for ADR-437

**Date**: 2026-07-10
**Status**: **Derivation stub.** This audit produced [ADR-437 — The Activation Model](../adr/ADR-437-the-activation-model-discovery-cold-landing-and-the-shared-artifact-wedge.md). Its full findings + receipts were absorbed into that ADR's decisions and are maintained there (Singular Implementation — the ADR is the one source of truth). This file is retained only as the ADR-407-style `Derivation:` breadcrumb: what the investigation found, and where it went.

---

## The thesis (confirmed)

> The onboarding was built on a legacy mental model that three ratified ADR bands
> superseded. `/setup` framed activation as "pick a program that forks a
> domain-shaped workspace" and asked the operator to "author a workspace-level
> constitution," and the whole flow was single-player.

**Verdict: CONFIRMED, with a sharpening nuance** — the *backend* had already migrated
(pure-empty genesis; activation resolves through a hire grant row). The drift was
concentrated at the **surface/framing layer**: `/setup` was a surface *lying about its
own data source*. That made the fix a subtraction + re-derivation, not a machinery
rebuild.

## The receipts (now maintained in ADR-437 §2, §5)

- `SetupSequence.tsx:148-152` — "a program forks a domain-shaped workspace" (pre-ADR-414
  D5; a program is an anytime hire into `agents/{slug}/`, never a workspace type).
- `SetupSequence.tsx:176-182` — "author your [workspace] constitution" (ADR-421: a
  workspace has no constitution of its own).
- Single-player throughout; genesis hardcodes `'My Workspace'`.
- The dead `WorkspaceSection.tsx` twin (consumed `first_run`, mounted nowhere).
- The fragile `/invite` accept page + the reactive-only, fail-open seat gate.
- **Verified NOT drift** (do not "fix"): no `workspace_type`/`kind` column or enum
  exists — personal-vs-team is derived at request time from `owner_id` +
  `principal_grants.role`; genesis is already pure; BYOK is ratified (ADR-409/439).

## Where it went

The two-channel activation model (cold discovery → the default landing with a
deliberate empty state; invited/shared → one accept surface, the shared-artifact wedge,
broad-by-default grants) became **ADR-437**, implemented in full (Phases A–E, all on
main). Read the ADR for the decisions, the guardrails (no substrate fork, no
org-above-workspace layer), and the implementation record.
