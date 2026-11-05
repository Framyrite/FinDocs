// frontend/src/App.tsx
import { useEffect, useState, useCallback } from 'react';
import type { Document, Answer } from './types/api';
import { api } from './api';
import { DocumentList } from './components/DocumentList';
import { UploadButton } from './components/UploadButton';
import { Chat } from './components/Chat';
import { Navbar } from './components/Navbar';
import type { Tab } from './components/Navbar';
import './App.css';
import { usePolling } from './hooks/usePolling';

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  // null = все документы, массив = выбранные
  const [selectedDocIds, setSelectedDocIds] = useState<string[] | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('chat'); // По умолчанию открыт чат
  const [pollingDocId, setPollingDocId] = useState<string | null>(null);

  useEffect(() => {
    // Загружаем документы при старте
    api.getDocuments().then((data) => {
      setDocuments(data.items);
      setIsLoading(false);
    })
    .catch(() => {
        alert('Не удалось загрузить список документов');
        setIsLoading(false);
      });
  }, []);

  const checkDocStatus = useCallback(async (id: string) => {
    const doc = await api.getDocumentById(id);

    // Обновляем документ в списке
    setDocuments(prev => 
      prev.map(d => d.id === id ? { ...d, ...doc } : d)
    );

    return doc.status;
  }, []);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const newDoc = await api.uploadDocument(file);

      // Обновляем список
      const data = await api.getDocuments();
      setDocuments(data.items);

      // Запускаем отслеживание статуса для этого документа
      setPollingDocId(newDoc.id);
      
    } catch {
      alert('Ошибка загрузки файла');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Удалить документ?')) return;
    try {
      await api.deleteDocument(id);
      setDocuments(prev => prev.filter(d => d.id !== id));

      // Если удаленный документ был выбран — убираем его из выбора
      setSelectedDocIds(prev => {
        if (prev === null) return null;
        const filtered = prev.filter(item => item !== id);
        return filtered.length === 0 ? null : filtered;
      });

    } catch {
      alert('Ошибка удаления');
    }
  };

  // Функция для отправки вопроса
  const handleAskQuestion = async (question: string, docIds: string[] | null): Promise<Answer> => {
    return api.askQuestion({ question, document_ids: docIds });
  };

  // 4. Хуки, зависящие от функций
  usePolling(
    pollingDocId, 
    checkDocStatus, 
    (_id, status) => {
      // Если статус конечный, сбрасываем polling
      if (status === 'ready' || status === 'error') {
        setPollingDocId(null);
      }
    }
  );

  const filteredDocs = documents.filter(doc => 
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Проверяем, есть ли хотя бы один готовый документ
  const hasReadyDocuments = documents.some(doc => doc.status === 'ready');

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <h1 style={{ marginBottom: '16px' }}>FinDocs</h1>
      
      <Navbar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Вкладка Документы */}
      {activeTab === 'documents' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2>Мои документы</h2>
            <UploadButton onUpload={handleUpload} disabled={isUploading} />
          </div>
          
          <DocumentList
            documents={filteredDocs}
            isLoading={isLoading}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            onDelete={handleDelete}
          />
        </>
      )}

      {/* Вкладка Чат */}
      {activeTab === 'chat' && (
      <Chat 
        onAsk={handleAskQuestion} 
        hasReadyDocuments={hasReadyDocuments} 
        documents={documents}
        selectedIds={selectedDocIds}
        onSelectionChange={setSelectedDocIds}
      />
      )}
    </div>
  );
}

export default App;
