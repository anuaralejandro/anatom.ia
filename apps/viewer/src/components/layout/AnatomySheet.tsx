import React, { useRef } from 'react';
import { useUIStore, uiActions } from '../../store/useUIStore';
import { StructureIdentity } from '../anatomy/StructureIdentity';
import { AnatomyTree } from '../anatomy/AnatomyTree';
import { AnatomySearch } from '../anatomy/AnatomySearch';

export const AnatomySheet: React.FC = () => {
  const snap = useUIStore((s) => s.sheetSnap);
  const activeTab = useUIStore((s) => s.sheetTab);
  const selectedId = useUIStore((s) => s.selectedId);
  const structures = useUIStore((s) => s.structures);

  const selected = structures.find((s) => s.id === selectedId);
  const sheetRef = useRef<HTMLDivElement>(null);

  // Compute height based on snap
  const sheetHeight =
    snap === 'expanded' ? '86%' : snap === 'mid' ? '52%' : '110px';

  return (
    <div
      ref={sheetRef}
      className="atlas-sheet"
      style={{ height: sheetHeight }}
      role="region"
      aria-label="Panel móvil de anatomía"
    >
      {/* Handle as accessible button */}
      <button
        type="button"
        className="atlas-sheet-handle-row atlas-control-btn"
        onClick={() => {
          if (snap === 'collapsed') uiActions.setSheetSnap('mid');
          else if (snap === 'mid') uiActions.setSheetSnap('expanded');
          else uiActions.setSheetSnap('collapsed');
        }}
        title="Arrastra o pulsa para cambiar tamaño del panel"
        aria-label={`Panel de anatomía en estado ${snap}. Pulsa para alternar tamaño.`}
        style={{ minHeight: '44px', width: '100%', border: 'none', background: 'none' }}
      >
        <div className="atlas-sheet-handle" />
      </button>

      {/* Collapsed Header / Summary */}
      {snap === 'collapsed' ? (
        <div
          style={{
            padding: '0 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            minHeight: '44px',
          }}
          onClick={() => uiActions.setSheetSnap('mid')}
        >
          <div>
            <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
              {selected ? selected.labels.es : 'Explorar estructuras'}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              {selected ? `TA2: ${selected.ta2Id} · ${selected.labels.la}` : 'Toca para abrir lista'}
            </div>
          </div>
          <button
            type="button"
            className="atlas-btn atlas-btn-primary atlas-control-btn"
            style={{ minHeight: '44px', padding: '8px 14px' }}
            onClick={(e) => {
              e.stopPropagation();
              uiActions.setSheetSnap('mid');
            }}
          >
            Ver detalles
          </button>
        </div>
      ) : (
        <>
          {/* Tabs */}
          <div className="atlas-sheet-tabs" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'info'}
              className={`atlas-sheet-tab atlas-control-btn ${activeTab === 'info' ? 'atlas-active' : ''}`}
              onClick={() => uiActions.setSheetTab('info')}
              style={{ minHeight: '44px' }}
            >
              Información
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'tree'}
              className={`atlas-sheet-tab atlas-control-btn ${activeTab === 'tree' ? 'atlas-active' : ''}`}
              onClick={() => uiActions.setSheetTab('tree')}
              style={{ minHeight: '44px' }}
            >
              Estructuras ({structures.length})
            </button>
            <button
              type="button"
              className="atlas-btn atlas-btn-icon atlas-control-btn"
              style={{ minWidth: '44px', minHeight: '44px', marginLeft: 'auto' }}
              onClick={() => uiActions.setSheetSnap('collapsed')}
              title="Colapsar panel"
              aria-label="Colapsar panel"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </button>
          </div>

          {/* Body */}
          <div className="atlas-sheet-body">
            {activeTab === 'info' ? (
              selected ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <StructureIdentity structure={selected} />
                  <div className="atlas-actions-grid">
                    <button
                      type="button"
                      className="atlas-btn atlas-btn-primary atlas-control-btn"
                      onClick={() => uiActions.isolateStructure(selected.id)}
                      style={{ minHeight: '44px' }}
                    >
                      Aislar (Demo)
                    </button>
                    <button
                      type="button"
                      className="atlas-btn atlas-control-btn"
                      onClick={() => uiActions.toggleVisibility(selected.id)}
                      style={{ minHeight: '44px' }}
                    >
                      {selected.visible !== false ? 'Ocultar (Demo)' : 'Mostrar (Demo)'}
                    </button>
                  </div>
                  <div className="atlas-meta-grid">
                    <div className="atlas-meta-item">
                      <span className="atlas-meta-label">Sistema</span>
                      <span className="atlas-meta-value">{selected.system}</span>
                    </div>
                    <div className="atlas-meta-item">
                      <span className="atlas-meta-label">Categoría</span>
                      <span className="atlas-meta-value" style={{ textTransform: 'capitalize' }}>
                        {selected.category}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="atlas-empty-state">
                  <p>Selecciona una estructura para inspeccionar detalles.</p>
                </div>
              )
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <AnatomySearch />
                <AnatomyTree />
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
