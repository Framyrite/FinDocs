// frontend/src/api/index.ts
import { mockApi } from '../mocks/mockApi';
import type { Document, AskRequest, Answer } from '../types/api';

// Флаг: используем ли мы mock-режим (пока да, так как бэкенда нет)
const USE_MOCK = true;

export const api = {
  async getDocuments(): Promise<{ items: Document[], total: number }> {
    if (USE_MOCK) return mockApi.getDocuments();
    
    // Позже здесь будет реальный запрос:
    // return request<{ items: Document[], total: number }>('/documents');
    throw new Error('Real API not implemented yet');
  },

  async askQuestion(req: AskRequest): Promise<Answer> {
    if (USE_MOCK) return mockApi.askQuestion(req);
    
    // Позже здесь будет реальный запрос:
    // return request<Answer>('/chat/ask', { method: 'POST', body: JSON.stringify(req) });
    throw new Error('Real API not implemented yet');
  },

  async uploadDocument(file: File): Promise<Document> {
    if (USE_MOCK) return mockApi.uploadDocument(file);
    
    throw new Error('Real API not implemented yet');
  },

  async deleteDocument(id: string): Promise<void> {
    if (USE_MOCK) return mockApi.deleteDocument(id);
    // return request<void>(`/documents/${id}`, { method: 'DELETE' });
    throw new Error('Real API not implemented yet');
  },
};
