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
  const isMountedRef = useRef(true);

  const checkStatusRef = useRef(checkStatus);
  const onStatusChangeRef = useRef(onStatusChange);
  const onErrorRef = useRef(onError);

  // Отслеживаем размонтирование
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    checkStatusRef.current = checkStatus;
    onStatusChangeRef.current = onStatusChange;
    onErrorRef.current = onError;
  });

  const idsKey = documentIds.join(",");

  useEffect(() => {
    const currentIds = new Set(documentIds);

    // 1. Останавливаем и отменяем запросы для удаленных документов
    Object.keys(stateRef.current).forEach((id) => {
      if (!currentIds.has(id)) {
        if (stateRef.current[id].timer) {
          clearTimeout(stateRef.current[id].timer);
        }
        if (stateRef.current[id].isRequesting) {
          stateRef.current[id].cancelled = true;
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

          // Если компонент размонтирован или документ отменен
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

    // 3. Cleanup: только при размонтировании компонента
    return () => {
      // Мы не отменяем здесь, потому что cleanup вызывается и при rerender
      // Отмена происходит в теле эффекта для удаленных документов
      // и через isMountedRef для полного размонтирования
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey, intervalMs, pollingErrors]);
}
