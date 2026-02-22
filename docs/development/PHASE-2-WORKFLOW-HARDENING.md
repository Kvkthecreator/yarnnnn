# Phase 2: Workflow Hardening — End-to-End Pipeline Integrity

> YARNNN-specific workflow issues that require holistic design discussion before execution.
> These are interconnected concerns — fixing one in isolation creates inconsistency elsewhere.
> Ref: ADR-072 (Unified Content Layer), ADR-056 (Per-Source Sync), ADR-053 (Monetization)

**Status**: Pending (requires Phase 1 completion + design discourse)
**Prerequisite**: Phase 1 technical debt cleared
**Approach**: Trace one piece of content end-to-end, then replicate pattern across platforms

---

## Why These Are Different From Phase 1

Phase 1 issues are **unconditionally wrong** — a `NameError`, a missing timeout, a bare `except:`. They have one correct fix regardless of product direction.

Phase 2 issues are **conditionally wrong** — they're wrong *given the current ADRs*, but the fix depends on confirming or revising those ADRs. Each issue below has at least two valid approaches, and the choice cascades into other decisions.

---

## The Core Problem: Seam Gaps

The four-layer model (ADR-063) is conceptually sound. Each layer works internally. The gaps are **between layers** — where one layer's output becomes another layer's input.

```
┌─────────────────────────────────────────────────────────────────┐
│                        CURRENT STATE                            │
│                                                                 │
│  Onboarding ──→ selected_sources saved to landscape  ✅        │
│       │                                                         │
│       ▼                                                         │
│  platform_worker ──→ loads selected_sources            ✅        │
│       │                  BUT ignores them in fetch     ❌        │
│       ▼                                                         │
│  platform_content ──→ schema exists                   ✅        │
│       │                  partial writes                ⚠️        │
│       ▼                                                         │
│  signal_extraction ──→ reads from LIVE APIs            ?         │
│       │                  not from platform_content     ?         │
│       │                  own filtering logic           ?         │
│       ▼                                                         │
│  signal_processing ──→ LLM reasoning pass             ✅        │
│       │                                                         │
│       ▼                                                         │
│  deliverable_execution ──→ generates output           ✅        │
│       │                      marks retention           ⚠️        │
│       ▼                                                         │
│  delivery ──→ exports to destination                  ✅        │
│                                                                 │
│  Monetization ──→ tier limits at UI level             ✅        │
│                    tier limits at sync level           ❌        │
│                    tier limits at signal level         ❌        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Decision Points (Require Discussion Before Execution)

### D1. Where does signal extraction read from?

**Current state**: Signal extraction calls live platform APIs directly (`_fetch_calendar_content()`, `_fetch_gmail_content()`, `_fetch_slack_content()`). Platform sync writes to `platform_content`. These are **two separate data paths**.

**Option A — Signals read from `platform_content`** (ADR-072's stated intent):
- Pro: Single source of truth. Sync handles API calls, filtering, storage. Signals just read.
- Pro: Source selection enforcement happens once (in sync), automatically applies to signals.
- Pro: Reduces API calls (no double-fetch).
- Con: Signal freshness depends on sync frequency. Free tier (2x/day) means signals see 12-hour-old data.
- Con: Requires sync to be complete and reliable first.

**Option B — Signals keep reading live APIs**:
- Pro: Always fresh data, independent of sync schedule.
- Pro: Works today without waiting for sync pipeline completion.
- Con: Two filtering implementations to maintain (sync filters + signal filters).
- Con: Monetization enforcement needed in two places.
- Con: Contradicts ADR-072's unified content layer thesis.

**Option C — Hybrid: Signals read `platform_content`, fall back to live APIs if stale**:
- Pro: Best of both — freshness when available, cached when not.
- Con: Most complex. Three code paths (cached fresh, cached stale, live fallback).

**This decision cascades into**: D2 (enforcement), D3 (sync frequency), D4 (platform coverage).

---

### D2. Where does monetization enforcement live?

**Current state**: Frontend source selection modal enforces tier limits. Backend `platform_limits.py` validates on save. But sync and signal processing have no enforcement.

**The question**: If a free-tier user selected 1 Slack channel but the worker ignores `selected_sources` and fetches 10, enforcement is theater.

**If D1 = Option A** (signals read from `platform_content`):
- Enforce at sync level only. Sync respects `selected_sources`, writes only selected content to `platform_content`. Everything downstream automatically scoped.
- Single enforcement point. Clean.

**If D1 = Option B** (signals read live APIs):
- Must enforce in BOTH sync AND signal extraction.
- Two places to maintain the same logic.
- Higher risk of drift.

**Additional consideration**: What happens on tier downgrade?
- User on Pro (20 channels) downgrades to Free (1 channel).
- Do we delete `platform_content` for the 19 now-unauthorized channels?
- Or just stop syncing them and let TTL expire?
- Or keep retained content but stop new syncs?

---

### D3. Sync frequency vs signal processing cadence

**Current state**:
- Sync frequency is tier-gated: Free=2x/day, Starter=4x/day, Pro=hourly
- Signal processing runs hourly for all users regardless of tier
- This means: Free user's signal processing reads the same stale content 11 times between syncs

**If D1 = Option A**: Signal processing cadence should match sync cadence per tier. No point reasoning about unchanged data.

**If D1 = Option B**: Signal processing cadence is independent of sync (always fresh from live APIs). But this means free users get hourly signal intelligence without paying for it — the monetization lever (sync frequency) is bypassed.

**Related ADR**: ADR-053 defines sync frequency as the monetization lever. If signals bypass this, the pricing model is undermined.

---

### D4. Platform coverage — what's MVP?

**Current state**:
- Slack: Sync works, signals work, delivery works
- Gmail: Sync works, signals work, delivery works
- Calendar: Signal extraction works (live API), NO sync to `platform_content`
- Notion: Sync works (but ignores selected_sources), signals return placeholder

**The question**: Which platforms need full pipeline coverage for launch?

**Consideration**: Calendar is time-sensitive (events in next 48h). Sync + TTL (1 day) means calendar content expires before the next sync for free users. Live API fetch may always be necessary for calendar regardless of D1.

**Consideration**: Notion's value proposition is different — it's about reference material (stale is fine) not real-time signals. May not need signal processing at all.

---

### D5. ADR-072 completion sequence

The remaining ADR-072 items are **ordered dependencies**:

```
1. Sync writes to platform_content ← Requires D1, D2 decisions
   └─ 2. Signal processing reads from platform_content ← Requires #1
       └─ 3. Signal processing marks retained=true ← Requires #2
           └─ 4. TP primitives read from platform_content ← Requires #1
               └─ 5. Deliverable execution uses TP headless mode ← Requires #4
                   └─ 6. Drop filesystem_items ← Requires all above
```

Each step requires the previous to be working. This is a **sequenced migration**, not parallel tasks.

**Risk**: Attempting to fix items 3-6 while items 1-2 are incomplete creates partial states that are harder to debug than the current clean separation.

---

## Proposed Discussion Structure

### Round 1: Settle D1 (data source for signals)
This is the keystone decision. Everything else follows from it.

### Round 2: Settle D2 + D3 (enforcement + cadence)
These are tightly coupled. Once D1 is decided, the correct answers for D2 and D3 are more constrained.

### Round 3: Settle D4 (platform scope)
With the pipeline pattern decided, scope which platforms need full coverage for next milestone.

### Round 4: Execute D5 (ADR-072 sequence)
With all decisions made, execute the migration in dependency order.

---

## What Phase 1 Unblocks

After Phase 1 is complete:

- Token handling is consistent → sync for all platforms uses the same reliable pattern
- Error handling is visible → when we trace the end-to-end flow, failures are logged not swallowed
- Queries are bounded → scheduler won't OOM while we test pipeline changes
- Startup validation → env misconfigurations caught immediately, not mid-sync
- Google API resilience → rate limits and timeouts handled, so sync is reliable enough to build on

Phase 1 makes the system **trustworthy enough to observe**. Phase 2 makes it **correct by design**.

---

## References

- ADR-072: Unified Content Layer & TP Execution Pipeline
- ADR-056: Per-Source Sync Implementation
- ADR-053: Platform Sync as Monetization Base Layer
- ADR-063: Four-Layer Model
- ADR-057: Streamlined Onboarding
- `docs/development/PHASE-1-TECHNICAL-DEBT.md` (prerequisite)
