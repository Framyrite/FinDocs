// frontend/src/api/client.ts
// Базовый клиент для работы с API FinDocs

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

/**
 * Универсальная функция для запросов к API.
 * Пока не используется, но задает структуру для будущих методов.
 */
export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}
