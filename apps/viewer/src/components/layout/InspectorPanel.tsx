import React from 'react';
import { useUIStore, uiActions } from '../../store/useUIStore';
import { StructureIdentity } from '../anatomy/StructureIdentity';

interface InspectorPanelProps {
  isDrawer?: boolean;
  onClose?: () => void;
}

export const InspectorPanel: React.FC<InspectorPanelProps> = ({ isDrawer, onClose }) => {
  const structures = useUIStore((s) => s.structures);
  const selectedId = useUIStore((s) => s.selectedId);

  const selected = structures.find((s) => s.id === selectedId);

  return (
    <aside
      className={`atlas-inspector ${isDrawer ? 'atlas-drawer atlas-drawer-right' : 'atlas-inspector-permanent'}`}
      aria-label="Panel de inspección anatómica"
    >
      <div className="atlas-inspector-header">
        {selected ? (
          <StructureIdentity structure={selected} />
        ) : (
          <div className="atlas-inspector-title-group">
            <h2 className="atlas-inspector-title">Sin selección</h2>
            <div className="atlas-inspector-latin">Selecciona una estructura</div>
          </div>
        )}

        {isDrawer && (
          <button
            type="button"
            className="atlas-btn atlas-btn-icon atlas-control-btn"
            onClick={onClose}
            title="Cerrar inspector"
            aria-label="Cerrar inspector"
            style={{ minWidth: '44px', minHeight: '44px' }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}
      </div>

      <div className="atlas-inspector-body">
        {selected ? (
          <>
            {/* Metadata Card */}
            <div className="atlas-inspector-section">
              <span className="atlas-section-title">Metadatos clínicos</span>
              <div className="atlas-meta-grid">
                <div className="atlas-meta-item">
                  <span className="atlas-meta-label">Sistema</span>
                  <span className="atlas-meta-value">{selected.system}</span>
                </div>
                <div className="atlas-meta-item">
                  <span className="atlas-meta-label">Lateralidad</span>
                  <span className="atlas-meta-value" style={{ textTransform: 'capitalize' }}>
                    {selected.side === 'unpaired_or_unspecified' ? 'Impar / Medio' : selected.side}
                  </span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="atlas-inspector-section">
              <span className="atlas-section-title">Acciones anatómicas (Simulación UI)</span>
              <div className="atlas-actions-grid">
                <button
                  type="button"
                  className="atlas-btn atlas-btn-primary atlas-control-btn"
                  onClick={() => uiActions.isolateStructure(selected.id)}
                  title="Aislar esta estructura (Simulación en árbol · Motor 3D en M05-B)"
                  aria-label={`Aislar ${selected.labels.es}`}
                  style={{ minHeight: '44px' }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <circle cx="12" cy="12" r="4" />
                  </svg>
                  Aislar (Demo)
                </button>

                <button
                  type="button"
                  className="atlas-btn atlas-control-btn"
                  onClick={() => uiActions.toggleVisibility(selected.id)}
                  title={selected.visible !== false ? 'Ocultar esta estructura (Simulación · Motor 3D en M05-B)' : 'Mostrar esta estructura (Simulación · Motor 3D en M05-B)'}
                  aria-label={selected.visible !== false ? `Ocultar ${selected.labels.es}` : `Mostrar ${selected.labels.es}`}
                  style={{ minHeight: '44px' }}
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                  {selected.visible !== false ? 'Ocultar (Demo)' : 'Mostrar (Demo)'}
                </button>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                * Control en modo conceptual; enlace GPU 3D real reservado para M05-B.
              </div>
            </div>

            {/* License Note */}
            <div
              style={{
                marginTop: 'auto',
                padding: '12px',
                borderRadius: '8px',
                backgroundColor: 'var(--bg-app)',
                border: '1px solid var(--border)',
                fontSize: '11px',
                color: 'var(--text-muted)',
                lineHeight: 1.4,
              }}
            >
              <strong>Contrato de fuente:</strong> TA2.csv verificado (26/26 IDs). Categorías validadas según Terminologia Anatomica 2. Assets 3D sujetos a revisión de licencia individual.
            </div>
          </>
        ) : (
          <div className="atlas-empty-state">
            <svg className="atlas-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
            <p style={{ fontSize: '13px' }}>Toca o haz clic sobre una estructura en el visor o selecciónala en el explorador.</p>
          </div>
        )}
      </div>
    </aside>
  );
};
