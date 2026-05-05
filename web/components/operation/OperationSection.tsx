'use client';

/**
 * OperationSection — body of /operation.
 *
 * The canonical home for workspace-level configuration:
 *   - Active program + switch/deactivate
 *   - Capability gaps (connected platforms)
 *   - Operation setup: the five authored files that govern how the
 *     system behaves (Mandate, Identity, Brand, Autonomy, Reviewer principles).
 *     Files are shown inline — content readable without leaving the page.
 *     Edits route through the chat panel on the right (ThreePanelLayout).
 *
 * Replaces WorkspaceSection (Settings › Workspace tab) and the
 * Mandate/Autonomy/Principles tabs on the YARNNN agent detail.
 * Those surfaces linked out; this one reads content inline.
 *
 * Hard boundary (ADR-244 D7): zero <input>/<textarea> edit affordances
 * for substrate content. Chat is the edit surface.
 */

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Loader2,
  Check,
  AlertCircle,
  Sparkles,
  ArrowRight,
  Power,
  Link2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { useTP } from '@/contexts/TPContext';
import { cn } from '@/lib/utils';

type WorkspaceState = Awaited<ReturnType<typeof api.workspace.getState>>;
type ProgramItem = WorkspaceState['available_programs'][number];
type FileStatusKey = keyof WorkspaceState['substrate_status'];

// Human-readable labels — no internal jargon
const FILE_LABELS: Record<FileStatusKey, string> = {
  mandate:    'Mandate',
  identity:   'Identity',
  brand:      'Brand',
  autonomy:   'Autonomy',
  principles: 'Reviewer principles',
};

// One-line description of what each file does
const FILE_DESCRIPTIONS: Record<FileStatusKey, string> = {
  mandate:    'Your primary goal and the guardrails the system operates within.',
  identity:   'Who you are, your domain, and how agents should represent you.',
  brand:      'Voice, tone, and style conventions for all produced content.',
  autonomy:   'How much the system can decide on your behalf without asking first.',
  principles: 'The criteria your Reviewer applies when evaluating proposals.',
};

// Edit prompts piped into chat when the operator clicks "Edit in chat"
const FILE_EDIT_PROMPTS: Record<FileStatusKey, string> = {
  mandate:    'Help me revise my mandate. Show me the current declaration and walk me through sharpening my primary goal, success criteria, and guardrails.',
  identity:   'Help me revise my identity file. Show me what\'s there and help me sharpen how I want agents to represent me.',
  brand:      'Help me revise my brand guidelines. Show me the current file and let\'s refine voice, tone, and style.',
  autonomy:   'Help me revise my autonomy settings. Show me the current delegation level and walk me through the options.',
  principles: 'Help me revise my Reviewer principles. Show me the current declaration and help me decide what to change.',
};

const FILE_PATHS: Record<FileStatusKey, string> = {
  mandate:    '/workspace/context/_shared/MANDATE.md',
  identity:   '/workspace/context/_shared/IDENTITY.md',
  brand:      '/workspace/context/_shared/BRAND.md',
  autonomy:   '/workspace/context/_shared/AUTONOMY.md',
  principles: '/workspace/review/principles.md',
};

const FILE_ORDER: FileStatusKey[] = ['mandate', 'identity', 'brand', 'autonomy', 'principles'];

export function OperationSection() {
  const { sendMessage } = useTP();
  const router = useRouter();
  const searchParams = useSearchParams();
  const isFirstRun = searchParams.get('first_run') === '1';

  const [state, setState] = useState<WorkspaceState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isMutating, setIsMutating] = useState<string | null>(null);
  const [opError, setOpError] = useState<string | null>(null);
  const [opSuccess, setOpSuccess] = useState<string | null>(null);

  // Per-file inline content
  const [fileContents, setFileContents] = useState<Partial<Record<FileStatusKey, string>>>({});
  const [fileLoading, setFileLoading] = useState<Partial<Record<FileStatusKey, boolean>>>({});
  const [expanded, setExpanded] = useState<Partial<Record<FileStatusKey, boolean>>>({});

  const refresh = async () => {
    try {
      const next = await api.workspace.getState();
      setState(next);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof APIError ? err.message : 'Failed to load operation state');
    }
  };

  useEffect(() => { refresh(); }, []);

  useEffect(() => {
    if (opSuccess) {
      const t = setTimeout(() => setOpSuccess(null), 4000);
      return () => clearTimeout(t);
    }
  }, [opSuccess]);

  const handleActivate = async (slug: string) => {
    setIsMutating(slug); setOpError(null);
    try {
      await api.programs.activate(slug);
      setOpSuccess(`Activated ${slug}`);
      await refresh();
    } catch (err) {
      setOpError(err instanceof APIError ? err.message : 'Activation failed');
    } finally { setIsMutating(null); }
  };

  const handleDeactivate = async () => {
    setIsMutating('deactivate'); setOpError(null);
    try {
      const res = await api.programs.deactivate();
      if (res.deactivated) setOpSuccess(`Deactivated ${res.prior_program_slug}`);
      await refresh();
    } catch (err) {
      setOpError(err instanceof APIError ? err.message : 'Deactivation failed');
    } finally { setIsMutating(null); }
  };

  const toggleExpand = async (key: FileStatusKey) => {
    const next = !expanded[key];
    setExpanded(e => ({ ...e, [key]: next }));

    if (next && fileContents[key] === undefined) {
      setFileLoading(l => ({ ...l, [key]: true }));
      try {
        const file = await api.workspace.getFile(FILE_PATHS[key]);
        setFileContents(c => ({ ...c, [key]: file.content ?? '' }));
      } catch {
        setFileContents(c => ({ ...c, [key]: '' }));
      } finally {
        setFileLoading(l => ({ ...l, [key]: false }));
      }
    }
  };

  const handleEditInChat = (key: FileStatusKey) => {
    sendMessage(FILE_EDIT_PROMPTS[key]);
  };

  if (loadError) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive flex items-center gap-2">
        <AlertCircle className="w-4 h-4 shrink-0" />
        <span>{loadError}</span>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const activeProgram = state.active_program_slug
    ? state.available_programs.find(p => p.slug === state.active_program_slug) ?? null
    : null;

  return (
    <div className="space-y-8 max-w-2xl">

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
          <button
            type="button"
            onClick={() => router.push('/chat')}
            className="text-sm font-medium text-primary hover:text-primary/80 flex items-center gap-1 shrink-0"
          >
            Go to chat <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Active program */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold">Active program</h2>
        {activeProgram ? (
          <div className="rounded-lg border border-primary/40 bg-primary/5 p-4 flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium">{activeProgram.title}</span>
                {activeProgram.current_phase && (
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
                    {activeProgram.current_phase}
                  </span>
                )}
              </div>
              {activeProgram.tagline && (
                <p className="text-xs text-muted-foreground mt-1">{activeProgram.tagline}</p>
              )}
            </div>
            <button
              type="button"
              onClick={handleDeactivate}
              disabled={isMutating !== null}
              className="px-3 py-1.5 text-xs font-medium border border-border rounded-md hover:bg-muted/20 disabled:opacity-40 flex items-center gap-1.5 shrink-0"
            >
              {isMutating === 'deactivate'
                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                : <Power className="w-3.5 h-3.5" />}
              Deactivate
            </button>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-border bg-muted/10 px-4 py-3">
            <p className="text-sm text-muted-foreground">
              No program activated. Pick one below or continue running as-is.
            </p>
          </div>
        )}
      </section>

      {/* Capability gaps */}
      {state.capability_gaps.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold">Platform connections needed</h2>
          <p className="text-xs text-muted-foreground">
            Your active program needs these platforms connected before it can execute autonomously.
            Chat still works in knowledge mode without them.
          </p>
          <div className="space-y-2">
            {state.capability_gaps.map(gap => (
              <div
                key={`${gap.capability}-${gap.requires_platform}`}
                className="rounded-md border border-border bg-card px-3 py-2 flex items-center justify-between gap-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{gap.capability}</div>
                  <div className="text-xs text-muted-foreground">
                    requires <code className="text-xs">{gap.requires_platform}</code>
                  </div>
                </div>
                {gap.connected ? (
                  <span className="text-xs text-green-700 dark:text-green-400 flex items-center gap-1 shrink-0">
                    <Check className="w-3.5 h-3.5" /> Connected
                  </span>
                ) : (
                  <a
                    href="/settings?tab=connectors"
                    className="text-xs font-medium text-primary hover:text-primary/80 flex items-center gap-1 shrink-0"
                  >
                    <Link2 className="w-3.5 h-3.5" /> Connect
                  </a>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Available programs */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold">
          {activeProgram ? 'Switch program' : 'Available programs'}
        </h2>
        <p className="text-xs text-muted-foreground">
          {activeProgram
            ? 'Switching forks the new program on top — your authored content is preserved.'
            : 'Activating a program forks its starting configuration into your workspace.'}
        </p>
        <div className="space-y-2">
          {state.available_programs.map(p => (
            <ProgramRow
              key={p.slug}
              program={p}
              isActive={p.slug === state.active_program_slug}
              isMutating={isMutating === p.slug}
              disabled={isMutating !== null && isMutating !== p.slug}
              onActivate={() => handleActivate(p.slug)}
            />
          ))}
        </div>
      </section>

      {/* Operation setup — the five config files */}
      <section className="space-y-3">
        <div>
          <h2 className="text-sm font-semibold">Operation setup</h2>
          <p className="text-xs text-muted-foreground mt-1">
            These files govern how YARNNN and your agents behave. Read them here — edit via chat on the right.
          </p>
        </div>
        <div className="space-y-2">
          {FILE_ORDER.map(key => (
            <ConfigFileCard
              key={key}
              fileKey={key}
              label={FILE_LABELS[key]}
              description={FILE_DESCRIPTIONS[key]}
              status={state.substrate_status[key]}
              isExpanded={!!expanded[key]}
              isLoadingContent={!!fileLoading[key]}
              content={fileContents[key]}
              onToggle={() => toggleExpand(key)}
              onEdit={() => handleEditInChat(key)}
            />
          ))}
        </div>
      </section>

      {/* Op feedback */}
      {opError && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{opError}</span>
        </div>
      )}
      {opSuccess && (
        <div className="rounded-md border border-green-500/30 bg-green-500/5 px-3 py-2 text-xs text-green-700 dark:text-green-400 flex items-center gap-2">
          <Check className="w-3.5 h-3.5 shrink-0" />
          <span>{opSuccess}</span>
        </div>
      )}
    </div>
  );
}

// ─── Config file card ─────────────────────────────────────────────────────────

function ConfigFileCard({
  fileKey,
  label,
  description,
  status,
  isExpanded,
  isLoadingContent,
  content,
  onToggle,
  onEdit,
}: {
  fileKey: FileStatusKey;
  label: string;
  description: string;
  status: WorkspaceState['substrate_status'][FileStatusKey];
  isExpanded: boolean;
  isLoadingContent: boolean;
  content: string | undefined;
  onToggle: () => void;
  onEdit: () => void;
}) {
  const stateBadge =
    status.state === 'authored' ? (
      <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-green-500/15 text-green-700 dark:text-green-400 shrink-0">
        Authored
      </span>
    ) : status.state === 'skeleton' ? (
      <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-700 dark:text-amber-400 shrink-0">
        Template
      </span>
    ) : (
      <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted text-muted-foreground shrink-0">
        Empty
      </span>
    );

  const hasContent = content !== undefined && content.trim().length > 0;

  return (
    <div className={cn(
      'rounded-lg border bg-card transition-colors',
      isExpanded ? 'border-border' : 'border-border/60',
    )}>
      {/* Header row — always visible */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-muted/30 transition-colors rounded-lg"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium">{label}</span>
            {stateBadge}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
        </div>
        {isExpanded
          ? <ChevronUp className="w-4 h-4 text-muted-foreground shrink-0" />
          : <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />}
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-border/40 pt-3 space-y-3">
          {isLoadingContent ? (
            <div className="flex items-center gap-2 py-2 text-xs text-muted-foreground">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Loading…
            </div>
          ) : hasContent ? (
            <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed max-h-64 overflow-y-auto rounded bg-muted/30 px-3 py-2">
              {content}
            </pre>
          ) : (
            <p className="text-xs text-muted-foreground italic py-2">
              {status.state === 'skeleton'
                ? 'Template content — not yet authored. Use the chat to write yours.'
                : 'Not yet authored. Use the chat to write yours.'}
            </p>
          )}
          <button
            type="button"
            onClick={onEdit}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors"
          >
            Edit in chat <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Program row ──────────────────────────────────────────────────────────────

function ProgramRow({
  program,
  isActive,
  isMutating,
  disabled,
  onActivate,
}: {
  program: ProgramItem;
  isActive: boolean;
  isMutating: boolean;
  disabled: boolean;
  onActivate: () => void;
}) {
  const interactive = !program.deferred && !isActive;
  return (
    <div className={cn(
      'rounded-lg border px-4 py-3',
      isActive ? 'border-primary/50 bg-primary/5' : 'border-border bg-card',
    )}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium">{program.title}</span>
            {isActive && (
              <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-primary/15 text-primary">
                Active
              </span>
            )}
            {program.deferred && (
              <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted text-muted-foreground/70">
                Coming soon
              </span>
            )}
            {program.current_phase && !program.deferred && !isActive && (
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
                {program.current_phase}
              </span>
            )}
          </div>
          {program.tagline && (
            <p className="text-xs text-muted-foreground mt-0.5">{program.tagline}</p>
          )}
        </div>
        {interactive && (
          <button
            type="button"
            onClick={onActivate}
            disabled={disabled}
            className="px-3 py-1.5 text-xs font-medium border border-border rounded-md hover:bg-muted/20 disabled:opacity-40 flex items-center gap-1.5 shrink-0"
          >
            {isMutating
              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
              : <Sparkles className="w-3.5 h-3.5" />}
            Activate
          </button>
        )}
      </div>
    </div>
  );
}
