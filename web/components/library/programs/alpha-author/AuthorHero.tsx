'use client';

/**
 * AuthorHero — alpha-author's ground-truth hero (Home slot #2, "what's
 * working").
 *
 * Six-slot contract (ADR-312 D2 + the 2026-06-04 amendment): a program
 * declares exactly ONE hero (slot #2) + ONE entity list (slot #4). The
 * hero answers the single human question "is this working?" — for an
 * author, that is **does my shipped writing still sound like me?** Voice
 * consistency is the headline; coherence + cadence are quiet support.
 *
 * This merges the former AuthorCorpus + AuthorVoice (two overlapping
 * metric cards that both surfaced "voice accuracy" and split the signal).
 * Singular signal, plain language — no metric wall of "0 / —".
 *
 * Substrate (unchanged from the merged components):
 *   _voice.md   → is the voice declared? how many style "tells"?
 *   _signal.md  → 30d voice-audit accuracy (the ground-truth number) +
 *                 audits run + coherence accuracy
 */

import { useEffect, useState } from 'react';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { Loader2, ShieldCheck, AlertTriangle, MessageSquare } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useHome } from '../../HomeContext';

const VOICE_PATH = '/workspace/operation/authored/_voice.md';
const SIGNAL_PATH = '/workspace/operation/authored/_signal.md';

interface HeroState {
  voiceDeclared: boolean;
  styleTells: number; // positive markers + anti-patterns = the fingerprint size
  // Ground-truth accuracy of the Reviewer's voice audits over 30 days. The
  // single "is it working?" number. Null until calibration has run.
  voiceAccuracy30d: number | null;
  auditsRun30d: number | null;
  coherenceAccuracy30d: number | null;
  signalStarted: boolean;
}

function extractSection(content: string, heading: string): string {
  const re = new RegExp(`##\\s+${heading}\\s*\\n([\\s\\S]*?)(?=\\n##\\s|$)`, 'i');
  const m = content.match(re);
  return m ? m[1].trim() : '';
}

function countBullets(body: string): number {
  return body
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => /^[-*]\s+/.test(l))
    .filter((l) => !l.toLowerCase().includes('example shape'))
    .filter((l) => !l.startsWith('> '))
    .length;
}

function parseVoice(content: string | undefined): { declared: boolean; tells: number } {
  if (!content) return { declared: false, tells: 0 };
  const positive = countBullets(extractSection(content, 'Pattern markers \\(positive\\)'));
  const anti = countBullets(extractSection(content, 'Anti-patterns \\(negative\\)'));
  const declSection = extractSection(content, 'Declared voice fingerprint');
  const declLines = declSection
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && !l.startsWith('>') && !l.startsWith('#'))
    .filter((l) => !/^example shapes?/i.test(l));
  const declared = declLines.length >= 2 || positive > 0 || anti > 0;
  return { declared, tells: positive + anti };
}

function parseSignal(content: string | undefined): {
  voiceAccuracy: number | null;
  audits: number | null;
  coherence: number | null;
} {
  if (!content) return { voiceAccuracy: null, audits: null, coherence: null };
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!fm) return { voiceAccuracy: null, audits: null, coherence: null };
  const body = fm[1];
  const va = body.match(/voice_audit_accuracy_30d:\s*([0-9.]+)/);
  const co = body.match(/continuity_audit_accuracy_30d:\s*([0-9.]+)/);
  // audits_total under the 30d window — grab the first 30d audits_total.
  const au = body.match(/30d:[\s\S]*?audits_total:\s*(\d+)/);
  return {
    voiceAccuracy: va ? parseFloat(va[1]) : null,
    coherence: co ? parseFloat(co[1]) : null,
    audits: au ? parseInt(au[1], 10) : null,
  };
}

function pct(value: number | null): string {
  if (value === null) return '—';
  return `${Math.round(value * 100)}%`;
}

export function AuthorHero() {
  const { onOpenChatDraft } = useHome();
  const [state, setState] = useState<HeroState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [voiceFile, signalFile] = await Promise.all([
          api.workspace.getFile(VOICE_PATH).catch(() => null),
          api.workspace.getFile(SIGNAL_PATH).catch(() => null),
        ]);
        if (cancelled) return;
        const voice = parseVoice(voiceFile?.content);
        const signal = parseSignal(signalFile?.content);
        setState({
          voiceDeclared: voice.declared,
          styleTells: voice.tells,
          voiceAccuracy30d: signal.voiceAccuracy,
          auditsRun30d: signal.audits,
          coherenceAccuracy30d: signal.coherence,
          signalStarted: !!signalFile?.content,
        });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <section aria-label="Voice" className="rounded-lg border border-border/60 bg-card/50 p-5">
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </section>
    );
  }
  if (!state) return null;

  // ── Plain-language headline ──────────────────────────────────────────
  // The single "is this working?" read. Three honest states:
  //   1. Voice not described yet → invite to describe it (the whole program
  //      hinges on this; say so plainly).
  //   2. Voice described, no audits yet → "watching" (set up, nothing to
  //      score yet).
  //   3. Voice described + audits run → the accuracy number, in words.
  let headline: string;
  let sub: string;
  let tone: 'ok' | 'warn' | 'idle';
  let Icon = ShieldCheck;

  if (!state.voiceDeclared) {
    headline = 'Describe your writing voice';
    sub = "So YARNNN can catch anything you ship that doesn't sound like you.";
    tone = 'warn';
    Icon = AlertTriangle;
  } else if (state.voiceAccuracy30d === null) {
    headline = 'Watching your voice';
    sub = `${state.styleTells} style tells described · nothing shipped to check against yet`;
    tone = 'idle';
    Icon = ShieldCheck;
  } else {
    const acc = Math.round(state.voiceAccuracy30d * 100);
    const onPoint = acc >= 80;
    headline = onPoint ? 'Your voice is holding' : 'Your voice is drifting';
    sub = `${pct(state.voiceAccuracy30d)} of shipped pieces sounded like you (last 30 days)`;
    tone = onPoint ? 'ok' : 'warn';
    Icon = onPoint ? ShieldCheck : AlertTriangle;
  }

  const toneClasses =
    tone === 'ok'
      ? 'text-emerald-600'
      : tone === 'warn'
      ? 'text-amber-600'
      : 'text-muted-foreground';

  return (
    <section aria-label="Voice" className="rounded-lg border border-border/60 bg-card/50 p-5">
      {/* Hero headline — the one signal */}
      <div className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${toneClasses}`} />
        <div className="flex-1 min-w-0">
          <h2 className="text-lg font-semibold text-foreground">{headline}</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">{sub}</p>
        </div>
        {!state.voiceDeclared && (
          <button
            type="button"
            onClick={() =>
              onOpenChatDraft(
                'Help me describe my writing voice — the patterns that make my prose sound like me, and the AI-slop patterns to avoid. Save it so the agent can audit new pieces against it.',
              )
            }
            className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted transition-colors"
          >
            <MessageSquare className="h-3.5 w-3.5" />
            Describe it
          </button>
        )}
      </div>

      {/* Quiet support — coherence + audit volume, only when there's signal */}
      {state.signalStarted && state.voiceDeclared && (
        <div className="mt-4 flex items-center gap-6 border-t border-border/40 pt-3 text-xs text-muted-foreground">
          {state.auditsRun30d !== null && (
            <span>
              <span className="font-medium text-foreground tabular-nums">{state.auditsRun30d}</span>{' '}
              pieces checked (30d)
            </span>
          )}
          {state.coherenceAccuracy30d !== null && (
            <span>
              Story stayed consistent{' '}
              <span className="font-medium text-foreground tabular-nums">
                {pct(state.coherenceAccuracy30d)}
              </span>{' '}
              of the time
            </span>
          )}
          <SurfaceLink
            to="files"
            params={{ path: VOICE_PATH }}
            className="ml-auto hover:text-foreground hover:underline"
          >
            Your voice →
          </SurfaceLink>
        </div>
      )}
    </section>
  );
}
