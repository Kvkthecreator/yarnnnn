'use client';

/**
 * WorkspaceConfigSection — body of /workspace.
 *
 * ADR-266 reshape:
 *   D1: program lifecycle collapses into ProgramLifecycleDrawer at bottom
 *       (default-collapsed, single-line summary). Daily-relevant content
 *       (the four concept cards) gets full page weight.
 *   D2: WorkspacePostureLine under the page title resets operator
 *       expectation — chat is the edit surface.
 *   D8: single getSetupBundle() call replaces 7 round-trips. Cards
 *       receive parsed data + lastRevision via props (singular implementation
 *       discipline — prop presence is the only signal that selects between
 *       data-prop and self-fetch paths).
 *
 * No content is editable inline; chat is the edit surface (ADR-244 D7).
 *
 * See docs/design/WORKSPACE-COMPONENTS.md (v1.1) for the component catalog.
 */

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2, AlertCircle, Sparkles, ArrowRight } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { useNarrative } from '@/contexts/NarrativeContext';
import { MandateCard } from '@/components/workspace-concepts/MandateCard';
import { DelegationCard } from '@/components/workspace-concepts/DelegationCard';
import { PrinciplesCard } from '@/components/workspace-concepts/PrinciplesCard';
import { IdentityBrandCard } from '@/components/workspace-concepts/IdentityBrandCard';
import { parse as parseMandate } from '@/lib/content-shapes/mandate';
import { parse as parsePrinciples, parseYaml as parsePrinciplesYaml, mergeThresholds } from '@/lib/content-shapes/principles';
import { parse as parseIdentity } from '@/lib/content-shapes/identity';
import { parse as parseBrand } from '@/lib/content-shapes/brand';
import { WorkspacePostureLine } from './WorkspacePostureLine';
import { ProgramLifecycleDrawer } from './ProgramLifecycleDrawer';

type SetupBundle = Awaited<ReturnType<typeof api.workspace.getSetupBundle>>;

export function WorkspaceConfigSection() {
  const { sendMessage } = useNarrative();
  const router = useRouter();
  const searchParams = useSearchParams();
  const isFirstRun = searchParams.get('first_run') === '1';

  const [bundle, setBundle] = useState<SetupBundle | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const next = await api.workspace.getSetupBundle();
      setBundle(next);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof APIError ? err.message : 'Failed to load workspace state');
    }
  };

  useEffect(() => { refresh(); }, []);

  // Chat edit handler — fires the prompt into the right panel
  const handleEdit = (prompt: string) => sendMessage(prompt);

  if (loadError) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive flex items-center gap-2">
        <AlertCircle className="w-4 h-4 shrink-0" />
        <span>{loadError}</span>
      </div>
    );
  }

  if (!bundle) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Parse each content via L2 parsers (singular implementation: bundle
  // delivers raw content, parsers run client-side, cards receive parsed data).
  const mandateData = parseMandate(bundle.mandate.content ?? '');
  const principlesProse = parsePrinciples(bundle.principles_prose.content ?? '');
  const principlesYaml = parsePrinciplesYaml(bundle.principles_yaml.content ?? '');
  const principlesData = mergeThresholds(principlesProse, principlesYaml);
  const identityData = parseIdentity(bundle.identity.content ?? '');
  const brandData = parseBrand(bundle.brand.content ?? '');

  // Most-recent revision across the two principles files — surfaces the
  // freshest of prose-edits and yaml-edits in PrinciplesCard's footnote.
  const principlesRevision =
    bundle.principles_prose.last_revision &&
    bundle.principles_yaml.last_revision
      ? new Date(bundle.principles_prose.last_revision.created_at) >=
        new Date(bundle.principles_yaml.last_revision.created_at)
        ? bundle.principles_prose.last_revision
        : bundle.principles_yaml.last_revision
      : bundle.principles_prose.last_revision ?? bundle.principles_yaml.last_revision;

  return (
    <div className="space-y-6 max-w-2xl">

      {/* Posture line (ADR-266 D2) */}
      <WorkspacePostureLine />

      {/* First-run banner */}
      {isFirstRun && (
        <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-primary shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium">Welcome to YARNNN</p>
            <p className="text-xs text-muted-foreground mt-1">
              Pick a program to get started, or head to chat and tell YARNNN what you want to do.
            </p>
          </div>
          <button type="button" onClick={() => router.push('/feed')}
            className="text-sm font-medium text-primary hover:text-primary/80 flex items-center gap-1 shrink-0">
            Go to chat <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* ── Concept components — workspace setup (ADR-266 D1: top of page) ── */}

      <div className="space-y-8">
        <MandateCard
          variant="full"
          onEdit={handleEdit}
          data={mandateData}
          rawContent={bundle.mandate.content}
          lastRevision={bundle.mandate.last_revision}
        />
        <DelegationCard
          variant="full"
          initialContent={bundle.autonomy_yaml.content}
          lastRevision={bundle.autonomy_yaml.last_revision}
        />
        <PrinciplesCard
          variant="full"
          onEdit={handleEdit}
          data={principlesData}
          lastRevision={principlesRevision ?? null}
        />
        <IdentityBrandCard
          variant="full"
          onEdit={handleEdit}
          identityData={identityData}
          brandData={brandData}
          identityRevision={bundle.identity.last_revision}
          brandRevision={bundle.brand.last_revision}
        />
      </div>

      {/* ── Program lifecycle (ADR-266 D1: collapsed at bottom) ───────── */}

      <ProgramLifecycleDrawer state={bundle.state} onMutation={refresh} />
    </div>
  );
}
