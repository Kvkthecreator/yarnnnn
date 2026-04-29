'use client';

/**
 * ProcessTab — Task execution process visualization.
 *
 * Three temporal states:
 *   1. Before run: Shows process definition from task type registry
 *   2. During run: Live progress polling — which step is active, which are done
 *   3. After run: Completed step outputs with expand/collapse
 *
 * Renamed from PipelineTab (ADR-145 Gate 3) — "process" is the user-facing term.
 */

import { useState, useEffect, useRef } from 'react';
import {
  Loader2,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Circle,
  ArrowDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { roleBadgeColor, roleDisplayName } from '@/lib/agent-identity';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import type { RecurrenceDetail, RecurrenceOutput, ProcessStepOutput, ProcessStepSummary, RunStatus } from '@/types';

// =============================================================================
// Completed step card (retrospective — after run)
// =============================================================================

function StepCard({
  step,
  isLast,
  defaultExpanded = false,
}: {
  step: ProcessStepOutput;
  isLast: boolean;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div>
      <div className="border border-border rounded-lg overflow-hidden">
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-3 p-3 hover:bg-muted/30 transition-colors text-left"
        >
          <div className="flex items-center justify-center w-7 h-7 rounded-full bg-green-500/10 text-green-600 text-xs font-bold shrink-0">
            {step.step}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium capitalize">{step.step_name}</span>
              <span className={cn('px-1.5 py-0.5 text-[9px] rounded', roleBadgeColor(step.agent_type))}>
                {roleDisplayName(step.agent_type)}
              </span>
            </div>
            <p className="text-[10px] text-muted-foreground/50 mt-0.5">
              {step.agent_slug}
              {step.tokens && (
                <span className="ml-2 font-mono">
                  {((step.tokens.input_tokens + step.tokens.output_tokens) / 1000).toFixed(1)}k tokens
                </span>
              )}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {step.content ? (
              <CheckCircle2 className="w-4 h-4 text-green-500" />
            ) : (
              <Circle className="w-4 h-4 text-muted-foreground/30" />
            )}
            {step.content && (
              expanded
                ? <ChevronDown className="w-4 h-4 text-muted-foreground/40" />
                : <ChevronRight className="w-4 h-4 text-muted-foreground/40" />
            )}
          </div>
        </button>

        {expanded && step.content && (
          <div className="border-t border-border bg-muted/20 p-3 max-h-80 overflow-y-auto">
            <MarkdownRenderer content={step.content} compact />
          </div>
        )}
      </div>

      {!isLast && (
        <div className="flex justify-center py-1">
          <ArrowDown className="w-3.5 h-3.5 text-muted-foreground/20" />
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Process definition view (before run — what will happen)
// =============================================================================

function ProcessDefinitionView({ definition }: { definition: ProcessStepSummary[] }) {
  return (
    <div className="space-y-1">
      <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mb-3">
        Process ({definition.length} steps)
      </p>
      {definition.map((step, idx) => (
        <div key={idx}>
          <div className="flex items-center gap-3 p-2.5 rounded-lg border border-border/50">
            <div className="flex items-center justify-center w-6 h-6 rounded-full bg-muted text-[10px] font-bold text-muted-foreground shrink-0">
              {idx + 1}
            </div>
            <span className="text-xs font-medium capitalize">{step.step}</span>
            <span className={cn('px-1.5 py-0.5 text-[9px] rounded', roleBadgeColor(step.agent_type))}>
              {roleDisplayName(step.agent_type)}
            </span>
          </div>
          {idx < definition.length - 1 && (
            <div className="flex justify-center py-0.5">
              <ArrowDown className="w-3 h-3 text-muted-foreground/15" />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// Live progress view (during run — real-time step stepper)
// =============================================================================

function LiveProgressView({ runStatus, definition }: { runStatus: RunStatus; definition?: ProcessStepSummary[] | null }) {
  const totalSteps = runStatus.total_steps || definition?.length || 0;
  const completedSet = new Set(runStatus.completed_steps.map(s => s.step));

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2 mb-3">
        <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
        <p className="text-[11px] font-medium text-primary uppercase tracking-wide">
          Running — step {runStatus.current_step}/{totalSteps}
        </p>
      </div>

      {Array.from({ length: totalSteps }, (_, idx) => {
        const stepNum = idx + 1;
        const isCompleted = completedSet.has(stepNum);
        const isActive = stepNum === runStatus.current_step + 1 && !isCompleted;
        const isPending = !isCompleted && !isActive;
        const completedInfo = runStatus.completed_steps.find(s => s.step === stepNum);
        const definitionInfo = definition?.[idx];
        const stepName = completedInfo?.step_name || definitionInfo?.step || `Step ${stepNum}`;
        const agentType = completedInfo?.agent_type || definitionInfo?.agent_type || '';

        return (
          <div key={stepNum}>
            <div className={cn(
              'flex items-center gap-3 p-2.5 rounded-lg border transition-all',
              isCompleted && 'border-green-200 bg-green-50/50 dark:border-green-900 dark:bg-green-950/30',
              isActive && 'border-primary/40 bg-primary/5 shadow-sm',
              isPending && 'border-border/30 opacity-50',
            )}>
              <div className={cn(
                'flex items-center justify-center w-6 h-6 rounded-full text-[10px] font-bold shrink-0',
                isCompleted && 'bg-green-500/15 text-green-600',
                isActive && 'bg-primary/15 text-primary',
                isPending && 'bg-muted text-muted-foreground',
              )}>
                {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : isActive ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : stepNum}
              </div>

              <span className={cn('text-xs font-medium capitalize', isPending && 'text-muted-foreground')}>
                {stepName}
              </span>

              {agentType && (
                <span className={cn('px-1.5 py-0.5 text-[9px] rounded', isPending ? 'bg-muted text-muted-foreground' : roleBadgeColor(agentType))}>
                  {roleDisplayName(agentType)}
                </span>
              )}
            </div>

            {stepNum < totalSteps && (
              <div className="flex justify-center py-0.5">
                <ArrowDown className={cn('w-3 h-3', isCompleted ? 'text-green-300' : 'text-muted-foreground/15')} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// =============================================================================
// ProcessTab (main export)
// =============================================================================

export function ProcessTab({
  task,
  selectedOutput,
}: {
  task: RecurrenceDetail;
  selectedOutput: RecurrenceOutput | null;
}) {
  const [steps, setSteps] = useState<ProcessStepOutput[]>([]);
  const [processDefinition, setProcessDefinition] = useState<ProcessStepSummary[] | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll for live execution progress
  useEffect(() => {
    const poll = () => {
      api.recurrences.getRunStatus(task.slug)
        .then(status => {
          if (status.status === 'running') {
            setRunStatus(status);
          } else if (status.status === 'completed' && runStatus?.status === 'running') {
            // Was running, now completed — clear status and refresh step outputs
            setRunStatus(null);
            if (selectedOutput?.folder || selectedOutput?.date) {
              const dateFolder = selectedOutput.folder || selectedOutput.date;
              if (dateFolder) {
                api.recurrences.getStepOutputs(task.slug, dateFolder)
                  .then(res => {
                    setSteps(res.steps || []);
                    if (res.process_definition) setProcessDefinition(res.process_definition);
                  })
                  .catch(() => {});
              }
            }
          } else {
            setRunStatus(null);
          }
        })
        .catch(() => setRunStatus(null));
    };

    // Poll every 3s for progress
    poll();
    pollRef.current = setInterval(poll, 3000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [task.slug, selectedOutput?.folder, selectedOutput?.date]);

  // Stop polling when run completes
  useEffect(() => {
    if (runStatus === null && pollRef.current) {
      // Keep polling at slower rate for new runs
      clearInterval(pollRef.current);
      pollRef.current = setInterval(() => {
        api.recurrences.getRunStatus(task.slug)
          .then(status => {
            if (status.status === 'running') setRunStatus(status);
          })
          .catch(() => {});
      }, 10000);
    }
  }, [runStatus, task.slug]);

  // Fetch step outputs for selected run
  useEffect(() => {
    if (!selectedOutput?.folder && !selectedOutput?.date) {
      setSteps([]);
      return;
    }

    const dateFolder = selectedOutput.folder || selectedOutput.date;
    if (!dateFolder) return;

    setLoading(true);
    setError(null);
    api.recurrences.getStepOutputs(task.slug, dateFolder)
      .then(res => {
        setSteps(res.steps || []);
        if (res.process_definition) setProcessDefinition(res.process_definition);
      })
      .catch(e => {
        setError('Failed to load process steps');
        console.error(e);
      })
      .finally(() => setLoading(false));
  }, [task.slug, selectedOutput?.folder, selectedOutput?.date]);

  // Live progress takes priority
  if (runStatus?.status === 'running') {
    return (
      <div className="p-5 space-y-4">
        <LiveProgressView runStatus={runStatus} definition={processDefinition} />
      </div>
    );
  }

  return (
    <div className="p-5 space-y-4">
      {loading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
        </div>
      )}

      {error && (
        <p className="text-xs text-red-500 text-center py-4">{error}</p>
      )}

      {/* After run: completed step outputs */}
      {!loading && !error && steps.length > 0 && (
        <>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Process — {steps.length} steps
            {selectedOutput?.date && (
              <span className="normal-case font-normal ml-1.5 text-muted-foreground/40">
                {selectedOutput.date}
              </span>
            )}
          </p>

          <div className="space-y-0">
            {steps.map((step, idx) => (
              <StepCard
                key={step.step}
                step={step}
                isLast={idx === steps.length - 1}
              />
            ))}
          </div>

          <div className="flex items-center gap-2 p-2.5 rounded-lg bg-primary/5 border border-primary/20">
            <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
            <p className="text-xs text-primary font-medium">
              Final deliverable composed from Step {steps.length} output
            </p>
          </div>
        </>
      )}

      {/* Before run: process definition from registry */}
      {!loading && !error && steps.length === 0 && processDefinition && (
        <>
          <ProcessDefinitionView definition={processDefinition} />
          <p className="text-[10px] text-muted-foreground/40 text-center">
            Run the task to see step-by-step execution details
          </p>
        </>
      )}

      {/* Fallback: no type-based process */}
      {!loading && !error && steps.length === 0 && !processDefinition && (
        <div className="text-center py-8">
          <p className="text-xs text-muted-foreground/40">
            {selectedOutput ? 'This output was generated as a single step' : 'No output selected — run the task or select a run from the Schedule tab'}
          </p>
          {task.agent_slugs && task.agent_slugs.length > 0 && (
            <div className="mt-4 space-y-1.5">
              <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mb-2">
                Assigned Agents
              </p>
              {task.agent_slugs.map((slug, idx) => (
                <div key={slug} className="flex items-center gap-2 text-xs text-muted-foreground px-2">
                  {task.agent_slugs!.length > 1 && (
                    <span className="w-5 h-5 rounded-full bg-muted flex items-center justify-center text-[9px] font-mono font-bold">{idx + 1}</span>
                  )}
                  <span>{slug}</span>
                </div>
              ))}
              {task.agent_slugs.length > 1 && (
                <p className="text-[10px] text-muted-foreground/40 mt-2">
                  Agents execute in sequence — each receives the prior agent&apos;s output as context.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
