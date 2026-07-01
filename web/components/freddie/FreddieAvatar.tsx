'use client';

/**
 * FreddieAvatar — the mascot for Freddie, the system agent (v3, 2026-07-01).
 *
 * THE DESIGN LANGUAGE (the operator's "Freddie Design System" framing):
 *   - ONE iconic mascot: Freddie = FRANKENSTEIN's monster (flat-top head, brow
 *     scar, temple bolts), rendered in the CRYPTOPUNKS idiom — a literal 24×24
 *     pixel grid of hard-edged blocks.
 *   - ONE APPEARANCE, LIKE A BRAND LOGO. Freddie is ALWAYS the full-color Frankie
 *     (green skin · dark flat-top · steel bolts). No monochrome variant.
 *   - MOTION IS THE STATE (v3, the operator call). The earlier version encoded
 *     "what Freddie is doing" as five FIXED poses — a static lookup table that
 *     read as mechanical. Replaced by the loader model (think Claude Code's
 *     streaming shimmer): Freddie is a STILL mark at rest, and ANIMATES only
 *     while working. Motion = the activity signal; stillness = nothing running.
 *     The working motion is a continuous idle-loop (pupils scan + temple bolts
 *     pulse) — it reads as "alive and computing," not a discrete labeled mood.
 *   - SEAT, NOT PERSONA. The face is Freddie-the-seat (the system agent /
 *     substrate steward, ADR-381/383). An operator persona (IDENTITY.md) changes
 *     the NAME, never the face (the ADR-315 seat≠occupant split).
 *
 * ANIMATION: pure CSS keyframes SCOPED inside the SVG (an inline <style> with a
 * per-instance id) — GPU-cheap, no JS tick, no global-CSS dependency (the
 * component stays a single portable file). `animate=false` renders the still
 * logo (pupils centered, bolts steady).
 *
 * GRID: 24×24, viewBox 0 0 24 24, one pixel = one unit. Each non-empty cell →
 * one <rect width=1 height=1>. Pixels are NOT merged (24×24 is tiny; the DOM
 * cost is trivial and the code stays a legible pixel map).
 */

import { useId } from 'react';
import { cn } from '@/lib/utils';

export interface FreddieAvatarProps {
  /**
   * Whether Freddie is WORKING. true → the loader motion (scanning pupils +
   * pulsing bolts). false → the still full-color mark. Default true for now —
   * v3 ships the motion always-on to prove it reads well; a follow-up wires it
   * to real activity signals (a response streaming, a wake running).
   */
  animate?: boolean;
  /** Sizing (Freddie is always the full-color mark). Default 'w-4 h-4'. */
  className?: string;
  /** Accessible label. */
  title?: string;
}

// ── Palette ──────────────────────────────────────────────────────────────
const PALETTE: Record<string, string> = {
  K: '#1f2937', //  hair / flat-top + outline (near-black slate)
  G: '#5bbf57', //  skin (Frankenstein green)
  D: '#3f9a45', //  skin shadow (jaw / cheek)
  B: '#9ca3af', //  bolt metal (steel)
  H: '#e5e7eb', //  bolt highlight (shiny cap)
  M: '#4b5563', //  bolt shadow / dark rim
  E: '#111827', //  eye whites / mouth ink
  P: '#111827', //  pupil (its own key so it can animate independently)
  S: '#3f9a45', //  forehead stitch scar
};

// ── Base grid (24×24) ─────────────────────────────────────────────────────
// Frankenstein anatomy: flat-top HAIR crown + fringe, TALL square FOREHEAD,
// temple BOLTS (M B B H out each side), deep-set EYES, long flat MOUTH, jaw.
// The eye SOCKETS are the two 3-wide gaps at row 11 (cols 7-9 and 14-16); the
// eye whites (E) fill them and the animated pupil (P) sits inside — so the
// pupil has room to scan left↔right within the white.
// prettier-ignore
const BASE: string[] = [
  '........................',  // 0
  '........................',  // 1
  '......KKKKKKKKKKKK......',  // 2  hair crown
  '.....KKKKKKKKKKKKKK.....',  // 3
  '.....KKKKKKKKKKKKKK.....',  // 4  flat-top block
  '.....KKK.KKKK.KKKKK.....',  // 5  hair fringe
  '.....KGGGGGGGGGGGGK.....',  // 6  forehead
  '.....KGGGGGGGGGGGGK.....',  // 7  TALL forehead
  '.....KGGGSSSSSSGGGK.....',  // 8  stitch scar
  '.MBBHKGGGGGGGGGGGGKHBBM.',  // 9  temple bolts
  '.MBBHKGGGGGGGGGGGGKHBBM.',  // 10
  '.....KGEEEGGGGEEEGK.....',  // 11 eye whites: L=7-9 R=14-16 (pupils centered 8/15)
  '.....KGGGGGGGGGGGGK.....',  // 12
  '.....KGGGGGGGGGGGGK.....',  // 13
  '.....KGEEEEEEEEEEGK.....',  // 14 mouth
  '.....KGGGGGGGGGGGGK.....',  // 15
  '.....KDGGGGGGGGGGDK.....',  // 16 cheek/jaw shadow
  '.....KKDDDDDDDDDDKK.....',  // 17 jaw
  '......KKKKKKKKKKKK......',  // 18 chin/neck
  '......KKKKKKKKKKKK......',  // 19
  '........................',  // 20
  '........................',  // 21
  '........................',  // 22
  '........................',  // 23
];

// Eye whites live at row 11: left socket cols 7-9, right socket cols 14-16.
// The pupil is a 1px block that starts CENTERED in each white (col 8 / col 15)
// and scans ±1 col while animating. We render the pupils as separate <rect>s
// (not baked into the grid) so CSS can translate them.
const PUPIL_ROW = 11;
const PUPIL_L_CENTER = 8;
const PUPIL_R_CENTER = 15;

// The temple bolt CAPS (the H highlight pixels) — pulsed while working.
// Rows 9-10; left cap col 4, right cap col 19.
const BOLT_CAPS: Array<{ r: number; c: number }> = [
  { r: 9, c: 4 }, { r: 10, c: 4 },
  { r: 9, c: 19 }, { r: 10, c: 19 },
];

export function FreddieAvatar({ animate = true, className, title }: FreddieAvatarProps) {
  const uid = useId().replace(/:/g, ''); // scope the keyframes per instance
  const scanKf = `freddie-scan-${uid}`;
  const pulseKf = `freddie-pulse-${uid}`;

  const rects: React.ReactNode[] = [];
  for (let r = 0; r < BASE.length; r++) {
    for (let c = 0; c < BASE[r].length; c++) {
      const key = BASE[r][c];
      if (key === '.') continue;
      const isBoltCap = key === 'H';
      rects.push(
        <rect
          key={`${r}-${c}`}
          x={c}
          y={r}
          width={1}
          height={1}
          fill={PALETTE[key] ?? '#000'}
          // bolt caps pulse while working
          style={animate && isBoltCap ? { animation: `${pulseKf} 1.4s ease-in-out infinite` } : undefined}
        />
      );
    }
  }

  // Pupils — rendered separately so they can scan. Still (centered) when not
  // animating; sweep ±1px on a loop when working.
  const pupils = [PUPIL_L_CENTER, PUPIL_R_CENTER].map((cx) => (
    <rect
      key={`pupil-${cx}`}
      x={cx}
      y={PUPIL_ROW}
      width={1}
      height={1}
      fill={PALETTE.P}
      style={animate ? { animation: `${scanKf} 2.4s ease-in-out infinite` } : undefined}
    />
  ));

  return (
    <svg
      viewBox="0 0 24 24"
      className={cn('shrink-0', className ?? 'w-4 h-4')}
      role="img"
      aria-label={title ?? (animate ? 'Freddie is working' : 'Freddie')}
      shapeRendering="crispEdges"
      xmlns="http://www.w3.org/2000/svg"
    >
      <title>{title ?? (animate ? 'Freddie is working' : 'Freddie')}</title>
      {animate && (
        <style>{`
          @keyframes ${scanKf} {
            0%, 100% { transform: translateX(-1px); }
            50%      { transform: translateX(1px); }
          }
          @keyframes ${pulseKf} {
            0%, 100% { opacity: 1; }
            50%      { opacity: 0.35; }
          }
        `}</style>
      )}
      {rects}
      {pupils}
    </svg>
  );
}
