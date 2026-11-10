import React from 'react';
import { useUIStore, uiActions } from '../../store/useUIStore';
import { ThemeToggle } from '../controls/ThemeToggle';
import { QualitySelector } from '../controls/QualitySelector';

export const TopBar: React.FC = () => {
  const layoutMode = useUIStore((s) => s.layoutMode);
  const activeOverlay = useUIStore((s) => s.activeOverlay);

  const isCompactOrTablet = layoutMode === 'compact' || layoutMode === 'compact-wide' || layoutMode === 'tablet';

  return (
    <header className="atlas-topbar">
      {/* Brand & Breadcrumbs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', minWidth: 0 }}>
        {isCompactOrTablet && (
          <button
            type="button"
            className="atlas-btn atlas-btn-icon atlas-control-btn"
            onClick={(e) => {
              if (activeOverlay === 'explorer') {
                uiActions.closeOverlay();
              } else {
                uiActions.openOverlay('explorer', e.currentTarget);
              }
            }}
            title="Abrir explorador de estructuras"
            aria-label="Abrir explorador"
            style={{ minWidth: '44px', minHeight: '44px' }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        )}

        <a href="/" className="atlas-brand" aria-label="anatom.ia Inicio">
          <div className="atlas-brand-mark">A</div>
          <span className="atlas-brand-title">anatom.ia</span>
        </a>

        <nav className="atlas-breadcrumb" aria-label="Ubicación anatómica">
          <span className="atlas-breadcrumb-sep">/</span>
          <span>Pelvis</span>
          <span className="atlas-breadcrumb-sep">/</span>
          <span className="atlas-breadcrumb-current">Masculino</span>
        </nav>
      </div>

      {/* Center Status: Truthful Conceptual Preview Indicator (F12) */}
      <div className="atlas-topbar-center">
        <div
          className="atlas-badge atlas-badge-conceptual"
          title="Vista conceptual M05-A · Enlace WebGPU/WebGL2 en M05-B"
          role="status"
          aria-label="Estado del motor: Vista conceptual M05-A"
        >
          <span className="atlas-badge-dot" />
          <span>VISTA CONCEPTUAL</span>
        </div>
      </div>

      {/* Right Actions */}
      <div className="atlas-topbar-actions">
        {layoutMode !== 'compact' && <QualitySelector />}
        <ThemeToggle />

        {isCompactOrTablet && (
          <button
            type="button"
            className="atlas-btn atlas-btn-icon atlas-control-btn"
            onClick={(e) => {
              if (activeOverlay === 'inspector') {
                uiActions.closeOverlay();
              } else {
                uiActions.openOverlay('inspector', e.currentTarget);
              }
            }}
            title="Abrir inspector de información"
            aria-label="Abrir inspector"
            style={{ minWidth: '44px', minHeight: '44px' }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
          </button>
        )}
      </div>
    </header>
  );
};
