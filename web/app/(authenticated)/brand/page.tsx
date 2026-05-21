'use client';

/**
 * /brand — atomic Brand surface (ADR-297 D1).
 *
 * Per ADR-297 D1, Brand is a peer atomic surface to Identity. The
 * underlying IdentityBrandCard co-renders both; /brand currently
 * redirects to /identity so operators discover the joint render.
 * Splitting into a dedicated /brand-only card is a follow-on if
 * operator demand surfaces.
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function BrandPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/identity');
  }, [router]);
  return null;
}
