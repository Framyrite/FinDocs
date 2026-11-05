import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DocumentCard } from "./DocumentCard";
import type { Document } from "../types/api";

describe("DocumentCard", () => {
  const mockDoc: Document = {
    id: "123",
    filename: "test.txt",
    format: "txt",
    status: "ready",
    error_code: null,
    error_message: null,
    size_bytes: 1024,
    created_at: "2026-11-04T10:00:00Z",
  };

  it("отображает имя документа и статус", () => {
    render(<DocumentCard doc={mockDoc} onDelete={() => {}} />);
    expect(screen.getByText("test.txt", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Готов")).toBeInTheDocument();
  });

  it("вызывает onDelete при клике на кнопку", () => {
    const handleDelete = vi.fn();
    render(<DocumentCard doc={mockDoc} onDelete={handleDelete} />);

    const button = screen.getByText("Удалить");
    button.click();

    expect(handleDelete).toHaveBeenCalledWith("123");
  });
});
