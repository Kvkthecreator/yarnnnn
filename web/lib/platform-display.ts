/**
 * Platform display registry (ADR-266 D6).
 *
 * Maps the `requires_platform` slug from a capability gap (which mirrors
 * `platform_connections.platform`) to operator-facing display strings.
 * Closes the leak where `trading requires trading` showed up on /workspace
 * — internal platform slugs are not user copy.
 *
 * Single source of truth. Imported by ProgramLifecycleDrawer and any
 * other surface that names a capability gap.
 *
 * Adding a platform: add a row here AND add the corresponding
 * platform_connections.platform value to the entry.
 */

export interface PlatformDisplay {
  /** What the operator sees (e.g. "Alpaca"). */
  name: string;
  /** Short verb-noun phrase explaining what connecting unlocks. */
  capability: string;
  /** Where to send the operator to connect. Today: /connectors. */
  href: string;
}

const REGISTRY: Record<string, PlatformDisplay> = {
  trading: {
    name: 'Alpaca',
    capability: 'Trading account access',
    href: '/connectors',
  },
  commerce: {
    name: 'Lemon Squeezy',
    capability: 'Commerce + revenue data',
    href: '/connectors',
  },
  slack: {
    name: 'Slack',
    capability: 'Slack workspace access',
    href: '/connectors',
  },
  notion: {
    name: 'Notion',
    capability: 'Notion workspace access',
    href: '/connectors',
  },
  github: {
    name: 'GitHub',
    capability: 'GitHub repo access',
    href: '/connectors',
  },
};

const FALLBACK: PlatformDisplay = {
  name: 'Platform',
  capability: 'Platform connection',
  href: '/connectors',
};

/** Resolve the operator-facing display info for a platform slug.
 *  Falls back to a generic label when the slug is unknown — never
 *  surfaces the raw slug. */
export function getPlatformDisplay(slug: string): PlatformDisplay {
  return REGISTRY[slug] ?? { ...FALLBACK, name: slug.charAt(0).toUpperCase() + slug.slice(1) };
}
