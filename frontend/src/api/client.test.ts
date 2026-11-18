import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiRequestError, request } from "./client";

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
    await expect(request("/documents/missing")).rejects.toBe(networkError);
  });
});
