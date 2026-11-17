import { render, screen, fireEvent } from "@testing-library/react";
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
    render(
      <DocumentCard
        doc={mockDoc}
        onDelete={() => {}}
        hasPollingError={false}
        onRetryPolling={() => {}}
      />,
    );

    expect(screen.getByText("test.txt")).toBeInTheDocument();
    expect(screen.getByText("Готов")).toBeInTheDocument();
  });

  it("вызывает onDelete после выбора удаления в меню", () => {
    const handleDelete = vi.fn();

    render(
      <DocumentCard
        doc={mockDoc}
        onDelete={handleDelete}
        hasPollingError={false}
        onRetryPolling={() => {}}
      />,
    );

    expect(
      screen.queryByRole("button", { name: "Удалить" }),
    ).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Действия с файлом «test.txt»",
      }),
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Удалить" }),
    );

    expect(handleDelete).toHaveBeenCalledExactlyOnceWith("123");
  });
});
