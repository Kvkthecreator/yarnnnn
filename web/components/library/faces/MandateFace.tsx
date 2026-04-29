'use client';

/**
 * MandateFace — face #1 of the four-face cockpit (ADR-228).
 *
 * Renders the operator's standing intent and autonomy posture as a single
 * dense face. This is what the operator walked up to ask: "what is this
 * workspace for, and what am I letting it do on my behalf?"
 *
 * Sources:
 *   - /workspace/context/_shared/MANDATE.md (ADR-207) — standing intent
 *   - /workspace/context/_shared/AUTONOMY.md (ADR-217) — autonomy posture
 *   - active bundle's MANIFEST.yaml — current_phase, phase label
 *
 * Skeleton state: when MANDATE is absent, the face renders destructive-tinted
 * with a single CTA to author. The other faces still render — the operator
 * is allowed to look at platform balance and recent activity even when
 * mandate is incomplete; what they cannot do without mandate is fairly
 * judge whether the operation is on track.
 *
 * Bundle override surface: the autonomy summary formatter (e.g., trader's
 * "Bounded autonomy on paper · $100/$500 day budget remaining") is bundle-
 * supplied. Kernel default reads `domains.default.level` from AUTONOMY.md
 * frontmatter and renders that label only.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Compass } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useComposition } from '@/lib/compositor';
import {
  AUTONOMY_PATH,
  parseAutonomy,
  formatAutonomySummary,
} from '@/lib/autonomy';
import { useCockpit } from '../CockpitContext';

const MANDATE_PATH = '/workspace/context/_shared/MANDATE.md';

interface MandateMeta {
  primary_action?: string;
  posture?: string;
  cadence?: string;
}

/**
 * Strip markdown noise from a line: blockquote prefixes, HTML comments,
 * trailing whitespace. Returns null if the line is decorative-only after
 * stripping.
 */
function stripLine(raw: string): string | null {
  let line = raw.replace(/^\s*>+\s?/, '').trim();
  if (!line) return null;
  // Skip pure HTML comments
  if (line.startsWith('<!--') && line.endsWith('-->')) return null;
  // Skip horizontal rules
  if (/^[-*_]{3,}$/.test(line)) return null;
  return line;
}

function parseMandate(content: string): {
  meta: MandateMeta;
  intent: string[];
  isSkeleton: boolean;
} {
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
  const trimmed = body.trim();
  const isSkeleton =
    !trimmed ||
    /^#\s*MANDATE\s*$/i.test(trimmed) ||
    /^_authored at workspace activation/i.test(trimmed);

  // Walk past leading headings + comments, collect prose paragraph
  // (consecutive non-blank, non-heading lines) for the intent block.
  const lines = body.split('\n');
  const intentLines: string[] = [];
  let inBlock = false;
  for (const raw of lines) {
    const t = raw.trim();
    if (!t) {
      if (inBlock) break; // blank line ends the first prose block
      continue;
    }
    if (t.startsWith('#')) {
      if (inBlock) break;
      continue;
    }
    if (t.startsWith('---')) continue;
    const stripped = stripLine(raw);
    if (!stripped) {
      if (inBlock) break;
      continue;
    }
    intentLines.push(stripped);
    inBlock = true;
  }
  return { meta, intent: intentLines, isSkeleton };
}

// `parseAutonomy` + `formatAutonomySummary` + `AutonomyMeta` lifted to
// `@/lib/autonomy` by ADR-238. Singular Implementation: do not re-inline
// here even temporarily.

export function MandateFace() {
  const { onOpenChatDraft } = useCockpit();
  const { data: composition } = useComposition();
  const phase = composition.active_bundles[0]?.current_phase_label ?? null;

  const [mandate, setMandate] = useState<string | null>(null);
  const [autonomy, setAutonomy] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [mandateR, autonomyR] = await Promise.allSettled([
        api.workspace.getFile(MANDATE_PATH),
        api.workspace.getFile(AUTONOMY_PATH),
      ]);
      if (cancelled) return;
      setMandate(mandateR.status === 'fulfilled' ? mandateR.value?.content ?? '' : '');
      setAutonomy(autonomyR.status === 'fulfilled' ? autonomyR.value?.content ?? '' : '');
      setLoaded(true);
    })();
    return () => { cancelled = true; };
  }, []);

  if (!loaded) return null;

  const { meta, intent, isSkeleton } = parseMandate(mandate ?? '');
  const autonomyMeta = parseAutonomy(autonomy ?? '');
  const autonomyLine = autonomy ? formatAutonomySummary(autonomyMeta) : 'No autonomy declared';

  const headerParts: string[] = [];
  if (phase) headerParts.push(phase);
  headerParts.push(autonomyLine);

  if (isSkeleton) {
    return (
      <section
        aria-label="Mandate"
        className="rounded-lg border-2 border-amber-300 bg-amber-50/60 p-5"
      >
        <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-amber-900">
          <Compass className="h-3.5 w-3.5" />
          Mandate
        </div>
        <p className="mb-3 text-sm font-medium text-amber-900">
          Delegation contract incomplete — author your mandate before relying on
          the operation.
        </p>
        <p className="mb-4 text-xs text-amber-900/80">
          Mandate declares what this workspace is for: the primary action you've
          delegated, the success criteria, and the boundaries you want enforced.
          Autonomy declares what the system is permitted to do without your
          approval. Both are read at every cockpit load.
        </p>
        <button
          onClick={() =>
            onOpenChatDraft(
              "Help me author my workspace MANDATE.md — what should my Primary Action be?",
            )
          }
          className="rounded-md bg-amber-900 px-3 py-1.5 text-xs font-medium text-amber-50 hover:bg-amber-900/90"
        >
          Draft mandate in chat →
        </button>
      </section>
    );
  }

  const tags: string[] = [];
  if (meta.posture) tags.push(meta.posture);
  if (meta.cadence) tags.push(meta.cadence);

  return (
    <section
      aria-label="Mandate"
      className="rounded-lg border border-border bg-card p-5"
    >
      <div className="mb-3 flex items-center justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-muted-foreground/70">
          Mandate
        </span>
        <span className="text-muted-foreground/60">
          {headerParts.join(' · ')}
        </span>
      </div>
      <Link
        href={`/context?path=${encodeURIComponent(MANDATE_PATH)}`}
        className="block"
      >
        {meta.primary_action ? (
          <p className="text-base font-medium leading-snug text-foreground hover:underline">
            {meta.primary_action}
          </p>
        ) : intent.length > 0 ? (
          <div className="space-y-1 text-sm leading-relaxed text-foreground hover:underline">
            {intent.slice(0, 4).map((line, idx) => (
              <p key={idx}>{line}</p>
            ))}
          </div>
        ) : (
          <p className="text-base font-medium leading-snug text-foreground hover:underline">
            Mandate authored
          </p>
        )}
      </Link>
      {tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-muted-foreground">
          {tags.map((tag) => (
            <span key={tag} className="rounded-sm bg-muted px-1.5 py-0.5">
              {tag}
            </span>
          ))}
        </div>
      )}
      <div className="mt-4 flex gap-3 text-[11px] text-muted-foreground/70">
        <Link
          href={`/context?path=${encodeURIComponent(MANDATE_PATH)}`}
          className="underline-offset-4 hover:text-foreground hover:underline"
        >
          MANDATE.md
        </Link>
        <Link
          href={`/context?path=${encodeURIComponent(AUTONOMY_PATH)}`}
          className="underline-offset-4 hover:text-foreground hover:underline"
        >
          AUTONOMY.md
        </Link>
      </div>
    </section>
  );
}
