'use client';

/**
 * PipelineTab — ADR-145 Gate 3: Pipeline visualization for task detail page.
 *
 * Shows multi-step execution pipeline with step details, agent attribution,
 * and collapsible step output content. Replaces AgentsTab.
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
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
import type { TaskDetail, TaskOutput, PipelineStepOutput, PipelineStepSummary } from '@/types';

function StepCard({
  step,
  isLast,
  defaultExpanded = false,
}: {
  step: PipelineStepOutput;
  isLast: boolean;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div>
      {/* Step card */}
      <div className="border border-border rounded-lg overflow-hidden">
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-3 p-3 hover:bg-muted/30 transition-colors text-left"
        >
          {/* Step number */}
          <div className="flex items-center justify-center w-7 h-7 rounded-full bg-primary/10 text-primary text-xs font-bold shrink-0">
            {step.step}
          </div>

          {/* Step info */}
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

          {/* Status + expand */}
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

        {/* Expandable content */}
        {expanded && step.content && (
          <div className="border-t border-border bg-muted/20 p-3 max-h-80 overflow-y-auto">
            <MarkdownRenderer content={step.content} compact />
          </div>
        )}
      </div>

      {/* Connector arrow */}
      {!isLast && (
        <div className="flex justify-center py-1">
          <ArrowDown className="w-3.5 h-3.5 text-muted-foreground/20" />
        </div>
      )}
    </div>
  );
}

function PipelineDefinitionView({ definition }: { definition: PipelineStepSummary[] }) {
  return (
    <div className="space-y-1">
      <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mb-3">
        Pipeline ({definition.length} steps)
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

export function PipelineTab({
  task,
  selectedOutput,
}: {
  task: TaskDetail;
  selectedOutput: TaskOutput | null;
}) {
  const [steps, setSteps] = useState<PipelineStepOutput[]>([]);
  const [pipelineDefinition, setPipelineDefinition] = useState<PipelineStepSummary[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedOutput?.folder && !selectedOutput?.date) {
      setSteps([]);
      return;
    }

    const dateFolder = selectedOutput.folder || selectedOutput.date;
    if (!dateFolder) return;

    setLoading(true);
    setError(null);
    api.tasks.getStepOutputs(task.slug, dateFolder)
      .then(res => {
        setSteps(res.steps || []);
        if (res.pipeline_definition) {
          setPipelineDefinition(res.pipeline_definition);
        }
      })
      .catch(e => {
        setError('Failed to load pipeline steps');
        console.error(e);
      })
      .finally(() => setLoading(false));
  }, [task.slug, selectedOutput?.folder, selectedOutput?.date]);

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

      {!loading && !error && steps.length > 0 && (
        <>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
            Pipeline — {steps.length} steps
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

          {/* Final deliverable indicator */}
          <div className="flex items-center gap-2 p-2.5 rounded-lg bg-primary/5 border border-primary/20">
            <CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
            <p className="text-xs text-primary font-medium">
              Final deliverable composed from Step {steps.length} output
            </p>
          </div>
        </>
      )}

      {!loading && !error && steps.length === 0 && pipelineDefinition && (
        <>
          <PipelineDefinitionView definition={pipelineDefinition} />
          <p className="text-[10px] text-muted-foreground/40 text-center">
            Run the task to see step-by-step execution details
          </p>
        </>
      )}

      {!loading && !error && steps.length === 0 && !pipelineDefinition && (
        <div className="text-center py-8">
          <p className="text-xs text-muted-foreground/40">
            {selectedOutput ? 'This output was generated as a single step' : 'No output selected — run the task or select a run from the Schedule tab'}
          </p>
          {/* Fallback: show assigned agents */}
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
