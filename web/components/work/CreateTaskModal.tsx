'use client';

/**
 * CreateTaskModal — explicit-intent task creation (ADR-205 F3 / ADR-206 CRUD split).
 *
 * ADR-206 CRUD split: **create via modal** (high-precision, well-specified), update/delete
 * via chat + YARNNN (judgment-shaped). The modal provides a structured form for operators
 * who arrive with a clear ask ("create a weekly competitor tracker"). For ambiguous intent
 * or iteration, operators stay in chat — YARNNN calls `ManageTask(action="create")`
 * internally the same way this modal calls `POST /api/tasks`.
 *
 * Fields (ADR-206 Phase 3 scope):
 *   - title                (required)
 *   - type_key             (registry catalog, optional — selecting populates mode + schedule defaults)
 *   - mode                 (recurring / goal / reactive — derived from type when present)
 *   - focus                (context / intent — free text, lands in objective.deliverable)
 *   - schedule             (optional — ADR-205 chat-first: empty = run-now)
 *
 * Submission calls `api.tasks.create` which routes through ManageTask._handle_create.
 * ADR-205 chat-first triggering: when schedule is empty, the task runs once on create.
 */

import { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import type { TaskType } from '@/types';

export interface CreateTaskModalProps {
  open: boolean;
  onClose: () => void;
  /** Called with the created task's slug on success. */
  onCreated: (slug: string) => void;
}

type Mode = 'recurring' | 'goal' | 'reactive' | '';

export function CreateTaskModal({ open, onClose, onCreated }: CreateTaskModalProps) {
  const [title, setTitle] = useState('');
  const [typeKey, setTypeKey] = useState<string>('');
  const [mode, setMode] = useState<Mode>('');
  const [focus, setFocus] = useState('');
  const [schedule, setSchedule] = useState('');
  const [types, setTypes] = useState<TaskType[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Esc / body scroll-lock
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) onClose();
    };
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
  }, [open, submitting, onClose]);

  // ADR-207 P4b (2026-04-22): `/api/tasks/types` catalog endpoint DELETED.
  // The modal no longer fetches a type list. YARNNN is the authoring surface;
  // the modal survives only as a quick-capture form that forwards a minimal
  // title + context (focus) to YARNNN via the create endpoint. The legacy
  // type picker is hidden but the `types` state is kept (always empty) so the
  // rest of the component renders without breakage.
  useEffect(() => {
    if (!open) return;
    setTypes([]);
  }, [open]);

  // When the operator picks a type, pre-fill mode (type registry declares defaults).
  useEffect(() => {
    if (!typeKey) return;
    const t = types.find(tt => tt.type_key === typeKey);
    if (t && t.default_mode && !mode) {
      setMode(t.default_mode as Mode);
    }
    if (t && !title) {
      setTitle(t.default_title || t.display_name || '');
    }
  }, [typeKey, types]);  // eslint-disable-line react-hooks/exhaustive-deps

  // Reset when closed
  useEffect(() => {
    if (open) return;
    setTitle('');
    setTypeKey('');
    setMode('');
    setFocus('');
    setSchedule('');
    setError(null);
  }, [open]);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Title is required.');
      return;
    }
    if (!typeKey && !focus.trim()) {
      setError('Either pick a task type or describe the task in Context.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await api.tasks.create({
        title: title.trim(),
        type_key: typeKey || undefined,
        mode: (mode || undefined) as TaskCreate['mode'],
        focus: focus.trim() || undefined,
        schedule: schedule.trim() || undefined,
      } as TaskCreate);
      onCreated(response.slug);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create task.';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-foreground/40 px-4 py-[10vh] backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Create task"
      onClick={e => {
        if (e.target === e.currentTarget && !submitting) onClose();
      }}
    >
      <form
        onSubmit={handleSubmit}
        onClick={e => e.stopPropagation()}
        className="w-full max-w-xl rounded-xl border border-border bg-background shadow-2xl"
      >
        <header className="flex items-start justify-between border-b border-border px-5 py-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
              New task
            </p>
            <h2 className="text-base font-semibold text-foreground">
              Create a new task
            </h2>
            <p className="mt-0.5 text-[11px] text-muted-foreground/70">
              Leave schedule empty to run once now. Add a schedule later to make it recurring.
            </p>
          </div>
          <button
            type="button"
            disabled={submitting}
            onClick={onClose}
            className="rounded p-1 text-muted-foreground/40 hover:bg-muted hover:text-muted-foreground disabled:opacity-50"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="space-y-4 px-5 py-4">
          <div className="space-y-1">
            <label htmlFor="task-title" className="text-xs font-medium text-muted-foreground">
              Title <span className="text-destructive">*</span>
            </label>
            <input
              id="task-title"
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="e.g., Weekly competitor brief"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-foreground/20"
              required
              disabled={submitting}
            />
          </div>

          <div className="space-y-1">
            <label htmlFor="task-type" className="text-xs font-medium text-muted-foreground">
              Task type (optional)
            </label>
            <select
              id="task-type"
              value={typeKey}
              onChange={e => setTypeKey(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-foreground/20"
              disabled={submitting}
            >
              <option value="">— pick a type (recommended) —</option>
              {types.map(t => (
                <option key={t.type_key} value={t.type_key}>
                  {t.display_name || t.type_key}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-muted-foreground/70">
              Type populates the default team, pipeline, and output kind.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label htmlFor="task-mode" className="text-xs font-medium text-muted-foreground">
                Mode
              </label>
              <select
                id="task-mode"
                value={mode}
                onChange={e => setMode(e.target.value as Mode)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-foreground/20"
                disabled={submitting}
              >
                <option value="">(default from type)</option>
                <option value="recurring">Recurring</option>
                <option value="goal">Goal</option>
                <option value="reactive">Reactive</option>
              </select>
            </div>

            <div className="space-y-1">
              <label htmlFor="task-schedule" className="text-xs font-medium text-muted-foreground">
                Schedule
              </label>
              <input
                id="task-schedule"
                type="text"
                value={schedule}
                onChange={e => setSchedule(e.target.value)}
                placeholder="daily / weekly / 0 9 * * 1"
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-foreground/20"
                disabled={submitting}
              />
            </div>
          </div>

          <div className="space-y-1">
            <label htmlFor="task-focus" className="text-xs font-medium text-muted-foreground">
              Context
            </label>
            <textarea
              id="task-focus"
              value={focus}
              onChange={e => setFocus(e.target.value)}
              placeholder="What should this task accomplish? Any specific focus, audience, or constraints?"
              rows={3}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-foreground/20"
              disabled={submitting}
            />
          </div>

          {error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {error}
            </div>
          )}
        </div>

        <footer className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-sm text-background hover:bg-foreground/90 disabled:opacity-50"
          >
            {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {submitting ? 'Creating…' : 'Create task'}
          </button>
        </footer>
      </form>
    </div>
  );
}

type TaskCreate = import('@/types').TaskCreate;
