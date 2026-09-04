# The harness drained the production pool — and the member was told "(402)"

2026-09-04. Triggered by an operator screenshot: a blogger lane reply rendered
as the bare string `Lane turn failed (402)`.

## What happened

The 402 is correct. The ADR-445 §9 draw gate blocked the turn because the
workspace's **effective balance was −$7.22** (later −$7.47).

| | |
|---|---|
| granted (anchor 2026-07-28) | $62.09 |
| billed since anchor (893 events) | $69.38 |
| **effective** | **−$7.22** |

**Today alone: $29.30 over 420 events**, all inside 04:00–06:00 UTC — 395 of
them `slug='lane'`, i.e. the real metered `run_lane_turn` path. 4.77M input
tokens, 5.55M cache reads. That window is yesterday's ADR-640 skills-discovery
A/B (3 asks × 2 arms × n=6, plus the clean-folder rerun), driven against the
**live production workspace**. The same signature appears on 08-31 ($11.10 /
65 ev) and 09-02 ($5.21 / 23 ev).

Restored with a $30 `admin_grant` (effective now **+$22.53**, verified against
`get_effective_balance`, not against the writer's silence — `grant_balance`
swallows its own failures).

## Finding 1 — nothing bounds a probe, because the owner is uncapped

`check_draw` layers two gates: the pool hard-stop, and the per-member cap. For
a probe running as the operator, **only the first one exists**:

- `member_caps.check_member_cap` line 132 — the owner carve returns
  `(True, None, 0.0)` before any cap is read. Deliberate and right (no
  self-lockout).
- So the sole bound on a 420-event burst was **the pool reaching $0**. There is
  no ceiling between "one turn" and "every dollar in the workspace".

⭐ **A hard-stop is not a bound. It is the absence of one, discovered late.**
It cannot distinguish a member working from a script looping, because by
construction it only ever fires once — after the money is gone.

## Finding 2 — the runaway-safety envelope exists and is decorative

`services/budget.py` resolves a per-workspace envelope
(`amount_usd`, kernel default **$50/monthly**) and `window_spend()` sums billed
draw over that window. Both are correct and both work.

**`routes/budget.py` is their only caller, and it is a display route.** It
computes `remaining = amount_usd - spent` and renders it. Nothing anywhere
compares the two to *refuse* anything — verified by grepping every `amount_usd`
reader in `api/`. Line 39 of that file describes it, in the present tense, as
"the backend runaway-safety envelope".

⭐⭐⭐ **A number that is displayed but never compared is not a safety envelope;
it is a gauge.** The mechanism ADR-327 built to prevent exactly this event was
already in the tree, already fed by the right ledger, and wired to a readout.

Calibration: today's 3-hour burst spent **59% of the monthly envelope**;
September stands at **$38.39 / $50 (77%) on day 4**. An enforced envelope would
have stopped the harness around event ~250 of 420 — and, notably, would *not*
have blocked the operator's blogger turn, which is the outcome we want.

## Finding 3 — the member was shown a number they cannot act on

The backend writes two *different*, well-phrased sentences for the two 402
causes — "balance is exhausted → top up" vs "you've reached your spend cap →
ask the owner" — because they are two different acts by two different people.

`web/lib/api/client.ts::streamLaneTurn` discarded both and rendered
`Lane turn failed (${res.status})`.

This is the **third recurrence of one defect in this file**, and both prior
fixes are documented in it:
- `APIError.messageFrom` — "every surface was showing `API Error: 409` instead"
- `errorDetailFrom` — written because ADR-499's self-heal read `data.detail`
  while the envelope had moved the string to `error.message`, so a member with
  a revoked grant "could not rejoin the workspace they had been re-invited to".

`streamLaneTurn` is the one error path in the file that never got either fix.
It is also the one the operator sees most.

⭐⭐ **A helper written to stop a class of defect only stops it at the call
sites that adopt it.** Both fixes were in the same file as the bug.

## Fixed

`streamLaneTurn` now reads the body through `errorDetailFrom` (the enveloped
shape is what `main.py` actually sends — a `detail`-only reader would have
silently missed it, which is precisely the ADR-499 failure), falling back to the
status line only when the body carries nothing legible.

Falsified over the six bodies production can produce — enveloped 402 (both
causes), raw `{detail}`, non-JSON gateway 502, JSON with no message,
whitespace-only detail. 6/6. `next build` green.

## Owed — not done here

Enforcing the envelope changes refusal behaviour on a costed kernel path that
every lane turn crosses. That is a decision, not a cleanup, and it wants an ADR:

1. **Where it binds.** `check_draw` is the natural chokepoint (both entries
   already cross it), but it is currently a *pool* gate; the envelope is a
   *rate* gate. Two questions, and ADR-557's "two flags, two questions" warns
   against merging them.
2. **Who it exempts.** If it exempts the owner it repeats Finding 1 verbatim
   and catches nothing. If it does not, a legitimate heavy operator day gets
   refused — so the refusal must name the envelope and be raisable by the
   operator themselves.
3. **What the harness does instead.** Probes should arguably draw a *separate*
   pool, or a scratch workspace, rather than being bounded inside the
   member-facing gate. Note `probe_adr638_register_ab.py` calls
   `route_completion` directly — real provider spend, invisible to the pool
   entirely. That is a second, unmetered hole.

No probe in `api/scripts/operator/` carries any spend guard today.

## Incidental — a stale gate found while verifying

`api/test_adr327_phase6_fe.py` is **15 PASS / 14 FAIL at HEAD, unchanged by
this edit** (verified by stashing the change and re-running — identical
counts). Every failure asserts the existence of a budget FE surface that no
longer exists: `/budget` in `KernelSurfaceSlug`, `BudgetCard.tsx`,
`useCockpitBudget`, the wallet icon, the UserMenu glance.

Same shape as the memory note *"a gate that pins a spelling pins the defect"* —
a gate outliving the surface it guards. Not swept here (out of scope, and it
guards the very envelope Finding 2 says should become enforced — whoever writes
that ADR should decide whether this gate is revived or deleted, not delete it
in passing).
