// frontend/src/types/api.ts
// Типы данных, соответствующие mvp-contracts.md v0.2

export type DocumentStatus = 'uploaded' | 'processing' | 'ready' | 'error';

export interface Document {
  id: string;
  filename: string;
  format: 'txt';
  status: DocumentStatus;
  error_code: string | null;
  error_message: string | null;
  size_bytes: number;
  created_at: string;
}

export type AnswerStatus = 'answered' | 'partial' | 'insufficient_info';

export interface Source {
  document_id: string;
  filename: string;
  block_id: string;
  chunk_id: string;
  start_char: number;
  end_char: number;
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
  document_ids: string[] | null;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
}
