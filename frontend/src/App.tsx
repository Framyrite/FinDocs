// frontend/src/App.tsx
import { useEffect, useState } from 'react';
import type { Document, Answer } from './types/api';
import { api } from './api';
import { DocumentList } from './components/DocumentList';
import { UploadButton } from './components/UploadButton';
import { Chat } from './components/Chat';
import './App.css';

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    // Загружаем документы при старте
    api.getDocuments().then((data) => {
      setDocuments(data.items);
      setIsLoading(false);
    });
  }, []);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      // 1. Отправляем файл (имитация)
      const newDoc = await api.uploadDocument(file);
      
      // 2. Добавляем в список
      setDocuments(prev => [newDoc, ...prev]);
      
      // 3. Имитация обработки (через 2 секунды меняем статус на ready)
      setTimeout(() => {
        setDocuments(prev => 
          prev.map(d => 
            d.id === newDoc.id ? { ...d, status: 'ready' as const } : d
          )
        );
      }, 2000);
      
    } catch (error) {
      alert('Ошибка загрузки файла');
    } finally {
      setIsUploading(false);
    }
  };

  // Функция для отправки вопроса
  const handleAskQuestion = async (question: string): Promise<Answer> => {
    return api.askQuestion({ question, document_ids: null });
  };

  const filteredDocs = documents.filter(doc => 
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

    // Проверяем, есть ли хотя бы один готовый документ
  const hasReadyDocuments = documents.some(doc => doc.status === 'ready');

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Мои документы</h1>
        <UploadButton onUpload={handleUpload} disabled={isUploading} />
      </div>
      
      <DocumentList
        documents={filteredDocs}
        isLoading={isLoading}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {/* Добавили чат внизу */}
      <Chat onAsk={handleAskQuestion} hasReadyDocuments={hasReadyDocuments} />
    </div>
  );
}

export default App;
