'use client';

/**
 * AgentFace — a colleague's picture (the operator's ruling, 2026-07-16).
 *
 * The face is an UPLOADED IMAGE, like a person's profile picture — not a
 * colour swatch (the shipped placeholder, which was debt §6.2: "a picture you
 * upload and never see is worse than no picture"), and not a generated
 * Freddie-style animation (which would make every agent a variant of the same
 * system creature — system-authored identity, cutting against "you named her").
 * An agent you HIRED having a face you CHOSE is the point.
 *
 * The URL chain (the ADR-395 bucket lane, the FileTile pattern): the manifest
 * stores a workspace PATH → the registry resolves it to the file's
 * `content_url` → this trades that for a fresh signed URL. A browser <img src>
 * can't carry a Bearer header, so the exchange must happen here.
 *
 * Fallback is the initial, never a broken image: an agent without a picture is
 * ordinary, and a colleague whose face fails to load should still be legible.
 */

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

interface AgentFaceProps {
  name: string;
  /** The file's `content_url` (served by the registry), if they have a picture. */
  avatarUrl?: string | null;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const SIZE: Record<string, string> = {
  sm: 'w-6 h-6 text-[10px]',
  md: 'w-9 h-9 text-xs',
  lg: 'w-14 h-14 text-lg',
};

export function AgentFace({ name, avatarUrl, size = 'md', className }: AgentFaceProps) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!avatarUrl) return;
    // Already a usable URL (data:/blob:/http:) — no exchange needed.
    if (/^(https?:|data:|blob:)/i.test(avatarUrl)) {
      setUrl(avatarUrl);
      return;
    }
    let cancelled = false;
    api.documents
      .blobUrl(avatarUrl)
      .then((r) => !cancelled && setUrl(r.url))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [avatarUrl]);

  const base = cn(
    'rounded-full shrink-0 grid place-items-center overflow-hidden',
    SIZE[size],
    className,
  );

  if (url && !failed) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt={name}
        className={cn(base, 'object-cover')}
        onError={() => setFailed(true)}
      />
    );
  }

  return (
    <span className={cn(base, 'bg-muted text-muted-foreground font-medium')}>
      {(name || '?').slice(0, 1).toUpperCase()}
    </span>
  );
}
