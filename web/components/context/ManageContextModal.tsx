'use client';

/**
 * ManageContextModal — explicit IDENTITY / BRAND / CONVENTIONS editor (ADR-205 F4 / ADR-206).
 *
 * ADR-206 CRUD split: **create via modal** (this), update/delete via chat + YARNNN for
 * judgment-shaped edits. This modal serves operators who want to directly edit their
 * Intent layer (ADR-206 — the authored rules that calibrate the operation).
 *
 * Targets the three `/workspace/context/_shared/` files (post-ADR-206 relocation):
 *   - IDENTITY.md    — who the user is (name, role, company, industry, timezone)
 *   - BRAND.md       — how outputs look and sound
 *   - CONVENTIONS.md — workspace filesystem rules (agent-readable)
 *
 * Writes route through the existing endpoints:
 *   - POST /api/memory/user/identity  (IDENTITY.md)
 *   - POST /api/memory/user/brand     (BRAND.md)
 *   - PUT  /api/workspace/file        (CONVENTIONS.md — generic workspace file PUT)
 *
 * CONVENTIONS write uses the generic workspace file PUT because there's no dedicated
 * endpoint — the ADR-206 workspace.py editable-prefixes were widened to permit it.
 */

import { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';

type Tab = 'identity' | 'brand' | 'conventions';

const CONVENTIONS_PATH = '/workspace/context/_shared/CONVENTIONS.md';

export interface ManageContextModalProps {
  open: boolean;
  onClose: () => void;
  /** Called after a successful save so the parent can refresh its tree. */
  onSaved?: (target: Tab) => void;
  initialTab?: Tab;
}

export function ManageContextModal({
  open,
  onClose,
  onSaved,
  initialTab = 'identity',
}: ManageContextModalProps) {
  const [tab, setTab] = useState<Tab>(initialTab);
  const [identityContent, setIdentityContent] = useState('');
  const [brandContent, setBrandContent] = useState('');
  const [conventionsContent, setConventionsContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedHint, setSavedHint] = useState<Tab | null>(null);

  // Esc / body scroll-lock
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !saving) onClose();
    };
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
  }, [open, saving, onClose]);

  // Load current content when modal opens
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const [idR, brR, convR] = await Promise.allSettled([
          api.identity.get(),
          api.brand.get(),
          api.workspace.getFile(CONVENTIONS_PATH),
        ]);
        if (cancelled) return;
        if (idR.status === 'fulfilled') setIdentityContent(idR.value.content ?? '');
        if (brR.status === 'fulfilled') setBrandContent(brR.value.content ?? '');
        if (convR.status === 'fulfilled') setConventionsContent(convR.value.content ?? '');
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load context');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [open]);

  // Reset tab on open
  useEffect(() => {
    if (open) setTab(initialTab);
    else {
      setError(null);
      setSavedHint(null);
    }
  }, [open, initialTab]);

  if (!open) return null;

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSavedHint(null);
    try {
      if (tab === 'identity') {
        await api.identity.save(identityContent);
      } else if (tab === 'brand') {
        await api.brand.save(brandContent);
      } else if (tab === 'conventions') {
        await api.workspace.editFile(CONVENTIONS_PATH, conventionsContent, 'Manage context: CONVENTIONS');
      }
      setSavedHint(tab);
      onSaved?.(tab);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const currentValue = tab === 'identity' ? identityContent : tab === 'brand' ? brandContent : conventionsContent;
  const setCurrentValue = (v: string) => {
    if (tab === 'identity') setIdentityContent(v);
    else if (tab === 'brand') setBrandContent(v);
    else setConventionsContent(v);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-foreground/40 px-4 py-[8vh] backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Manage context"
      onClick={e => {
        if (e.target === e.currentTarget && !saving) onClose();
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        className="w-full max-w-3xl rounded-xl border border-border bg-background shadow-2xl"
      >
        <header className="flex items-start justify-between border-b border-border px-5 py-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
              Context
            </p>
            <h2 className="text-base font-semibold text-foreground">
              Manage workspace context
            </h2>
            <p className="mt-0.5 text-[11px] text-muted-foreground/70">
              Intent layer — who you are, how your outputs sound, and the conventions your agents honor.
            </p>
          </div>
          <button
            type="button"
            disabled={saving}
            onClick={onClose}
            className="rounded p-1 text-muted-foreground/40 hover:bg-muted hover:text-muted-foreground disabled:opacity-50"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <nav className="flex gap-1 border-b border-border px-3 pt-2">
          {([
            { id: 'identity', label: 'Identity' },
            { id: 'brand', label: 'Brand' },
            { id: 'conventions', label: 'Conventions' },
          ] as const).map(t => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={
                'rounded-t-md px-3 py-1.5 text-xs font-medium ' +
                (tab === t.id
                  ? 'bg-foreground text-background'
                  : 'text-muted-foreground hover:text-foreground')
              }
              disabled={saving}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <div className="px-5 py-4">
          {loading ? (
            <div className="flex h-[300px] items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <textarea
              value={currentValue}
              onChange={e => setCurrentValue(e.target.value)}
              placeholder={
                tab === 'identity'
                  ? '# Who I am\n\nName: …\nRole: …\nCompany: …\n'
                  : tab === 'brand'
                  ? '# Brand\n\nTone: …\nVoice: …\n'
                  : '# Workspace Conventions\n\n- …\n'
              }
              rows={14}
              className="w-full resize-y rounded-md border border-border bg-background px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-foreground/20"
              disabled={saving}
            />
          )}

          {error && (
            <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {error}
            </div>
          )}
          {savedHint && !error && (
            <div className="mt-3 rounded-md border border-border bg-muted px-3 py-2 text-xs text-muted-foreground">
              Saved.
            </div>
          )}
        </div>

        <footer className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || loading}
            className="inline-flex items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-sm text-background hover:bg-foreground/90 disabled:opacity-50"
          >
            {saving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {saving ? 'Saving…' : `Save ${tab}`}
          </button>
        </footer>
      </div>
    </div>
  );
}
