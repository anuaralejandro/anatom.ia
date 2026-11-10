import React from 'react';
import { useUIStore, uiActions } from '../../store/useUIStore';
import type { QualityProfile } from '../../runtime/bridge-types';

export const QualitySelector: React.FC = () => {
  const quality = useUIStore((s) => s.qualityPreference);

  return (
    <select
      className="atlas-btn atlas-control-btn"
      value={quality}
      onChange={(e) => uiActions.setQualityPreference(e.target.value as QualityProfile)}
      aria-label="Perfil de calidad de renderizado"
      style={{ paddingRight: '24px', minHeight: '44px' }}
    >
      <option value="low">Calidad: Baja</option>
      <option value="medium">Calidad: Media</option>
      <option value="high">Calidad: Alta</option>
    </select>
  );
};
