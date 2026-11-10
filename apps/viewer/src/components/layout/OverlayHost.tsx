import React, { useEffect, useRef, useCallback } from 'react';
import { useUIStore, uiActions, uiStore } from '../../store/useUIStore';
import { ExplorerPanel } from './ExplorerPanel';
import { InspectorPanel } from './InspectorPanel';

export const OverlayHost: React.FC = () => {
  const activeOverlay = useUIStore((s) => s.activeOverlay);
  const drawerRef = useRef<HTMLDivElement>(null);

  // Focus trap and keyboard navigation handler
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        uiActions.closeOverlay();
        return;
      }

      if (e.key === 'Tab') {
        const container = drawerRef.current;
        if (!container) return;

        const focusableSelector =
          'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
        const focusables = Array.from(
          container.querySelectorAll<HTMLElement>(focusableSelector)
        ).filter((el) => {
          const style = window.getComputedStyle(el);
          return style.display !== 'none' && style.visibility !== 'hidden';
        });

        if (focusables.length === 0) {
          e.preventDefault();
          return;
        }

        const first = focusables[0];
        const last = focusables[focusables.length - 1];

        if (e.shiftKey) {
          // Backward tab
          if (document.activeElement === first || !container.contains(document.activeElement)) {
            e.preventDefault();
            last.focus();
          }
        } else {
          // Forward tab
          if (document.activeElement === last || !container.contains(document.activeElement)) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    },
    []
  );

  useEffect(() => {
    if (activeOverlay !== 'none') {
      // Store trigger element if none already registered
      if (!uiStore.getState().focusReturnTarget && document.activeElement instanceof HTMLElement) {
        uiStore.setState(() => ({ focusReturnTarget: document.activeElement as HTMLElement }));
      }

      window.addEventListener('keydown', handleKeyDown);

      // Initial focus transfer into drawer
      const timer = setTimeout(() => {
        if (!drawerRef.current) return;
        const firstFocusable = drawerRef.current.querySelector<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (firstFocusable) {
          firstFocusable.focus();
        }
      }, 30);

      return () => {
        clearTimeout(timer);
        window.removeEventListener('keydown', handleKeyDown);
      };
    }
    return undefined;
  }, [activeOverlay, handleKeyDown]);

  if (activeOverlay === 'none') {
    return null;
  }

  const overlayTitle =
    activeOverlay === 'explorer' ? 'Explorador anatómico' : 'Inspector de estructura';

  return (
    <>
      <div
        className="atlas-drawer-backdrop"
        onClick={() => uiActions.closeOverlay()}
        aria-hidden="true"
      />

      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-label={overlayTitle}
        tabIndex={-1}
        style={{ outline: 'none' }}
      >
        {activeOverlay === 'explorer' && (
          <ExplorerPanel isDrawer onClose={() => uiActions.closeOverlay()} />
        )}

        {activeOverlay === 'inspector' && (
          <InspectorPanel isDrawer onClose={() => uiActions.closeOverlay()} />
        )}
      </div>
    </>
  );
};
