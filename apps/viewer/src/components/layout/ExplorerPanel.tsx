import React from 'react';
import { useUIStore, uiActions } from '../../store/useUIStore';
import { AnatomySearch } from '../anatomy/AnatomySearch';
import { AnatomyTree } from '../anatomy/AnatomyTree';

interface ExplorerPanelProps {
  isDrawer?: boolean;
  onClose?: () => void;
}

const CATEGORIES = [
  { id: 'all', label: 'Todos' },
  { id: 'bone', label: 'Huesos' },
  { id: 'joint', label: 'Articulaciones' },
  { id: 'muscle', label: 'Músculos' },
  { id: 'organ', label: 'Órganos' },
  { id: 'vascular', label: 'Vasos' },
  { id: 'nervous', label: 'Nervios' },
];

export const ExplorerPanel: React.FC<ExplorerPanelProps> = ({ isDrawer, onClose }) => {
  const structures = useUIStore((s) => s.structures);
  const activeCategory = useUIStore((s) => s.selectedCategory);

  return (
    <aside
      className={`atlas-explorer ${isDrawer ? 'atlas-drawer atlas-drawer-left' : 'atlas-explorer-permanent'}`}
      aria-label="Panel de exploración anatómica"
    >
      <div className="atlas-explorer-header">
        <div className="atlas-explorer-title-row">
          <span className="atlas-explorer-title">Estructuras</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="atlas-explorer-count">{structures.length} elementos</span>
            {isDrawer && (
              <button
                type="button"
                className="atlas-btn atlas-btn-icon atlas-control-btn"
                onClick={onClose}
                title="Cerrar explorador"
                aria-label="Cerrar explorador"
                style={{ minWidth: '44px', minHeight: '44px' }}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>
        </div>

        <AnatomySearch />

        <div className="atlas-filter-chips" role="tablist" aria-label="Filtrar por categoría">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              type="button"
              role="tab"
              aria-selected={activeCategory === cat.id}
              className={`atlas-chip ${activeCategory === cat.id ? 'atlas-active' : ''}`}
              onClick={() => uiActions.setSelectedCategory(cat.id)}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      <AnatomyTree />
    </aside>
  );
};
