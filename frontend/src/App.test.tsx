import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { api } from "./api";
import type { Document } from "./types/api";

// Проверяем связку App → выбор области → чат → API, а не копию логики выбора.
vi.mock("./api", () => ({
  api: {
    getDocuments: vi.fn(),
    deleteDocument: vi.fn(),
    askQuestion: vi.fn(),
    getDocumentById: vi.fn(),
    uploadDocument: vi.fn(),
  },
}));

const documents: Document[] = ["first", "second"].map((id) => ({
  id,
  filename: `${id}.txt`,
  format: "txt",
  status: "ready",
  size_bytes: 100,
  created_at: "2026-11-04T10:00:00Z",
  error_code: null,
  error_message: null,
}));

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.getDocuments).mockResolvedValue({ items: documents, total: 2 });
  vi.mocked(api.deleteDocument).mockResolvedValue(undefined);
  vi.mocked(api.askQuestion).mockResolvedValue({
    status: "answered",
    answer: "Ответ",
    sources: [],
  });
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

afterEach(() => vi.restoreAllMocks());

async function openChat() {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", {
    name: "Задайте вопрос вашим документам",
  });
  await user.click(screen.getByRole("button", { name: /Область поиска:/ }));
  return user;
}

async function deleteFirst(user: ReturnType<typeof userEvent.setup>) {
  await user.click(
    screen.getByRole("button", { name: "Мои документы", exact: true }),
  );
  await user.click(
    screen.getByRole("button", { name: "Действия с файлом «first.txt»" }),
  );
  await user.click(
    screen.getByRole("button", { name: "Удалить", exact: true }),
  );
  await waitFor(() =>
    expect(screen.queryByText("first.txt")).not.toBeInTheDocument(),
  );
  expect(api.deleteDocument).toHaveBeenCalledWith("first");
  await user.click(screen.getByRole("button", { name: "Чат", exact: true }));
}

describe("Область поиска в App", () => {
  it("не отправляет пустой выбор и возвращается к all только по нажатию пользователя", async () => {
    const user = await openChat();
    await user.click(screen.getByRole("checkbox", { name: "first.txt" }));
    const input = screen.getByRole("textbox", { name: "Ваш вопрос" });
    await user.type(input, "Вопрос");
    await user.click(screen.getByRole("button", { name: /Область поиска:/ }));
    await user.click(screen.getByRole("checkbox", { name: "first.txt" }));

    expect(screen.getByRole("status")).toHaveTextContent(
      "Выберите хотя бы один документ",
    );
    expect(
      screen.getByRole("button", { name: "Все готовые документы" }),
    ).toHaveAttribute("aria-pressed", "false");
    expect(input).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Отправить", exact: true }),
    ).toBeDisabled();

    // Прямые события не должны обходить блокировку кнопки или отправлять [].
    const form = input.closest("form");
    if (!form) throw new Error("Форма вопроса не найдена");
    fireEvent.submit(form);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(api.askQuestion).not.toHaveBeenCalled();

    await user.click(
      screen.getByRole("button", { name: "Все готовые документы" }),
    );
    expect(input).toBeEnabled();
    expect(input).toHaveValue("Вопрос");
    await user.click(
      screen.getByRole("button", { name: "Отправить", exact: true }),
    );
    await waitFor(() =>
      expect(api.askQuestion).toHaveBeenCalledExactlyOnceWith({
        question: "Вопрос",
        document_ids: null,
      }),
    );
  });

  it("после удаления последнего выбранного документа сохраняет пустой выбор при наличии других файлов", async () => {
    const user = await openChat();
    await user.click(screen.getByRole("checkbox", { name: "first.txt" }));
    await deleteFirst(user);

    expect(
      screen.getByRole("button", {
        name: "Область поиска: Документы не выбраны",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Отправить", exact: true }),
    ).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Выберите хотя бы один документ",
    );
    expect(api.askQuestion).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: /Область поиска:/ }));
    expect(
      screen.getByRole("checkbox", { name: "second.txt" }),
    ).not.toBeChecked();
    expect(
      screen.getByRole("button", { name: "Все готовые документы" }),
    ).toHaveAttribute("aria-pressed", "false");
  });

  it("после удаления одного из выбранных документов отправляет только оставшиеся ID", async () => {
    const user = await openChat();
    await user.click(screen.getByRole("checkbox", { name: "first.txt" }));
    await user.click(screen.getByRole("checkbox", { name: "second.txt" }));
    await deleteFirst(user);

    expect(
      screen.getByRole("button", { name: "Область поиска: Выбрано файлов: 1" }),
    ).toBeInTheDocument();
    await user.type(
      screen.getByRole("textbox", { name: "Ваш вопрос" }),
      "Вопрос",
    );
    await user.click(
      screen.getByRole("button", { name: "Отправить", exact: true }),
    );
    await waitFor(() =>
      expect(api.askQuestion).toHaveBeenCalledWith({
        question: "Вопрос",
        document_ids: ["second"],
      }),
    );
  });

  it("удаление документа в режиме all сохраняет режим all", async () => {
    const user = await openChat();
    await deleteFirst(user);
    expect(
      screen.getByRole("button", { name: "Область поиска: Все документы" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Ваш вопрос" })).toBeEnabled();
  });
});
