'use client';

/**
 * BeingIcon — a being's glyph, from the registry's `icon` field.
 *
 * ONE HOME, deliberately (extracted 2026-08-27, ADR-614). This map used to be
 * a local const in `AgentsSurface.tsx`. The new-chat door now lists beings too,
 * and copying the map there would have made a SECOND place to remember when
 * the registry gains a row — the exact drift its own comment warns about:
 * Supervisor rendered the fallback Bot for a day because the registry said
 * `clipboard-list` and the map had three keys.
 *
 * Mapped EXPLICITLY rather than resolved dynamically: lucide's dynamic import
 * pulls the whole icon set into the bundle, and a being whose icon is missing
 * should render the neutral fallback, not crash the surface.
 *
 * One entry per `icon` value in `api/services/agents_registry.AGENTS`. A being
 * whose icon is missing renders the fallback Bot glyph — silently, and looking
 * like every other unmapped being. A being's glyph is part of how the member
 * tells one desk from another, so a miss is a real defect, not a cosmetic one.
 * Add the row when the registry does.
 */

import { Bot, ClipboardList, Palette, PenTool } from 'lucide-react';
import { cn } from '@/lib/utils';

export const BEING_ICONS: Record<string, React.ElementType> = {
  'pen-tool': PenTool,             // authoring — decks and prose (ADR-602 D4)
  palette: Palette,                // generation — the metered pipeline
  'clipboard-list': ClipboardList, // the standing declaration — Supervisor's desk
};

export function BeingIcon({ icon, className }: { icon: string; className?: string }) {
  const Glyph = BEING_ICONS[icon] ?? Bot;
  return <Glyph className={cn('h-4 w-4 text-muted-foreground', className)} />;
}
