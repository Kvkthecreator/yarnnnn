'use client';

/**
 * /program — atomic Program surface (ADR-297 D1).
 *
 * Renders /workspace/_program.yaml and program-lifecycle controls via
 * the existing ProgramLifecycleDrawer component (extracted intact from
 * the deleted /workspace container). Lifecycle decisions (activate /
 * switch / deactivate / capability gaps) live here.
 */

import { useEffect, useState } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { SurfacePage } from '@/components/shell/SurfacePage';
import { ProgramLifecycleDrawer } from '@/components/library/ProgramLifecycleDrawer';

type WorkspaceState = Awaited<ReturnType<typeof api.workspace.getState>>;

export default function ProgramPage() {
  const [state, setState] = useState<WorkspaceState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const next = await api.workspace.getState();
      setState(next);
      setError(null);
    } catch (err) {
      setError(err instanceof APIError ? err.message : 'Failed to load program state');
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <SurfacePage
      iconKey="package"
      title="Program"
      summary="Active program bundle, phase, and capability gaps."
    >
      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {!state && !error && (
        <div className="flex items-center justify-center py-10">
          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      )}
      {state && (
        <ProgramLifecycleDrawer state={state} onMutation={refresh} />
      )}
    </SurfacePage>
  );
}
