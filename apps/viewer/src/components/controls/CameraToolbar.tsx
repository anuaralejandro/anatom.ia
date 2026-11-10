import React from 'react';

interface CameraToolbarProps {
  onResetCamera?: () => void;
  onFocus?: () => void;
}

export const CameraToolbar: React.FC<CameraToolbarProps> = ({
  onResetCamera,
  onFocus,
}) => {
  return (
    <div className="atlas-camera-toolbar" role="toolbar" aria-label="Acciones de cámara anatómica">
      <button
        type="button"
        className="atlas-btn atlas-btn-icon atlas-control-btn"
        disabled
        onClick={onResetCamera}
        title="Restablecer cámara · Disponible en M05-B con AtlasEngine 3D"
        aria-label="Restablecer cámara (Disponible en M05-B)"
        style={{ minWidth: '44px', minHeight: '44px' }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
      </button>

      <div className="atlas-toolbar-divider" />

      <button
        type="button"
        className="atlas-btn atlas-btn-icon atlas-control-btn"
        disabled
        onClick={onFocus}
        title="Enfocar estructura seleccionada · Disponible en M05-B con AtlasEngine 3D"
        aria-label="Enfocar estructura (Disponible en M05-B)"
        style={{ minWidth: '44px', minHeight: '44px' }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      </button>
    </div>
  );
};
