# ADR-202: External Channel Discipline — Expository Pointers, No Replacement UX

> **Status**: Phase 1 (frontend forward-compat) Implemented 2026-04-20. **Phase 2 (backend — daily-update template + alert discipline + pending-distribution marker) Implemented 2026-04-20.** Phase 3 (frontend Ship-Now UX) Proposed. Phase 4 (legacy cleanup) Proposed.
> **Date**: 2026-04-20
> **Authors**: KVK, Claude
> **Extends**: ADR-198 v2 (cockpit service model, Refinements 1-3 on external Channels); FOUNDATIONS v6.0 Axiom 6 (Channel) + Derived Principle 12 (Channel legibility gates autonomy); ADR-161 (daily-update heartbeat), ADR-185 (Distribution Derivatives)
> **Depends on**: ADR-199 (Overview shipped — deep-link targets exist), ADR-200 (Review shipped), ADR-201 (Team route exists)
> **Implements**: Fourth and final cockpit surface phase per ADR-198 v2 §Implementation

---

## Context

ADR-198 v2 established the cockpit service model: operator works *inside* YARNNN; external distribution is derivative. That commitment ripples through three specific external-Channel behaviors that currently leak cockpit-replacement UX into external surfaces:

1. **Daily-update email** (ADR-161) — currently composes a briefing email with embedded content (summary numbers, task counts, etc.). Under ADR-198 Refinement 3, this should shift to **expository pointer** form: legible headline summary + deep-links into cockpit surfaces. Today the email is the UX; tomorrow the email is the notification that the cockpit has something to show.

2. **Alert notifications (push / SMS / email for time-sensitive events)** — ADR-192 risk-gate rejections + autonomous proposal emissions need operator attention. Currently routed via email (where present). Under ADR-198 Refinement 2, these must be **pointer-only**: the notification says "trade proposal expires in 45m — review in cockpit" with a deep-link; approval happens *in cockpit Queue*, never via SMS reply or email button.

3. **`produces_deliverable` task external distribution** — tasks with a `## Delivery` section naming external recipients (email, Slack, Notion) currently treat the rendered artifact as the primary output. Under ADR-198 §6, the **cockpit surface** is primary; the external distribution is a post-compose derivative per ADR-185. The operator reviews in cockpit first (auto on Overview for standard tasks; on Work detail for fresh outputs); the external ship happens after operator approval (or by schedule if task is configured for auto-deliver).

### Cockpit dependencies are now satisfied

ADR-202 was blocked on Overview (the primary deep-link target for daily-update + alerts) and Review (the target for "see decisions" pointers). Both shipped in ADR-199 + ADR-200. Team shipped in ADR-201. Every deep-link this ADR specifies now resolves to a real surface.

---

## Decision

### 1. Daily-update email becomes an expository pointer

**Current shape (pre-ADR-202):** daily-update email contains composed content — summary prose, numbers, task-level updates.

**Post-ADR-202 shape:** daily-update email contains:

- **One-line headline** — what's happened since yesterday at a glance ("3 task runs · 2 proposals pending · 1 reviewer decision")
- **Pointer cluster** — deep-links into cockpit surfaces, one per salient substrate:
  - "See today's overview →" → `/overview`
  - "Review 2 pending proposals →" → `/overview#queue` (or `/overview?focus=queue` — backend's call)
  - "See 1 new reviewer decision →" → `/review?identity=ai` (if AI-filed) or `/review?since=<iso>`
  - "Open your book →" → `/context?path=/workspace/context/_performance_summary.md`
- **Empty-state handling** — ADR-161 heartbeat discipline preserved. If genuinely nothing to point at, email says so honestly with a single CTA back to `/overview`.

Rationale: operator gets the heartbeat (system is alive, email arrived), sees what matters at-a-glance (headline + counts), opens cockpit for actual operation (deep-link one click away). Email stops being the UX; it becomes the invitation to the UX.

### 2. Alert notifications — pointer-only pattern

**Applies to:**
- Time-sensitive proposals (irreversible actions: trade orders, bulk price changes, campaign sends — ADR-192 + ADR-193)
- AI Reviewer deferred decisions requiring human judgment (ADR-194 Phase 3)
- Platform-connection failures with operator-action required (token refresh, rate-limit exhaustion)

**Notification content:**
- **Subject line:** event summary ("Trade proposal · AAPL bracket · expires 45m")
- **Body:** one-line context + single deep-link CTA. No approve/reject buttons in the email/SMS itself.
- **Link target:** the cockpit surface where the affordance lives. Queue for proposals, Review for deferred decisions, Settings/Integrations for platform issues.

**Explicitly forbidden (singular-implementation discipline):**
- "Approve via email" links that take destructive actions via GET
- Reply-to-approve email parsing
- SMS reply handling that mutates substrate
- Any UX that duplicates a cockpit affordance on an external Channel

If a future ADR proposes SMS-approval for convenience, it must show (a) why cockpit can't be reached fast enough (mobile responsive web or PWA should cover this), and (b) how the audit trail stays coherent without the cockpit's identity-aware writes.

### 3. `produces_deliverable` external distribution as derivative

**Changes to the compose pipeline contract** (backend):
- When a task with `## Delivery: external` runs, the pipeline renders the output to `/tasks/{slug}/outputs/{date}/` (substrate — unchanged per Axiom 1)
- **Before** shipping to external recipients, the pipeline writes a "pending distribution" marker to the output manifest
- **Distribution fires** per the task's schedule OR on operator approval via cockpit Work detail (new UX affordance)
- For standard recurring tasks (weekly reports, daily digests) with trusted distribution, auto-fire remains the default — the cockpit surface is the *audit* Channel, not a manual-approval gate
- For high-stakes tasks (one-off reports to external stakeholders, campaign sends, etc.) marked `delivery_requires_approval: true`, distribution waits on operator cockpit approval

**Cockpit-side UX (frontend):**
- Work task-detail shows a "Pending distribution" badge when an output is rendered but not yet shipped
- Distribution history tab/section shows past deliveries with timestamps + recipients
- Manual "Ship now" button for pending-distribution outputs

### 4. External-Channel content discipline (the "expository" in expository pointer)

For every external notification / email / SMS / Slack post emitted by YARNNN:

| Content element | Included? | Rationale |
|---|---|---|
| Event / change headline | Yes, always | Operator knows what the notification is about at a glance |
| Current state summary (1-2 lines) | Yes — concrete numbers or fact | Legible enough to decide whether to open cockpit |
| Full rich content | No | That's what the cockpit surface is for |
| Reasoning / narrative | No | Same |
| Action buttons | No (deep-link only) | Preserves cockpit as the approval Channel |
| Deep-link CTA | Yes, always | The point of the notification |
| Empty-state honesty | Yes | ADR-161 discipline — never silent, even when nothing happened |

---

## Implementation plan — split scope

### Backend-owned scope (ADR-202 Phase 1)

**Owner: backend session.** Changes to server-side template rendering + notification pipelines.

- `api/services/delivery.py` (or equivalent) — daily-update template rewritten per §1 (headline + pointer cluster + empty-state)
- Alert notification infrastructure — audit existing alert paths (proposal creation, reviewer deferrals, platform failures) and update content to pointer-only per §2
- Compose pipeline — `produces_deliverable` output-manifest gains pending-distribution marker; distribution timing respects `delivery_requires_approval` flag (task type extension) per §3
- Deep-link URL builder — new utility that produces `https://app.yarnnn.com/overview?...` URLs with valid deep-link params. Single source of truth for deep-link shape.

### Frontend-owned scope (ADR-202 Phase 2)

**Owner: frontend (this session).** Minimal; cockpit surfaces already exist.

- **Overview surface** — ensure deep-link params `?since=<iso>`, `?focus=queue`, `?focus=alerts` work (params for deep-link targeting from external notifications). Likely no change; URL-driven filtering already supported by the surface structure.
- **Review surface** — same: ensure `?identity=ai|human|impersonated` and `?since=<iso>` filters work (already wired in DecisionsStreamPane).
- **Work task-detail** — NEW: pending-distribution badge + "Ship now" affordance for outputs awaiting operator approval. Scoped to implementation when backend's output-manifest marker lands.

### Frontend placeholders shipping now (this commit)

This commit includes the **doc** (this ADR) + minimal frontend-side preparation:
- Overview page: accept + ignore `?focus=<queue|alerts>` query param (forward-compat with backend deep-links — no UX change yet; scoped to follow-up when the backend deep-links start firing)
- Review page: no change — filters already accept `?identity=`, `?decision=`, `?since=` query params per ADR-200 spec

**Not in this commit:** the pending-distribution badge on Work task-detail. That waits on backend's output-manifest contract extension.

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Notes |
|--------|--------|-------|
| **E-commerce** | **Helps** | Daily email becomes a briefing pointer; operator opens cockpit for the actual view. Campaign-send proposals get expository pointer SMS with deep-link to Queue — no "Send via email" button that could misfire. Weekly-report-to-CFO distribution gates on operator approval for higher-stakes ships. |
| **Day trader** | **Helps** | Critical domain. Trade-proposal SMS says "AAPL bracket · expires 45m — review" with cockpit link. Operator approves in cockpit Queue, never via SMS. Audit trail stays coherent. |
| **AI influencer** (scheduled) | Forward-helps | Campaign-send approvals gated same pattern. Daily content-performance briefing becomes a pointer. |
| **International trader** (scheduled) | Forward-helps | Compliance alerts pointer-only — decision happens in cockpit where the decisions.md audit is live. |

No domain hurt. Gate passes. This phase hardens the cockpit commitment against external-Channel drift.

---

## Implementation sequence

Phased backend-first, then frontend catches up:

| Phase | Owner | Scope | Status |
|---|---|---|---|
| 1 | Frontend | ADR spec + deep-link query-param forward-compat on cockpit surfaces | **Implemented 2026-04-20** |
| 2 | Backend | Daily-update template rewrite + alert content discipline + output-manifest pending-distribution marker | **Implemented 2026-04-20** |
| 3 | Frontend | Work task-detail pending-distribution UX (badge + Ship now affordance) after backend contract lands | Proposed |
| 4 | Backend | Delete legacy alert-body-with-buttons code paths — singular implementation | Proposed (no legacy found in audit; this phase may be a no-op) |

---

## What this does NOT change

- **Substrate** — Axiom 1 unchanged. Task outputs still land in `/tasks/{slug}/outputs/`. Emails don't replace the substrate.
- **Queue surface behavior** — approvals still flow through `/api/proposals/{id}/approve` regardless of how the operator got to the cockpit (direct navigation, deep-link from email, rail).
- **ADR-185 Distribution Derivatives** — unchanged. This ADR tightens the "what is primary" answer; ADR-185's framing of derivatives is already correct.
- **ADR-161 heartbeat discipline** — preserved. Daily-update still fires every day; it still carries content (now pointer + summary content); empty workspaces still get a deterministic honest message.

---

## Open questions

1. **Deep-link URL shape** — `/overview?focus=queue` vs `/overview#queue` vs `/overview/queue`? Query param is simplest (no route change needed) but anchor-link feels more native for "scroll to this pane." Backend's call during template rewrite. Frontend accepts any.
2. **Push notification support** — mobile push requires native app or PWA. Scope-wise outside this ADR; but SMS fallback for critical alerts (trading) is reasonable near-term.
3. **`delivery_requires_approval` flag** — new task-type property. Scoping and defaults TBD during backend Phase 2 (e.g., per-task-type default? operator-configurable at task creation?).
4. **Frontend signal for distribution pending** — polled from task-detail endpoint, or push via session messages? Simpler to poll for now; revisit if operator signal shows latency concerns.

---

## What this completes

When Phases 1–4 all land, the cockpit is structurally consistent end-to-end:
- **Substrate** (files) → the source of truth
- **Cockpit surfaces** (Overview / Team / Work / Context / Review) → the operator's primary Channel
- **External notifications** (email / SMS / push) → expository pointers back to cockpit
- **External distribution** (PDF / email-to-CFO / Slack posts) → post-cockpit-approval derivatives

No Channel duplicates another. No external UX replaces cockpit UX. No drift possible without violating a named ADR.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-20 | v1 — Initial proposal. Backend-frontend split implementation. Phase 1 (this commit): ADR spec + forward-compat for deep-link query params. Phases 2-4 follow in backend + frontend cycles as contracts land. |
| 2026-04-20 | v1.1 — **Phase 2 shipped.** Backend implementation: `api/services/deep_links.py` (NEW) as single source of truth for cockpit URLs via APP_URL env. `api/services/daily_update_email.py` (NEW) emits expository-pointer shape for populated daily-update: deterministic headline ("3 task runs · 2 proposals pending · 1 reviewer decision") + contextual pointer cluster (queue / review / book) + empty-state. `_deliver_email_from_manifest` branches on `task_slug == "daily-update"` to use the pointer template (agent-generated digest still lives at cockpit, not in email). Empty-state template (`_build_empty_workspace_html/markdown`) rewritten to pointer shape with `0 task runs · 0 proposals pending · 0 reviewer decisions` headline + `chat_url()` CTA + `overview_url()` footer link. `notifications.py::_send_notification_email` URL routing migrated to `deep_links` helpers — `agent_id` now routes to `team_url(agent=...)` per ADR-201 (was `/agents/{id}`); new `proposal_id` context routes to `review_url(proposal=...)`. `SysManifest` dataclass extended with `pending_distribution: bool` + `pending_distribution_approved_at: Optional[str]`; backward-compatible (legacy manifests without these fields parse to defaults). `task_types.delivery_requires_approval(type_key)` helper: safe default `False` (no task type declares it yet); opt-in per-task-type by adding `"delivery_requires_approval": True` to the dict. `deliver_from_output_folder` respects the flag: when True + `pending_distribution_approved_at` is None, marks manifest and returns `ExportStatus.SKIPPED` (new enum value — distinct from FAILED because no error, output is composed and waiting). Phase 3 frontend flips `pending_distribution_approved_at` via a Ship-Now affordance. |
