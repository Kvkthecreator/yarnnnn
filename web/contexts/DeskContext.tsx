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
  isKernelSurfaceSlug,
} from '@/types/desk';
import { api } from '@/lib/api/client';
import { isHomeRoute } from '@/lib/routes';

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
      if (state.attention.some((item) => item.runId === action.item.runId)) {
        return state;
      }
      return { ...state, attention: [...state.attention, action.item] };

    case 'REMOVE_ATTENTION':
      return {
        ...state,
        attention: state.attention.filter((item) => item.runId !== action.runId),
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
            type: 'agent-review',
            agentId: next.agentId,
            runId: next.runId,
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
  removeAttention: (runId: string) => void;
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
      const response = await api.agents.list();
      const items: AttentionItem[] = [];

      for (const agent of response) {
        if (agent.latest_version_status === 'staged') {
          // Get the staged version ID
          const detail = await api.agents.get(agent.id);
          const stagedVersion = detail.versions.find((v) => v.status === 'staged');
          if (stagedVersion) {
            items.push({
              type: 'agent-staged',
              agentId: agent.id,
              runId: stagedVersion.id,
              title: agent.title,
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
  // Initialize: load attention queue on mount
  // ---------------------------------------------------------------------------
  useEffect(() => {
    // Only run initialization once
    if (initializedRef.current) return;
    initializedRef.current = true;

    const initialize = async () => {
      dispatch({ type: 'SET_LOADING', isLoading: true });

      // Load attention queue
      await refreshAttention();

      dispatch({ type: 'SET_LOADING', isLoading: false });
    };

    initialize();
  }, [refreshAttention]);

  // ---------------------------------------------------------------------------
  // Sync surface state with URL (handles direct URL visits + back/forward)
  // ADR-297 axiom: URL is the deep-link transport for the surface state
  // that lives in DeskContext. Direct visits to atomic surface routes
  // (e.g. /cadence) hydrate DeskState into the atomic shape so the rest
  // of the shell (Dock active-highlight, useSurfacePreferences last-
  // active, etc.) sees a consistent picture regardless of how the
  // operator arrived.
  // ---------------------------------------------------------------------------
  useEffect(() => {
    // ADR-297: pathname like `/cadence` maps to an atomic surface in
    // DeskState. The leading slash + first segment is the slug.
    const firstSegment = pathname.split('/').filter(Boolean)[0];
    if (firstSegment && isKernelSurfaceSlug(firstSegment)) {
      const bag: Record<string, string> = {};
      searchParams.forEach((v, k) => { if (v) bag[k] = v; });
      const incoming: DeskSurface = {
        type: 'atomic',
        slug: firstSegment,
        params: Object.keys(bag).length > 0 ? bag : undefined,
      };
      // Avoid dispatch when state already matches — protects against
      // setSurface → URL push → useEffect → setSurface loops.
      const current = state.surface;
      const same =
        current.type === 'atomic' &&
        current.slug === incoming.slug &&
        JSON.stringify(current.params ?? {}) === JSON.stringify(incoming.params ?? {});
      if (!same) {
        dispatch({ type: 'SET_SURFACE', surface: incoming });
      }
      return;
    }

    // Legacy URL-param-driven sync — only on home route (/feed).
    if (!isHomeRoute(pathname)) {
      return;
    }

    // Parse surface from current URL params
    const surfaceFromUrl = paramsToSurface(searchParams);

    // Compare with current state to avoid unnecessary updates
    const currentType = state.surface.type;
    const urlType = surfaceFromUrl.type;

    // Simple comparison - if types differ, update state
    // For complex surfaces, also check IDs
    let shouldUpdate = currentType !== urlType;

    if (!shouldUpdate && currentType === urlType) {
      // Same type, check if IDs differ for surfaces with IDs
      if (currentType === 'agent-detail') {
        const current = state.surface as { type: 'agent-detail'; agentId: string };
        const url = surfaceFromUrl as { type: 'agent-detail'; agentId: string };
        shouldUpdate = current.agentId !== url.agentId;
      } else if (currentType === 'agent-review') {
        const current = state.surface as { type: 'agent-review'; agentId: string; runId: string };
        const url = surfaceFromUrl as { type: 'agent-review'; agentId: string; runId: string };
        shouldUpdate = current.agentId !== url.agentId || current.runId !== url.runId;
      } else if (currentType === 'context-editor') {
        const current = state.surface as { type: 'context-editor'; memoryId: string };
        const url = surfaceFromUrl as { type: 'context-editor'; memoryId: string };
        shouldUpdate = current.memoryId !== url.memoryId;
      } else if (currentType === 'document-viewer') {
        const current = state.surface as { type: 'document-viewer'; documentId: string };
        const url = surfaceFromUrl as { type: 'document-viewer'; documentId: string };
        shouldUpdate = current.documentId !== url.documentId;
      } else if (currentType === 'platform-detail') {
        const current = state.surface as { type: 'platform-detail'; platform: string };
        const url = surfaceFromUrl as { type: 'platform-detail'; platform: string };
        shouldUpdate = current.platform !== url.platform;
      }
    }

    if (shouldUpdate) {
      dispatch({ type: 'SET_SURFACE', surface: surfaceFromUrl });
    }
  }, [searchParams, pathname, state.surface]);

  // Note: Removed auto-redirect from idle to agent-review
  // The dashboard (idle) now shows attention items inline, user clicks to review

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------
  const setSurface = useCallback(
    (surface: DeskSurface) => {
      dispatch({ type: 'SET_SURFACE', surface });

      // ADR-297 axiom: setSurface is the canonical action. URL update
      // is a side effect so deep-links + browser back/forward stay
      // operator-friendly.
      //
      // For atomic surfaces, sync to the per-slug bookmark route
      // (`/cadence`, `/mandate`, etc. — existing kernel routes per
      // kernel_surfaces.py's `route` field). Optional params in the
      // surface bag (task slug, agent slug, file path) become query
      // params on that route. The route is the deep-link transport;
      // DeskState is the source of truth.
      if (surface.type === 'atomic') {
        const target = `/${surface.slug}`;
        if (surface.params && Object.keys(surface.params).length > 0) {
          const qs = new URLSearchParams(surface.params).toString();
          router.push(`${target}?${qs}`, { scroll: false });
        } else if (pathname !== target) {
          router.push(target, { scroll: false });
        }
        return;
      }

      // Legacy non-atomic surfaces — original behavior preserved.
      // Only update URL with surface params when on /feed (home).
      if (isHomeRoute(pathname)) {
        const params = surfaceToParams(surface);
        const newUrl = `${pathname}?${params.toString()}`;
        router.push(newUrl, { scroll: false });
      }
    },
    [pathname, router]
  );

  const clearSurface = useCallback(() => {
    dispatch({ type: 'CLEAR_SURFACE' });
    // Only update URL when on /dashboard
    if (isHomeRoute(pathname)) {
      router.push(pathname, { scroll: false });
    }
  }, [pathname, router]);

  const nextAttention = useCallback(() => {
    dispatch({ type: 'NEXT_ATTENTION' });
  }, []);

  const removeAttention = useCallback((runId: string) => {
    dispatch({ type: 'REMOVE_ATTENTION', runId });
  }, []);

  const setSurfaceWithHandoff = useCallback(
    (surface: DeskSurface, message: string) => {
      dispatch({ type: 'SET_SURFACE_WITH_HANDOFF', surface, handoffMessage: message });

      // Only update URL with surface params when on /dashboard
      if (isHomeRoute(pathname)) {
        const params = surfaceToParams(surface);
        const newUrl = `${pathname}?${params.toString()}`;
        // Use push instead of replace so browser back/forward works
        router.push(newUrl, { scroll: false });
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
