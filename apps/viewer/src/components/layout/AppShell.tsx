import React, { useEffect, useRef } from 'react';
import { useUIStore, uiActions, uiStore } from '../../store/useUIStore';
import type { LayoutMode } from '../../runtime/bridge-types';
import { TopBar } from './TopBar';
import { NavigationRail } from './NavigationRail';
import { ExplorerPanel } from './ExplorerPanel';
import { ViewerStage } from './ViewerStage';
import { InspectorPanel } from './InspectorPanel';
import { AnatomySheet } from './AnatomySheet';
import { OverlayHost } from './OverlayHost';

export const AppShell: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const layoutMode = useUIStore((s) => s.layoutMode);
  const theme = useUIStore((s) => s.theme);

  // Sync theme with root dataset
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  // Viewport & layout calculation according to normative responsive contract
  useEffect(() => {
    const updateLayout = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;

      let mode: LayoutMode;

      if (width < 600) {
        mode = 'compact';
      } else if (height < 500) {
        // Critical Height Guard: When height < 500px, MUST degrade to compact-wide
        // to maximize central anatomical stage without permanent sidebars
        mode = 'compact-wide';
      } else if (width < 840) {
        mode = 'compact-wide';
      } else if (width < 1120) {
        mode = 'tablet';
      } else if (width < 1536) {
        // Workstation guard: requires stage >= 640px and height >= 500px
        const railW = 56;
        const explorerW = 296;
        const potentialStage = width - (railW + explorerW);

        if (potentialStage >= 640 && height >= 500) {
          mode = 'workstation';
        } else {
          mode = 'tablet';
        }
      } else {
        // Pro-wide guard: requires stage >= 720px and height >= 650px
        const railW = 64;
        const explorerW = 296;
        const inspectorW = 344;
        const potentialStage = width - (railW + explorerW + inspectorW);

        if (potentialStage >= 720 && height >= 650) {
          mode = 'pro-wide';
        } else if (width >= 1120 && (width - 56 - 296) >= 640 && height >= 500) {
          mode = 'workstation';
        } else {
          mode = 'tablet';
        }
      }

      if (uiStore.getState().layoutMode !== mode) {
        uiActions.setLayoutMode(mode);
      }
    };

    updateLayout();
    window.addEventListener('resize', updateLayout);
    return () => window.removeEventListener('resize', updateLayout);
  }, []);

  return (
    <div
      ref={containerRef}
      className="atlas-app"
      data-layout={layoutMode}
      data-theme={theme}
    >
      <TopBar />

      <div className="atlas-workspace">
        <NavigationRail />
        <ExplorerPanel />
        <ViewerStage />
        <InspectorPanel />
        <AnatomySheet />
        <OverlayHost />
      </div>
    </div>
  );
};
