// frontend/src/hooks/usePolling.ts
import { useEffect, useRef } from "react";

interface PollState {
  timer: number | null;
  isRequesting: boolean;
  cancelled?: boolean;
}

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
  const stateRef = useRef<Record<string, PollState>>({});

  const checkStatusRef = useRef(checkStatus);
  const onStatusChangeRef = useRef(onStatusChange);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    checkStatusRef.current = checkStatus;
    onStatusChangeRef.current = onStatusChange;
    onErrorRef.current = onError;
  });

  const idsKey = documentIds.join(",");

  useEffect(() => {
    const currentIds = new Set(documentIds);

    // 1. Останавливаем таймеры для удаленных документов
    Object.keys(stateRef.current).forEach((id) => {
      if (!currentIds.has(id)) {
        if (stateRef.current[id].timer) {
          clearTimeout(stateRef.current[id].timer);
        }
        if (stateRef.current[id].isRequesting) {
          stateRef.current[id].cancelled = true;
          stateRef.current[id].timer = null;
        } else {
          delete stateRef.current[id];
        }
      }
    });

    // 2. Запускаем новые
    documentIds.forEach((id) => {
      if (pollingErrors && pollingErrors[id]) return;

      if (stateRef.current[id]?.isRequesting) return;
      if (stateRef.current[id]?.timer) return;

      stateRef.current[id] = { timer: null, isRequesting: false };

      const poll = async () => {
        const state = stateRef.current[id];
        if (!state) return;
        if (state.cancelled) {
          delete stateRef.current[id];
          return;
        }

        state.isRequesting = true;
        state.timer = null;

        try {
          const status = await checkStatusRef.current(id);

          // Проверяем, не удалили ли документ за время запроса
          const currentState = stateRef.current[id];
          if (!currentState || currentState.cancelled) {
            delete stateRef.current[id];
            return;
          }

          if (status === "ready" || status === "error") {
            delete stateRef.current[id];
          } else {
            onStatusChangeRef.current(id, status);
            currentState.isRequesting = false;
            currentState.timer = window.setTimeout(poll, intervalMs);
          }
        } catch {
          const currentState = stateRef.current[id];
          if (!currentState) return;
          currentState.isRequesting = false;
          delete stateRef.current[id];
          onErrorRef.current(id);
        }
      };

      poll();
    });

    // 3. Cleanup: копируем ссылку на объект в локальную переменную
    const stateRecord = stateRef.current;

    return () => {
      Object.keys(stateRecord).forEach((id) => {
        if (stateRecord[id].timer) {
          clearTimeout(stateRecord[id].timer);
          stateRecord[id].timer = null;
        }
      });
    };
    // Мы используем idsKey для стабильности, а documentIds берем из замыкания.
    // Это предотвращает бесконечные перезапуски эффекта.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey, intervalMs, pollingErrors]);
}
