'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * Desk context - manages current surface and attention queue
 */

import React, { createContext, useContext, useReducer, useCallback, useEffect, ReactNode } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import {
  DeskState,
  DeskAction,
  DeskSurface,
  AttentionItem,
  surfaceToParams,
  paramsToSurface,
} from '@/types/desk';
import { api } from '@/lib/api/client';

// =============================================================================
// Initial State
// =============================================================================

const initialState: DeskState = {
  surface: { type: 'idle' },
  attention: [],
  isLoading: true,
  error: null,
};

// =============================================================================
// Reducer
// =============================================================================

function deskReducer(state: DeskState, action: DeskAction): DeskState {
  switch (action.type) {
    case 'SET_SURFACE':
      return { ...state, surface: action.surface, error: null };

    case 'SET_ATTENTION':
      return { ...state, attention: action.items };

    case 'ADD_ATTENTION':
      // Avoid duplicates
      if (state.attention.some((item) => item.versionId === action.item.versionId)) {
        return state;
      }
      return { ...state, attention: [...state.attention, action.item] };

    case 'REMOVE_ATTENTION':
      return {
        ...state,
        attention: state.attention.filter((item) => item.versionId !== action.versionId),
      };

    case 'CLEAR_SURFACE':
      return { ...state, surface: { type: 'idle' } };

    case 'NEXT_ATTENTION': {
      // If there are items in attention queue, open the first one
      const [next, ...rest] = state.attention;
      if (next) {
        return {
          ...state,
          surface: {
            type: 'deliverable-review',
            deliverableId: next.deliverableId,
            versionId: next.versionId,
          },
          attention: rest,
        };
      }
      return { ...state, surface: { type: 'idle' } };
    }

    case 'SET_LOADING':
      return { ...state, isLoading: action.isLoading };

    case 'SET_ERROR':
      return { ...state, error: action.error, isLoading: false };

    default:
      return state;
  }
}

// =============================================================================
// Context
// =============================================================================

interface DeskContextValue {
  state: DeskState;
  surface: DeskSurface;
  attention: AttentionItem[];
  isLoading: boolean;
  error: string | null;

  // Actions
  setSurface: (surface: DeskSurface) => void;
  clearSurface: () => void;
  nextAttention: () => void;
  refreshAttention: () => Promise<void>;
  removeAttention: (versionId: string) => void;
}

const DeskContext = createContext<DeskContextValue | null>(null);

// =============================================================================
// Provider
// =============================================================================

interface DeskProviderProps {
  children: ReactNode;
}

export function DeskProvider({ children }: DeskProviderProps) {
  const [state, dispatch] = useReducer(deskReducer, initialState);
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // ---------------------------------------------------------------------------
  // Load attention queue on mount
  // ---------------------------------------------------------------------------
  const refreshAttention = useCallback(async () => {
    try {
      const response = await api.deliverables.list();
      const items: AttentionItem[] = [];

      for (const deliverable of response) {
        if (deliverable.latest_version_status === 'staged') {
          // Get the staged version ID
          const detail = await api.deliverables.get(deliverable.id);
          const stagedVersion = detail.versions.find((v) => v.status === 'staged');
          if (stagedVersion) {
            items.push({
              type: 'deliverable-staged',
              deliverableId: deliverable.id,
              versionId: stagedVersion.id,
              title: deliverable.title,
              stagedAt: stagedVersion.staged_at || stagedVersion.created_at,
            });
          }
        }
      }

      // Sort by staged time (oldest first)
      items.sort((a, b) => new Date(a.stagedAt).getTime() - new Date(b.stagedAt).getTime());

      dispatch({ type: 'SET_ATTENTION', items });
    } catch (err) {
      console.error('Failed to load attention queue:', err);
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Initialize: handle deep links and load attention
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const initialize = async () => {
      dispatch({ type: 'SET_LOADING', isLoading: true });

      // Check URL params for deep link
      const surfaceFromUrl = paramsToSurface(searchParams);
      if (surfaceFromUrl.type !== 'idle') {
        dispatch({ type: 'SET_SURFACE', surface: surfaceFromUrl });
      }

      // Load attention queue
      await refreshAttention();

      // If no deep link and we have attention items, show first one
      if (surfaceFromUrl.type === 'idle') {
        // Will be handled after attention loads
      }

      dispatch({ type: 'SET_LOADING', isLoading: false });
    };

    initialize();
  }, [searchParams, refreshAttention]);

  // ---------------------------------------------------------------------------
  // Auto-open first attention item if idle
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!state.isLoading && state.surface.type === 'idle' && state.attention.length > 0) {
      const first = state.attention[0];
      dispatch({
        type: 'SET_SURFACE',
        surface: {
          type: 'deliverable-review',
          deliverableId: first.deliverableId,
          versionId: first.versionId,
        },
      });
    }
  }, [state.isLoading, state.surface.type, state.attention]);

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------
  const setSurface = useCallback(
    (surface: DeskSurface) => {
      dispatch({ type: 'SET_SURFACE', surface });

      // Update URL (shallow, no navigation)
      const params = surfaceToParams(surface);
      const newUrl = `${pathname}?${params.toString()}`;
      router.replace(newUrl, { scroll: false });
    },
    [pathname, router]
  );

  const clearSurface = useCallback(() => {
    dispatch({ type: 'CLEAR_SURFACE' });
    router.replace(pathname, { scroll: false });
  }, [pathname, router]);

  const nextAttention = useCallback(() => {
    dispatch({ type: 'NEXT_ATTENTION' });
  }, []);

  const removeAttention = useCallback((versionId: string) => {
    dispatch({ type: 'REMOVE_ATTENTION', versionId });
  }, []);

  // ---------------------------------------------------------------------------
  // Context value
  // ---------------------------------------------------------------------------
  const value: DeskContextValue = {
    state,
    surface: state.surface,
    attention: state.attention,
    isLoading: state.isLoading,
    error: state.error,
    setSurface,
    clearSurface,
    nextAttention,
    refreshAttention,
    removeAttention,
  };

  return <DeskContext.Provider value={value}>{children}</DeskContext.Provider>;
}

// =============================================================================
// Hook
// =============================================================================

export function useDesk(): DeskContextValue {
  const context = useContext(DeskContext);
  if (!context) {
    throw new Error('useDesk must be used within a DeskProvider');
  }
  return context;
}
