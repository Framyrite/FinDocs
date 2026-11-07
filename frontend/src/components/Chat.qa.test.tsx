import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Chat } from "./Chat";

describe("Chat QA Edge Cases (UI-14, UI-16)", () => {
  it("блокирует отправку пустого или состоящего только из пробелов вопроса", async () => {
    const handleAsk = vi.fn();
    render(<Chat onAsk={handleAsk} hasReadyDocuments={true} documents={[]} selectedIds={null} onSelectionChange={() => {}} />);
    
    const input = screen.getByPlaceholderText("Введите свой вопрос...");
    const button = screen.getByText("Отправить");

    await userEvent.type(input, "   ");
    await userEvent.click(button);
    
    expect(handleAsk).not.toHaveBeenCalled();
  });

  it("запрещает повторную отправку во время ожидания ответа", async () => {
    const pendingPromise = new Promise(() => {});
    const handleAsk = vi.fn().mockReturnValue(pendingPromise);

    render(<Chat onAsk={handleAsk} hasReadyDocuments={true} documents={[]} selectedIds={null} onSelectionChange={() => {}} />);
    
    const input = screen.getByPlaceholderText("Введите свой вопрос...");
    const button = screen.getByText("Отправить");

    await userEvent.type(input, "Вопрос");
    await userEvent.click(button);
    await userEvent.click(button); 
    
    expect(handleAsk).toHaveBeenCalledTimes(1);
  });
  
  it("очищает старый ответ с экрана при отправке нового вопроса", async () => {
    const handleAsk = vi.fn().mockResolvedValue({ status: "answered", answer: "Старый ответ", sources: [] });
    
    render(<Chat onAsk={handleAsk} hasReadyDocuments={true} documents={[]} selectedIds={null} onSelectionChange={() => {}} />);
    const input = screen.getByPlaceholderText("Введите свой вопрос...");
    const button = screen.getByText("Отправить");

    await userEvent.type(input, "Вопрос 1");
    await userEvent.click(button);
    expect(await screen.findByText("Старый ответ", { exact: false })).toBeInTheDocument();

    handleAsk.mockReturnValue(new Promise(() => {}));
    await userEvent.clear(input);
    await userEvent.type(input, "Вопрос 2");
    await userEvent.click(button);

    expect(screen.queryByText("Старый ответ", { exact: false })).not.toBeInTheDocument();
  });
});