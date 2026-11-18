import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiNetworkError,
  ApiRequestError,
  ApiResponseError,
  request,
} from "./client";

afterEach(() => vi.unstubAllGlobals());

describe("HTTP-ошибки API-клиента", () => {
  it("сохраняет HTTP-код 404 и сообщение из контрактного ответа", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "DOCUMENT_NOT_FOUND",
              message: "Документ не найден",
            },
          }),
          { status: 404 },
        ),
      ),
    );
    const result = request("/documents/missing");
    await expect(result).rejects.toBeInstanceOf(ApiRequestError);
    await expect(result).rejects.toMatchObject({
      status: 404,
      message: "DOCUMENT_NOT_FOUND: Документ не найден",
    });
  });

  it("сохраняет HTTP-код даже при ответе без JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response("Not found", { status: 404, statusText: "Not Found" }),
        ),
    );
    await expect(request("/documents/missing")).rejects.toMatchObject({
      status: 404,
      message: "API error: 404 Not Found",
    });
  });

  it("не выдаёт сетевой сбой за HTTP 404", async () => {
    const networkError = new TypeError("Failed to fetch");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(networkError));
    const result = request("/documents/missing");
    await expect(result).rejects.toBeInstanceOf(ApiNetworkError);
    await expect(result).rejects.toMatchObject({ cause: networkError });
  });
});

describe("Проверка успешного ответа API", () => {
  it.each(["application/json; charset=utf-8", "application/vnd.findocs+json"])(
    "принимает JSON-объект с Content-Type %s",
    async (contentType) => {
      vi.stubGlobal(
        "fetch",
        vi
          .fn()
          .mockResolvedValue(
            new Response(JSON.stringify({ items: [], total: 0 }), {
              headers: { "Content-Type": contentType },
            }),
          ),
      );
      await expect(request("/documents")).resolves.toEqual({
        items: [],
        total: 0,
      });
    },
  );

  it.each(["text/html", "text/plain"])(
    "отклоняет HTTP 200 с %s вместо JSON",
    async (contentType) => {
      vi.stubGlobal(
        "fetch",
        vi
          .fn()
          .mockResolvedValue(
            new Response("<html>Vite</html>", {
              headers: { "Content-Type": contentType },
            }),
          ),
      );
      const result = request("/documents");
      await expect(result).rejects.toBeInstanceOf(ApiResponseError);
      await expect(result).rejects.toMatchObject({
        status: 200,
        message: "Сервер вернул некорректный ответ. Попробуйте ещё раз.",
      });
    },
  );

  it("отклоняет повреждённый JSON даже при правильном Content-Type", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response('{"items":', {
            headers: { "Content-Type": "application/json" },
          }),
        ),
    );
    await expect(request("/documents")).rejects.toBeInstanceOf(
      ApiResponseError,
    );
  });

  it.each(["null", "[]"])("отклоняет %s вместо объекта", async (body) => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(body, {
            headers: { "Content-Type": "application/json" },
          }),
        ),
    );
    await expect(request("/documents")).rejects.toBeInstanceOf(
      ApiResponseError,
    );
  });

  it("сохраняет успешное удаление с 204 без тела и JSON-заголовка", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );
    await expect(
      request("/documents/id", { method: "DELETE" }),
    ).resolves.toBeUndefined();
  });

  it("не теряет HTTP 500 и не формирует undefined из некорректного тела ошибки", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ error: {} }), {
            status: 500,
            statusText: "Internal Server Error",
          }),
        ),
    );
    await expect(request("/documents")).rejects.toMatchObject({
      status: 500,
      message: "API error: 500 Internal Server Error",
    });
  });

  it("не переименовывает отмену запроса в сетевую ошибку", async () => {
    const error = new DOMException("Отмена", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(error));
    await expect(request("/documents")).rejects.toBe(error);
  });
});
