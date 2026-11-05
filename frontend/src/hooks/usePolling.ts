// frontend/src/hooks/usePolling.ts
import { useEffect, useRef } from "react";

export function usePolling(
  documentIds: string[],
  checkStatus: (
    id: string,
  ) => Promise<"processing" | "ready" | "error" | "uploaded">,
  onStatusChange: (id: string, status: string) => void,
  onError: (id: string) => void,
  pollingErrors: Record<string, boolean>,
  intervalMs: number = 2000,
) {
  const timersRef = useRef<Record<string, number>>({});
  const isPollingRef = useRef<Record<string, boolean>>({});

  const checkStatusRef = useRef(checkStatus);
  const onStatusChangeRef = useRef(onStatusChange);
  const onErrorRef = useRef(onError);

  // Обновляем ссылки, не вызывая перезапуск эффекта
  useEffect(() => {
    checkStatusRef.current = checkStatus;
    onStatusChangeRef.current = onStatusChange;
    onErrorRef.current = onError;
  });

  // Стабилизируем массив: превращаем его в строку, чтобы useEffect не реагировал на пересоздание массива
  const idsKey = documentIds.join(",");

  useEffect(() => {
    // Очищаем таймеры для удаленных документов
    Object.keys(timersRef.current).forEach((id) => {
      if (!documentIds.includes(id)) {
        clearTimeout(timersRef.current[id]);
        delete timersRef.current[id];
        isPollingRef.current[id] = false;
      }
    });

    documentIds.forEach((id) => {
      // Если уже опрашивается или есть ошибка polling — пропускаем
      if (isPollingRef.current[id] || (pollingErrors && pollingErrors[id])) {
        return;
      }

      isPollingRef.current[id] = true;

      const poll = async () => {
        if (!isPollingRef.current[id]) return;

        try {
          const status = await checkStatusRef.current(id);

          if (status === "ready" || status === "error") {
            isPollingRef.current[id] = false;
            delete timersRef.current[id];
          } else {
            onStatusChangeRef.current(id, status);
            timersRef.current[id] = window.setTimeout(poll, intervalMs);
          }
        } catch {
          isPollingRef.current[id] = false;
          delete timersRef.current[id];
          onErrorRef.current(id);
        }
      };

      poll();
    });

    return () => {
      Object.values(timersRef.current).forEach(clearTimeout);
      timersRef.current = {};
      isPollingRef.current = {};
    };
    // Мы используем idsKey для стабильности, а documentIds берем из замыкания.
    // Это предотвращает бесконечные перезапуски эффекта при пересоздании массива.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey, intervalMs, pollingErrors]);
}
