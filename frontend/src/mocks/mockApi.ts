// frontend/src/mocks/mockApi.ts
import type { Document, AskRequest, Answer } from '../types/api';
import { mockDocuments, mockAnswer, mockAnswerInsufficient } from './data';

// Имитация задержки сети (чтобы видеть состояния загрузки)
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const mockApi = {
  // Имитация GET /documents
  async getDocuments(): Promise<{ items: Document[], total: number }> {
    await delay(500);
    return { items: mockDocuments, total: mockDocuments.length };
  },

  async uploadDocument(file: File): Promise<Document> {
    await delay(800); // Имитация отправки на сервер
    
    const newDoc: Document = {
      id: crypto.randomUUID(), // Генерируем UUID прямо в браузере
      filename: file.name,
      format: 'txt',
      status: 'uploaded',
      error_code: null,
      error_message: null,
      size_bytes: file.size,
      created_at: new Date().toISOString(),
    };
    
    return newDoc;
  },

  async deleteDocument(id: string): Promise<void> {
    await delay(300);
    // В моке просто ничего не делаем, список обновится на фронте
  },

  // Имитация POST /chat/ask
  async askQuestion(request: AskRequest): Promise<Answer> {
    await delay(1000);
    
    // Простая логика для демонстрации:
    // Если в вопросе есть слово "нет" или "недостаточно", возвращаем ответ об отсутствии инфы
    const q = request.question.toLowerCase();
    if (q.includes('нет') || q.includes('недостаточно')) {
      return mockAnswerInsufficient;
    }
    
    // В остальных случаях возвращаем полный ответ
    return mockAnswer;
  },
};
