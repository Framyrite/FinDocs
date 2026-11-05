// frontend/src/api/client.ts
import type { ApiErrorResponse } from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

/**
 * Универсальная функция для запросов к API.
 * Обрабатывает ошибки в формате контракта.
 */
export async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

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
    throw new Error(errorMessage);
  }

  // 204 No Content — тело пустое
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
