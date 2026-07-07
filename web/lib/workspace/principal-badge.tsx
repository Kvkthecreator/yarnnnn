'use client';

/**
 * Principal badge — the ONE visual primitive for "who acted", shared across
 * the Flow timeline, the Notifications panel, and the chat thread (2026-06-30).
 *
 * This is the *visual* half of the ADR-388 attribution module. The pure logic
 * (classify / label / accent / mcp-host) lives in `attribution.ts` (React-free,
 * server-safe). This file adds the ICON dimension on top of that single source
 * of truth and composes a `<PrincipalBadge>` — a tinted icon chip + the
 * canonical label — so every surface renders the same actor identically.
 *
 * Scope discipline (the operator's "registry + shared primitives, not a
 * god-component" decision): this gives the surfaces a shared ICON + LABEL
 * primitive to consume. It does NOT impose a row layout — Flow, Notifications,
 * and chat keep their own row structure; they just render this badge where the
 * actor goes. (The standard design-system move: shared primitives, per-surface
 * layout.)
 *
 * Icon policy (ADR-379 "brand SVG where known, glyph fallback"): the two MCP
 * hosts an operator actually sees — Claude + ChatGPT — get their real brand
 * marks; every other actor class (and the long-tail MCP hosts) uses a tinted
 * lucide glyph. The mark/glyph is tinted with the per-class accent the
 * attribution module already defines, so the one-glance dot story scales up to
 * a full badge without inventing a second color vocabulary.
 */

import type { ReactNode } from 'react';
import {
  Bot,
  ShieldCheck,
  Sparkles,
  UserCircle,
  Plug,
  Cog,
  Wrench,
} from 'lucide-react';
import { getMcpHostIcon } from '@/components/ui/PlatformIcons';
import {
  authorClass,
  authorAccent,
  formatAuthorLabel,
  formatAuthorLabelOrSystem,
  mcpHostId,
  type AuthorClass,
} from './attribution';
import { cn } from '@/lib/utils';

/**
 * The actor's icon for a given `authored_by`. Brand mark where known (the two
 * MCP hosts), tinted lucide glyph otherwise. `className` controls the glyph
 * size + color (callers pass the accent text-color); brand marks take
 * currentColor too, so the same className tints both.
 */
export function principalIcon(
  authored_by: string | null | undefined,
  className?: string,
): ReactNode {
  const cls = authorClass(authored_by);
  if (cls === 'mcp') {
    const host = mcpHostId(authored_by);
    const brand = host ? getMcpHostIcon(host, className) : null;
    // Long-tail MCP hosts (Gemini/Cursor/…/unknown) have no brand mark → glyph.
    return brand ?? <Bot className={className} />;
  }
  switch (cls) {
    case 'you':
      return <UserCircle className={className} />;
    // Lane embodiment (ADR-411) — the actor is the human member (acting
    // through a model transport), so the human glyph, in the member teal.
    case 'member':
      return <UserCircle className={className} />;
    case 'reviewer':
      return <ShieldCheck className={className} />;
    case 'yarnnn':
      return <Sparkles className={className} />;
    case 'agent':
      return <Bot className={className} />;
    case 'platform':
      return <Plug className={className} />;
    case 'specialist':
      return <Wrench className={className} />;
    case 'system':
    case 'unknown':
    default:
      return <Cog className={className} />;
  }
}

/**
 * The accent TEXT color (mirrors `authorAccent`'s bg-* dot, as a text-*) so a
 * brand mark / glyph reads in the actor's color. Kept here (not in the
 * React-free attribution.ts) because it's purely presentational.
 */
function accentText(cls: AuthorClass): string {
  switch (cls) {
    case 'you':
      return 'text-primary';
    // Indigo, mirroring authorAccent's ADR-381 relabel (the prior rose read
    // as alarm); keep the two accent maps in lockstep.
    case 'reviewer':
      return 'text-indigo-400';
    case 'yarnnn':
      return 'text-sky-400';
    case 'mcp':
      return 'text-amber-500';
    case 'member':
      return 'text-teal-400';
    case 'agent':
      return 'text-violet-400';
    case 'platform':
      return 'text-cyan-500';
    default:
      return 'text-muted-foreground/60';
  }
}

export interface PrincipalBadgeProps {
  /** The ADR-209 `authored_by` string. */
  authoredBy: string | null | undefined;
  /** Render the label text next to the icon (default true). When false, just
   *  the icon chip — for dense rows that show the label elsewhere. */
  showLabel?: boolean;
  /** When there is no attribution, render "System" rather than nothing
   *  (glance contexts). Default false → label may be null and is omitted. */
  fallbackToSystem?: boolean;
  /** Icon size in px (square). Default 14. */
  size?: number;
  className?: string;
}

/**
 * `<PrincipalBadge authoredBy="yarnnn:mcp:chatgpt" />` → the ChatGPT mark in
 * amber + "ChatGPT (via MCP)". The single composition every surface uses.
 */
export function PrincipalBadge({
  authoredBy,
  showLabel = true,
  fallbackToSystem = false,
  size = 14,
  className,
}: PrincipalBadgeProps) {
  const cls = authorClass(authoredBy);
  const label = fallbackToSystem
    ? formatAuthorLabelOrSystem(authoredBy)
    : formatAuthorLabel(authoredBy);
  const accent = accentText(cls);
  const dim = { width: size, height: size };

  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <span className={cn('inline-flex shrink-0', accent)} style={dim} aria-hidden>
        {principalIcon(authoredBy, 'w-full h-full')}
      </span>
      {showLabel && label && (
        <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
          {label}
        </span>
      )}
    </span>
  );
}
