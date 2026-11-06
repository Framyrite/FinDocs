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
  // Внутреннее состояние для каждого документа (таймер, флаг запроса, флаг отмены)
  const stateRef = useRef<Record<string, PollState>>({});

  // Флаг, что компонент смонтирован (защита от запросов после размонтирования)
  const isMountedRef = useRef(true);

  // Храним актуальные функции в ref, чтобы useEffect не зависел от их пересоздания
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

  // Стабильный ключ для отслеживания изменений списка документов и ошибок (для кнопки "Повторить")
  const idsKey =
    documentIds.join(",") + "|" + Object.keys(pollingErrors).join(",");

  // ЭФФЕКТ 1: Управление списком опрашиваемых документов
  useEffect(() => {
    const currentIds = new Set(documentIds);

    // 1. Очищаем таймеры и состояние для документов, которые были удалены
    Object.keys(stateRef.current).forEach((id) => {
      if (!currentIds.has(id)) {
        if (stateRef.current[id].timer) {
          clearTimeout(stateRef.current[id].timer);
        }
        if (stateRef.current[id].isRequesting) {
          // Если запрос уже в процессе, помечаем, что его результат не нужен
          stateRef.current[id].cancelled = true;
        } else {
          delete stateRef.current[id];
        }
      }
    });

    // 2. Запускаем опрос для новых или тех, кому нужно продолжить
    documentIds.forEach((id) => {
      // Пропускаем, если для документа уже есть ошибка polling
      if (errorsRef.current[id]) return;

      // Если документ был отменен (удален), но вернулся — полностью удаляем старое состояние
      if (stateRef.current[id]?.cancelled) {
        delete stateRef.current[id];
      }

      const existingState = stateRef.current[id];
      // Пропускаем, если уже идет запрос или тикает таймер
      if (existingState?.timer || existingState?.isRequesting) return;

      // Создаем НОВОЕ состояние и сохраняем на него ссылку
      const currentState: PollState = {
        timer: null,
        isRequesting: false,
        cancelled: false,
      };
      stateRef.current[id] = currentState;

      const poll = async () => {
        // Проверяем перед запросом: компонент жив, запрос не отменен
        if (!isMountedRef.current || currentState.cancelled) {
          return;
        }

        currentState.isRequesting = true;
        currentState.timer = null;

        try {
          const status = await checkStatusRef.current(id);

          // ГЛАВНАЯ ПРОВЕРКА: не заменили ли наше состояние, пока мы ждали?
          // Если stateRef.current[id] !== currentState, значит это "старый" запрос
          if (
            !isMountedRef.current ||
            stateRef.current[id] !== currentState ||
            currentState.cancelled
          ) {
            return;
          }

          if (status === "ready" || status === "error") {
            delete stateRef.current[id]; // Конечный статус — прекращаем опрос
          } else {
            onStatusChangeRef.current(id, status); // Промежуточный статус — обновляем UI
            currentState.isRequesting = false;
            currentState.timer = window.setTimeout(poll, intervalMs); // Планируем следующий
          }
        } catch {
          if (
            !isMountedRef.current ||
            stateRef.current[id] !== currentState ||
            currentState.cancelled
          ) {
            return;
          }
          currentState.isRequesting = false;
          delete stateRef.current[id];
          onErrorRef.current(id); // Сообщаем об ошибке (кнопка "Повторить")
        }
      };

      poll();
    });

    // Здесь нет cleanup! Мы управляем таймерами вручную, чтобы они не сбивались при ререндере.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey, intervalMs]);

  // ЭФФЕКТ 2: Полная очистка при размонтировании компонента
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      // Убиваем все активные таймеры
      Object.keys(stateRef.current).forEach((id) => {
        if (stateRef.current[id].timer) {
          clearTimeout(stateRef.current[id].timer);
        }
      });
      // Полностью очищаем состояние
      stateRef.current = {};
    };
  }, []);
}
