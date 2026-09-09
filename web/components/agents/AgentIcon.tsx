'use client';

/**
 * AgentIcon — a agent's glyph, from the registry's `icon` field.
 *
 * ONE HOME, deliberately (extracted 2026-08-27, ADR-614). This map used to be
 * a local const in `AgentsSurface.tsx`. The new-chat door now lists agents too,
 * and copying the map there would have made a SECOND place to remember when
 * the registry gains a row — the exact drift its own comment warns about:
 * Supervisor (since deleted, ADR-639) rendered the fallback Bot for a day
 * because the registry said `clipboard-list` and the map had three keys.
 *
 * Mapped EXPLICITLY rather than resolved dynamically: lucide's dynamic import
 * pulls the whole icon set into the bundle, and an agent whose icon is missing
 * should render the neutral fallback, not crash the surface.
 *
 * One entry per `icon` value in `api/services/agents_registry.AGENTS`. An agent
 * whose icon is missing renders the fallback Bot glyph — silently, and looking
 * like every other unmapped being. A agent's glyph is part of how the member
 * tells one app from another, so a miss is a real defect, not a cosmetic one.
 * Add the row when the registry does.
 */

import { Bot, Feather, Palette, PenTool } from 'lucide-react';
import { cn } from '@/lib/utils';

export const BEING_ICONS: Record<string, React.ElementType> = {
  'pen-tool': PenTool,             // authoring — decks and prose (ADR-602 D4)
  palette: Palette,                // generation — the metered pipeline
  // 'clipboard-list' — Supervisor's glyph, DELETED with the agent (ADR-639).
  feather: Feather,                // published prose — Blogger's pane (ADR-627)
};

/**
 * The AGENT accent — ADR-641.
 *
 * ONE hue for the class, not one per agent. `authorAccent` (attribution.ts)
 * already resolves an agent-authored revision to `violet-400`, so a member who
 * sees a violet dot beside a file in Files meets the same violet on the agent's
 * own row. Reusing it costs nothing and closes the drift; inventing a second
 * agent palette here would make the roster and the attribution dots disagree
 * about what an agent looks like.
 *
 * NOT keyed per-agent, and not keyed on the agent's APP. Since ADR-601 D1 an
 * agent may serve several apps (Editor → Slides + Text), so an app-derived hue
 * has no single answer for exactly the many-to-one case that ADR made free —
 * it would have to pick one app and silently misname the others. The APP chips
 * on the same row already carry the per-app hues (`resolveSurfaceAccent`);
 * the glyph says "an agent", the chips say "these apps".
 */
const AGENT_ACCENT = 'text-violet-500';

export function AgentIcon({ icon, className }: { icon: string; className?: string }) {
  const Glyph = BEING_ICONS[icon] ?? Bot;
  return <Glyph className={cn('h-4 w-4', AGENT_ACCENT, className)} />;
}

/**
 * AgentMark — an agent's FACE if it has one, its glyph if it does not.
 *
 * ADR-641 amendment. The Agents page and the roster both drew
 * `<div class="…rounded-full bg-muted"><AgentIcon/></div>` — the same disc,
 * spelled twice, and neither could show a picture. One component now answers
 * "how does this agent appear?" so the face reaches every roster site at once
 * and a third site cannot quietly render only the glyph.
 *
 * The FACE (an uploaded picture, the 2026-07-16 ruling) is the identity; the
 * GLYPH is the fallback, and it keeps the class violet because a glyph is a
 * class marker, not a face. `AgentFace` is deliberately NOT reused here: it
 * falls back to an INITIAL, which is the right fallback in a conversation
 * (where a letter reads as a speaker) and the wrong one on the roster (where
 * the craft glyph says more than "B").
 */
export function AgentMark({
  icon,
  avatarUrl,
  name,
  size = 'md',
  className,
}: {
  icon: string;
  avatarUrl?: string | null;
  name: string;
  size?: 'sm' | 'md';
  className?: string;
}) {
  const box = size === 'sm' ? 'h-8 w-8' : 'h-10 w-10';
  if (avatarUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={avatarUrl}
        alt={name}
        className={cn('shrink-0 rounded-full object-cover', box, className)}
      />
    );
  }
  return (
    <span className={cn('grid shrink-0 place-items-center rounded-full bg-muted', box, className)}>
      <AgentIcon icon={icon} />
    </span>
  );
}
