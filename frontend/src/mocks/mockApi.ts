// frontend/src/mocks/mockApi.ts
import type { Document, AskRequest, Answer } from '../types/api';
import { mockDocuments, mockAnswer } from './data';

// Имитация задержки сети (чтобы видеть состояния загрузки)
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const mockApi = {
  // Имитация GET /documents
  async getDocuments(): Promise<{ items: Document[], total: number }> {
    await delay(500);
    return { items: mockDocuments, total: mockDocuments.length };
  },

  // Имитация POST /chat/ask
  async askQuestion(_request: AskRequest): Promise<Answer> {
    await delay(1000);
    // Для демонстрации всегда возвращаем один и тот же ответ
    return mockAnswer;
  }
};
