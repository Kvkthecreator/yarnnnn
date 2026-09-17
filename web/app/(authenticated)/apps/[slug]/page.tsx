'use client';

/**
 * /apps/{slug} — a MEMBER app's route (ADR-653 D3.c).
 *
 * The first TWO-SEGMENT surface route in the product. Every kernel surface is
 * `/{slug}` because its slug is in a compile-time union; a member app's slug is
 * AUTHORED, so it cannot be — it lives under one namespace instead.
 *
 * ⚠️ THE NAMESPACE IS PROTECTED EXPLICITLY (`APP_NAMESPACE_PREFIX` in
 * lib/supabase/middleware.ts). The auth gate derives its protected set from
 * KERNEL_SURFACE_SLUGS as `/{slug}` — single-segment by construction — so this
 * route slips under that derivation no matter how current the roster is, and
 * would serve 200 to a logged-out visitor. That is the 2026-08-20 incident's
 * SHAPE (eight surfaces ungated), reached a different way.
 *
 * Like every other per-slug route this is a deep-link transport: the real
 * render happens in the viewport, which resolves the slug against the served
 * roster and mounts the ONE generic AppSurface. This page body is what shows
 * if the shell's window system is not mounted over it.
 */

import { useParams } from 'next/navigation';
import { AppSurface } from '@/components/apps/AppSurface';

export default function MemberAppPage() {
  const params = useParams<{ slug: string }>();
  const slug = typeof params?.slug === 'string' ? params.slug : '';
  if (!slug) return null;
  return <AppSurface slug={slug} />;
}
