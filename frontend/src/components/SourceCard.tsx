// frontend/src/components/SourceCard.tsx
import React from 'react';
import type { Source } from '../types/api';

interface SourceCardProps {
  source: Source;
  index: number;
}

export const SourceCard: React.FC<SourceCardProps> = ({ source, index }) => {
  return (
    <div style={{
      border: '1px solid #e0e0e0',
      borderRadius: '6px',
      padding: '10px',
      marginBottom: '8px',
      backgroundColor: '#f9f9f9',
      fontSize: '13px'
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
        [{index + 1}] {source.filename}
      </div>
      <div style={{ color: '#555', fontStyle: 'italic' }}>
        «{source.quote}»
      </div>
    </div>
  );
};
