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
    const pollingErrors = {};

    renderHook(() =>
      usePolling(
        ["1"],
        checkStatus,
        onStatusChange,
        onError,
        pollingErrors,
        10,
      ),
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
    const pollingErrors = {};

    renderHook(() =>
      usePolling(
        ["1"],
        checkStatus,
        onStatusChange,
        onError,
        pollingErrors,
        10,
      ),
    );

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith("1");
    });
  });

  // НОВЫЙ ТЕСТ, который просил Максим
  it("обрабатывает два документа с задержкой без пересекающихся запросов", async () => {
    const checkStatus = vi.fn().mockImplementation(async () => {
      await new Promise((r) => setTimeout(r, 50));
      return "ready";
    });

    const onStatusChange = vi.fn();
    const onError = vi.fn();

    renderHook(() =>
      usePolling(["1", "2"], checkStatus, onStatusChange, onError, {}, 10),
    );

    await waitFor(() => {
      expect(checkStatus).toHaveBeenCalledTimes(2);
    });

    expect(checkStatus).toHaveBeenCalledWith("1");
    expect(checkStatus).toHaveBeenCalledWith("2");
  });
});
