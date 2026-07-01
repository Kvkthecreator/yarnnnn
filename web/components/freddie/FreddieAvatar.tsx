'use client';

/**
 * FreddieAvatar — the mascot for Freddie, the system agent (v2, 2026-07-01).
 *
 * THE DESIGN LANGUAGE (the operator's "Freddie Design System" framing):
 *   - ONE iconic mascot: Freddie = FRANKENSTEIN's monster (flat-top head, brow
 *     scar, neck bolts), rendered in the CRYPTOPUNKS idiom — a literal 24×24
 *     pixel grid of hard-edged blocks. The v1 curved-vector attempt read as a
 *     "shield clown"; this is the retrofit: a pixel-punk Frankie.
 *   - MODULAR PIXEL CONSTRUCTION (the CryptoPunks insight, literally). A base
 *     24×24 grid + per-STATE trait overlays that swap specific pixels (eyes,
 *     mouth, brow). Traits express STATE, not cosmetic identity — the modular
 *     stack drives a FUNCTIONAL signal, not random variety. A future v2 trait
 *     library (hat/glasses/accessory rows) drops onto the same grid.
 *   - STATE-EXPRESSIVE. `liveness` swaps the eye + mouth pixel rows so the
 *     mascot visually communicates what the system agent is doing.
 *   - SEAT, NOT PERSONA. The face is Freddie-the-seat (the system agent /
 *     substrate steward, ADR-381/383). An operator persona (IDENTITY.md →
 *     "Simons") changes the NAME, never the face (the ADR-315 seat≠occupant
 *     split). So one mascot is correct.
 *
 * TWO TONES (drop-in discipline):
 *   - `tone="mono"` (default) — the whole punk is drawn in ONE color via
 *     currentColor (ink pixels only; the fills collapse to the ink). A
 *     byte-for-byte drop-in wherever a lucide glyph renders today (the
 *     attribution badge passes a className that sets size + the rose accent).
 *   - `tone="full"` — the full palette Frankie (green skin, dark flat-top,
 *     metal bolts). Right for hero placements (the top-bar chip, the /agents
 *     detail header) where Freddie is the subject.
 *
 * GRID: 24×24, viewBox 0 0 24 24, one pixel = one unit. Rendering maps each
 * non-empty grid cell to a `<rect width=1 height=1>`. Adjacent same-color
 * pixels are NOT merged (24×24 is small; the DOM cost is trivial and the code
 * stays a legible pixel map).
 */

import { cn } from '@/lib/utils';

/** What Freddie is doing — the axis the mascot expresses (operator call). */
export type FreddieLiveness =
  | 'idle' //     calm, at rest — nothing to do
  | 'thinking' // eyes up, focused — a wake is being evaluated
  | 'acting' //   alert, eyes forward — executing / writing substrate
  | 'waiting' //  looking at you — something queued for your decision
  | 'paused'; //  asleep — autonomy paused or dormant

export interface FreddieAvatarProps {
  /** What Freddie is doing. Default 'idle'. */
  state?: FreddieLiveness;
  /** `mono` (default): one-color via currentColor — the glyph drop-in.
   *  `full`: the full-palette Frankenstein Freddie for hero placements. */
  tone?: 'mono' | 'full';
  /** Sizing + (in mono) color, via currentColor. Mirrors a lucide glyph's
   *  className contract so this is a drop-in. Default 'w-4 h-4'. */
  className?: string;
  /** Accessible label. Default derives from state. */
  title?: string;
}

// ── Palette ──────────────────────────────────────────────────────────────
// Single-letter keys keep the grid map readable. In `full` tone each maps to a
// real color; in `mono` tone every ink key collapses to currentColor and the
// skin/light fills drop out (so the punk reads as a one-color glyph).
const PALETTE_FULL: Record<string, string> = {
  K: '#1f2937', //  hair / flat-top + outline (near-black slate)
  G: '#4ade80', //  skin (Frankenstein green)
  D: '#16a34a', //  skin shadow (jaw / brow underside)
  B: '#e5e7eb', //  bolt metal (light steel)
  M: '#334155', //  bolt shadow / stitch ink
  E: '#111827', //  eyes / mouth ink
  S: '#15803d', //  brow scar stitch (dark green — reads as sewn skin)
};

// In mono, ink-ish keys → currentColor, everything else → transparent so the
// silhouette + features read in a single tint (the glyph contract).
const MONO_INK = new Set(['K', 'E', 'M']);

// ── Base grid (24×24) ─────────────────────────────────────────────────────
// '.' = empty. Rows are the flat-top head, face, jaw, and neck+bolts. Eyes and
// mouth are left as '.' here — the per-state overlay stamps them (the modular
// trait layer). Designed so the head is centered with a heavy flat-top and two
// neck bolts poking out the sides.
// prettier-ignore
const BASE: string[] = [
  '........................',
  '.....KKKKKKKKKKKKKK.....',  // flat-top hair, one row taller
  '.....KKKKKKKKKKKKKK.....',
  '.....KKKKKKKKKKKKKK.....',
  '....KKKKKKKKKKKKKKKK....',
  '....KGGGGGGGGGGGGGGK....',  // forehead
  '....KGGGGGGGGGGGGGGK....',
  '....KGSSGGGGGGGGSSGK....',  // stitched brow scar (dark stitch marks S)
  '....KGGGGGGGGGGGGGGK....',
  '....KGG..GGGG..GGGGK....',  // eye sockets (overlay fills)
  '....KGG..GGGG..GGGGK....',
  '....KGGGGGGGGGGGGGGK....',
  '....KGGGGGGGGGGGGGGK....',
  '....KGGGGGGGGGGGGGGK....',  // mouth region (overlay fills)
  '....KGGGGGGGGGGGGGGK....',
  '....KDGGGGGGGGGGGGDK....',  // jaw shadow
  '....KKDDDDDDDDDDDDKK....',
  'MB...KKKKKKKKKKKKKK...BM',  // BOLTS: metal stud (B) + shadow (M), on neck line
  'MB...KMMMMMMMMMMMMK...BM',  // neck band, bolts flush to the sides
  '.....KMGGGGGGGGGGMK.....',
  '.....KMMMMMMMMMMMMK.....',
  '......KKKKKKKKKKKK......',
  '........................',
  '........................',
];

// ── Per-state overlays ─────────────────────────────────────────────────────
// Each entry stamps pixels at [row, col] = key. Only eyes + mouth (+ brow tweak)
// change — the modular trait swap. Coordinates target the BASE eye sockets
// (cols 7-8 and 13-14, rows 9-10) and the mouth band (rows 13-14).
type Stamp = { r: number; c: number; k: string };

function overlayFor(state: FreddieLiveness): Stamp[] {
  const eyeCols = [7, 8, 13, 14];
  const eye = (r: number, k = 'E'): Stamp[] => eyeCols.map((c) => ({ r, c, k }));

  switch (state) {
    case 'paused': // closed eyes (a single ink line) + flat mouth
      return [
        ...eye(10),
        { r: 13, c: 9, k: 'E' }, { r: 13, c: 10, k: 'E' }, { r: 13, c: 11, k: 'E' },
        { r: 13, c: 12, k: 'E' }, { r: 13, c: 13, k: 'E' }, { r: 13, c: 14, k: 'E' },
      ];
    case 'thinking': // eyes up (row 9) + small neutral mouth
      return [
        ...eye(9),
        { r: 14, c: 10, k: 'E' }, { r: 14, c: 11, k: 'E' },
        { r: 14, c: 12, k: 'E' }, { r: 14, c: 13, k: 'E' },
      ];
    case 'acting': // full eyes (both rows) + open focus mouth
      return [
        ...eye(9), ...eye(10),
        { r: 13, c: 10, k: 'E' }, { r: 13, c: 13, k: 'E' },
        { r: 14, c: 10, k: 'E' }, { r: 14, c: 11, k: 'E' },
        { r: 14, c: 12, k: 'E' }, { r: 14, c: 13, k: 'E' },
      ];
    case 'waiting': // wide eyes (both rows) + upward mouth (looking AT you)
      return [
        ...eye(9), ...eye(10),
        { r: 14, c: 9, k: 'E' }, { r: 14, c: 14, k: 'E' },
        { r: 13, c: 10, k: 'E' }, { r: 13, c: 11, k: 'E' },
        { r: 13, c: 12, k: 'E' }, { r: 13, c: 13, k: 'E' },
      ];
    default: // idle — steady eyes (row 10) + calm flat mouth
      return [
        ...eye(10),
        { r: 14, c: 10, k: 'E' }, { r: 14, c: 11, k: 'E' },
        { r: 14, c: 12, k: 'E' }, { r: 14, c: 13, k: 'E' },
      ];
  }
}

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

  // Build the final grid: base + state overlay (overlay wins per cell).
  const grid = BASE.map((row) => row.split(''));
  for (const { r, c, k } of overlayFor(state)) {
    if (grid[r] && grid[r][c] !== undefined) grid[r][c] = k;
  }

  // Paused softens the whole punk (dormant); the color still comes from tone.
  const groupOpacity = state === 'paused' ? 0.55 : 1;

  const rects: React.ReactNode[] = [];
  for (let r = 0; r < grid.length; r++) {
    for (let c = 0; c < grid[r].length; c++) {
      const key = grid[r][c];
      if (key === '.') continue;
      let fill: string;
      if (isFull) {
        fill = PALETTE_FULL[key] ?? '#000';
      } else {
        // mono: only ink pixels paint (currentColor); skin/bolt/fill drop out
        // so the punk reads as a single-tint glyph. Empty cells already skipped.
        if (!MONO_INK.has(key)) continue;
        fill = 'currentColor';
      }
      rects.push(<rect key={`${r}-${c}`} x={c} y={r} width={1} height={1} fill={fill} />);
    }
  }

  // In mono, an ink-only render loses the head silhouette (skin doesn't paint).
  // Give mono a currentColor outline pass so the flat-top head still reads.
  // (The 'K' outline pixels ARE ink in mono, so the silhouette survives — no
  // extra pass needed; skin interior is simply empty, which reads as a clean
  // line-art punk. That's the intended mono look.)

  return (
    <svg
      viewBox="0 0 24 24"
      className={cn('shrink-0', className ?? 'w-4 h-4')}
      role="img"
      aria-label={title ?? labelFor(state)}
      shapeRendering="crispEdges"
      xmlns="http://www.w3.org/2000/svg"
    >
      <title>{title ?? labelFor(state)}</title>
      <g opacity={groupOpacity}>{rects}</g>
    </svg>
  );
}
