import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { SearchScopeSelector } from "./SearchScopeSelector";
import type { Document } from "../types/api";

describe("SearchScopeSelector QA Edge Cases", () => {
  const processingDoc: Document = {
    id: "3", filename: "proc.txt", format: "txt", status: "processing",
    error_code: null, error_message: null, size_bytes: 100, created_at: "2026-11-04T10:00:00Z",
  };

  it("не показывает документы со статусом uploaded или processing", async () => {
    render(<SearchScopeSelector documents={[processingDoc]} selectedIds={null} onChange={() => {}} />);
    
    await userEvent.click(screen.getByText("Все документы"));
    expect(screen.queryByText("proc.txt")).not.toBeInTheDocument();
  });

  it("не сбрасывает неявно на 'Все документы' при снятии последней галочки", async () => {
    const handleChange = vi.fn();
    const readyDoc: Document = {
      id: "1", filename: "ready.txt", format: "txt", status: "ready",
      error_code: null, error_message: null, size_bytes: 100, created_at: "2026-11-04T10:00:00Z",
    };
    render(<SearchScopeSelector documents={[readyDoc]} selectedIds={["1"]} onChange={handleChange} />);
    
    await userEvent.click(screen.getByText("Выбрано: 1"));
    await userEvent.click(screen.getByText("ready.txt"));
    
    expect(handleChange).toHaveBeenCalledWith([]);
  });
});