import React, { useMemo } from 'react';
import { useUIStore, uiActions } from '../../store/useUIStore';

export const AnatomyTree: React.FC = () => {
  const structures = useUIStore((s) => s.structures);
  const selectedId = useUIStore((s) => s.selectedId);
  const query = useUIStore((s) => s.searchQuery).toLowerCase().trim();
  const category = useUIStore((s) => s.selectedCategory);

  const filtered = useMemo(() => {
    return structures.filter((s) => {
      // Category filter
      if (category !== 'all' && s.category !== category) {
        return false;
      }
      // Query filter
      if (!query) return true;
      const matchEs = s.labels.es.toLowerCase().includes(query);
      const matchEn = s.labels.en.toLowerCase().includes(query);
      const matchLa = s.labels.la.toLowerCase().includes(query);
      const matchId = s.ta2Id.toLowerCase().includes(query) || s.id.toLowerCase().includes(query);
      return matchEs || matchEn || matchLa || matchId;
    });
  }, [structures, query, category]);

  if (filtered.length === 0) {
    return (
      <div className="atlas-empty-state">
        <svg className="atlas-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <p style={{ fontSize: '13px' }}>No se encontraron estructuras con ese criterio.</p>
      </div>
    );
  }

  return (
    <div className="atlas-explorer-body" role="tree" aria-label="Árbol de estructuras anatómicas">
      {filtered.map((item) => {
        const isSelected = item.id === selectedId;
        const isVisible = item.visible ?? true;

        return (
          <div
            key={item.id}
            role="treeitem"
            tabIndex={0}
            aria-selected={isSelected}
            className={`atlas-tree-node ${isSelected ? 'atlas-selected' : ''}`}
            onClick={() => uiActions.selectStructure(item.id)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                uiActions.selectStructure(item.id);
              }
            }}
          >
            <div className="atlas-tree-content">
              <span className="atlas-tree-label">{item.labels.es}</span>
            </div>

            <div className="atlas-tree-actions">
              <button
                type="button"
                className="atlas-tree-action-btn"
                title={isVisible ? 'Ocultar estructura' : 'Mostrar estructura'}
                aria-label={isVisible ? `Ocultar ${item.labels.es}` : `Mostrar ${item.labels.es}`}
                onClick={(e) => {
                  e.stopPropagation();
                  uiActions.toggleVisibility(item.id);
                }}
              >
                {isVisible ? (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                ) : (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};
