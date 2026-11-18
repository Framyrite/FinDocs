import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import type { Answer, Document, Source } from "../types/api";
import { api } from "./index";
import { ApiResponseError } from "./client";

// Проверяем реальные API-методы и HTTP-клиент, без backend и frontend mock.
vi.mock("./config", () => ({ USE_MOCK: false, API_BASE_URL: "/api" }));

const document: Document = {
  id: "doc-1",
  filename: "пример.txt",
  format: "txt",
  status: "ready",
  error_code: null,
  error_message: null,
  size_bytes: 216,
  created_at: "2026-11-18T16:43:13.155599Z",
};
const source: Source = {
  document_id: document.id,
  filename: document.filename,
  block_id: "block-1",
  chunk_id: "chunk-1",
  start_char: 0,
  end_char: 15,
  quote: "Тестовая цитата",
};
const answer: Answer = {
  status: "answered",
  answer: "Тестовый ответ",
  sources: [source],
};
const list = { items: [document], total: 1 };
const invalidMessage = "Сервер вернул некорректный ответ. Попробуйте ещё раз.";

function jsonResponse(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  vi.spyOn(window, "alert").mockImplementation(() => {});
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("Структура ответов на границе API", () => {
  it.each([
    {
      name: "GET списка с items: null",
      body: { items: null, total: 1 },
      call: () => api.getDocuments(),
    },
    {
      name: "GET списка с некорректным документом",
      body: { items: [{ ...document, filename: {} }], total: 1 },
      call: () => api.getDocuments(),
    },
    {
      name: "GET документа с неизвестным статусом",
      body: { ...document, status: "unknown" },
      call: () => api.getDocumentById(document.id),
    },
    {
      name: "ответ чата с sources: null",
      body: { ...answer, sources: null },
      call: () => api.askQuestion({ question: "Вопрос", document_ids: null }),
    },
    {
      name: "ответ чата с объектом вместо текста цитаты",
      body: { ...answer, sources: [{ ...source, quote: {} }] },
      call: () => api.askQuestion({ question: "Вопрос", document_ids: null }),
    },
    {
      name: "POST файла с некорректным размером в ответе",
      body: { ...document, size_bytes: "216" },
      call: () => api.uploadDocument(new File(["Текст"], "пример.txt")),
    },
  ])("отклоняет $name контролируемой ошибкой", async ({ body, call }) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body)));
    const result = call();
    await expect(result).rejects.toBeInstanceOf(ApiResponseError);
    await expect(result).rejects.toMatchObject({ message: invalidMessage });
  });

  it("принимает корректные список, документ, результат загрузки и ответ с источником", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(list))
        .mockResolvedValueOnce(jsonResponse(document))
        .mockResolvedValueOnce(jsonResponse(document, 202))
        .mockResolvedValueOnce(jsonResponse(answer)),
    );
    await expect(api.getDocuments()).resolves.toEqual(list);
    await expect(api.getDocumentById(document.id)).resolves.toEqual(document);
    await expect(
      api.uploadDocument(new File(["Текст"], "пример.txt")),
    ).resolves.toEqual(document);
    await expect(
      api.askQuestion({ question: "Вопрос", document_ids: null }),
    ).resolves.toEqual(answer);
  });

  it("принимает пустой список и недостаток информации без источников", async () => {
    const emptyAnswer: Answer = {
      status: "insufficient_info",
      answer: "Недостаточно информации",
      sources: [],
    };
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse({ items: [], total: 0 }))
        .mockResolvedValueOnce(jsonResponse(emptyAnswer)),
    );
    await expect(api.getDocuments()).resolves.toEqual({ items: [], total: 0 });
    await expect(
      api.askQuestion({ question: "Вопрос", document_ids: null }),
    ).resolves.toEqual(emptyAnswer);
  });

  it("не принимает 204 вместо обязательного тела документа", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );
    await expect(api.getDocumentById(document.id)).rejects.toBeInstanceOf(
      ApiResponseError,
    );
  });
});

describe("Некорректная структура не приводит к падению интерфейса", () => {
  it("items: null показывает ошибку библиотеки и позволяет успешно повторить запрос", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ items: null, total: 0 }))
      .mockResolvedValueOnce(jsonResponse(list));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(invalidMessage);
    expect(
      screen.getByRole("button", { name: "Отправить", exact: true }),
    ).toBeDisabled();
    expect(window.alert).not.toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", { name: "Повторить", exact: true }),
    );
    expect(
      await screen.findByRole("heading", {
        name: "Задайте вопрос вашим документам",
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Ваш вопрос" })).toBeEnabled();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("sources: null показывает ошибку чата, восстанавливает вопрос и позволяет повторить с источником", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse(list))
        .mockResolvedValueOnce(jsonResponse({ ...answer, sources: null }))
        .mockResolvedValueOnce(jsonResponse(answer)),
    );
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", {
      name: "Задайте вопрос вашим документам",
    });
    const input = screen.getByRole("textbox", { name: "Ваш вопрос" });
    await user.type(input, "Вопрос");
    await user.click(
      screen.getByRole("button", { name: "Отправить", exact: true }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(invalidMessage);
    expect(input).toHaveValue("Вопрос");
    expect(
      screen.queryByRole("article", { name: "Ответ" }),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Повторить запрос" }));
    expect(await screen.findByText("Тестовый ответ")).toBeInTheDocument();
    expect(input).toHaveValue("");
    await user.click(screen.getByRole("button", { name: /^Источники/ }));
    expect(screen.getByText("«Тестовая цитата»")).toBeInTheDocument();
  });
});
