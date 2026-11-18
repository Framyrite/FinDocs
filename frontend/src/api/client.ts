// frontend/src/api/client.ts
import type { ApiErrorResponse } from "../types/api";

import { API_BASE_URL } from "./config";

// Сохраняем HTTP-код отдельно от текста, чтобы UI мог различать, например,
// отсутствие документа (404), отказ сервера и обычную сетевую ошибку fetch.
export class ApiRequestError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

/**
 * Универсальная функция для запросов к API.
 * Обрабатывает ошибки в формате контракта.
 */
export async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  // Не отправляем production-запрос на случайный адрес frontend при
  // отсутствующей конфигурации. В dev config.ts уже подставляет /api.
  if (!API_BASE_URL) {
    throw new Error(
      "Не задан адрес API. Укажите VITE_API_BASE_URL и пересоберите frontend.",
    );
  }
  const url = `${API_BASE_URL}${endpoint}`;

  // Content-Type задаёт вызывающий метод. Для FormData браузер должен
  // сформировать multipart-заголовок с boundary самостоятельно.
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
    },
  });

  // Если ответ не OK (4xx, 5xx)
  if (!response.ok) {
    let errorMessage = `API error: ${response.status} ${response.statusText}`;
    try {
      const errorData: ApiErrorResponse = await response.json();
      errorMessage = `${errorData.error.code}: ${errorData.error.message}`;
    } catch {
      // Если не удалось распарсить JSON, оставляем стандартное сообщение
    }
    throw new ApiRequestError(response.status, errorMessage);
  }

  // DELETE возвращает 204 без тела: попытка response.json() вызвала бы ошибку.
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
