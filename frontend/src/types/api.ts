// frontend/src/types/api.ts
// Типы данных, соответствующие mvp-contracts.md v0.2

// Значения статусов сохраняем как в контракте API независимо от подписей в UI.
export type DocumentStatus = "uploaded" | "processing" | "ready" | "error";

export interface Document {
  id: string;
  filename: string;
  format: "txt";
  status: DocumentStatus;
  error_code: string | null;
  error_message: string | null;
  size_bytes: number;
  // API передаёт ISO 8601 в UTC; локальное отображение выполняет интерфейс.
  created_at: string;
}

export type AnswerStatus = "answered" | "partial" | "insufficient_info";

export interface Source {
  document_id: string;
  filename: string;
  block_id: string;
  chunk_id: string;
  start_char: number;
  end_char: number;
  // Готовая цитата для показа: frontend не вычисляет её по индексам.
  quote: string;
}

export interface Answer {
  status: AnswerStatus;
  answer: string;
  sources: Source[];
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiErrorResponse {
  error: ApiError;
}

export interface AskRequest {
  question: string;
  // null — все готовые документы; пустой массив контрактом не допускается.
  document_ids: string[] | null;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
}
