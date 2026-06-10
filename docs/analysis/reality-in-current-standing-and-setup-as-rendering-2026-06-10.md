# Reality-In: Current Standing, Attestation, and Setup-as-Rendering

**Date:** 2026-06-10 (third session capture, same day)
**Hat:** B (external-developer surface — discourse capture, receipts-grounded).
**Origin:** continuation of the 2026-06-10 regroup. Sequence: the operator asked
for *current* (not theoretical) standing of the three flows → audit corrected
the prior session's claims → the onboarding/catch-up question → the operator
caught a dual-tracking creep forming ("is this just platform integrations
recurring?") and challenged the settings-tab answer for first-boot UX → both
challenges resolved.
**Succeeds / refines:** `author-blindness-and-invariant-capabilities-2026-06-10.md`
§3 (the invariants re-keyed as flows; Invariant 1+2 collapse into one
consequence-pipe arc; a retraction recorded in §3 below).
**Status:** Hardened. Handoff prompt for the scoped audit/ADR session at
`SESSION-PROMPT-reality-in-and-setup-surface.md`.

---

## 0. Re-verification corrections (added 2026-06-10, scoped audit/ADR session)

The scoped session (`SESSION-PROMPT-reality-in-and-setup-surface.md`)
re-verified every receipt in §1–§4 against live code before drafting the two
ADRs. **All four-flow claims hold** (provider count = 2, alpha-author declares
no ground-truth, single-file 25MB upload, calibration mirror reads
`substrate_abi.ground_truth` and degrades to cadence-only when absent). Three
**non-claim drifts** were found — cosmetic to the argument, material to the
ADR's code-pointers, so corrected here in place:

1. **First-run redirect target moved.** §1/§4 below (and the SESSION-PROMPT)
   describe the redirect as `/settings?tab=workspace&first_run=1` (ADR-244 D5).
   ADR-297 (atomic-surface migration) already moved it: `web/app/auth/callback/page.tsx`
   now redirects first-run operators to **`/program?first_run=1`**, rendering
   `ProgramLifecycleDrawer` over `api.workspace.getState()`. The "anti-welcome
   settings tab" premise is now "the `/program` lifecycle drawer" — still a
   reference/random-access surface, not a guided sequence, so §4's
   sequence-vs-reference argument **stands**; ADR-331 amends ADR-297's redirect,
   not ADR-244 D5.

2. **Domain substrate paths moved `context/` → `operation/`.** ADR-320
   (constitution/operation/governance topological cut) relocated accumulated
   domain context to `operation/{domain}/`; governance to `governance/`;
   constitution to `constitution/`. The reconciler writes
   `/workspace/operation/{domain}/_money_truth.md`. Wherever §1–§4 say
   `context/{domain}/` or `context/_shared/`, read `operation/{domain}/` and
   `constitution/` + `governance/` respectively.

3. **The surface model is ADR-297 atomic surfaces, not page-as-container.**
   §4's "build `/setup` (FE route)" lands as a **kernel atomic surface** in the
   `KERNEL_SURFACES` registry (`api/services/kernel_surfaces.py`), consumed by
   the compositor's `surfaces[]` registry and the summon-index — fully
   consonant with §4's "one substrate, two renderings." ADR-331 frames `/setup`
   this way.

**One stale-prose note (not a code path):** `outcomes/base.py` docstrings still
reference the dropped `action_outcomes` SQL table; ADR-195 v2 moved persistence
to filesystem `_money_truth.md`. The TypedDict and provider contract are
correct; only the prose lags. ADR-330 notes it for a same-commit docstring fix.

---

## 1. The four flows — current standing (audited against live `api/`, 2026-06-10)

The "three invariants" framing dissolves into a flow picture: the operation's
loop has four flows; the build question is which are under-built.

| Flow | What it is | Current standing (receipts) |
|---|---|---|
| **1. Context in** (perception) | World-state entering, feeds production | **Built as capability, thin as practice, absent as catch-up.** See §1a. |
| **2. Work out** (the acts) | Artifacts / transactions / messages leaving | **Built.** Artifact: WriteFile + compose (11 section kinds). Transaction: 11 trading write tools (brackets, trailing stops, partial closes), 8 commerce write tools (refunds, variants, bulk pricing). Message: audience email EXISTS (`platform_email_send` + `_send_bulk` under `write_email`) — distinct from operator-notification infra (ADR-304 `SYSTEM_INFRASTRUCTURE_TOOLS`: email-to-operator, Slack DM, Notion comment). Missing only: social/web publish (commodity last-mile, absorb). |
| **3. Outcomes in** (consequence / ground truth) | Reality's verdict on flow 2, feeds judgment | **Built for two domains only.** `OutcomeProvider` ABC (ADR-195) with exactly 2 registered providers (Alpaca, Lemon Squeezy) in `reconciler.DEFAULT_PROVIDERS`. Calibration mirror (ADR-327) reads MANIFEST `substrate_abi.ground_truth`; **alpha-author declares none** — second active program's loop is structurally dark. No manual/CSV/agent intake of any kind. |
| **4. The loop** (calibration) | Outcomes reconcile vs verdicts → sharper judgment | **Built** (ADR-327 `_calibration.md` kernel mirror) — but can only run where flow 3 exists. |

### 1a. Context-in has three modes — only one and a half exist

- **Mode A — live reads (pull at execution time): built, shelf-state.** Read
  tools registered and capability-gated for Slack (`list_channels`,
  `get_channel_history`), Notion (`search`, `get_page`), GitHub (5 tools),
  Trading (5 tools), Commerce (5 tools), plus kernel `WebSearch`. **But active
  bundles declare only:** alpha-trader = trading; alpha-author = `read_uploads`
  + `websearch`. Slack/Notion/GitHub reads are wired and used by no active
  program. (Corrects the prior doc's "context in: built, purified" — built as
  *capability*, not as lived flow.)
- **Mode B — operator-push: built, manual-grade.** Single-file upload (25MB,
  typed), chat, MCP `remember_this`, and a `bulk-import` text-paste endpoint
  (`memory.py::extract_from_text_to_user_memory`). No archive/multi-file path.
- **Mode C — catch-up/harvest of pre-YARNNN reality: not built.** A new
  operator's fragmented reality (Notion, Slack, drives, logs) has no door
  beyond one-file-at-a-time. **This is the onboarding gap.**

### 1b. Mode C does not violate ADR-153 purity

ADR-153 killed *continuous sync into an unattributed shadow content table*. A
catch-up harvest is dimensionally different: a **bounded invocation** —
addressed trigger, reads via Mode-A tools that already exist, writes
**attributed, curated substrate** into context domains (`agent:harvest`,
dated, revisioned). The machinery exists end-to-end; what's missing is the
*product motion*, not architecture.

---

## 2. Attestation — who vouches for an outcome row

Generalizing flow 3 beyond Alpaca quietly dilutes the moat claim ("ground truth
the agent cannot author") unless every outcome row carries **who attested it**:

| Level | Voucher | Strength | Example |
|---|---|---|---|
| **Platform-attested** | External API independent of operator + agent | Gold — supports "judged against reality" | Alpaca fill, LS order |
| **Operator-attested** | The operator's own import (CSV, manual entry) | Agent still can't fake it; operator can (incl. unconsciously — cherry-picked rows). Supports "judged against your own records." | Trade-log CSV, deal-history import |
| **Agent-attested** | An agent read/asserted the number | Weakest — the calibrated thing participates in producing the evidence. Needs corroboration/labeling. | Agent scrapes newsletter stats page |

**Spec requirement:** stamp attestation level on every `OutcomeCandidate`;
calibration weights or at least labels by it.

---

## 3. The dual-tracking retraction (the operator's catch — record it)

The operator asked: *"is the 'bring in reality' surface just a recurrence of
platform integrations?"* — and the answer exposed a creep already underway: the
proposed "setup-completeness readout with **harvest coverage**" was a parallel
state-tracking layer forming — `sync_registry` / `_tracker.md` reborn in
onboarding clothes. **Retracted.**

**The bright line (hold this):**

> **Harvest is an invocation, not a subsystem. The substrate is the record.**
> What's been brought in = the files that exist, attributed and dated. A
> harvest *invocation* whose only trace is narrative entries + attributed
> substrate is the system being itself; a harvest *manager* with its own
> coverage state is the unhealthy dual. Any future addition must pass the test:
> is this stored setup-state (reject) or a derivation over substrate (fine —
> ADR-244's `substrate_status` / `capability_gaps` pass; "harvest coverage"
> fails).

Lifecycle already exists in canon: ADR-205's inline-action→recurrence
graduation. Harvest = the inline action ("read these 3 Notion spaces, last 12
months, author into these domains"); ongoing live reads = its graduated
recurrence form. **One mechanism, two trigger shapes (Axiom 4). No third thing.**

---

## 4. Setup-as-rendering (the UX resolution)

The operator's second challenge: a brand-new-Mac first-boot experience is NOT a
settings tab. Correct — and the macOS mapping resolves it without dual
machinery, because macOS Setup Assistant **has no state of its own**: it writes
the same preferences domain System Settings displays. One substrate, two
presentation registers.

| macOS | YARNNN | Standing |
|---|---|---|
| Setup Assistant (first boot, thin, guided sequence) | `/setup` — **a sequence RENDERING over the existing workspace-state endpoint** | To build (FE route; the current `first_run=1` → Settings redirect per ADR-244 D5 is an anti-welcome) |
| Migration Assistant (bring your stuff; separate, **re-runnable**) | The harvest invocation(s), fired from a `/setup` step or chat, with scope control | To build (invocation + picker, no subsystem) |
| System Settings (random-access reference) | Settings → Workspace (ADR-244: program lifecycle, substrate status, capability gaps) + connectors | Built |
| Desktop / Finder | Home (ADR-312 composition; empty state POINTS to setup, never becomes it) / Files (ADR-329 substrate surface) | Built; discipline: don't colonize Home with setup chrome |

**The shape:** one state source (workspace-state endpoint), one action set
(activate program · connect platform · author via chat/ADR-226 overlay · fire
harvest invocation), **two renderings** — sequence (`/setup`, full-bleed,
ordered, re-enterable — "setup, not onboarding") and reference (Settings).
"Progress" is **derived** from substrate (which files authored, which
connections active, whether harvest invocations ran) — never stored
wizard-state. Complete a step anywhere; both renderings reflect it. Dual
tracking is impossible because there is nothing to drift.

**Plausible sequence steps (each an existing mechanism):** pick program (or
bare workspace) → author constitution (chat overlay deep-link) → connect
platforms → bring in reality (harvest invocations + scope picker) → first
artifact lands.

---

## 5. Open design questions (for the scoped ADR session)

1. **Harvest scope control** — Migration Assistant works because you pick what
   to migrate. Needs: source/range selection, dry-run estimate ("~400 pages →
   these domains"), then fire. Without it, "bring in reality" = "ingest
   everything" (cost + curation failure — the substrate's value is authored,
   not hoarded).
2. **Attestation weighting** — does calibration weight by attestation level or
   only label? (Lean: label first, weight when evidence demands.)
3. **Consequence-pipe naming** — "OutcomeProvider" misled its own architect
   (read as pipeline-out). Candidate rename at spec time: ground-truth intake /
   consequence pipe (Axiom 8 vocabulary).
4. **alpha-author ground truth** — what file + what accumulation recurrence
   (multi-signal per MANIFEST oracle shape), so the second active program's
   loop lights up.
5. **Bare-kernel default** — does the no-program workspace deserve a "default
   program" bundle so horizontal users land in something shaped? ~~(Raised, not
   discussed — carried open.)~~ **CLOSED 2026-06-10** by
   `four-flow-completeness-and-program-floor-2026-06-10.md` §3: Direction A
   (bare-kernel-product-floor, ratified 2026-06-01) reaffirmed and strengthened
   — a program IS a flow-declaration set; a "default program" would be a
   declaration set with no operation behind it. No default program; the
   singular path is signup → resting kernel → `/setup` → pick program → walk
   its declared flows to completeness.
