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
});
