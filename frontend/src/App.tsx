// frontend/src/App.tsx
import { useEffect, useState } from 'react';
import type { Document } from './types/api';
import { api } from './api';
import { DocumentList } from './components/DocumentList';
import './App.css';

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    // Загружаем документы при старте (пока из моков)
    api.getDocuments().then((data) => {
      setDocuments(data.items);
      setIsLoading(false);
    });
  }, []);

  // Фильтрация по поиску (просто для демонстрации)
  const filteredDocs = documents.filter(doc => 
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <h1>Мои документы</h1>
      <DocumentList
        documents={filteredDocs}
        isLoading={isLoading}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />
    </div>
  );
}

export default App;
