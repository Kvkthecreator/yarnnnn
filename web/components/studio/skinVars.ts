// The skin-variable parse (DESIGN-SYSTEMS.md §5/§6) — ONE parse, two readers.
// The Design tab reads the artifact's marked element (what THIS artifact
// wears); the manage panel reads the resolved skin_element (what the SYSTEM
// is). Both surface the kernel-consumed vocabulary first — those are the
// tokens that actually theme the chrome (§5 Move 1).

/** The kernel-consumed slot vocabulary (STUDIO_KERNEL_CSS v9, §5 Move 1).
 *  Categories, never a vendor's instances (ADR-222): the ink ramp steps the
 *  chrome reads, the radius + type scales, the semantic trio. */
export const KERNEL_CONSUMED_VARS = new Set([
  'ink', 'ink-06', 'ink-10', 'paper', 'muted', 'accent', 'deck-stage',
  'radius-sm', 'radius-md', 'radius-lg', 'radius-pill',
  'text-xs', 'text-sm', 'text-base', 'text-lg', 'text-xl',
  'text-2xl', 'text-3xl', 'text-4xl', 'text-5xl', 'fresh', 'danger', 'warn',
]);

export type SkinVar = { name: string; value: string };

/** Parse the custom properties a skin's CSS defines, kernel-consumed first.
 *  Collection is capped (a real export defines ~119; the tail is
 *  scaffolding); `limit` caps what the caller shows. */
export function parseSkinVars(css: string, limit = 12): SkinVar[] {
  const out: SkinVar[] = [];
  const rx = /--([a-z0-9-]+)\s*:\s*([^;}]+)[;}]/gi;
  const cap = Math.max(40, limit);
  let m;
  while ((m = rx.exec(css)) && out.length < cap) {
    out.push({ name: m[1], value: m[2].trim() });
  }
  return out
    .sort(
      (a, b) =>
        Number(KERNEL_CONSUMED_VARS.has(b.name)) -
        Number(KERNEL_CONSUMED_VARS.has(a.name)),
    )
    .slice(0, limit);
}

/** Every definition as a lookup map, LAST definition winning (the cascade's
 *  answer — a maps-bridge `:root` block is prepended, so the skin's own later
 *  declaration correctly overrides it here too). ADR-487 D3: the controls
 *  read this to paint themselves with the applied system's values. */
export function skinVarMap(css: string): Map<string, string> {
  const map = new Map<string, string>();
  const rx = /--([a-z0-9-]+)\s*:\s*([^;}]+)[;}]/gi;
  let m;
  while ((m = rx.exec(css))) {
    map.set(m[1], m[2].trim());
  }
  return map;
}

/** Resolve a var through the map, following one-level `var(--x)` indirection
 *  (the maps bridge emits exactly that shape); `fallback` = the kernel's
 *  literal, so an unskinned artifact paints its true default. */
export function resolveSkinVar(
  map: Map<string, string>,
  name: string,
  fallback: string,
): string {
  let value = map.get(name) ?? null;
  for (let hop = 0; value && hop < 3; hop += 1) {
    const ref = value.match(/^var\(\s*--([a-z0-9-]+)\s*(?:,\s*([^)]+))?\)$/i);
    if (!ref) break;
    value = map.get(ref[1]) ?? ref[2]?.trim() ?? null;
  }
  return value ?? fallback;
}

/** A value the theme row can show as a color swatch. */
export function isColorValue(value: string): boolean {
  return /^(#|rgb|hsl)/i.test(value);
}
