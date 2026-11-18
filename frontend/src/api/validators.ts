import type {
  Answer,
  Document,
  DocumentListResponse,
  Source,
} from "../types/api";

// Проверяем внешние данные до помещения в состояние React. Дополнительные
// поля допускаются; UUID, содержание цитат и прочие бизнес-правила здесь не проверяем.
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

export function isDocument(value: unknown): value is Document {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.filename === "string" &&
    value.format === "txt" &&
    (value.status === "uploaded" ||
      value.status === "processing" ||
      value.status === "ready" ||
      value.status === "error") &&
    isNullableString(value.error_code) &&
    isNullableString(value.error_message) &&
    isNonNegativeInteger(value.size_bytes) &&
    typeof value.created_at === "string"
  );
}

export function isDocumentListResponse(
  value: unknown,
): value is DocumentListResponse {
  return (
    isRecord(value) &&
    Array.isArray(value.items) &&
    value.items.every(isDocument) &&
    isNonNegativeInteger(value.total)
  );
}

function isSource(value: unknown): value is Source {
  return (
    isRecord(value) &&
    typeof value.document_id === "string" &&
    typeof value.filename === "string" &&
    typeof value.block_id === "string" &&
    typeof value.chunk_id === "string" &&
    isNonNegativeInteger(value.start_char) &&
    isNonNegativeInteger(value.end_char) &&
    typeof value.quote === "string"
  );
}

export function isAnswer(value: unknown): value is Answer {
  return (
    isRecord(value) &&
    (value.status === "answered" ||
      value.status === "partial" ||
      value.status === "insufficient_info") &&
    typeof value.answer === "string" &&
    Array.isArray(value.sources) &&
    value.sources.every(isSource)
  );
}
