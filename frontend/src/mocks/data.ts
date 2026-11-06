// frontend/src/mocks/data.ts
import type { Document, Answer } from "../types/api";

// Фейковые документы в разных статусах
export const mockDocuments: Document[] = [
  {
    id: "1f2b8c1e-5a47-4d0e-9b62-1c7f0a9e4d11",
    filename: "Лекция 3. Облигации.txt",
    format: "txt",
    status: "ready",
    error_code: null,
    error_message: null,
    size_bytes: 48213,
    created_at: "2026-11-02T14:05:00Z",
  },
  {
    id: "2a3c9d4f-6b58-4e1f-8c73-2d8f1b0a5e22",
    filename: "Конспект по макроэкономике.txt",
    format: "txt",
    status: "processing",
    error_code: null,
    error_message: null,
    size_bytes: 12400,
    created_at: "2026-11-02T15:10:00Z",
  },
  {
    id: "3b4d1e5a-7c69-4f2a-9d84-3e9a2c1b6f33",
    filename: "Битый файл.txt",
    format: "txt",
    status: "error",
    error_code: "invalid_encoding",
    error_message:
      "Не удалось прочитать файл: поддерживается только кодировка UTF-8.",
    size_bytes: 2048,
    created_at: "2026-11-02T14:10:00Z",
  },
];

// Фейковый ответ на вопрос
export const mockAnswer: Answer = {
  status: "answered",
  answer:
    "[MOCK] Найдены фрагменты по ключевым словам вопроса:\n1. «Облигация — эмиссионная ценная бумага, закрепляющая право её владельца на получение от эмитента номинальной стоимости в оговорённый срок.»",
  sources: [
    {
      document_id: "1f2b8c1e-5a47-4d0e-9b62-1c7f0a9e4d11",
      filename: "Лекция 3. Облигации.txt",
      block_id: "b6d1c0a4-7e52-5f0b-a3c8-2d9e4f6a1b70",
      chunk_id: "c2f8a9d3-1b64-5e7a-9d05-8a3b6c4e2f91",
      start_char: 1204,
      end_char: 1341,
      quote:
        "Облигация — эмиссионная ценная бумага, закрепляющая право её владельца на получение от эмитента номинальной стоимости в оговорённый срок.",
    },
  ],
};

// Ответ, когда информации недостаточно
export const mockAnswerInsufficient: Answer = {
  status: "insufficient_info",
  answer:
    "В выбранных материалах не удалось найти достаточную информацию для ответа.",
  sources: [],
};

// Ответ, когда произошла техническая ошибка (имитация)
export const mockAnswerError: Answer = {
  status: "answered", // В контракте нет статуса error, ошибка ловится через HTTP
  answer: "",
  sources: [],
};
