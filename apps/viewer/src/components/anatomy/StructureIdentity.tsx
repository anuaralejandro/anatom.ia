import React from 'react';
import type { AnatomyStructure } from '../../runtime/bridge-types';

interface StructureIdentityProps {
  structure: AnatomyStructure;
}

export const StructureIdentity: React.FC<StructureIdentityProps> = ({ structure }) => {
  return (
    <div className="atlas-inspector-title-group">
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
        <span className="atlas-inspector-id-pill">TA2: {structure.ta2Id}</span>
        <span className="atlas-badge" style={{ textTransform: 'capitalize' }}>
          {structure.category}
        </span>
      </div>
      <h2 className="atlas-inspector-title">{structure.labels.es}</h2>
      <div className="atlas-inspector-latin">{structure.labels.la}</div>
      <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
        EN: {structure.labels.en}
      </div>
    </div>
  );
};
