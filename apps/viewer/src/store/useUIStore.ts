/**
 * ANATOM.IA — UI STORE
 * Lightweight pub/sub store with useSyncExternalStore for strict React 18+ concurrency.
 */

import { useSyncExternalStore, useCallback } from 'react';
import type {
  ThemeMode,
  LayoutMode,
  ActiveOverlay,
  SheetSnap,
  QualityProfile,
  AnatomyStructure,
} from '../runtime/bridge-types';
import { PELVIS_STRUCTURES } from '../data/canonicalCatalog';

export interface UIState {
  theme: ThemeMode;
  layoutMode: LayoutMode;
  activeOverlay: ActiveOverlay;
  sheetSnap: SheetSnap;
  sheetTab: 'info' | 'tree';
  searchQuery: string;
  selectedCategory: string;
  selectedId: string | null;
  structures: AnatomyStructure[];
  qualityPreference: QualityProfile;
  backend: 'webgpu' | 'webgl2';
  isOffline: boolean;
  focusReturnTarget: HTMLElement | null;
}

const initialState: UIState = {
  theme: 'dark',
  layoutMode: 'pro-wide',
  activeOverlay: 'none',
  sheetSnap: 'collapsed',
  sheetTab: 'info',
  searchQuery: '',
  selectedCategory: 'all',
  selectedId: 'ta2:1071', // Default focus on Sacrum as in approved D0
  structures: PELVIS_STRUCTURES,
  qualityPreference: 'medium',
  backend: 'webgpu',
  isOffline: false,
  focusReturnTarget: null,
};

type Listener = () => void;
let state: UIState = { ...initialState };
const listeners = new Set<Listener>();

function emitChange() {
  for (const listener of listeners) {
    listener();
  }
}

export const uiStore = {
  getState(): UIState {
    return state;
  },
  setState(fn: (prev: UIState) => Partial<UIState>) {
    const update = fn(state);
    state = { ...state, ...update };
    emitChange();
  },
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};

export function useUIStore<T>(selector: (s: UIState) => T): T {
  const getSnapshot = useCallback(() => selector(uiStore.getState()), [selector]);
  return useSyncExternalStore(uiStore.subscribe, getSnapshot);
}

// Action Helpers
export const uiActions = {
  setTheme(theme: ThemeMode) {
    uiStore.setState(() => ({ theme }));
    document.documentElement.dataset.theme = theme;
  },
  toggleTheme() {
    const next = uiStore.getState().theme === 'dark' ? 'light' : 'dark';
    this.setTheme(next);
  },
  setLayoutMode(layoutMode: LayoutMode) {
    uiStore.setState(() => ({ layoutMode }));
  },
  openOverlay(overlay: ActiveOverlay, returnTarget?: HTMLElement | null) {
    uiStore.setState((prev) => ({
      activeOverlay: overlay,
      focusReturnTarget: returnTarget ?? prev.focusReturnTarget,
    }));
  },
  closeOverlay() {
    const returnTarget = uiStore.getState().focusReturnTarget;
    uiStore.setState(() => ({ activeOverlay: 'none', focusReturnTarget: null }));
    if (returnTarget && typeof returnTarget.focus === 'function') {
      returnTarget.focus();
    }
  },
  setSheetSnap(sheetSnap: SheetSnap) {
    uiStore.setState(() => ({ sheetSnap }));
  },
  setSheetTab(sheetTab: 'info' | 'tree') {
    uiStore.setState(() => ({ sheetTab }));
  },
  setSearchQuery(searchQuery: string) {
    uiStore.setState(() => ({ searchQuery }));
  },
  setSelectedCategory(selectedCategory: string) {
    uiStore.setState(() => ({ selectedCategory }));
  },
  selectStructure(id: string | null) {
    uiStore.setState(() => ({ selectedId: id }));
  },
  toggleVisibility(id: string) {
    uiStore.setState((prev) => ({
      structures: prev.structures.map((s) =>
        s.id === id ? { ...s, visible: !(s.visible ?? true) } : s
      ),
    }));
  },
  isolateStructure(id: string) {
    uiStore.setState((prev) => ({
      selectedId: id,
      structures: prev.structures.map((s) => ({
        ...s,
        visible: s.id === id,
      })),
    }));
  },
  resetVisibility() {
    uiStore.setState((prev) => ({
      structures: prev.structures.map((s) => ({ ...s, visible: true })),
    }));
  },
  setQualityPreference(qualityPreference: QualityProfile) {
    uiStore.setState(() => ({ qualityPreference }));
  },
  setBackend(backend: 'webgpu' | 'webgl2') {
    uiStore.setState(() => ({ backend }));
  },
  setOffline(isOffline: boolean) {
    uiStore.setState(() => ({ isOffline }));
  },
};
