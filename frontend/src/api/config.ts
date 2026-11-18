// Vite передаёт VITE_* как строки. Boolean("false") дал бы true,
// поэтому заглушку включает только явно заданное значение "true".
// Это режим frontend, независимый от FINDOCS_LLM_PROVIDER на backend.
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

// Убираем пробелы и завершающие /, чтобы не получать двойной / перед endpoint.
const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim().replace(
  /\/+$/,
  "",
);

// В разработке безопасно используем уже настроенный Vite proxy.
// В production адрес должен быть задан явно: dev proxy там не работает.
export const API_BASE_URL =
  configuredBaseUrl || (import.meta.env.DEV ? "/api" : undefined);
