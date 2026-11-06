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
  // Хранилище состояний для каждого ID
  const stateRef = useRef<Record<string, PollState>>({});

  // Флаг, что компонент жив (для защиты от запросов после размонтирования)
  const isMountedRef = useRef(true);

  // Актуальные ссылки на пропсы и функции (чтобы не перезапускать эффекты)
  const checkStatusRef = useRef(checkStatus);
  const onStatusChangeRef = useRef(onStatusChange);
  const onErrorRef = useRef(onError);
  const errorsRef = useRef(pollingErrors);

  // Обновляем ссылки при каждом рендере
  useEffect(() => {
    checkStatusRef.current = checkStatus;
    onStatusChangeRef.current = onStatusChange;
    onErrorRef.current = onError;
    errorsRef.current = pollingErrors;
  });

  // Ключ зависит от списка ID и от ошибок (чтобы кнопка "Повторить" работала)
  const idsKey =
    documentIds.join(",") + "|" + Object.keys(pollingErrors).join(",");

  // ЭФФЕКТ 1: Управление списком документов
  useEffect(() => {
    const currentIds = new Set(documentIds);

    // 1. Очищаем таймеры и состояние для удаленных документов
    Object.keys(stateRef.current).forEach((id) => {
      if (!currentIds.has(id)) {
        if (stateRef.current[id].timer) {
          clearTimeout(stateRef.current[id].timer);
        }
        if (stateRef.current[id].isRequesting) {
          stateRef.current[id].cancelled = true; // помечаем, что результат не нужен
        } else {
          delete stateRef.current[id];
        }
      }
    });

    // 2. Запускаем опрос для новых или тех, кому нужно продолжить
    documentIds.forEach((id) => {
      if (errorsRef.current[id]) return; // если есть ошибка polling — не запускаем

      // Если документ был отменен (удален), но вернулся — полностью удаляем старое состояние
      if (stateRef.current[id]?.cancelled) {
        delete stateRef.current[id];
      }

      const state = stateRef.current[id];
      if (state?.timer || state?.isRequesting) return; // уже работает

      // Создаем новое чистое состояние
      stateRef.current[id] = {
        timer: null,
        isRequesting: false,
        cancelled: false,
      };

      const poll = async () => {
        const currentState = stateRef.current[id];
        if (!currentState) return;

        // Если компонент размонтирован или документ удален — выходим
        if (!isMountedRef.current || currentState.cancelled) {
          delete stateRef.current[id];
          return;
        }

        currentState.isRequesting = true;
        currentState.timer = null;

        try {
          const status = await checkStatusRef.current(id);

          // После await проверяем, что компонент жив и документ актуален
          if (
            !isMountedRef.current ||
            !stateRef.current[id] ||
            stateRef.current[id].cancelled
          ) {
            delete stateRef.current[id];
            return;
          }

          if (status === "ready" || status === "error") {
            delete stateRef.current[id];
          } else {
            onStatusChangeRef.current(id, status);
            stateRef.current[id].isRequesting = false;
            stateRef.current[id].timer = window.setTimeout(poll, intervalMs);
          }
        } catch {
          if (
            !isMountedRef.current ||
            !stateRef.current[id] ||
            stateRef.current[id].cancelled
          )
            return;
          stateRef.current[id].isRequesting = false;
          delete stateRef.current[id];
          onErrorRef.current(id);
        }
      };

      poll();
    });

    // Мы не делаем cleanup здесь! Мы просто управляем состоянием.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey, intervalMs]);

  // ЭФФЕКТ 2: Полная очистка при размонтировании компонента
  useEffect(() => {
    isMountedRef.current = true; // компонент смонтирован
    return () => {
      isMountedRef.current = false;
      // Убиваем все таймеры
      Object.keys(stateRef.current).forEach((id) => {
        if (stateRef.current[id].timer) {
          clearTimeout(stateRef.current[id].timer);
        }
      });
      // Очищаем состояние
      stateRef.current = {};
    };
  }, []);
}
