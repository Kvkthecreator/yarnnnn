'use client';

/**
 * AgentCard — the hiring card (agent-hiring-card spec).
 *
 * THE FRAMING: you are HIRING a colleague, not configuring a product. When you
 * hire someone you don't configure their competence — you learn what they're
 * good at, then decide what to call them and how you want them to sound. So
 * the capability isn't greyed out because we're withholding it; it's fixed
 * because it's WHO THEY ARE. To change what Lisa is, hire someone else — which
 * is exactly what making another Agent is.
 *
 * ⚠️ THE ANTI-PATTERN THIS REFUSES ⚠️
 * The ChatGPT business-agent editor (the benchmark for this page's FORM)
 * carries "Write action safety: Never ask" as a dropdown — the ADR-307
 * consequential gate, sold as a <select>, settable by anyone in one click with
 * no mandate, no witness, no track record. That is precisely the cliff ADR-460
 * D3.a made UNREPRESENTABLE.
 *
 * So: THIS COMPONENT CONTAINS NO AUTHORITY CONTROL, IN ANY STATE. Not enabled,
 * not disabled, not "upgrade to unlock", not an affordance-shaped hole where
 * authority would go — because a greyed-out switch invites "how do I turn this
 * on?", and D3.a's structural guarantee must not degrade into a CSS property.
 * What the Agent can't do is stated as PROSE — a fact about a colleague, which
 * invites nothing because it is simply true. `test_agent_registry.py` asserts
 * this file stays clean of the banned vocabulary.
 */

import { useState } from 'react';
import { Loader2, Upload, X } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { AgentFace } from '@/components/agents/AgentFace';

interface KernelChoice {
  slug: string;
  name: string;
  blurb: string;
  /** The engine's label (e.g. "GPT-5") — the technical fact, kept VISIBLE.
   *  The operator's rule: a nickname must still say what it IS, at minimum
   *  the model and the role. The chooser still never ASKS an engine question
   *  (ADR-460 D4); it REPORTS one. */
  engine?: string;
  /** Optional to match the envelope's shape; the caller filters to kernel rows. */
  kernel?: boolean;
}

interface AgentCardProps {
  /** The kernel capabilities a member may hire (kernel:true rows only). */
  choices: KernelChoice[];
  /** Editing an existing Agent of theirs; absent = hiring a new one. */
  existing?: {
    slug: string;
    name: string;
    based_on: string;
    tone?: string;
    avatar?: string;
    /** The resolved image reference, for the preview well. */
    avatar_url?: string;
  } | null;
  onDone: () => void;
  onCancel: () => void;
}

export function AgentCard({ choices, existing, onDone, onCancel }: AgentCardProps) {
  const [name, setName] = useState(existing?.name ?? '');
  const [basedOn, setBasedOn] = useState(existing?.based_on ?? choices[0]?.slug ?? '');
  const [tone, setTone] = useState(existing?.tone ?? '');
  const [avatar, setAvatar] = useState(existing?.avatar ?? '');
  // The uploaded image, resolved for preview (the picture, not a swatch).
  const [avatarUrl, setAvatarUrl] = useState(existing?.avatar_url ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hired = choices.find((c) => c.slug === basedOn);
  const firstName = name.trim() || 'They';

  const uploadAvatar = async (file: File) => {
    setError(null);
    try {
      // The avatar rides the built ADR-395 bucket lane — the same upload path
      // Phase-A image attachments use. No new storage. The route is a BATCH
      // door (results[]), so a single file is results[0).
      const res = await api.documents.upload(file);
      const first = res.results?.[0];
      if (!first?.success || !first.workspace_path) {
        setError(first?.error || 'That image could not be uploaded');
        return;
      }
      setAvatar(first.workspace_path);
      // Preview immediately from the local file — the member SEES the picture
      // they picked, without waiting for a round-trip through the bucket.
      setAvatarUrl(URL.createObjectURL(file));
    } catch {
      setError('That image could not be uploaded');
    }
  };

  const submit = async () => {
    if (!name.trim() || !basedOn) return;
    setBusy(true);
    setError(null);
    try {
      const body = {
        name: name.trim(),
        based_on: basedOn,
        ...(tone.trim() ? { tone: tone.trim() } : {}),
        ...(avatar ? { avatar } : {}),
      };
      if (existing) await api.lanes.editAgent(existing.slug, body);
      else await api.lanes.makeAgent(body);
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save this agent');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-lg border border-border bg-background p-4 space-y-4 text-sm">
      <div className="flex items-start justify-between">
        <h3 className="font-medium">{existing ? `Edit ${existing.name}` : 'Make your own agent'}</h3>
        <button
          type="button"
          onClick={onCancel}
          className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
          aria-label="Cancel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Avatar + name — the profile row (the operator's "like a user profile"). */}
      <div className="flex items-center gap-3">
        <label
          className={cn(
            'w-14 h-14 rounded-full shrink-0 grid place-items-center cursor-pointer',
            'border border-dashed border-input hover:border-foreground/40 transition-colors',
            avatar && 'border-solid overflow-hidden',
          )}
          title="Upload a picture"
        >
          {avatarUrl ? (
            <AgentFace name={name || '?'} avatarUrl={avatarUrl} size="lg" />
          ) : (
            <Upload className="w-4 h-4 text-muted-foreground" />
          )}
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void uploadAvatar(f);
              e.target.value = '';
            }}
          />
        </label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name them — Lisa, Marcus, whoever"
          className="flex-1 rounded border border-input bg-background px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-ring"
          autoFocus
        />
      </div>

      {/* WHO YOU'RE HIRING — the capability. Fixed on edit: changing it means
          hiring someone else, which is what making another Agent is. */}
      <div className="space-y-1.5">
        <div className="text-xs text-muted-foreground">
          {existing ? 'Hired as' : "Who you're hiring"}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {choices.map((c) => (
            <button
              key={c.slug}
              type="button"
              disabled={!!existing}
              onClick={() => setBasedOn(c.slug)}
              className={cn(
                'px-2 py-1 rounded border text-xs transition-colors',
                basedOn === c.slug
                  ? 'border-primary bg-primary/10 text-foreground'
                  : 'border-input text-muted-foreground hover:text-foreground hover:bg-muted',
                existing && 'opacity-60 cursor-default',
              )}
            >
              {c.name}
            </button>
          ))}
        </div>
        {hired && (
          <p className="text-xs text-muted-foreground">
            {hired.blurb}
            {hired.engine && (
              <span className="text-muted-foreground/60"> · runs on {hired.engine}</span>
            )}
          </p>
        )}
      </div>

      {/* Tone — theirs, in their own words. */}
      <div className="space-y-1.5">
        <div className="text-xs text-muted-foreground">How they sound (optional)</div>
        <textarea
          value={tone}
          onChange={(e) => setTone(e.target.value)}
          rows={2}
          placeholder="Warm and direct. Skips preamble. Calls me Kev."
          className="w-full resize-none rounded border border-input bg-background px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        />
      </div>

      {/* WHAT THEY CAN'T DO — prose, not a switch. This is the ADR-460 D3.a
          cliff, shown as a fact about a colleague. A disabled toggle invites
          "how do I enable this?"; a true sentence invites nothing. */}
      <p className="text-xs text-muted-foreground border-t border-border pt-3 leading-relaxed">
        {firstName} works on your files — reads, writes, edits. {firstName} can&apos;t send
        email, spend money, or act while you&apos;re away. They answer when you ask.
      </p>

      {error && <p className="text-xs text-destructive">{error}</p>}

      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-2 py-1 rounded text-xs text-muted-foreground hover:text-foreground hover:bg-muted"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={() => void submit()}
          disabled={!name.trim() || busy}
          className="px-3 py-1 rounded bg-primary text-primary-foreground text-xs disabled:opacity-40 inline-flex items-center gap-1.5"
        >
          {busy && <Loader2 className="w-3 h-3 animate-spin" />}
          {existing ? 'Save' : 'Hire'}
        </button>
      </div>
    </div>
  );
}
