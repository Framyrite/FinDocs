import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Chat } from "./Chat";
import type { Answer } from "../types/api";
import {
  ApiNetworkError,
  ApiRequestError,
  ApiResponseError,
} from "../api/client";

describe("Chat", () => {
  it("отправляет вопрос и показывает ответ", async () => {
    const mockAnswer: Answer = {
      status: "answered",
      answer: "Тестовый ответ",
      sources: [
        {
          document_id: "1",
          filename: "test.txt",
          block_id: "b1",
          chunk_id: "c1",
          start_char: 0,
          end_char: 10,
          quote: "Цитата",
        },
      ],
    };

    const handleAsk = vi.fn().mockResolvedValue(mockAnswer);

    render(
      <Chat
        onAsk={handleAsk}
        hasReadyDocuments={true}
        documents={[]}
        selectedIds={null}
        onSelectionChange={() => {}}
      />,
    );

    const input = screen.getByPlaceholderText("Введите свой вопрос...");
    const button = screen.getByRole("button", { name: "Отправить" });

    await userEvent.type(input, "Что такое облигация?");
    await userEvent.click(button);

    expect(handleAsk).toHaveBeenCalledWith("Что такое облигация?", null);

    const answerText = await screen.findByText("Тестовый ответ", {
      exact: false,
    });
    expect(answerText).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^Источники/ }));

    expect(screen.getByText("test.txt", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("«Цитата»", { exact: false })).toBeInTheDocument();
  });

  it("показывает сообщение при недостатке информации", async () => {
    const mockAnswer: Answer = {
      status: "insufficient_info",
      answer:
        "В выбранных материалах не удалось найти достаточную информацию для ответа.",
      sources: [],
    };

    const handleAsk = vi.fn().mockResolvedValue(mockAnswer);

    render(
      <Chat
        onAsk={handleAsk}
        hasReadyDocuments={true}
        documents={[]}
        selectedIds={null}
        onSelectionChange={() => {}}
      />,
    );

    const input = screen.getByPlaceholderText("Введите свой вопрос...");
    await userEvent.type(input, "Тестовый вопрос");
    await userEvent.click(screen.getByRole("button", { name: "Отправить" }));

    const answerText = await screen.findByText(
      "В выбранных материалах не удалось найти достаточную информацию для ответа.",
    );
    expect(answerText).toBeInTheDocument();
  });

  it("блокирует поле ввода, если нет готовых документов", () => {
    const handleAsk = vi.fn();

    render(
      <Chat
        onAsk={handleAsk}
        hasReadyDocuments={false}
        documents={[]}
        selectedIds={null}
        onSelectionChange={() => {}}
      />,
    );

    const input = screen.getByPlaceholderText(
      "Сначала загрузите и дождитесь обработки документа",
    );
    expect(input).toBeDisabled();
  });

  it("показывает техническую ошибку при сбое API", async () => {
    const handleAsk = vi.fn().mockRejectedValue(new Error("LLM unavailable"));

    render(
      <Chat
        onAsk={handleAsk}
        hasReadyDocuments={true}
        documents={[]}
        selectedIds={null}
        onSelectionChange={() => {}}
      />,
    );

    const input = screen.getByPlaceholderText("Введите свой вопрос...");
    await userEvent.type(input, "Тестовый вопрос");
    await userEvent.click(screen.getByRole("button", { name: "Отправить" }));

    const errorText = await screen.findByText(
      "Произошла техническая ошибка при получении ответа. Попробуйте еще раз.",
    );
    expect(errorText).toBeInTheDocument();
  });

  it("показывает предупреждение при частичном ответе (partial)", async () => {
    const mockAnswer: Answer = {
      status: "partial",
      answer: "Частичный ответ",
      sources: [],
    };

    const handleAsk = vi.fn().mockResolvedValue(mockAnswer);

    render(
      <Chat
        onAsk={handleAsk}
        hasReadyDocuments={true}
        documents={[]}
        selectedIds={null}
        onSelectionChange={() => {}}
        onUpload={vi.fn().mockResolvedValue(undefined)}
        isUploading={false}
      />,
    );

    const input = screen.getByPlaceholderText("Введите свой вопрос...");
    await userEvent.type(input, "Тестовый вопрос");
    await userEvent.click(screen.getByRole("button", { name: "Отправить" }));

    const partialWarning = await screen.findByText(
      "Ответ неполный: система нашла информацию только по части вопроса.",
    );
    expect(partialWarning).toBeInTheDocument();
  });
});

describe("Причина технической ошибки в чате", () => {
  it.each([
    {
      error: new ApiResponseError(200),
      message: "Сервер вернул некорректный ответ. Попробуйте ещё раз.",
    },
    {
      error: new ApiNetworkError(new TypeError("Failed to fetch")),
      message:
        "Не удалось связаться с сервером. Проверьте подключение и попробуйте ещё раз.",
    },
    {
      error: new ApiRequestError(
        503,
        "LLM_UNAVAILABLE: Сервис временно недоступен",
        "Сервис временно недоступен",
      ),
      message: "Сервис временно недоступен",
    },
  ])("показывает $message вместо общей ошибки", async ({ error, message }) => {
    const user = userEvent.setup();
    const onAsk = vi.fn().mockRejectedValue(error);
    render(
      <Chat
        onAsk={onAsk}
        hasReadyDocuments
        documents={[]}
        selectedIds={null}
        onSelectionChange={() => {}}
        onUpload={vi.fn()}
        isUploading={false}
      />,
    );
    const input = screen.getByRole("textbox", { name: "Ваш вопрос" });
    await user.type(input, "Вопрос");
    await user.click(
      screen.getByRole("button", { name: "Отправить", exact: true }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(
      screen.getByRole("button", { name: "Повторить запрос" }),
    ).toBeEnabled();
    expect(input).toHaveValue("Вопрос");
    expect(
      screen.queryByRole("article", { name: "Ответ" }),
    ).not.toBeInTheDocument();
  });
});
