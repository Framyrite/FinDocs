import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { usePolling } from "./usePolling";

describe("usePolling", () => {
  it("останавливается при статусе ready", async () => {
    const checkStatus = vi
      .fn()
      .mockResolvedValueOnce("processing")
      .mockResolvedValueOnce("ready");
    const onStatusChange = vi.fn();
    const onError = vi.fn();
    renderHook(() =>
      usePolling(["1"], checkStatus, onStatusChange, onError, {}, 10),
    );
    await waitFor(() => {
      expect(checkStatus).toHaveBeenCalledTimes(2);
    });
    await new Promise((r) => setTimeout(r, 50));
    expect(checkStatus).toHaveBeenCalledTimes(2);
  });

  it("вызывает onError при ошибке сети", async () => {
    const checkStatus = vi.fn().mockRejectedValue(new Error("Network error"));
    const onStatusChange = vi.fn();
    const onError = vi.fn();
    renderHook(() =>
      usePolling(["1"], checkStatus, onStatusChange, onError, {}, 10),
    );
    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith("1");
    });
  });

  it("не запускает параллельные запросы при изменении списка", async () => {
    // Управляемый промис для b
    let resolveB: (status: string) => void;
    const bPromise = new Promise((res) => {
      resolveB = res;
    });

    const checkStatus = vi.fn().mockImplementation(async (id) => {
      if (id === "a") return "ready"; // a отвечает сразу
      if (id === "b") return bPromise; // b висит
    });

    const onStatusChange = vi.fn();
    const onError = vi.fn();

    // Запускаем для a и b
    const { rerender } = renderHook(
      ({ ids }) =>
        usePolling(ids, checkStatus, onStatusChange, onError, {}, 10),
      { initialProps: { ids: ["a", "b"] } },
    );

    // Ждем, пока a завершится, b начнет запрос
    await waitFor(() => {
      expect(checkStatus).toHaveBeenCalledWith("a");
      expect(checkStatus).toHaveBeenCalledWith("b");
    });

    // Меняем список на ["b"] (a удалили)
    rerender({ ids: ["b"] });

    // Проверяем, что для b не запустился второй запрос
    // (потому что первый еще висит)
    expect(checkStatus.mock.calls.filter((c) => c[0] === "b").length).toBe(1);

    // Завершаем b
    resolveB!("processing");

    // Ждем следующий тик
    await new Promise((r) => setTimeout(r, 30));

    // Теперь должен запуститься следующий запрос для b
    await waitFor(() => {
      expect(
        checkStatus.mock.calls.filter((c) => c[0] === "b").length,
      ).toBeGreaterThan(1);
    });
  });

  it("останавливает polling при размонтировании", async () => {
    let resolvePromise: (status: string) => void;
    const pendingPromise = new Promise<string>((res) => {
      resolvePromise = res;
    });

    const checkStatus = vi.fn().mockImplementation(async () => {
      return pendingPromise;
    });

    const onStatusChange = vi.fn();
    const onError = vi.fn();

    const { unmount } = renderHook(() =>
      usePolling(["1"], checkStatus, onStatusChange, onError, {}, 10),
    );

    // Ждем, пока запрос начнется
    await waitFor(() => {
      expect(checkStatus).toHaveBeenCalledTimes(1);
    });

    // Размонтируем компонент до завершения запроса
    unmount();

    // Завершаем запрос
    resolvePromise!("processing");
    await new Promise((r) => setTimeout(r, 30));

    // Проверяем, что после размонтирования не было новых запросов и обработчиков
    expect(checkStatus).toHaveBeenCalledTimes(1);
    expect(onStatusChange).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });

  it("корректно обрабатывает удаление и повторное добавление документа во время запроса", async () => {
    let resolveFirst: (status: string) => void;
    const firstPromise = new Promise<string>((res) => {
      resolveFirst = res;
    });

    const checkStatus = vi.fn().mockImplementation(async (id) => {
      if (id === "1") {
        // Первый вызов возвращает висящий промис
        if (checkStatus.mock.calls.filter((c) => c[0] === "1").length === 1) {
          return firstPromise;
        }
        // Второй вызов (после повторного добавления) возвращает ready
        return "ready";
      }
    });

    const onStatusChange = vi.fn();
    const onError = vi.fn();

    // Запускаем для "1"
    const { rerender } = renderHook(
      ({ ids }) =>
        usePolling(ids, checkStatus, onStatusChange, onError, {}, 10),
      { initialProps: { ids: ["1"] } },
    );

    // Ждем, пока первый запрос начнется
    await waitFor(() => {
      expect(checkStatus).toHaveBeenCalledTimes(1);
    });

    // Удаляем "1" (он отменяется)
    rerender({ ids: [] });

    // Сразу добавляем "1" обратно
    rerender({ ids: ["1"] });

    // Проверяем, что для "1" был запущен второй запрос (потому что старый отменен)
    await waitFor(() => {
      expect(checkStatus.mock.calls.filter((c) => c[0] === "1").length).toBe(2);
    });

    // Завершаем первый запрос — он должен проигнорироваться
    resolveFirst!("processing");

    await new Promise((r) => setTimeout(r, 30));

    // Главная проверка: старый запрос не должен был вызвать onStatusChange
    expect(onStatusChange).not.toHaveBeenCalled();
    // И не должен был вызвать onError
    expect(onError).not.toHaveBeenCalled();
  });
  it("не отправляет запрос по таймеру после размонтирования", async () => {
    const checkStatus = vi.fn().mockResolvedValue("processing");
    const onStatusChange = vi.fn();
    const onError = vi.fn();

    const { unmount } = renderHook(() =>
      usePolling(["1"], checkStatus, onStatusChange, onError, {}, 50),
    );

    // Ждем, пока первый запрос завершится и поставится таймер
    await waitFor(() => {
      expect(checkStatus).toHaveBeenCalledTimes(1);
    });

    // Размонтируем ДО того, как таймер сработает
    unmount();

    // Ждем больше, чем интервал таймера
    await new Promise((r) => setTimeout(r, 100));

    // Проверяем, что второго запроса не было
    expect(checkStatus).toHaveBeenCalledTimes(1);
  });
});
