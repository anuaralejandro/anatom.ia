import React from 'react';
import { useUIStore, uiActions } from '../../store/useUIStore';

export const AnatomySearch: React.FC = () => {
  const query = useUIStore((s) => s.searchQuery);

  return (
    <div className="atlas-search-box">
      <svg
        className="atlas-search-icon"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
      <input
        type="search"
        className="atlas-search-input"
        placeholder="Buscar por TA2, español, latín..."
        value={query}
        onChange={(e) => uiActions.setSearchQuery(e.target.value)}
        aria-label="Buscar estructuras anatómicas"
        autoComplete="off"
        spellCheck="false"
      />
      {query && (
        <button
          type="button"
          className="atlas-search-clear"
          onClick={() => uiActions.setSearchQuery('')}
          title="Borrar búsqueda"
          aria-label="Borrar búsqueda"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      )}
    </div>
  );
};
