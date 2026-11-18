// frontend/src/api/client.ts
import { API_BASE_URL } from "./config";

// HTTP-ответ получен, но сервер вернул 4xx/5xx. Код нужен, в частности,
// для синхронизации библиотеки после DELETE с ответом 404.
export class ApiRequestError extends Error {
  readonly status: number;
  readonly serverMessage?: string;

  constructor(status: number, message: string, serverMessage?: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.serverMessage = serverMessage;
  }
}

// fetch не получил HTTP-ответ: это не то же самое, что HTTP 404 или 500.
export class ApiNetworkError extends Error {
  constructor(cause: unknown) {
    super(
      "Не удалось связаться с сервером. Проверьте подключение и попробуйте ещё раз.",
      { cause },
    );
    this.name = "ApiNetworkError";
  }
}

// HTTP успешен, но формат или структура тела не соответствует ожидаемому ответу.
export class ApiResponseError extends Error {
  readonly status: number;

  constructor(status: number) {
    super("Сервер вернул некорректный ответ. Попробуйте ещё раз.");
    this.name = "ApiResponseError";
    this.status = status;
  }
}

// Показываем понятные сообщения известных ошибок. Неизвестная ошибка
// получает подпись конкретного действия, а не внутренний текст исключения.
export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiNetworkError || error instanceof ApiResponseError) {
    return error.message;
  }
  if (error instanceof ApiRequestError) {
    return (
      error.serverMessage ||
      `Сервер вернул ошибку (HTTP ${error.status}). Попробуйте ещё раз.`
    );
  }
  return fallback;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Универсальный HTTP-клиент. Различает транспортный сбой, HTTP-ошибку
 * и некорректный успешный ответ. Проверку полей выбирает конкретный API-метод.
 */
export async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  validate?: (value: unknown) => value is T,
): Promise<T> {
  // В dev config.ts подставляет /api. В production адрес задаётся явно.
  if (!API_BASE_URL) {
    throw new Error(
      "Не задан адрес API. Укажите VITE_API_BASE_URL и пересоберите frontend.",
    );
  }
  const url = `${API_BASE_URL}${endpoint}`;

  let response: Response;
  try {
    // Для FormData браузер сам сформирует Content-Type с boundary.
    response = await fetch(url, {
      ...options,
      headers: { ...options.headers },
    });
  } catch (error) {
    // Отмена запроса не является потерей соединения.
    if (
      (error instanceof DOMException || error instanceof Error) &&
      error.name === "AbortError"
    ) {
      throw error;
    }
    throw new ApiNetworkError(error);
  }

  if (!response.ok) {
    let errorMessage = `API error: ${response.status} ${response.statusText}`;
    let serverMessage: string | undefined;
    try {
      const data: unknown = await response.json();
      // Не полагаемся на TypeScript-тип для внешних данных: иначе некорректное
      // тело ошибки могло бы дать пользователю строку "undefined: undefined".
      if (
        isRecord(data) &&
        isRecord(data.error) &&
        typeof data.error.code === "string" &&
        data.error.code.trim() &&
        typeof data.error.message === "string" &&
        data.error.message.trim()
      ) {
        serverMessage = data.error.message;
        errorMessage = `${data.error.code}: ${serverMessage}`;
      }
    } catch {
      // HTML, пустое или повреждённое тело не меняет полученный HTTP-код.
    }
    throw new ApiRequestError(response.status, errorMessage, serverMessage);
  }

  // Успешный DELETE возвращает 204 без тела и без JSON-заголовка.
  if (response.status === 204) {
    // Для DELETE тело не нужно, но методы с валидатором обязаны вернуть данные.
    if (validate) throw new ApiResponseError(response.status);
    return undefined as T;
  }

  const contentType = (response.headers.get("Content-Type") || "")
    .split(";")[0]
    .trim()
    .toLowerCase();
  const isJson =
    contentType === "application/json" ||
    (contentType.startsWith("application/") && contentType.endsWith("+json"));
  if (!isJson) throw new ApiResponseError(response.status);

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new ApiResponseError(response.status);
  }

  // Сначала проверяем общий формат, затем обязательные поля и вложенные
  // элементы по валидатору конкретного метода. Некорректные данные не попадут в UI.
  if (!isRecord(data) || (validate && !validate(data))) {
    throw new ApiResponseError(response.status);
  }
  return data as T;
}
