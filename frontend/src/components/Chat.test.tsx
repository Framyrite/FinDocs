import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Chat } from "./Chat";
import type { Answer } from "../types/api";

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
    const button = screen.getByText("Отправить");

    await userEvent.type(input, "Что такое облигация?");
    await userEvent.click(button);

    expect(handleAsk).toHaveBeenCalledWith("Что такое облигация?", null);

    const answerText = await screen.findByText("Тестовый ответ", {
      exact: false,
    });
    expect(answerText).toBeInTheDocument();

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
    await userEvent.click(screen.getByText("Отправить"));

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
    await userEvent.click(screen.getByText("Отправить"));

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
      />,
    );

    const input = screen.getByPlaceholderText("Введите свой вопрос...");
    await userEvent.type(input, "Тестовый вопрос");
    await userEvent.click(screen.getByText("Отправить"));

    const partialWarning = await screen.findByText(
      "⚠️ Ответ неполный: система нашла информацию только по части вопроса.",
    );
    expect(partialWarning).toBeInTheDocument();
  });
});
