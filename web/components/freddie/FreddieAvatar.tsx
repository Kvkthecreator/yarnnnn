'use client';

/**
 * FreddieAvatar — the mascot for Freddie, the system agent (2026-07-01, v1).
 *
 * THE DESIGN LANGUAGE (the operator's "Freddie Design System" framing):
 *   - ONE iconic mascot, not an avatar creator. There is a single Freddie face.
 *   - LAYERED SVG COMPOSITION. The face is built from independent `<g>` layers
 *     (base · brow · eyes · mouth · status ring), composed at render time — the
 *     CryptoPunks-modular INSIGHT (base + swappable trait layers) applied to a
 *     FUNCTIONAL signal, not cosmetic variety. Traits here express STATE, not
 *     random identity.
 *   - STATE-EXPRESSIVE. Freddie's `liveness` drives the eyes + mouth + ring so
 *     the mascot visually communicates what the system agent is doing. This is
 *     the payload that makes it more than a sticker.
 *   - SEAT, NOT PERSONA. The face is Freddie-the-seat (the system agent /
 *     substrate steward, ADR-381/383). When the operator authors a persona
 *     (IDENTITY.md → "Simons"), the persona changes the NAME/voice, never the
 *     face (the ADR-315 seat≠occupant split). So one mascot is correct.
 *
 * TWO TONES (drop-in discipline):
 *   - `tone="mono"` (default) — single-color, driven by `currentColor`, so it is
 *     a byte-for-byte drop-in wherever a lucide glyph renders today. The
 *     attribution badge (principal-badge.tsx) passes a `className` that sets
 *     size + the rose accent via currentColor; a mono FreddieAvatar inherits it
 *     exactly like `<ShieldCheck className={...} />` does. This is what lets one
 *     component replace the glyph across Flow / Notifications / chat / roster.
 *   - `tone="full"` — the brand-colored mascot (rose face, ADR ROLE_META
 *     avatarHex #e11d48). Right for hero placements (the top-bar chip, the
 *     /agents detail header) where Freddie is the subject, not an inline actor.
 *
 * v1 SCOPE: base mascot + the 5 liveness states, mono + full tone. The trait
 * LIBRARY (accessories, richer expressions, animation) is the deferred v2 —
 * this file is built so v2 adds layers, it doesn't rewrite the base.
 */

import { cn } from '@/lib/utils';

/** What Freddie is doing — the axis the v1 mascot expresses (operator call). */
export type FreddieLiveness =
  | 'idle' //     calm, at rest — nothing to do
  | 'thinking' // eyes up, focused — a wake is being evaluated
  | 'acting' //   alert, eyes forward — executing / writing substrate
  | 'waiting' //  looking at you — something queued for your decision
  | 'paused'; //  asleep / dimmed — autonomy paused or dormant

export interface FreddieAvatarProps {
  /** What Freddie is doing. Default 'idle'. */
  state?: FreddieLiveness;
  /**
   * `mono` (default): single-color via currentColor — the glyph drop-in.
   * `full`: brand-colored mascot for hero placements.
   */
  tone?: 'mono' | 'full';
  /** Sizing + (in mono) the color, via currentColor. Mirrors a lucide glyph's
   *  className contract so this is a drop-in. Default 'w-4 h-4'. */
  className?: string;
  /** Accessible label. Default derives from state. */
  title?: string;
}

// Brand palette (full tone). Rose is Freddie's ROLE_META avatarHex (#e11d48).
const FULL = {
  face: '#e11d48', //     rose-600 — the mark
  faceDim: '#fb7185', //  rose-400 — paused/idle softening
  ink: '#ffffff', //      eyes/mouth on the rose face
  ring: '#e11d48',
} as const;

function labelFor(state: FreddieLiveness): string {
  switch (state) {
    case 'thinking':
      return 'Freddie is thinking';
    case 'acting':
      return 'Freddie is acting';
    case 'waiting':
      return 'Freddie is waiting for you';
    case 'paused':
      return 'Freddie is paused';
    default:
      return 'Freddie';
  }
}

export function FreddieAvatar({
  state = 'idle',
  tone = 'mono',
  className,
  title,
}: FreddieAvatarProps) {
  const isFull = tone === 'full';
  // In mono tone every layer is currentColor (the glyph contract). In full
  // tone the face carries brand color and the ink (eyes/mouth) sits on top.
  const face = isFull ? (state === 'paused' || state === 'idle' ? FULL.faceDim : FULL.face) : 'currentColor';
  const ink = isFull ? FULL.ink : 'currentColor';
  // In mono, eyes/mouth must read as cut-outs, not paint-over-paint. We draw
  // them with the surface color by punching via a mask-like light opacity trick
  // is overkill at 16px — instead mono uses stroke for features so they read on
  // any monochrome fill. Full tone paints solid ink on the rose face.
  const featureStroke = isFull ? 'none' : 'currentColor';
  const featureFill = isFull ? ink : 'none';

  return (
    <svg
      viewBox="0 0 24 24"
      className={cn('shrink-0', className ?? 'w-4 h-4')}
      role="img"
      aria-label={title ?? labelFor(state)}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <title>{title ?? labelFor(state)}</title>

      {/* ── Layer: BASE — the shield-derived steward head. A rounded shield
          nods to Freddie's shield-check lineage + the "guards your substrate"
          role, softened into a friendly face. ── */}
      <g className="freddie-base">
        <path
          d="M12 2.4c2.7 1.3 5.2 1.9 7.4 1.9v6.2c0 5.2-3.1 9.1-7.4 11-4.3-1.9-7.4-5.8-7.4-11V4.3c2.2 0 4.7-.6 7.4-1.9Z"
          fill={isFull ? face : 'currentColor'}
          opacity={isFull ? 1 : 0.14}
        />
        {/* mono keeps a crisp outline so the face reads on light backgrounds */}
        {!isFull && (
          <path
            d="M12 2.4c2.7 1.3 5.2 1.9 7.4 1.9v6.2c0 5.2-3.1 9.1-7.4 11-4.3-1.9-7.4-5.8-7.4-11V4.3c2.2 0 4.7-.6 7.4-1.9Z"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinejoin="round"
          />
        )}
      </g>

      {/* ── Layer: EYES — the primary expression carrier. Position + shape
          shift by liveness. ── */}
      <g className="freddie-eyes" fill={featureFill} stroke={featureStroke} strokeWidth="1.4" strokeLinecap="round">
        {state === 'paused' ? (
          // closed eyes — two gentle arcs
          <>
            <path d="M8.4 10.6c.5.5 1.1.5 1.6 0" fill="none" />
            <path d="M14 10.6c.5.5 1.1.5 1.6 0" fill="none" />
          </>
        ) : state === 'thinking' ? (
          // eyes up (looking at the problem)
          <>
            <circle cx="9.2" cy="9.6" r="1.15" stroke="none" fill={isFull ? ink : 'currentColor'} />
            <circle cx="14.8" cy="9.6" r="1.15" stroke="none" fill={isFull ? ink : 'currentColor'} />
          </>
        ) : state === 'waiting' ? (
          // wide, attentive — looking AT you
          <>
            <circle cx="9.2" cy="10.4" r="1.35" stroke="none" fill={isFull ? ink : 'currentColor'} />
            <circle cx="14.8" cy="10.4" r="1.35" stroke="none" fill={isFull ? ink : 'currentColor'} />
          </>
        ) : (
          // idle / acting — steady dots (acting adds the mouth + ring energy)
          <>
            <circle cx="9.2" cy="10.4" r="1.15" stroke="none" fill={isFull ? ink : 'currentColor'} />
            <circle cx="14.8" cy="10.4" r="1.15" stroke="none" fill={isFull ? ink : 'currentColor'} />
          </>
        )}
      </g>

      {/* ── Layer: MOUTH — secondary expression. ── */}
      <g className="freddie-mouth" fill="none" stroke={isFull ? ink : 'currentColor'} strokeWidth="1.4" strokeLinecap="round">
        {state === 'acting' ? (
          // small open focus — "on it"
          <path d="M10.4 14.2c.9.7 2.3.7 3.2 0" />
        ) : state === 'waiting' ? (
          // slight upward — inviting your decision
          <path d="M10.2 14c1 .9 2.6.9 3.6 0" />
        ) : state === 'paused' ? (
          // flat rest
          <path d="M10.6 14.4h2.8" />
        ) : (
          // idle / thinking — calm neutral
          <path d="M10.6 14.2h2.8" />
        )}
      </g>

      {/* ── Layer: STATUS RING — only for the active/attention states, and only
          in full tone (a hero affordance). A subtle accent that signals "live".
          Kept out of mono so the drop-in glyph stays clean. ── */}
      {isFull && (state === 'acting' || state === 'waiting') && (
        <circle
          cx="12"
          cy="12"
          r="11"
          fill="none"
          stroke={FULL.ring}
          strokeWidth="1.4"
          strokeLinecap="round"
          strokeDasharray={state === 'acting' ? '3 4' : '0 1000'}
          opacity="0.55"
        />
      )}
    </svg>
  );
}
