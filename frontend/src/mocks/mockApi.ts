// frontend/src/mocks/mockApi.ts
import type { Document, AskRequest, Answer } from '../types/api';
import { mockDocuments, mockAnswer, mockAnswerInsufficient } from './data';

// Имитация задержки сети
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// «Живое» хранилище документов (изменяется в течение сессии)
let documentsStore: Document[] = [...mockDocuments];

export const mockApi = {
  // Имитация GET /documents
  async getDocuments(): Promise<{ items: Document[], total: number }> {
    await delay(500);
    return { items: [...documentsStore], total: documentsStore.length };
  },

  // Имитация GET /documents/{id}
  async getDocumentById(id: string): Promise<Document> {
    await delay(300);
    const doc = documentsStore.find(d => d.id === id);
    if (!doc) throw new Error('Документ не найден');

    // Простая имитация: uploaded -> processing -> ready
    let newStatus = doc.status;

    if (doc.status === 'uploaded') {
      newStatus = 'processing';
    } else if (doc.status === 'processing') {
      newStatus = 'ready';
    }

    if (newStatus !== doc.status) {
      // Обновляем в хранилище
      documentsStore = documentsStore.map(d => 
        d.id === id ? { ...d, status: newStatus } : d
      );
      // Возвращаем обновленную версию
      return { ...doc, status: newStatus };
    }

    return { ...doc };
  },

  // Имитация POST /documents
  async uploadDocument(file: File): Promise<Document> {
    await delay(800);
    
    const newDoc: Document = {
      id: crypto.randomUUID(),
      filename: file.name,
      format: 'txt',
      status: 'uploaded',
      error_code: null,
      error_message: null,
      size_bytes: file.size,
      created_at: new Date().toISOString(),
    };
    
    // Добавляем в хранилище!
    documentsStore = [newDoc, ...documentsStore];
    return { ...newDoc };
  },

  // Имитация DELETE /documents/{id}
  async deleteDocument(id: string): Promise<void> {
    await delay(300);
    // Удаляем из хранилища!
    documentsStore = documentsStore.filter(d => d.id !== id);
  },

  // Имитация POST /chat/ask
  async askQuestion(request: AskRequest): Promise<Answer> {
    await delay(1000);
    
    const q = request.question.toLowerCase();
    if (q.includes('нет') || q.includes('недостаточно')) {
      return mockAnswerInsufficient;
    }
    
    return mockAnswer;
  },
};
