'use client';

/**
 * OnboardingModal — Two-step program-pick + platform-connect at signup.
 *
 * Authored by ADR-240 (Round 4 of the ADR-236 frontend cockpit
 * coherence pass). FE consumption layer for ADR-226 Phase 1 backend
 * infrastructure (POST /api/programs/activate).
 *
 * Two steps, never more:
 *
 *   Step 1 — Program: cards listing active programs from
 *     GET /api/programs/activatable, plus a "Start without a program"
 *     card. Selecting an active program calls
 *     POST /api/programs/activate and waits for the fork to complete.
 *     Deferred programs render disabled with "Coming soon" label.
 *
 *   Step 2 — Platform connection: appears only if Step 1 activated a
 *     program. Surfaces the platform integration the bundle needs for
 *     mandate's capabilities to bind (per ADR-207 capability gating).
 *     Skip is allowed; modal closes and operator lands in /chat where
 *     YARNNN's activation overlay walks them through authored files.
 *
 * Honest skip semantics per ADR-240 D4: skipping doesn't pretend the
 * operator made the optimal choice — it records the choice and proceeds.
 *
 * Idempotency gate is at the parent level (auth/callback): the modal
 * mounts only when activation_state === 'none' AND active_program_slug
 * is null. Re-signing-in or session resets do NOT re-prompt operators
 * who already picked.
 *
 * Singular Implementation: this is THE program-activation FE call site.
 * No other FE file references api.programs.activate. The OAuth flow for
 * Step 2's "Connect Alpaca" hand-off uses the same authorization API
 * the Settings page uses (api.integrations.authorize) — no duplication
 * of ConnectedIntegrationsSection logic.
 */

import { useEffect, useState } from 'react';
import { Loader2, ArrowRight, Sparkles, Check, AlertCircle } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';

interface ActivatableProgram {
  slug: string;
  title: string;
  tagline: string | null;
  status: 'active' | 'deferred';
  deferred: boolean;
  oracle: Record<string, unknown>;
  current_phase: string | null;
}

interface OnboardingModalProps {
  /** Called when the operator finishes (skipped or completed). Parent triggers redirect. */
  onComplete: () => void;
}

type Step = 1 | 2;

// Bundle slug → required platform connector. Mirrors the bundle MANIFEST's
// `activation_preconditions` declaration. Kept FE-side as a small map (the
// bundle reader's MANIFEST schema isn't exposed via API today; this is the
// minimum needed for Step 2's affordance). Future ADR can surface the
// preconditions through the activatable endpoint response if multi-bundle
// pressure surfaces.
const BUNDLE_PLATFORM_REQUIREMENTS: Record<string, { provider: string; label: string }> = {
  'alpha-trader': { provider: 'alpaca', label: 'Alpaca (paper or live trading)' },
  'alpha-commerce': { provider: 'lemonsqueezy', label: 'Lemon Squeezy' },
};

export function OnboardingModal({ onComplete }: OnboardingModalProps) {
  const [step, setStep] = useState<Step>(1);
  const [programs, setPrograms] = useState<ActivatableProgram[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activatingSlug, setActivatingSlug] = useState<string | null>(null);
  const [activatedSlug, setActivatedSlug] = useState<string | null>(null);
  const [activationError, setActivationError] = useState<string | null>(null);

  // Load activatable programs on mount.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.programs.listActivatable();
        if (cancelled) return;
        setPrograms(res.programs);
      } catch (err) {
        if (cancelled) return;
        const msg = err instanceof APIError ? err.message : 'Failed to load programs';
        setLoadError(msg);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSelectProgram = async (slug: string) => {
    setActivatingSlug(slug);
    setActivationError(null);
    try {
      await api.programs.activate(slug);
      setActivatedSlug(slug);
      // Step 2 only matters if the bundle has a platform requirement.
      const needsPlatform = !!BUNDLE_PLATFORM_REQUIREMENTS[slug];
      if (needsPlatform) {
        setStep(2);
      } else {
        // No platform precondition — operator is done.
        onComplete();
      }
    } catch (err) {
      const msg = err instanceof APIError ? err.message : 'Activation failed';
      setActivationError(msg);
    } finally {
      setActivatingSlug(null);
    }
  };

  const handleSkipProgram = () => {
    // Honest skip per ADR-240 D4: no fork, kernel-default workspace, redirect.
    onComplete();
  };

  const handleSkipPlatform = () => {
    // Operator picked a program but skipped platform. Bundle was already
    // forked at Step 1; YARNNN's activation overlay engages on first chat
    // and surfaces the capability gap honestly per ADR-240 D6.
    onComplete();
  };

  const handleConnectPlatform = (provider: string) => {
    // Hand off to OAuth flow — same API the Settings page uses. Returns
    // to /auth/callback?next=/chat&onboarding=continue (parent decides
    // re-mount). For now: simple authorize redirect; parent re-mounts
    // the modal at Step 2 if active_program_slug is set on next callback.
    // Per ADR-240 R3: query-param-driven re-entry is the correct shape;
    // implementation here delegates to the existing authorize endpoint.
    window.location.href = `/api/integrations/${provider}/authorize?redirect_to=${encodeURIComponent('/auth/callback?next=/chat&onboarding=continue')}`;
  };

  // ─── Render ──────────────────────────────────────────────────────────

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="w-full max-w-2xl mx-4 rounded-xl border border-border bg-card shadow-xl">
        <div className="px-6 py-5 border-b border-border">
          <h2 className="text-lg font-semibold">
            {step === 1 ? 'What are you running?' : 'One more step'}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {step === 1
              ? 'Pick a program to fork its starting substrate, or start without one.'
              : `Your ${activatedSlug ?? 'workspace'} mandate needs a platform connection to execute autonomously.`}
          </p>
        </div>

        <div className="px-6 py-5">
          {step === 1 ? (
            <Step1Body
              programs={programs}
              loadError={loadError}
              activatingSlug={activatingSlug}
              activationError={activationError}
              onSelect={handleSelectProgram}
              onSkip={handleSkipProgram}
            />
          ) : (
            <Step2Body
              activatedSlug={activatedSlug}
              onConnect={handleConnectPlatform}
              onSkip={handleSkipPlatform}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Step 1 ──────────────────────────────────────────────────────────

function Step1Body({
  programs,
  loadError,
  activatingSlug,
  activationError,
  onSelect,
  onSkip,
}: {
  programs: ActivatableProgram[] | null;
  loadError: string | null;
  activatingSlug: string | null;
  activationError: string | null;
  onSelect: (slug: string) => void;
  onSkip: () => void;
}) {
  if (loadError) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive flex items-center gap-2">
        <AlertCircle className="w-4 h-4 shrink-0" />
        <span>{loadError}</span>
      </div>
    );
  }

  if (programs === null) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {programs.map((p) => (
        <ProgramCard
          key={p.slug}
          program={p}
          activating={activatingSlug === p.slug}
          disabled={p.deferred || (!!activatingSlug && activatingSlug !== p.slug)}
          onSelect={() => onSelect(p.slug)}
        />
      ))}

      <button
        type="button"
        onClick={onSkip}
        disabled={!!activatingSlug}
        className="w-full text-left rounded-lg border border-dashed border-border bg-muted/10 px-4 py-3 hover:bg-muted/20 transition-colors disabled:opacity-50"
      >
        <div className="flex items-start gap-3">
          <Sparkles className="w-4 h-4 mt-0.5 text-muted-foreground/50 shrink-0" />
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium">Start without a program</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Run the kernel as-is. You can activate a program later from Settings.
            </p>
          </div>
          <ArrowRight className="w-4 h-4 text-muted-foreground/30 shrink-0 mt-0.5" />
        </div>
      </button>

      {activationError && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{activationError}</span>
        </div>
      )}
    </div>
  );
}

function ProgramCard({
  program,
  activating,
  disabled,
  onSelect,
}: {
  program: ActivatableProgram;
  activating: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={disabled || program.deferred}
      className="w-full text-left rounded-lg border border-border bg-card px-4 py-3 hover:bg-muted/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium">{program.title}</h3>
            {program.deferred && (
              <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted text-muted-foreground/70">
                Coming soon
              </span>
            )}
            {program.current_phase && !program.deferred && (
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
                {program.current_phase}
              </span>
            )}
          </div>
          {program.tagline && (
            <p className="text-xs text-muted-foreground mt-0.5">{program.tagline}</p>
          )}
        </div>
        {activating ? (
          <Loader2 className="w-4 h-4 animate-spin text-muted-foreground shrink-0 mt-0.5" />
        ) : (
          <ArrowRight className="w-4 h-4 text-muted-foreground/30 shrink-0 mt-0.5" />
        )}
      </div>
    </button>
  );
}

// ─── Step 2 ──────────────────────────────────────────────────────────

function Step2Body({
  activatedSlug,
  onConnect,
  onSkip,
}: {
  activatedSlug: string | null;
  onConnect: (provider: string) => void;
  onSkip: () => void;
}) {
  const requirement = activatedSlug ? BUNDLE_PLATFORM_REQUIREMENTS[activatedSlug] : null;

  if (!requirement) {
    // Defensive — should not reach Step 2 without a requirement; if we
    // do, treat as already-complete and let the operator skip cleanly.
    return (
      <div className="space-y-4">
        <div className="rounded-md border border-border bg-muted/10 px-4 py-3 text-sm">
          <Check className="w-4 h-4 text-green-600 inline mr-2" />
          Your workspace is ready.
        </div>
        <button
          type="button"
          onClick={onSkip}
          className="w-full rounded-md bg-foreground px-3 py-2 text-sm font-medium text-background hover:bg-foreground/90 transition-colors"
        >
          Continue to chat
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border bg-muted/10 px-4 py-3">
        <h3 className="text-sm font-medium">{requirement.label}</h3>
        <p className="text-xs text-muted-foreground mt-1">
          Required for {activatedSlug}'s mandate to execute autonomously. You can
          connect now or skip and connect later from Settings — either is fine.
        </p>
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => onConnect(requirement.provider)}
          className="flex-1 rounded-md bg-foreground px-3 py-2 text-sm font-medium text-background hover:bg-foreground/90 transition-colors"
        >
          Connect {requirement.label.split(' ')[0]}
        </button>
        <button
          type="button"
          onClick={onSkip}
          className="rounded-md border border-border px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-muted/20 transition-colors"
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}
