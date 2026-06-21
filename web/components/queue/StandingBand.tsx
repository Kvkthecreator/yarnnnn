'use client';

/**
 * StandingBand — the operation's STANDING OBLIGATION, rendered at the head of
 * the Notifications → "To do" pane (above the discrete action_proposals queue).
 *
 * ADR-350 (the settled-state sibling of ADR-351's in-flight render): the
 * Reviewer derives owed-vs-actual every wake (ADR-344 / DP30) and the operator
 * never saw it — it was diagnosed silently in the judgment narrative. This band
 * surfaces it as the deepest "to-do": what the operation is on the hook for, and
 * what its Reviewer is currently watching/flagging about reaching it.
 *
 * It RENDERS substrate the Reviewer already produces — it computes nothing and
 * reasons nothing (ADR-350 §5; ADR-344 §7 "no new primitive/schema/table"):
 *   Read-1 — the declared contract from governance/_expected_output.yaml
 *            (reuses the stable ADR-348 useExpectedOutput hook).
 *   Read-2 — the Reviewer's forward-looking standing intent from
 *            persona/standing_intent.md (ADR-284), rendered as PROSE AS-IS.
 *            That file is free-form Reviewer-authored markdown with NO schema,
 *            so the band does no field-parsing — whatever the Reviewer writes,
 *            it surfaces. This is forward-compatible by construction: if the
 *            posture layer ever reshapes that prose, this keeps rendering it.
 *
 * Framing (ADR-345 autonomy-as-witness): a standing item is the operation
 * SURFACING what it is tracking / what it owes — it is a thing to Decide, NOT
 * the agent being prevented from working. The agent always works the full job;
 * this band is where a standing decision is owed to the operator, consistent
 * with QUEUE = "decided, awaiting witness".
 *
 * Region discipline (ADR-320): the band READS persona-region substrate; the
 * operator never writes standing_intent.md here (Reviewer-authored). The only
 * write affordance is the link to DECLARE an expected-output contract, which
 * lands in governance via the existing ExpectedOutputCard (operator-writable).
 *
 * If BOTH reads are empty it renders nothing — no hollow band.
 */

import { useEffect, useState } from 'react';
import { Target, Eye } from 'lucide-react';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { useExpectedOutput, formatExpectedOutputSummary } from '@/lib/content-shapes/expected-output';
import { PERSONA_STANDING_INTENT_PATH, EXPECTED_OUTPUT_SETTINGS_HINT } from './standing-band.constants';

interface StandingIntentState {
  content: string | null;
  updatedAt: string | null;
  loading: boolean;
}

/**
 * Minimal read of persona/standing_intent.md. Prose-only — no parsing. Empty or
 * absent → content stays null and the band omits Read-2 entirely.
 */
function useStandingIntent(): StandingIntentState {
  const [state, setState] = useState<StandingIntentState>({ content: null, updatedAt: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const file = await api.workspace.getFile(`/workspace/${PERSONA_STANDING_INTENT_PATH}`);
        if (cancelled) return;
        const raw = (file?.content ?? '').trim();
        setState({ content: raw.length > 0 ? raw : null, updatedAt: file?.updated_at ?? null, loading: false });
      } catch {
        if (!cancelled) setState({ content: null, updatedAt: null, loading: false });
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return state;
}

export function StandingBand() {
  const { meta, loading: contractLoading } = useExpectedOutput();
  const intent = useStandingIntent();

  if (contractLoading && intent.loading) return null;

  const hasContract = !!meta && (!!meta.kind || !!meta.delivery_cadence);
  const summary = formatExpectedOutputSummary(meta);
  const hasIntent = !!intent.content;

  // Nothing to stand on — render nothing rather than a hollow band.
  if (!hasContract && !hasIntent) return null;

  return (
    <section
      aria-label="Standing obligation"
      className="mb-4 rounded-lg border border-border/70 bg-muted/30 p-4"
    >
      {/* Read-1 — the contract (what the operation owes). */}
      <div className="flex items-start gap-2">
        <Target className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
        <div className="min-w-0">
          <p className="text-xs font-medium text-foreground">Standing obligation</p>
          {hasContract ? (
            <p className="text-xs text-muted-foreground">{summary}</p>
          ) : (
            <p className="text-xs text-muted-foreground">
              No output contract declared — the Reviewer derives what it owes from budget + mandate.{' '}
              <span className="text-foreground/70">{EXPECTED_OUTPUT_SETTINGS_HINT}</span>
            </p>
          )}
        </div>
      </div>

      {/* Read-2 — the Reviewer's standing intent (what it's watching / flagging),
          rendered as prose as-is. The deepest to-do when a gap is open. */}
      {hasIntent && (
        <div className="mt-3 border-t border-border/60 pt-3">
          <div className="mb-1.5 flex items-center gap-1.5">
            <Eye className="h-3.5 w-3.5 text-muted-foreground" />
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              What your Reviewer is watching
            </p>
          </div>
          <div className="prose prose-sm max-w-none text-muted-foreground dark:prose-invert">
            <MarkdownRenderer content={intent.content!} compact />
          </div>
        </div>
      )}
    </section>
  );
}
