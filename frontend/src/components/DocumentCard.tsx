// frontend/src/components/DocumentCard.tsx
import React from 'react';
import type { Document } from '../types/api';

interface DocumentCardProps {
  doc: Document;
  onDelete: (id: string) => void;
  hasPollingError: boolean;
  onRetryPolling: (id: string) => void;
}

const statusLabels: Record<Document['status'], string> = {
  uploaded: 'Загружен',
  processing: 'Обрабатывается',
  ready: 'Готов',
  error: 'Ошибка',
};

const statusColors: Record<Document['status'], string> = {
  uploaded: '#888',
  processing: '#f0ad4e',
  ready: '#5cb85c',
  error: '#d9534f',
};

export const DocumentCard: React.FC<DocumentCardProps> = ({ 
  doc, 
  onDelete, 
  hasPollingError, 
  onRetryPolling 
}) => {
  return (
    <div style={{
      border: '1px solid #ddd',
      borderRadius: '8px',
      padding: '12px',
      marginBottom: '8px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center'
    }}>
      <div>
        <div style={{ fontWeight: 'bold' }}>📄 {doc.filename}</div>
        <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
          {new Date(doc.created_at).toLocaleDateString('ru-RU')}
        </div>
        
        {/* Ошибка обработки (от бэкенда) */}
        {doc.status === 'error' && doc.error_message && (
          <div style={{ fontSize: '12px', color: '#d9534f', marginTop: '4px' }}>
            {doc.error_message}
          </div>
        )}
        
        {/* Ошибка polling (сеть) */}
        {hasPollingError && (
          <div style={{ fontSize: '12px', color: '#f0ad4e', marginTop: '4px' }}>
            Ошибка соединения
          </div>
        )}
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ 
          color: statusColors[doc.status], 
          fontWeight: 'bold',
          fontSize: '14px'
        }}>
          {statusLabels[doc.status]}
        </div>
        
        {/* Кнопка повтора polling */}
        {hasPollingError && (
          <button 
            onClick={() => onRetryPolling(doc.id)} 
            title="Повторить запрос статуса"
            style={{ 
              color: '#f0ad4e', 
              border: '1px solid #f0ad4e', 
              background: 'none', 
              borderRadius: '50%',
              width: '28px',
              height: '28px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              fontSize: '16px',
              padding: 0
            }}
          >
            ↻
          </button>
        )}

        <button 
          onClick={() => onDelete(doc.id)} 
          style={{ 
            color: 'red', 
            border: '1px solid #d9534f', 
            background: 'none', 
            borderRadius: '4px',
            padding: '4px 8px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          Удалить
        </button>
      </div>
    </div>
  );
};
