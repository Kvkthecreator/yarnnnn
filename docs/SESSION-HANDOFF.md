# Session Handoff — 2026-04-17 (end of day)

> **For the next Claude session.** Read this first before continuing architectural work.
> Delete / archive this file once you've absorbed it and moved past the handoff window.

---

## Working agreement (unusual, verify with user)

- **Direct push to main, no PRs.** Pre-launch. User explicitly approved this workflow mid-session. Use `git push origin HEAD:main` from the current worktree.
- **Conglomerate alpha, not single-persona SaaS.** User is personally running ≥4 test accounts across structurally different business domains (e-commerce + day trader active; AI influencer + international trader scheduled). See ADR-191.
- **Agnostic core is non-negotiable.** Every new ADR must include an Impact table against `docs/architecture/DOMAIN-STRESS-MATRIX.md`. "Helps one, hurts others" = reject. "Helps one, neutral elsewhere" = verticalization warning that requires explicit justification.
- **Glossary discipline.** User is very particular about this. Never say "TP" / "Thinking Partner" in user-facing copy — always "YARNNN". See `docs/architecture/GLOSSARY.md`.

---

## Where we actually are

**Today (2026-04-17) shipped five ADRs to main as ~27 commits:**

| ADR | Status | What |
|-----|--------|------|
| ADR-189 | Implemented | Three-layer cognition (YARNNN / Specialists / Agents); authored-team model; GLOSSARY.md ratified |
| ADR-190 | Implemented | Inference-driven scaffold depth — rich-input first-act creates full workspace via `UpdateContext(target="workspace")` |
| ADR-191 | Implemented | Polymath operator ICP + conglomerate alpha + DOMAIN-STRESS-MATRIX.md as anti-verticalization gate |
| ADR-192 | Implemented | 14 new platform tools (7 trading + 5 commerce + 2 email) + risk-gate primitive + `_risk.md` schema + Resend provider + prompts |
| ADR-193 | Implemented | ProposeAction + approval loop (action_proposals table, ProposalCard UI, risk-gate auto-proposal, TTL sweep) |

The alpha operator infrastructure is substantially built. An e-commerce or day-trader friend can be onboarded TODAY with real write capability, risk-gated trading, and approval loops.

**Read these canonical docs to absorb the full picture:**

1. `docs/adr/ADR-191-polymath-operator-icp-domain-stress-discipline.md` — strategic thesis (ICP + alpha strategy)
2. `docs/architecture/DOMAIN-STRESS-MATRIX.md` — the conscience doc; gate for every future ADR
3. `docs/architecture/GLOSSARY.md` — vocabulary
4. `docs/adr/ADR-192-write-primitive-coverage-expansion.md` — write surface + risk gate
5. `docs/adr/ADR-193-propose-action-approval-loop.md` — approval loop architecture

Recent commits visible via `git log --oneline -30` will show the phase-by-phase path.

---

## What's next (in priority order)

### Option A — Continue the five-ADR sequence from ADR-191

Two ADRs remain:

**ADR-194 — Surface archetypes (document / dashboard / operational pane).**
The product's rendering layer currently assumes every output is a composed document (ADR-130 HTML-native, ADR-170 compose substrate). For day-trader and e-commerce alphas to be usable, we need:
- **Dashboard archetype**: live view over context domain entities (positions + P&L + watchlist for trader; customers + revenue + product performance for e-commerce). Backed by existing context_files, new rendering layer.
- **Operational pane archetype**: action-ready cards — pending proposals from ADR-193, actionable signals, alerts. This is where `/proposals` gets its dedicated surface (vs today's inline-chat-only).
- **Document archetype**: current strength, unchanged.

This ADR was scoped in ADR-191's follow-on sequence and in ADR-193 Phase 5 closing notes.

**ADR-195 — TP autonomous decision loop.**
Signal → ProposeAction generation. Uses ADR-192 risk gate. Uses ADR-193 approval surface. This is where autonomous behavior becomes self-initiating — YARNNN notices "abandoned carts ≥48h" or "competitor dropped price" or "stop-loss hit" and emits a proposal without being asked. Requires ADR-194's operational pane as the destination surface.

### Option B — Alpha account spin-up first, then design with observed friction

User mentioned this path during ADR-193 closing. Rationale: ADRs 192-193 shipped a lot of write + approval surface without observed usage. Spinning up one or two real alpha accounts (friend's LS store, friend's Alpaca paper account) would generate real pain signals. Those signals sharpen ADR-194's surface design and catch integration bugs Render's auto-deploy import-checks miss.

User's stated preference (from previous turn): happy to push through without testing unless context requires it. But they asked for validation option at every transition. If fresh session can ask user: "proceed to ADR-194 or spin up alpha first?" that's probably the right opener.

### Option C — User may pivot

This is a long session. The user may have accumulated thoughts overnight. Before diving into 194/195, **ask what they're thinking**.

---

## Architectural shape to hold in your head

```
Three-layer cognition (ADR-189):
  YARNNN — the super-agent. User addresses YARNNN directly. Internally
           `YarnnnAgent` class; role='thinking_partner' persists in DB.
  Specialists — 6 role-typed capabilities (Researcher, Analyst, Writer,
           Tracker, Designer, Reporting). YARNNN's palette. Not user-addressed.
  Agents — user-created, domain-scoped workers. On /agents. Authored by
           conversation with YARNNN. Zero at signup (origin filter
           hides infrastructure).

Write + safety stack (ADR-192 + ADR-193):
  Platform tool (e.g. submit_bracket_order)
    → check_risk_limits (if trading; reads /workspace/context/trading/_risk.md)
      → if rejected + mode=autonomous: emit ProposeAction
      → if rejected + mode=supervised: hard error
    → if approved: Alpaca / LS / Resend API call
  ProposeAction → action_proposals row (pending, TTL by reversibility)
    → ProposalCard renders inline in chat
    → ExecuteProposal (via /api/proposals/{id}/approve) runs through
      execute_primitive; re-gates for safety
  back-office-proposal-cleanup runs daily, expires stale pending rows.

Agnostic core (ADR-188 + ADR-191):
  Fixed framework: output_kind (4), roles (6+TP+bots), modes (3), pipeline
  Contextual per workspace: domains, task defs, agent identities, step instructions
  Alpha domains: e-commerce + day trader active; AI influencer + intl trader scheduled.
```

---

## Gotchas / watch-outs

1. **Render has 4 services** (API, Unified Scheduler, MCP Server, Output Gateway). All shipped code today is on API + Scheduler paths. MCP + Output Gateway untouched. But env var parity matters — any new env var needs all four checked. None added today.
2. **No frontend tsconfig check was run in the worktree** — we don't have node_modules here. TypeScript changes in Phase 2/4 of various ADRs ship to Render unverified locally. Watch Render's web build logs on next deploy.
3. **Phases 3-5 of ADR-193 reference auth context** — when the task pipeline calls `handle_propose_action` from an autonomous scheduled context, the `auth` object must have `user_id` and `client`. Worth verifying the task pipeline's auth shape matches if autonomous proposal emission is tested.
4. **Supervised-mode risk-gate rejection re-execution subtlety** — if the user approves an autonomous proposal via ExecuteProposal, the platform handler re-runs in supervised mode. Rules that hard-block (e.g., `max_order_size_shares`) will re-reject. User must adjust `_risk.md` first. This is correct; document it if it surfaces confusion.
5. **Two existing test workspaces** won't get `back-office-proposal-cleanup` until they reinitialize. New signups get all 3 back-office tasks. Not urgent (zero proposals to clean).
6. **Stale TP string audit passed on 2026-04-17 but watch for regressions** — future ADRs / docs / prompts might slip "TP" back in. Glossary rule is strict.

---

## Session discipline the user values (based on observed preferences)

- Strategic discourse BEFORE code implementation. User explicitly pushed back on jumping to flows before ICP was locked.
- ADRs drafted as docs FIRST, then phased implementation commits. Each phase commits green.
- Prompt CHANGELOG entries per phase (even doc-only phases).
- Impact table per ADR per matrix gate.
- Singular implementation — delete legacy when replacing, no dual approaches.
- Direct to main, no PRs.

The execution-disciplines hook ( `.claude/hooks/execution-reminders.txt` ) auto-injects 11 rules on every user message. Respect them.

---

## When you wrap (not today, but the handoff session after)

Delete or archive this file. The fresh session's orientation hooks (session-reorient.sh) + CLAUDE.md will carry forward from the commit log. This doc exists for ONE handoff cycle — to bridge today's in-context state into a fresh session's absence of that context.

If the fresh session absorbs this and the work moves on, this file becomes noise. Delete it in the commit that starts ADR-194 (or whichever direction the user chooses).
