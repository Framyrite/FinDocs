// frontend/src/hooks/usePolling.ts
import { useEffect, useRef } from 'react';

export function usePolling(
  documentId: string | null,
  checkStatus: (id: string) => Promise<'processing' | 'ready' | 'error' | 'uploaded'>,
  onStatusChange: (id: string, status: string) => void,
  intervalMs: number = 2000
) {
  const timerRef = useRef<number | null>(null);
  const isPollingRef = useRef(false);
  
  // Сохраняем актуальные функции в ref, чтобы useEffect не зависел от них
  const checkStatusRef = useRef(checkStatus);
  const onStatusChangeRef = useRef(onStatusChange);

  useEffect(() => {
    checkStatusRef.current = checkStatus;
    onStatusChangeRef.current = onStatusChange;
  });

  useEffect(() => {
    if (!documentId) return;

    isPollingRef.current = true;

    const poll = async () => {
      if (!isPollingRef.current) return;

      try {
        const status = await checkStatusRef.current(documentId);

        if (status === 'ready' || status === 'error') {
          isPollingRef.current = false;
          if (timerRef.current) clearInterval(timerRef.current);
        }
        onStatusChangeRef.current(documentId, status);
        
      } catch (e) {
        console.error('[HOOK] Ошибка polling:', e);
        isPollingRef.current = false;
        if (timerRef.current) clearInterval(timerRef.current);
      }
    };

    poll();
    timerRef.current = window.setInterval(poll, intervalMs);

    return () => {
      isPollingRef.current = false;
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [documentId, intervalMs]); // <-- Убрали checkStatus и onStatusChange
}
