// frontend/src/api/index.ts
import { mockApi } from "../mocks/mockApi";
import { request } from "./client";
import type {
  Document,
  AskRequest,
  Answer,
  DocumentListResponse,
} from "../types/api";

// false — реальные HTTP-запросы через client.ts; true — заглушка frontend.
// Это НЕ FINDOCS_LLM_PROVIDER: сервер может использовать MockLLM,
// одновременно предоставляя реальные загрузку, обработку и поиск документов.
const USE_MOCK = false;

export const api = {
  // GET /documents
  async getDocuments(): Promise<DocumentListResponse> {
    if (USE_MOCK) return mockApi.getDocuments();
    return request<DocumentListResponse>("/documents");
  },

  // GET /documents/{id}
  async getDocumentById(id: string): Promise<Document> {
    if (USE_MOCK) {
      return mockApi.getDocumentById(id);
    }
    return request<Document>(`/documents/${id}`);
  },

  // POST /documents
  async uploadDocument(file: File): Promise<Document> {
    if (USE_MOCK) return mockApi.uploadDocument(file);

    const formData = new FormData();
    formData.append("file", file);

    return request<Document>("/documents", {
      method: "POST",
      body: formData,
      // Не ставим Content-Type, браузер сам выставит multipart/form-data с boundary
      headers: {},
    });
  },

  // DELETE /documents/{id}
  async deleteDocument(id: string): Promise<void> {
    if (USE_MOCK) return mockApi.deleteDocument(id);
    return request<void>(`/documents/${id}`, { method: "DELETE" });
  },

  // POST /chat/ask
  async askQuestion(req: AskRequest): Promise<Answer> {
    if (USE_MOCK) return mockApi.askQuestion(req);
    return request<Answer>("/chat/ask", {
      method: "POST",
      body: JSON.stringify(req),
      headers: {
        "Content-Type": "application/json",
      },
    });
  },
};
