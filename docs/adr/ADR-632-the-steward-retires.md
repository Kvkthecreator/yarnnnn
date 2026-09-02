# ADR-632 — The steward retires: the review seat, the wake stack, and its doors are deleted

> **Status**: **Accepted + Implemented** (2026-09-02). Operator ruling in the skills discourse: *"ok that seat is now gone. if so, should be removed in full including the residue."* Executes ADR-596 D3 (ratified direction, phased) in one arc, with the ordering D3 itself prescribed: what the prose frame protected was inventoried before the frame was deleted.
> **Dimensional classification** (Axiom 0): **Trigger** (Axiom 4 — the wake sources and the funnel are gone; Trigger is the member's turn or a standing declaration's schedule) + **Identity** (Axiom 2 — no systemic agent; every agent is an app's resident) + **Mechanism** (the steward's prompt layer, model selector and tool rosters are deleted).
> **Supersedes / closes**: ADR-296 v2 (the wake architecture), ADR-298 (the wake queue), ADR-301/327 D6 (the kernel mirrors), ADR-315 (seat≠occupant), ADR-381/383/414 D2–D3 (Freddie, the system agent), ADR-402/463 D3 (the steward's model table), ADR-403 (the envelope), ADR-375 §6 (the steward-presence gate), ADR-352 (the ask-gate), ADR-454 D3 (the steward chrome), ADR-426 (the Freddie System Agent door), ADR-157 D-referential (already retired by ADR-630). **ADR-596 D3 phases (a)–(e): executed.**
> **Preserves**: ADR-307 (the one consequential gate — `permission.py` stands; `ProposeAction`/`ReturnVerdict` names stay fail-closed), ADR-405 (grants), ADR-624 (agent homes and their locked grant sidecars), ADR-603 (standing declarations — the only unattended trigger), ADR-618 (standing work bounded by the pool), ADR-467 D4 (the uniform lane surface), the `freddie:` attribution prefix on historical revisions (data-compat, display-resolved).

## 1. Context — dormant, still wired

The dependency audit (2026-09-02) measured the seat before the cut:

| Signal | Count |
|---|---|
| Steward-attributed revisions, all time | 31 |
| Steward-attributed revisions since 1 Aug | 1 |
| Wake-queue rows, all time | 15,388 |
| Wake-queue rows enqueued since 1 Aug | 1 |
| Steward modules wired, lines | 9 modules, 5,425 lines |
| Live member actions that still enqueued a wake | 2 (a proposal insert; a `_hooks.yaml` match) |

The stack could still reach a model and spend (the scheduler tick called the drainer; the wake module imported the steward). Its chrome had been dark since ADR-454 D3; its recurrence source inert since ADR-603 D5; the member-facing doors were redirect stubs. Four modules on the naive manifest were **not** stack members — `narrative.py`, `capabilities.py`, `substrate_reapply.py`, and two symbols of `model_selection.py` — and the live strings and capture lanes sat **nested inside** the `if is_agent_enabled():` steward block, so a flag meant for the steward could switch off the one lane with production tenants.

## 2. Decisions

### D1 — The stack is deleted, not gated

`agents/` (the prompt layer, sections, occupant contract, base, cockpit awareness), `services/wake.py`, `wake_queue.py`, `wake_drainer.py`, `wake_evaluation.py`, `wake_sources/` (all five), `review_rotation.py`, `review_proposal_dispatch.py`, `freddie_envelope.py`, `freddie_chat_surfacing.py`, `substrate_snapshot.py`, `kernel_mirrors.py`, `model_selection.py`, `agent_gating.py`, `recurrence.py`, `recurrence_prompt_inference.py`, `commands.py`, `execution_router.py`, `routes/feed.py`, and the steward-only primitives (`FireInvocation`, `Schedule`, `ManageHook`, the three `Mirror*` + `MirrorSignalState`, `GetSystemState`, `Compose` — the compose **engine** stays, ADR-417 — and `Clarify`). The three LLM tool rosters (`CHAT_PRIMITIVES` / `HEADLESS_PRIMITIVES` / `FREDDIE_PRIMITIVES`) and `get_tools_for_mode` go with them: the live surfaces declare their own sets (`lane_runner.LANE_TOOL_NAMES`, `mcp_server._INTEROP_VERBS`); `PRIMITIVES` survives as the derived list of every declared tool, the dispatch side.

### D2 — The shared symbols move first

`strip_provider` and `accept_model_override` live in `services/system_calls.py` (their only live consumers: that module and `model_router`). `freddie_audit.py` is renamed `judgment_log.py` — the verdict record is unchanged, the verdict-giver is the operator. The scheduling module keeps the schedule math (`compute_next_run_at`, `resolve_semantic_schedule`, `preserve_due_commitment`) that strings and capture use, and loses the recurrence index. The program fork no longer seeds recurrences or materializes the `tasks` index.

### D3 — The tick has no steward gate

The capture lane and the strings lane run unconditionally, each behind only its own flag; the kernel skills mirror (ADR-630) runs beside them. `dispatch_due_invocations`, the hook walker, the queue reclaim + drain, and the kernel mirrors are gone. `AGENT_ENABLED` has no reader; strip it from Render with `YARNNN_MODEL_{SHAPE}` and `YARNNN_ROUNDS_{SHAPE}`.

### D4 — The doors close

`POST /feed`, `/feed/cancel`, `/feed/attach`, `/feed/history`, `/feed/sessions`, `/commands`, the admin `trigger-task` door, the `system-agent` surface row and its redirect stub (with `/autonomy`, `/expected-output`, `/delegation`), the `STEWARD_SURFACE_SLUGS` filter, the `queue_depth` field on the budget envelope, the connector payload's `agent_enabled`, the proposals occupant read (now `{}` — the documented "default human"), the init-time steward session, and the wake call on proposal insert. On the web: the narrative context, the transcript components, the chat drawer and its chrome registration, the FAB and mascot, the persona hook, the steward-chrome flag, the session-messages realtime hook (the file-revisions hook stands on its own), and the drawer state in the shell context. `ProposalCard` moves to the queue it serves and labels a verdict from the row (`human:` → "You"; historical rows keep the steward's name).

### D5 — What the prose frame protected, and where it went

Per ADR-596 D3's ordering, the frame's protections were inventoried before deletion. Four were already code gates and are untouched: the budget ceiling (`budget.py`, `platform_limits.check_balance`), the lock-set (`_is_path_locked`), the autonomy ceiling (`permission.resolve_permission` + `review_policy`), and the attribution grammar (`is_valid_author`). Three lived only in prose — anti-confabulation, source-citation, the unanswered-turn verdict fallback — and every one guarded **the steward's own outputs**. With no steward output there is nothing left for them to guard; the lane frame's citation discipline (ADR-533/617 constants) is unchanged. Recorded here so the next reader does not re-derive a gap.

### D6 — Vocabulary

*Seat*, *occupant*, *steward*, *Reviewer*, *Freddie*, *wake* are historical. The billing **seat** (ADR-445) keeps its word. GLOSSARY carries a **Steward (historical)** entry; the seat canon under `docs/architecture/` is archived to `previous_versions/`; CLAUDE.md's Prompt Change Protocol re-targets to the live frame (`lane_runner._CONVENTIONS_FRAME`, the app postures, `services/skills/`), with the ratchets in this ADR's gate.

## 3. What this deliberately leaves

- **ProposeAction / ReturnVerdict / the queue / the autonomy and budget dials** stay. They are ADR-307's gate and ADR-596 D3 phase (d)'s territory — review as a grant plus policy declaration — and the operator is the verdict-giver until that ADR lands. No producer of proposals exists today; the surface tells the truth about that.
- **The `wake_queue` and `tasks` tables** stay as data until a follow-up migration drops them.
- **The entity primitives** (`LookupEntity`/`EditEntity`/`ListEntities`/`ManageDomains`) and the trading primitives keep their handlers; each deserves its own caller audit.
- **The `freddie:` prefix** on historical revisions is display-resolved, never rewritten.

## 4. Gates

`api/test_adr632_the_seat_retires.py`: no stack module imports; the scheduler has no steward gate and drains strings + capture unconditionally; the feed router is unmounted; no wake source, no rosters; the two live frame ratchets (the conventions scaffold and the studio posture frame, measured at ship); the web has no narrative context, drawer, or mascot; the GLOSSARY marks the steward historical; CLAUDE.md's protocol names live files. Re-anchored ~40 gates; deleted ~55 whose subject was the steward; archived 11 canon docs; deleted 26 operator probes and canaries.
