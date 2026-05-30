'use client';

/**
 * AuthorMandate — alpha-author program section (order: 1 per SURFACES.yaml).
 *
 * Standing-intent face: surfaces operator's MANDATE primary action +
 * autonomy posture + voice-fingerprint declaration state.
 *
 * Per ADR-283 step 3 + ADR-245 three-layer model: this is an L3
 * structured affordance composed from L2 content-shape parsers
 * (mandate.ts + autonomy.ts) reading L1 substrate via api.workspace.getFile.
 * Approach A — substrate-read only, no new backend routes.
 *
 * Graceful degradation: file missing → "not yet authored — start in chat";
 * file is template-only skeleton → operator-actionable empty state.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, Shield, ShieldAlert, ShieldCheck, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api/client';
import { parse as parseMandate, type MandateData } from '@/lib/content-shapes/mandate';
import { parseAutonomy, formatAutonomySummary, stripTierFrontmatter, type AutonomyMeta } from '@/lib/content-shapes/autonomy';

const MANDATE_PATH = '/workspace/context/_shared/MANDATE.md';
const VOICE_PATH = '/workspace/context/authored/_voice.md';
const AUTONOMY_PATH = '/workspace/context/_shared/_autonomy.yaml';

interface AuthorMandateState {
  mandate: MandateData | null;
  voiceDeclared: boolean;
  autonomy: AutonomyMeta | null;
  loading: boolean;
  error: string | null;
}

function autonomyIcon(level: string | undefined) {
  if (level === 'autonomous') return ShieldAlert;
  if (level === 'bounded') return ShieldCheck;
  return Shield;
}

function autonomyTone(level: string | undefined): string {
  if (level === 'autonomous') return 'text-amber-600';
  if (level === 'bounded') return 'text-emerald-600';
  return 'text-muted-foreground';
}

function detectVoiceDeclared(content: string | undefined): boolean {
  if (!content) return false;
  // _voice.md ships with template prompts in blockquotes and an `Example shapes`
  // section. We treat it as "declared" when there's non-template prose under
  // ## Declared voice fingerprint (i.e., at least one non-blockquote, non-heading
  // line that doesn't start with "Example shapes" or "> Author here").
  const declSection = content.match(/##\s+Declared voice fingerprint\s*\n([\s\S]*?)(?=\n##\s|$)/i);
  if (!declSection) return false;
  const body = declSection[1].trim();
  const meaningfulLines = body
    .split('\n')
    .map(l => l.trim())
    .filter(l => l.length > 0)
    .filter(l => !l.startsWith('>'))
    .filter(l => !l.startsWith('#'))
    .filter(l => !/^example shapes?/i.test(l));
  return meaningfulLines.length >= 2;
}

export function AuthorMandate() {
  const [state, setState] = useState<AuthorMandateState>({
    mandate: null,
    voiceDeclared: false,
    autonomy: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [mandateFile, voiceFile, autonomyFile] = await Promise.all([
          api.workspace.getFile(MANDATE_PATH).catch(() => null),
          api.workspace.getFile(VOICE_PATH).catch(() => null),
          api.workspace.getFile(AUTONOMY_PATH).catch(() => null),
        ]);
        if (cancelled) return;

        const mandate = mandateFile?.content ? parseMandate(mandateFile.content) : null;
        const voiceDeclared = detectVoiceDeclared(voiceFile?.content);
        const autonomy = autonomyFile?.content
          ? parseAutonomy(stripTierFrontmatter(autonomyFile.content))
          : null;

        setState({ mandate, voiceDeclared, autonomy, loading: false, error: null });
      } catch (err) {
        if (!cancelled) {
          setState(s => ({ ...s, loading: false, error: 'Failed to load mandate substrate' }));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.loading) {
    return (
      <section
        aria-label="Author mandate"
        className="rounded-lg border border-border bg-card p-5"
      >
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </section>
    );
  }

  const mandateEmpty = !state.mandate || state.mandate.isEmpty;
  const autonomyLevel = state.autonomy?.default_delegation;
  const AutonomyIcon = autonomyIcon(autonomyLevel);
  const autonomyText = state.autonomy
    ? formatAutonomySummary(state.autonomy)
    : 'autonomy not configured';

  return (
    <section
      aria-label="Author mandate"
      className="rounded-lg border border-border bg-card p-5"
    >
      <div className="mb-4 flex items-center justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-muted-foreground/70">
          Mandate
        </span>
        <span className={`flex items-center gap-1 ${autonomyTone(autonomyLevel)}`}>
          <AutonomyIcon className="h-3.5 w-3.5" />
          {autonomyText}
        </span>
      </div>

      {mandateEmpty ? (
        <div className="flex items-start gap-3 rounded-md bg-muted/40 p-4 text-sm">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          <div>
            <div className="font-medium">Mandate not yet authored</div>
            <div className="mt-1 text-muted-foreground">
              Open chat to declare your Primary Action — what authored corpus
              compounds in this workspace. YARNNN walks you through the template.
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div>
            <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
              Primary Action
            </div>
            <div className="text-base leading-snug">{state.mandate?.primaryAction}</div>
          </div>
          {state.mandate && state.mandate.successCriteria.length > 0 && (
            <div className="text-xs text-muted-foreground">
              {state.mandate.successCriteria.length} success criteria · {state.mandate.boundaryCount} boundary conditions
            </div>
          )}
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs">
        <span className="text-muted-foreground/70">
          Voice fingerprint:{' '}
          <span className={state.voiceDeclared ? 'text-foreground' : 'text-amber-600'}>
            {state.voiceDeclared ? 'declared' : 'not yet declared'}
          </span>
        </span>
        <Link
          href={`/context?path=${encodeURIComponent(MANDATE_PATH)}`}
          className="text-muted-foreground/70 hover:text-foreground hover:underline"
        >
          Open mandate →
        </Link>
      </div>
    </section>
  );
}
