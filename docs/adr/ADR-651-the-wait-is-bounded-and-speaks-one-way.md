# ADR-651 — The wait is bounded and speaks one way

**Status**: Accepted + Implemented · 2026-09-13 (operator ask: *"audit our codebase and see how we're
handling the loading and page redirecting and overall loading handling from pages to chats … have a
similar feel to that of claude code … straightforward, long standing, future proof and thus scalable and
accounting for edge cases in the most minimal and compact way possible, so that even in failure modes we
don't have infinite loading"*).
**Amends** [docs/design/ACTION-FEEDBACK.md](../design/ACTION-FEEDBACK.md) — a sixth lane, **Waiting**.
**Preserves** [ADR-308](ADR-308-redirect-stubs-as-pure-transport.md) (a redirect stub is transport and
renders nothing — untouched, and re-verified: every interior stub is a server `redirect()`),
[ADR-441](ADR-441-the-conversation-mount-contract.md) D4 (one SSE transport loop; this ADR gives it a deadline, not a
second reader), [ADR-648](ADR-648-a-read-is-bounded-and-says-so.md) (one home per rule).
**Hat**: A. **Gate**: `web/scripts/gates/adr651_the_wait_is_bounded.mjs` (run from the repo root).

---

## 1. The audit — every wait was hand-drawn, and none of them could end

The 2026-09-13 sweep of `web/` (receipts in the gate's §3, which enumerates the shapes it found):

- **~115 sites** rendered a lucide `Loader2 animate-spin` with no wrapper, no shared size, and six
  different sizes; **5** copy-pasted the same `h-24 … animate-pulse` block; **8** Suspense fallbacks
  rendered a bare `<p>Loading...</p>`. Three idioms, zero components.
- **Not one wait was bounded.** No `AbortSignal` existed outside the lane stream; `request()` in
  `lib/api/client.ts` set no deadline; the SSE reader had no idle deadline; no wait ever said "still
  working" or offered an exit. A fetch a proxy left hanging kept its surface loading for ever.
- **The chat could spin for ever.** The in-flight row was `sending === true` and nothing else: no
  elapsed time, no stall detection, and a socket kept half-open by a proxy was indistinguishable from a
  thinking engine. Thinking is not on the wire, so an honest turn can be silent for minutes.
- **The one animation vocabulary in `globals.css` was dead.** The "Workfloor Liveness" block
  (`agent-working`, `desk-glow`, a `shimmer` keyframe, `tp-pulse`) had zero JSX consumers and referenced
  an undefined `--agent-color`. `framer-motion` is declared and imported nowhere.
- **Reduced motion froze every spinner** on its first frame: the global guard turned `animate-spin`
  into a still icon with no other signal.
- **Redirects were already right.** ADR-308 holds: every interior stub is a pure server `redirect()`;
  the remaining `router.push` calls are click handlers or the window manager's own URL sync.

The reference the operator named is Claude Code's spinner (`docs/analysis/src_claudeCC/components/Spinner*`):
a glyph cycling `· ✢ ✳ ✶ ✻ ✽` forward then back at 120ms, a verb with a three-character band of light
sweeping across it, elapsed time and a stop hint in dim text, and a shift to red when tokens stop for 3s.
Under reduced motion, a single slowly-flashing dot.

## 2. Decisions

**D1 — ONE wait primitive.** `web/components/shared/Working.tsx` (`Working`, and `WorkingGlyph` for a row
that already carries its own words) is the only way a wait a member reads is rendered. It is Claude Code's
glyph cycle beside a label a band of foreground sweeps across. The motion is CSS (`.working-*` in
`globals.css`): no timer, no per-frame render, safe inside a Suspense fallback, and under
`prefers-reduced-motion` the base state IS the still frame — a "·" and plain muted text. Forced-colors
mode gets a guard, because clip-to-text paints nothing there. The dead liveness block is deleted.

**D2 — Bounded by construction.** A wait that cannot report progress is bounded by the primitive itself:
after `SLOW_MS` (6s) the row says "still working"; after `STUCK_MS` (30s) it offers an exit — the caller's
`onRetry`, else Reload. No caller remembers this; it cannot be forgotten at a new site. A caller that CAN
report progress passes `since` (the chat turn): the row shows elapsed time and never self-escalates,
because a long honest turn is not a stuck one — **the transport bounds that wait (D3)**. The gate holds
`SLOW_MS < STUCK_MS ≤ 60s`.

**D3 — The transport bounds what the primitive cannot see.** Three deadlines, one home each:
- `request()` carries `AbortSignal.timeout(REQUEST_TIMEOUT_MS)` (60s) unless the caller brought a
  `signal`; `timeoutMs` overrides it for an endpoint that honestly runs long (memory extraction: 180s).
  The deadline's rejection wears `APIError` so every `runAction` and `error.message` site reports it in
  the member's words. Direct `fetch` sites (upload, export) are untouched — they are not `request()`.
- `sseEvents` takes `idleMs` and raises `SseIdleError` when no bytes arrive in that window, cancelling
  the reader so the server sees the disconnect and persists the partial. The lane stream sets
  `LANE_IDLE_MS` (45s) and reports the idle as the turn's failure — the placeholder drops, the composer
  gives the text back. The strict window arms only once the server has sent a comment frame (proof it
  heartbeats); until then the window is `LANE_IDLE_MS_UNTIL_HEARTBEAT` (450s, the engine's hung-call
  timeout plus margin). So the two halves of this seam ship in any order: a web deploy that lands before
  the API's cannot cut an honest long thought, and a proxy that strips comments still gets a bound.
- The server heartbeats the lane stream: `_with_heartbeat` in `api/routes/lanes.py` yields an SSE
  comment frame (`: ping`) whenever `_HEARTBEAT_S` (15s) passes with no event. Comment frames are SSE's
  own keepalive; every reader skips them by spec, and any bytes reset the client's idle clock. The gate
  holds `2 × _HEARTBEAT_S ≤ LANE_IDLE_MS`. Cancelling the consumer cancels the producer, so a member's
  stop still reaches the turn (driven: a producer sleeping 5s is cancelled when the consumer is).

**D4 — The wait is a live region.** `role="status"` on the primitive, so a screen reader hears it once
when it appears and hears the escalation; the elapsed counter is `aria-hidden` so it never re-announces.

**D5 — Micro-feedback stays at the control.** A control acknowledging itself — the icon swap inside a
button while its own verb runs — is ACTION-FEEDBACK's micro-feedback lane, not a wait the member reads.
Those ~80 `Loader2` sites inside buttons stay lucide; the gate's §3 regex is on `<div>`, never `<button>`.
An inline image slot in prose is a still box, not a wait.

**D6 — Redirects stay as ADR-308 left them.** Nothing here paints during transport.

## 3. What changed

- New: `web/components/shared/Working.tsx`; the `.working-*` block in `web/app/globals.css`; the gate.
- Transport: `web/lib/sse.ts` (idle deadline), `web/lib/api/client.ts` (`REQUEST_TIMEOUT_MS`,
  `LANE_IDLE_MS`, the two catches), `api/routes/lanes.py` (`_HEARTBEAT_S`, `_with_heartbeat`).
- Chat: `LanePanel.tsx` — the in-flight row is `Working` in its patient form with `turnStartedAt`;
  `StreamSteps.tsx` — the in-flight step spins the same glyph.
- 47 files: every hand-drawn wait block, the six boundary fallbacks (`(authenticated)/layout`, login,
  callback, `mcp/auth`, `mcp/authorize`, admin), the five pulse blocks, `BlobLoading`. Labels keep each
  surface's own words; `...` became `…`. Studio's lane row stopped rendering an error and a wait through
  one spinner (ACTION-FEEDBACK §6).
- Deleted: the Workfloor Liveness CSS block (70 lines, zero consumers).

## 4. Verification

- Gate 20/20; proven RED on the unchanged tree (1/20), and two executing checks falsified in place: a
  broken keyframe stop reddened §2 (a frame with no glyph), a 30s heartbeat reddened §5.
- `tsc --noEmit` clean; `next build` exit 0; `check-build-traces` packs clean (78 traces, 6603 refs).
- Driven in Chrome (puppeteer-core, the real `globals.css` block): the lit glyph sampled at 120ms runs
  `· ✢ ✳ ✻ ✽ ✻ ✶ ✳ ✢ ·`; the shimmer position differs at every sample; under reduced motion exactly one
  glyph (·) is lit and the shimmer holds still. **The drive found what the gate could not**: the first
  cut lit ZERO glyphs under reduced motion — `.working-glyph > span { opacity: 0 }` (0,1,1) outranked the
  frame-0 base (0,1,0). Fixed by specificity; the CSS comment names it.
- `test_adr562` (pins the speaker in "is working…"), `test_adr495` 24/24, `test_adr558` 51/51,
  `test_adr411` 13/13, `test_adr495_conversation` 14/14, `test_no_undefined_names` 220/220.
- Baseline-red, untouched, now on the handoff list: `test_adr412_chat_surface` (4 red:
  `FileNotFoundError` on files deleted long ago) and `test_retired_vocabulary_ratchet`
  (`operator_proxy/scenarios.py` 5 > 4, committed this morning in `65e6b31`).

## 5. Not done, named

- A prod click-pass of a real lane turn showing the elapsed counter, a heartbeat in the network tab,
  and a real idle timeout (both deploys must be live; order does not matter — D3).
- `framer-motion` is a dead dependency; removing it needs a lockfile write (`pnpm` is not on this
  machine's PATH, and Vercel installs frozen).
- The button-embedded spinners (D5) could adopt `WorkingGlyph` for one motion everywhere; that is a
  choice about micro-feedback, not a wait, and is left to ACTION-FEEDBACK's owner.
