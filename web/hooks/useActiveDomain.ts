'use client';

/**
 * ADR-034: Hook to get the active domain for the current context.
 *
 * Domain is determined by:
 * 1. If viewing a deliverable, use that deliverable's domain
 * 2. If user has only one non-default domain, use it implicitly
 * 3. Otherwise, null (ambiguous)
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api/client';
import { ActiveDomainResponse } from '@/types';
import { useDesk } from '@/contexts/DeskContext';

export interface ActiveDomain {
  id: string;
  name: string;
  isDefault: boolean;
}

export interface UseActiveDomainResult {
  domain: ActiveDomain | null;
  source: 'deliverable' | 'single_domain' | 'ambiguous' | 'loading';
  domainCount: number;
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

export function useActiveDomain(): UseActiveDomainResult {
  const { surface } = useDesk();
  const [data, setData] = useState<ActiveDomainResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Get deliverable ID from surface context
  const deliverableId =
    surface.type === 'deliverable-review' || surface.type === 'deliverable-detail'
      ? ('deliverableId' in surface ? surface.deliverableId : undefined)
      : undefined;

  const fetchDomain = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await api.domains.getActive(deliverableId);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch domain'));
    } finally {
      setIsLoading(false);
    }
  }, [deliverableId]);

  // Fetch on mount and when deliverableId changes
  useEffect(() => {
    fetchDomain();
  }, [fetchDomain]);

  return {
    domain: data?.domain
      ? {
          id: data.domain.id,
          name: data.domain.name,
          isDefault: data.domain.is_default,
        }
      : null,
    source: isLoading ? 'loading' : (data?.source ?? 'ambiguous'),
    domainCount: data?.domain_count ?? 0,
    isLoading,
    error,
    refresh: fetchDomain,
  };
}
