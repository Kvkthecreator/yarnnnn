# alpha-author

> The **substrate-continuity** application running on the YARNNN agent-native operating system. This folder is the program **bundle**. Operator-authored corpus workflow with persistent editor seat — accumulated work that compounds across cadence, voice, and audience.
>
> Machine-readable contract: [MANIFEST.yaml](MANIFEST.yaml). Composition manifest: [SURFACES.yaml](SURFACES.yaml). Bundled starter substrate: [reference-workspace/](reference-workspace/). Format and structure ratified by [ADR-223](../../adr/ADR-223-program-bundle-specification.md). Bundle scope-lock + dogfood plan: [ADR-283](../../adr/ADR-283-alpha-author-bundle.md). Companion axiom rename: [ADR-282](../../adr/ADR-282-axiom-8-ground-truth-rename.md).

## Position relative to the kernel

alpha-author is the second program (after [alpha-trader](../alpha-trader/README.md)) running on the YARNNN kernel, per [ADR-222](../../adr/ADR-222-agent-native-operating-system-framing.md) + [FOUNDATIONS Principle 16](../../architecture/FOUNDATIONS.md). This bundle describes the program — its surfaces, scaffolding, success bar — not the kernel underneath.

When this program needs work that would also serve alpha-trader or future bundles, that work ships as kernel-layer (e.g., Notion page-write extension under ADR-283 roadmap step 2). When it needs work that only alpha-author benefits from, that work ships under this bundle or under `docs/alpha/personas/alpha-author/` (persona-layer authoring).

## Archetype relative to alpha-trader

alpha-trader and alpha-author exercise **different bundle archetypes** within the YARNNN architecture. The distinction is load-bearing — they prove different parts of the framework and pitch differently to operators.

| Dimension | alpha-trader | alpha-author |
|---|---|---|
| Archetype | Autonomous-execution | Substrate-continuity |
| Reviewer role | Capital-EV approver | Editor + continuity guardian |
| Loop tension | Hours-to-days; ground-truth attributable per trade | Continuous (coherence) + days-to-weeks (audience) + months (revenue when present) |
| Ground-truth substrate | `_money_truth.md` (Alpaca P&L; ADR-195 v2 instance) | `_signal.md` (multi-signal: coherence + audience + revenue; ADR-283 D4 instance) |
| Single-signal vs multi-signal | Single-signal (P&L) | Multi-signal (coherence always present; audience + revenue when connected) |
| GTM pitch | "Agent acts within bounds you authored" | "Persistent seat that grows into your domain and applies your discipline" |
| Operator success | P&L curve | Corpus that compounds (signal-attributable revenue OR recognized voice OR demonstrable audience growth) |

The substrate-continuity archetype is **the more defensible long-term position** — the autonomous-execution race commoditizes through 2026-2027 (every agent platform pitches autonomy); substrate accumulation + operator-authored judgment compounding is structurally harder to commoditize because the moat is operator's accumulated work product + operator's authored principles, not vendor IP.

## Oracle profile

| Property | Value |
|---|---|
| Oracle source | Multi-signal: corpus coherence (always present) + audience engagement (when audience-bearing) + commerce revenue (when commerce-bearing) |
| Latency | Continuous internal (coherence audits) to weekly external (audience response) to months (revenue cohort) |
| Attribution | Per-piece for content production; cohort-level for audience response; sparse for revenue |
| Action space | Voice audit, continuity audit, ship/defer, schedule, cross-post |
| Action irreversibility | Partially reversible (content can be unpublished or revised; audience perception persists) |
| Capital threshold | $0 — pre-monetization workspaces are first-class |
| Stationarity | Operator's voice is mostly stable; corpus continuity is the slowly-evolving substrate the Reviewer audits against |

This is a **weaker oracle** than alpha-trader's by design — and the architecture has to handle that gracefully. Internal coherence is always available (Reviewer-detected); audience signal arrives in days; revenue signal arrives in months and may never arrive for pre-monetization workspaces. The Reviewer's calibration is necessarily looser than alpha-trader's. **This is acceptable for the archetype.** Substrate-continuity bundles accept multi-timescale calibration as the cost of broader operator applicability.

## ICP

The operator who self-conceives as **authoring a body of work** — not "creating content," not "running a social account." Specifically:

- **Newsletter writers** (paid or free): Substack, Beehiiv, ghost, ConvertKit
- **Podcasters** (interview or essay-shaped): per-guest substrate + per-episode pipeline
- **Founder-content authors**: build-in-public, IR-narrative, customer-development
- **Paid-community curators**: editorial curation as the primary product
- **Video essayists**: YouTube long-form, but only when the operator treats episodes as corpus pieces with continuity
- **Screenwriters / novelists / longform authors**: workspaces where the corpus is an evolving single artifact (script, manuscript), not a stream of published pieces

The bundle is **medium-agnostic** within "operator authoring a body of work." It filters out the operators who churn posts to feed an algorithm — that audience is alpha-creator-shaped (broader, commodity-positioning) and explicitly **not** alpha-author's ICP.

## Surfaces the program needs

These are program-layer commitments — the OS hosts them but does not claim them as universal cockpit features. Compositor binding declared in [SURFACES.yaml](SURFACES.yaml).

| Surface | What it is | Hosting tab |
|---|---|---|
| **Author-aware Work list** | When alpha-author is the active program, `/work` list mode pins `pre-ship-audit` + `weekly-corpus-review` and surfaces a phase-aware banner | Work |
| **Corpus dashboard** | Live read of `/workspace/context/authored/` — recent pieces, voice fingerprint state, continuity threads. Wired via four-face cockpit composition (see SURFACES.yaml) | Work cockpit |
| **Voice-audit review queue** | Pre-ship audit proposals surfaced in Queue archetype with voice-drift detection + continuity-check + anti-slop scoring alongside approve/reject | Work task-detail (proposals also visible at `/agents?agent=reviewer`) |
| **Cadence-health indicator** | Renders operator's declared cadence (from `_preferences.yaml`) against actual ship dates; surfaces "you said weekly, you haven't shipped in 12 days" | Work, surfaced on the AuthorPipeline cockpit face |
| **Per-piece detail view** | Drill into `/workspace/context/authored/{piece-slug}/` — content, voice fingerprint match, continuity threads, revision lineage per ADR-209 | Work task-detail |

The OS provides the cockpit shell, narrative substrate, primitive surface. The program provides the author-shaped reads on top.

## Scaffolding

What the program brings to a workspace, beyond what the OS scaffolds at signup. Machine-readable in [MANIFEST.yaml](MANIFEST.yaml).

### Capability bundles
- **Kernel-side (shipped)**: `read_uploads`, `websearch`, `write_notion` (comment-only today)
- **Kernel-side (deferred to ADR-283 step 2)**: `write_notion_pages` (extend Notion writes beyond comment), `write_email` (Resend; for newsletter operators with API access)
- **Bundle-declared (deferred to ADR-283 step 2)**: `write_linkedin_post`, `write_x_post`, `write_newsletter` — publishing-platform writes specific to alpha-author's surface needs

The bundle is **activatable today in knowledge-only mode** (reads + comments + drafts in Notion + lived-attention via uploads + websearch). Audience-bearing capabilities (publishing-platform writes) ship in step 2 and unlock the audience signal slice of `_signal.md`.

### Context domains
- `/workspace/context/authored/` — per-piece entities (one folder per draft or published piece). Operator authors `_voice.md` (declared voice fingerprint + anti-patterns) and `_editorial.md` (what gets shipped, what doesn't). `_signal.md` accumulates corpus-coherence audit results.
- `/workspace/context/audience/` — per-platform engagement state. Empty by default; populated only when audience-bearing capabilities are connected (LinkedIn, X, newsletter, commerce platforms).

### Recurrence types
Capability-shaped, not schedule-shaped (per ADR-283 D9). The bundle ships capability specs; workspace-level `_preferences.yaml` declares cadence:

- `corpus-coherence-check` (judgment, periodic) — Reviewer reads recent corpus + flags voice drift or continuity breaks
- `pre-ship-audit` (judgment, reactive) — fires when operator marks a draft `ready_for_review`; Reviewer audits before approving ship
- `outcome-reconciliation` (judgment, daily) — folds the day's signals into `_signal.md` (coherence audit results + audience-signal slices when connected)
- `track-linkedin` / `track-x` / `track-newsletter` (mechanical, when audience-bearing) — mirror publishing-platform engagement state into `context/audience/{platform}/`

Plus operator-declared deliverable cadence via `_preferences.yaml`:
- `weekly-corpus-review` (Sunday) — voice-fingerprint stability, audience response synthesis, cadence-health
- `quarterly-voice-audit` (quarter-end) — quarterly check on voice fingerprint drift vs declared corpus baseline

### Agent roster (universal roles, contextual application)
Standard YARNNN agents apply. The **Reviewer** is the load-bearing seat for alpha-author — see [reference-workspace/review/IDENTITY.md](reference-workspace/review/IDENTITY.md) for the editor-shaped default persona.

### Principles content (program guidance, operator authors)
Templates ship in [reference-workspace/review/principles.md](reference-workspace/review/principles.md). Defaults:

- Voice fingerprint enforcement (drift detection against declared `_voice.md` baseline)
- Continuity audit (every draft checked against prior published corpus for contradiction)
- Anti-AI-slop signature detection (list-of-three openers, "It's worth noting", hedge-laden middles)
- Cadence enforcement (operator declares cadence; Reviewer flags missed cadence)
- Anti-overclaim (stance inflation blocked; hedged claims masquerading as strong rejected)

Operators fork their own MANDATE / `_voice.md` / `_editorial.md` / `principles.md` from these. The program does not author them; the OS doesn't either.

## OS dependencies

Machine-readable in [MANIFEST.yaml](MANIFEST.yaml) (`dependencies.required` blocks activation; `dependencies.lean` is informational — deferred to step 2).

| Dependency | OS ADR | Status |
|---|---|---|
| Authored substrate (revision chain on every corpus revision) | ADR-209 | Shipped |
| Reviewer-as-editor seat | ADR-194 v2 | Shipped (seat occupant-class-agnostic; alpha-author ships editor-persona default) |
| AUTONOMY.md delegation file | ADR-217 | Shipped |
| Source-agnostic feedback (`system_voice_drift` source for Reviewer-detected drift) | ADR-181 | Shipped |
| Action proposal queue (pre-ship audits emit ProposeAction) | ADR-194 v2 + ADR-202 | Shipped |
| Ground-Truth Substrate axiom (kernel-level concept) | ADR-282 | Shipped 2026-05-15 |
| Notion page-write extension (beyond current comment-only) | TBD — ADR-283 roadmap step 2 | Deferred |
| Publishing-platform write integrations (LinkedIn / X / newsletter) | TBD — ADR-283 roadmap step 2 | Deferred |
| Program-specific cockpit face components | TBD — ADR-283 roadmap step 3 | Deferred |

## OS stress points

What this program asks of the OS that the OS must deliver cleanly:

1. **Multi-signal ground-truth substrate** — alpha-author's `_signal.md` carries coherence + audience + revenue signals in one file with graceful degradation when external slices are absent. The reconciler architecture (alpha-trader's `OutcomeProvider`) must extend to multi-signal aggregation per `_signal.md` schema.
2. **Reviewer-as-editor without persona collapse** — the editor seat must read corpus + audit drafts without becoming a content generator. The independence boundary (Reviewer ≠ writer) must hold; the Reviewer audits operator-authored drafts, never authors content itself.
3. **Cadence enforcement under archetype mismatch** — operators may declare weekly cadence then drop into multi-week revision cycles on a single piece (Netflix screenplay case). The Reviewer must distinguish "missed cadence" from "single-piece long-arc revision" without false alarms.
4. **Pre-audience graceful degradation** — Netflix-screenplay workspaces have zero external audience signal for months. The cockpit, `_signal.md`, and Reviewer's calibration must function on internal-coherence-only without degrading to "missing data" displays.

## Success bar

The program is validated when:

1. **Accumulation Phase (Phase 0)**: Operator authors MANDATE + voice fingerprint + 30 days of corpus. Reviewer's voice-audit detects at least one real drift signal the operator agrees with.
2. **Cadence Discipline (Phase 1)**: 60 consecutive days of operator shipping on declared cadence. `_signal.md` shows voice fingerprint stability (no false-positive drift alarms; no missed real drift).
3. **Selective Autonomy (Phase 2)**: At least one corpus category (e.g., newsletter weekly edition) flips to bounded-autonomous — Reviewer pre-ship audit binds approve without operator click, voice-audit + continuity-audit gating execution.
4. **Corpus Compounds milestone (Phase 3)**: Operator hits their chosen success bar — signal-attributable revenue (commerce-bearing workspaces) OR recognized voice fingerprint (qualitative; audience-bearing workspaces) OR demonstrable audience growth (subscriber/follower compounding over 6+ months).

These are bars, not promises. Failure of any one is signal about the program; failure of all is signal about the substrate-continuity archetype's viability in this domain.

## Phase milestones

Machine-readable in [MANIFEST.yaml](MANIFEST.yaml) (`phases` + `current_phase`). Phase-aware cockpit chrome declared in [SURFACES.yaml](SURFACES.yaml) (`phase_overlays`).

- **Phase 0 — Accumulation** (current) — operator authors MANDATE + `_voice.md` + first 30 days of corpus. AUTONOMY manual. Reviewer audits on request, does not push to ship.
- **Phase 1 — Cadence Discipline** — 60 days of operator shipping on declared cadence. Voice fingerprint stability calibrated. AUTONOMY bounded.
- **Phase 2 — Selective Autonomy** — Reviewer pre-ship audits consultative; per-corpus-category auto-approve carve-outs per principles.md (e.g., newsletter weekly edition cleared with voice-pass + continuity-pass).
- **Phase 3 — Corpus Compounds** — substrate moat structurally real, not just claimed.

## Relationship to the persona layer

Operator workspace artifacts (`docs/alpha/personas/alpha-author/{workspace-slug}/`) are operator-authored, per-workspace. Program artifacts (this folder) are platform-authored, stable across operators of the program. The persona layer evolves; the program layer commits.

Per [ADR-283 D5](../../adr/ADR-283-alpha-author-bundle.md): the dogfood plan declares two persona workspaces — `yarnnn-author` (founder content) and `netflix-script-author` (screenplay). Persona-level overrides at `docs/alpha/personas/alpha-author/{workspace-slug}/overrides/` per ADR-230 D6.

## Open program-layer questions

Tracked here, not in OS ADRs:

- What's the right `_voice.md` declaration shape — prose fingerprint, structured patterns, or both? (Decided in step 1 ref-workspace authoring; revisit after first dogfood.)
- Should `pre-ship-audit` block ship on voice drift, or surface as advisory? (Phase 0 default: advisory. Phase 1+ may flip per operator preference.)
- How does the cadence-health indicator handle revision-pulse workspaces (screenplay) vs ship-pulse workspaces (newsletter) gracefully? (Decided in step 3 cockpit face design.)
- Multi-program operators — does kvk activate alpha-trader AND alpha-author simultaneously? (ADR-230 says one program per workspace; multi-workspace per operator handles this case.)
- Pricing model — same as alpha-trader (platform usage), or program-tier above the OS billing? Defer until Phase 1.
