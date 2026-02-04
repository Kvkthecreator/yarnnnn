'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * Desk context - manages current surface and attention queue
 */

import React, { createContext, useContext, useReducer, useCallback, useEffect, useRef, ReactNode } from 'react';
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
  handoffMessage: null,
};

// =============================================================================
// Reducer
// =============================================================================

function deskReducer(state: DeskState, action: DeskAction): DeskState {
  switch (action.type) {
    case 'SET_SURFACE':
      return { ...state, surface: action.surface, error: null, handoffMessage: null };

    case 'SET_SURFACE_WITH_HANDOFF':
      return { ...state, surface: action.surface, handoffMessage: action.handoffMessage, error: null };

    case 'CLEAR_HANDOFF':
      return { ...state, handoffMessage: null };

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
  /** Message from TP shown at top of surface after navigation */
  handoffMessage: string | null;

  // Actions
  setSurface: (surface: DeskSurface) => void;
  /** Set surface with a handoff message from TP */
  setSurfaceWithHandoff: (surface: DeskSurface, message: string) => void;
  clearSurface: () => void;
  clearHandoff: () => void;
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
  const initializedRef = useRef(false);

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
  // Initialize: handle deep links and load attention (only once on mount)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    // Only run initialization once
    if (initializedRef.current) return;
    initializedRef.current = true;

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

  // Note: Removed auto-redirect from idle to deliverable-review
  // The dashboard (idle) now shows attention items inline, user clicks to review

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------
  const setSurface = useCallback(
    (surface: DeskSurface) => {
      dispatch({ type: 'SET_SURFACE', surface });

      // Only update URL with surface params when on /dashboard
      // Other routes (like /settings) don't use the surface system
      if (pathname === '/dashboard' || pathname.startsWith('/dashboard/')) {
        const params = surfaceToParams(surface);
        const newUrl = `${pathname}?${params.toString()}`;
        router.replace(newUrl, { scroll: false });
      }
    },
    [pathname, router]
  );

  const clearSurface = useCallback(() => {
    dispatch({ type: 'CLEAR_SURFACE' });
    // Only update URL when on /dashboard
    if (pathname === '/dashboard' || pathname.startsWith('/dashboard/')) {
      router.replace(pathname, { scroll: false });
    }
  }, [pathname, router]);

  const nextAttention = useCallback(() => {
    dispatch({ type: 'NEXT_ATTENTION' });
  }, []);

  const removeAttention = useCallback((versionId: string) => {
    dispatch({ type: 'REMOVE_ATTENTION', versionId });
  }, []);

  const setSurfaceWithHandoff = useCallback(
    (surface: DeskSurface, message: string) => {
      dispatch({ type: 'SET_SURFACE_WITH_HANDOFF', surface, handoffMessage: message });

      // Only update URL with surface params when on /dashboard
      if (pathname === '/dashboard' || pathname.startsWith('/dashboard/')) {
        const params = surfaceToParams(surface);
        const newUrl = `${pathname}?${params.toString()}`;
        router.replace(newUrl, { scroll: false });
      }
    },
    [pathname, router]
  );

  const clearHandoff = useCallback(() => {
    dispatch({ type: 'CLEAR_HANDOFF' });
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
    handoffMessage: state.handoffMessage,
    setSurface,
    setSurfaceWithHandoff,
    clearSurface,
    clearHandoff,
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
