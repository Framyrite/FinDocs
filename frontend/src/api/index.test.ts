import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockApi } from "../mocks/mockApi";

vi.mock("../mocks/mockApi", () => ({
  mockApi: { getDocuments: vi.fn() },
}));

beforeEach(() => {
  vi.resetModules();
  vi.clearAllMocks();
  vi.stubEnv("DEV", true);
  vi.stubEnv("VITE_USE_MOCK", undefined);
  vi.stubEnv("VITE_API_BASE_URL", undefined);
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

function mockFetch() {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ items: [], total: 0 }), {
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("Выбор режима и адреса API из окружения", () => {
  it.each([undefined, "", "false"])(
    "при VITE_USE_MOCK=%s и без адреса в dev обращается к /api/documents",
    async (mode) => {
      vi.stubEnv("VITE_USE_MOCK", mode);
      const fetchMock = mockFetch();
      const { api } = await import("./index");
      await expect(api.getDocuments()).resolves.toEqual({
        items: [],
        total: 0,
      });
      expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
        "/api/documents",
        expect.any(Object),
      );
      expect(mockApi.getDocuments).not.toHaveBeenCalled();
    },
  );

  it("при true использует frontend mock и не выполняет HTTP-запрос", async () => {
    vi.stubEnv("VITE_USE_MOCK", "true");
    vi.mocked(mockApi.getDocuments).mockResolvedValue({ items: [], total: 0 });
    const fetchMock = mockFetch();
    const { api } = await import("./index");
    await expect(api.getDocuments()).resolves.toEqual({ items: [], total: 0 });
    expect(mockApi.getDocuments).toHaveBeenCalledOnce();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("использует заданный адрес без пробелов и двойного слеша", async () => {
    vi.stubEnv("VITE_API_BASE_URL", " http://127.0.0.1:8000/ ");
    const fetchMock = mockFetch();
    const { api } = await import("./index");
    await api.getDocuments();
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
      "http://127.0.0.1:8000/documents",
      expect.any(Object),
    );
  });

  it("без адреса в production отклоняет запрос с диагностикой до вызова fetch", async () => {
    vi.stubEnv("DEV", false);
    const fetchMock = mockFetch();
    const { api } = await import("./index");
    await expect(api.getDocuments()).rejects.toThrow("Не задан адрес API");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(mockApi.getDocuments).not.toHaveBeenCalled();
  });

  it("в production использует явно настроенный путь API", async () => {
    vi.stubEnv("DEV", false);
    vi.stubEnv("VITE_API_BASE_URL", "/api");
    const fetchMock = mockFetch();
    const { api } = await import("./index");
    await api.getDocuments();
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith(
      "/api/documents",
      expect.any(Object),
    );
  });

  it("frontend mock в production не требует адреса backend", async () => {
    vi.stubEnv("DEV", false);
    vi.stubEnv("VITE_USE_MOCK", "true");
    vi.mocked(mockApi.getDocuments).mockResolvedValue({ items: [], total: 0 });
    const fetchMock = mockFetch();
    const { api } = await import("./index");
    await api.getDocuments();
    expect(mockApi.getDocuments).toHaveBeenCalledOnce();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
