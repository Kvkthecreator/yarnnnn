'use client';

/**
 * MandateStrip — Cockpit pane #6 in the six-question cockpit framing
 * (2026-04-28 reshape). The pane that answers "what's my standing intent
 * right now?"
 *
 * Universal across program bundles. Every delegation product has a
 * Mandate (ADR-207); this strip surfaces it as a one-line summary at the
 * top of the cockpit so the operator sees their own delegation contract
 * on every visit.
 *
 * Source: /workspace/context/_shared/MANDATE.md frontmatter (preferred) or
 * the first non-empty heading-line of the body. The strip is read-only;
 * editing the Mandate is R3 Substrate (Files tab inline editor).
 *
 * Empty state: when MANDATE.md is still skeleton (operator hasn't authored
 * yet), the strip renders an authoring prompt — the only cockpit pane
 * with a chat-seeding affordance, because absent Mandate is the one
 * substrate gap the operator MUST close before any other loop component
 * is meaningful.
 */

import { useEffect, useState } from 'react';
import { Compass } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api/client';
import { useCockpit } from './CockpitContext';

const MANDATE_PATH = '/workspace/context/_shared/MANDATE.md';

interface MandateMeta {
  primary_action?: string;
  posture?: string;
  cadence?: string;
}

function parseMandate(content: string): { meta: MandateMeta; firstLine: string | null; isSkeleton: boolean } {
  // YAML frontmatter parse — minimal, two scalar fields max
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  const meta: MandateMeta = {};
  let body = content;
  if (fm) {
    body = content.slice(fm[0].length);
    for (const line of fm[1].split('\n')) {
      const m = line.match(/^([a-z_]+):\s*(.*)$/);
      if (!m) continue;
      const k = m[1].trim();
      const v = m[2].trim().replace(/^['"]|['"]$/g, '');
      if (k === 'primary_action') meta.primary_action = v;
      if (k === 'posture') meta.posture = v;
      if (k === 'cadence') meta.cadence = v;
    }
  }
  // Skeleton detection: empty body OR body is just a placeholder heading
  const trimmed = body.trim();
  const isSkeleton = !trimmed || /^#\s*MANDATE\s*$/i.test(trimmed) || /^_authored at workspace activation/i.test(trimmed);
  // First line: prefer summary-shape — first non-heading non-blank line
  let firstLine: string | null = null;
  for (const line of body.split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#') || t.startsWith('---')) continue;
    firstLine = t;
    break;
  }
  return { meta, firstLine, isSkeleton };
}

export function MandateStrip() {
  const [content, setContent] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const { onOpenChatDraft } = useCockpit();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const file = await api.workspace.getFile(MANDATE_PATH);
        if (!cancelled) setContent(file?.content ?? '');
      } catch {
        if (!cancelled) setContent('');
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (!loaded) return null;

  const { meta, firstLine, isSkeleton } = parseMandate(content ?? '');

  if (isSkeleton) {
    return (
      <button
        onClick={() => onOpenChatDraft('Help me author my workspace MANDATE.md — what should my Primary Action be?')}
        className="flex w-full items-center gap-2 rounded-md border border-dashed border-amber-300 bg-amber-50/60 px-3 py-2 text-left text-xs text-amber-900 hover:bg-amber-50"
      >
        <Compass className="h-3.5 w-3.5 shrink-0" />
        <span className="flex-1">
          <span className="font-medium">Mandate not authored yet.</span>
          {' '}Click to draft your standing intent in chat.
        </span>
        <span className="font-medium underline-offset-4 hover:underline">Author →</span>
      </button>
    );
  }

  // Rendered, populated case: one-line strip with mode+cadence inline + link to file
  const summary = meta.primary_action ?? firstLine ?? 'Mandate authored';
  const tags: string[] = [];
  if (meta.posture) tags.push(meta.posture);
  if (meta.cadence) tags.push(meta.cadence);

  return (
    <Link
      href={`/context?path=${encodeURIComponent(MANDATE_PATH)}`}
      className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-xs text-muted-foreground hover:border-foreground/20 hover:text-foreground"
    >
      <Compass className="h-3.5 w-3.5 shrink-0 text-foreground/60" />
      <span className="flex-1 line-clamp-1 font-medium text-foreground">{summary}</span>
      {tags.length > 0 && (
        <span className="shrink-0 text-[11px] text-muted-foreground/70">
          {tags.join(' · ')}
        </span>
      )}
    </Link>
  );
}
