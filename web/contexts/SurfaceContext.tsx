'use client';

/**
 * ADR-013: Conversation + Surfaces
 * Context provider for managing drawer/surface state
 */

import { createContext, useContext, useReducer, useCallback, ReactNode } from 'react';
import type { SurfaceState, SurfaceAction, SurfaceType, SurfaceData, ExpandLevel } from '@/types/surfaces';

const initialState: SurfaceState = {
  isOpen: false,
  type: null,
  data: null,
  expandLevel: 'half',
};

function surfaceReducer(state: SurfaceState, action: SurfaceAction): SurfaceState {
  switch (action.type) {
    case 'OPEN_SURFACE':
      return {
        ...state,
        isOpen: true,
        type: action.payload.surfaceType,
        data: action.payload.data ?? null,
        expandLevel: action.payload.expandLevel ?? 'half',
      };
    case 'CLOSE_SURFACE':
      return {
        ...state,
        isOpen: false,
      };
    case 'SET_EXPAND':
      return {
        ...state,
        expandLevel: action.payload.expandLevel,
      };
    case 'SET_DATA':
      return {
        ...state,
        data: action.payload.data,
      };
    default:
      return state;
  }
}

interface SurfaceContextValue {
  state: SurfaceState;
  openSurface: (type: SurfaceType, data?: SurfaceData, expandLevel?: ExpandLevel) => void;
  closeSurface: () => void;
  setExpand: (level: ExpandLevel) => void;
  setData: (data: SurfaceData) => void;
}

const SurfaceContext = createContext<SurfaceContextValue | null>(null);

export function SurfaceProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(surfaceReducer, initialState);

  const openSurface = useCallback((type: SurfaceType, data?: SurfaceData, expandLevel?: ExpandLevel) => {
    dispatch({
      type: 'OPEN_SURFACE',
      payload: { surfaceType: type, data, expandLevel },
    });
  }, []);

  const closeSurface = useCallback(() => {
    dispatch({ type: 'CLOSE_SURFACE' });
  }, []);

  const setExpand = useCallback((level: ExpandLevel) => {
    dispatch({ type: 'SET_EXPAND', payload: { expandLevel: level } });
  }, []);

  const setData = useCallback((data: SurfaceData) => {
    dispatch({ type: 'SET_DATA', payload: { data } });
  }, []);

  return (
    <SurfaceContext.Provider value={{ state, openSurface, closeSurface, setExpand, setData }}>
      {children}
    </SurfaceContext.Provider>
  );
}

export function useSurface() {
  const context = useContext(SurfaceContext);
  if (!context) {
    throw new Error('useSurface must be used within SurfaceProvider');
  }
  return context;
}
