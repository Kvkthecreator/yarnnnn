'use client';

/**
 * ADR-020: Deliverable-Centric Chat
 *
 * Context provider for floating chat that's accessible from any page.
 * Chat is contextual - it adapts to the current page and provides
 * relevant context to Thinking Partner.
 */

import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  ReactNode,
  useEffect,
} from 'react';
import type { Deliverable, DeliverableVersion } from '@/types';

// Page context types for different views
export type PageContextType =
  | 'global'
  | 'deliverables-dashboard'
  | 'deliverable-detail'
  | 'deliverable-review'
  | 'project';

export interface PageContext {
  type: PageContextType;
  // Deliverable context
  deliverable?: Deliverable | null;
  deliverableId?: string;
  currentVersion?: DeliverableVersion | null;
  // Project context (legacy)
  projectId?: string;
  projectName?: string;
}

interface FloatingChatState {
  isOpen: boolean;
  isMinimized: boolean;
  pageContext: PageContext;
  // Track if user manually opened/closed to avoid auto-opening
  userInteracted: boolean;
}

type FloatingChatAction =
  | { type: 'OPEN' }
  | { type: 'CLOSE' }
  | { type: 'MINIMIZE' }
  | { type: 'RESTORE' }
  | { type: 'TOGGLE' }
  | { type: 'SET_PAGE_CONTEXT'; payload: PageContext };

const initialState: FloatingChatState = {
  isOpen: false,
  isMinimized: false,
  pageContext: { type: 'global' },
  userInteracted: false,
};

function floatingChatReducer(
  state: FloatingChatState,
  action: FloatingChatAction
): FloatingChatState {
  switch (action.type) {
    case 'OPEN':
      return {
        ...state,
        isOpen: true,
        isMinimized: false,
        userInteracted: true,
      };
    case 'CLOSE':
      return {
        ...state,
        isOpen: false,
        isMinimized: false,
        userInteracted: true,
      };
    case 'MINIMIZE':
      return {
        ...state,
        isMinimized: true,
      };
    case 'RESTORE':
      return {
        ...state,
        isMinimized: false,
      };
    case 'TOGGLE':
      return {
        ...state,
        isOpen: !state.isOpen,
        isMinimized: false,
        userInteracted: true,
      };
    case 'SET_PAGE_CONTEXT':
      return {
        ...state,
        pageContext: action.payload,
      };
    default:
      return state;
  }
}

interface FloatingChatContextValue {
  state: FloatingChatState;
  open: () => void;
  close: () => void;
  minimize: () => void;
  restore: () => void;
  toggle: () => void;
  setPageContext: (context: PageContext) => void;
}

const FloatingChatContext = createContext<FloatingChatContextValue | null>(null);

export function FloatingChatProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(floatingChatReducer, initialState);

  const open = useCallback(() => {
    dispatch({ type: 'OPEN' });
  }, []);

  const close = useCallback(() => {
    dispatch({ type: 'CLOSE' });
  }, []);

  const minimize = useCallback(() => {
    dispatch({ type: 'MINIMIZE' });
  }, []);

  const restore = useCallback(() => {
    dispatch({ type: 'RESTORE' });
  }, []);

  const toggle = useCallback(() => {
    dispatch({ type: 'TOGGLE' });
  }, []);

  const setPageContext = useCallback((context: PageContext) => {
    dispatch({ type: 'SET_PAGE_CONTEXT', payload: context });
  }, []);

  // Listen for keyboard shortcut (Cmd/Ctrl + K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        dispatch({ type: 'TOGGLE' });
      }
      // Escape to close
      if (e.key === 'Escape' && state.isOpen) {
        dispatch({ type: 'CLOSE' });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state.isOpen]);

  return (
    <FloatingChatContext.Provider
      value={{
        state,
        open,
        close,
        minimize,
        restore,
        toggle,
        setPageContext,
      }}
    >
      {children}
    </FloatingChatContext.Provider>
  );
}

export function useFloatingChat() {
  const context = useContext(FloatingChatContext);
  if (!context) {
    throw new Error('useFloatingChat must be used within FloatingChatProvider');
  }
  return context;
}
