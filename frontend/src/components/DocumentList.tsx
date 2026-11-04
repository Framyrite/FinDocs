// frontend/src/components/DocumentList.tsx
import React from 'react';
import type { Document } from '../types/api';
import { DocumentCard } from './DocumentCard';

interface DocumentListProps {
  documents: Document[];
  isLoading: boolean;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onDelete: (id: string) => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  isLoading,
  searchQuery,
  onSearchChange,
  onDelete,
}) => {
  if (isLoading) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Загрузка документов...</div>;
  }

  return (
    <div>
      <div style={{ marginBottom: '16px' }}>
        <input
          type="text"
          placeholder="Поиск по документам..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          style={{
            width: '100%',
            padding: '8px 12px',
            border: '1px solid #ddd',
            borderRadius: '6px',
            fontSize: '14px'
          }}
        />
      </div>

      {documents.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#666' }}>
          <p>Нет файлов</p>
          <p style={{ fontSize: '14px' }}>Загрузите первый документ, чтобы начать работу</p>
        </div>
      ) : (
        <div>
          {documents.map((doc) => (
            <DocumentCard key={doc.id} doc={doc} onDelete={onDelete} />
          ))}
        </div>
      )}
    </div>
  );
};
