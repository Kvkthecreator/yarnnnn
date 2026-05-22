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

      // D19.2 (2026-05-22): atomic-surface URL-write branch DELETED.
      // The pre-D19.2 setSurface(atomic) wrote the URL via
      // window.history.replaceState. Removed because URL is
      // informational add-on of the workspace, not a tracker of the
      // foregrounded window — the Dock indicator dot is the canonical
      // "what's foregrounded" signal. Cold-load deep-link transport
      // still works because Effect A in AuthenticatedLayout reads
      // pathname on first paint and calls foregroundSurface(match.slug);
      // after first paint the URL stays where the cold-load put it
      // (typically /desktop). Singular Implementation: foregroundSurface
      // owns "open + foreground"; setSurface owns DeskState for legacy
      // consumers; no parallel URL-writing mechanism.
      if (surface.type === 'atomic') {
        return;
      }

      // Legacy non-atomic surfaces — original behavior preserved.
      // Only update URL with surface params when on /feed (home).
      if (isHomeRoute(pathname)) {
        const params = surfaceToParams(surface);
        const newUrl = `${pathname}?${params.toString()}`;
        if (typeof window !== 'undefined') {
          window.history.replaceState(null, '', newUrl);
        }
      }
    },
    [pathname]
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

      // D19.2 (2026-05-22): atomic-surface URL-write branch DELETED.
      // Mirrors setSurface — URL is informational add-on, not a
      // tracker of the foregrounded window. See setSurface above.
      if (surface.type === 'atomic') {
        return;
      }

      if (isHomeRoute(pathname)) {
        const params = surfaceToParams(surface);
        const newUrl = `${pathname}?${params.toString()}`;
        if (typeof window !== 'undefined') {
          window.history.replaceState(null, '', newUrl);
        }
      }
    },
    [pathname]
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
