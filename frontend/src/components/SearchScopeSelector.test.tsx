import { useState } from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SearchScopeSelector } from "./SearchScopeSelector";
import type { Document } from "../types/api";

function makeDocument(
  id: string,
  status: Document["status"] = "ready",
): Document {
  return {
    id,
    filename: `${id}.txt`,
    format: "txt",
    status,
    error_code: null,
    error_message: null,
    size_bytes: 1024,
    created_at: "2026-11-04T10:00:00Z",
  };
}

const documents = [
  makeDocument("first"),
  makeDocument("second"),
  makeDocument("processing", "processing"),
];

function renderSelector() {
  const onChange = vi.fn();

  function Harness() {
    const [selectedIds, setSelectedIds] = useState<string[] | null>(null);

    return (
      <SearchScopeSelector
        documents={documents}
        selectedIds={selectedIds}
        onChange={(ids) => {
          onChange(ids);
          setSelectedIds(ids);
        }}
      />
    );
  }

  render(<Harness />);

  fireEvent.click(screen.getByRole("button", { name: /Область поиска:/ }));

  return onChange;
}

describe("SearchScopeSelector", () => {
  it("изначально включает «Все» без галочек у файлов", () => {
    renderSelector();

    expect(
      screen.getByRole("button", { name: "Все готовые документы" }),
    ).toHaveAttribute("aria-pressed", "true");

    expect(screen.getAllByRole("checkbox")).toHaveLength(2);

    expect(
      screen.getByRole("checkbox", { name: "first.txt" }),
    ).not.toBeChecked();

    expect(
      screen.getByRole("checkbox", { name: "second.txt" }),
    ).not.toBeChecked();

    expect(screen.queryByText("processing.txt")).not.toBeInTheDocument();
    expect(screen.getByRole("separator")).toBeInTheDocument();
  });

  it("выбирает только отмеченный файл", () => {
    const onChange = renderSelector();

    fireEvent.click(screen.getByRole("checkbox", { name: "first.txt" }));

    expect(onChange).toHaveBeenLastCalledWith(["first"]);

    expect(screen.getByRole("checkbox", { name: "first.txt" })).toBeChecked();

    expect(
      screen.getByRole("checkbox", { name: "second.txt" }),
    ).not.toBeChecked();

    expect(
      screen.getByRole("button", { name: "Все готовые документы" }),
    ).toHaveAttribute("aria-pressed", "false");
  });

  it("после снятия последней галочки сохраняет пустой выбор и позволяет выбрать другой файл", () => {
    const onChange = renderSelector();

    fireEvent.click(screen.getByRole("checkbox", { name: "first.txt" }));

    fireEvent.click(screen.getByRole("checkbox", { name: "first.txt" }));

    expect(onChange).toHaveBeenLastCalledWith([]);
    expect(
      screen.getByRole("button", {
        name: "Область поиска: Документы не выбраны",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: "Все готовые документы" }),
    ).toHaveAttribute("aria-pressed", "false");

    expect(
      screen.getByRole("checkbox", { name: "first.txt" }),
    ).not.toBeChecked();

    expect(
      screen.getByRole("checkbox", { name: "second.txt" }),
    ).not.toBeChecked();

    fireEvent.click(screen.getByRole("checkbox", { name: "second.txt" }));

    expect(onChange).toHaveBeenLastCalledWith(["second"]);

    expect(screen.getByRole("checkbox", { name: "second.txt" })).toBeChecked();
  });

  it("сохраняет оставшийся файл при снятии одной из нескольких галочек", () => {
    const onChange = renderSelector();

    fireEvent.click(screen.getByRole("checkbox", { name: "first.txt" }));

    fireEvent.click(screen.getByRole("checkbox", { name: "second.txt" }));

    expect(onChange).toHaveBeenLastCalledWith(["first", "second"]);

    fireEvent.click(screen.getByRole("checkbox", { name: "first.txt" }));

    expect(onChange).toHaveBeenLastCalledWith(["second"]);

    expect(screen.getByRole("checkbox", { name: "second.txt" })).toBeChecked();
  });

  it("переключается на «Все» и снимает галочки по нажатию отдельного пункта", () => {
    const onChange = renderSelector();

    fireEvent.click(screen.getByRole("checkbox", { name: "first.txt" }));

    fireEvent.click(
      screen.getByRole("button", { name: "Все готовые документы" }),
    );

    expect(onChange).toHaveBeenLastCalledWith(null);

    expect(
      screen.getByRole("button", { name: "Все готовые документы" }),
    ).toHaveAttribute("aria-pressed", "true");

    expect(
      screen.getByRole("checkbox", { name: "first.txt" }),
    ).not.toBeChecked();
  });

  it("фильтрует файлы без изменения выбора и сохраняет галочку после очистки поиска", () => {
    const onChange = renderSelector();

    fireEvent.click(screen.getByRole("checkbox", { name: "first.txt" }));

    onChange.mockClear();

    const search = screen.getByRole("searchbox", {
      name: "Поиск файлов для выбора",
    });

    fireEvent.change(search, { target: { value: "SECOND" } });

    expect(
      screen.queryByRole("checkbox", { name: "first.txt" }),
    ).not.toBeInTheDocument();

    expect(
      screen.getByRole("checkbox", { name: "second.txt" }),
    ).toBeInTheDocument();

    expect(onChange).not.toHaveBeenCalled();

    fireEvent.change(search, { target: { value: "" } });

    expect(screen.getByRole("checkbox", { name: "first.txt" })).toBeChecked();

    expect(onChange).not.toHaveBeenCalled();
  });

  it("показывает отсутствие совпадений и очищает поиск при повторном открытии", () => {
    const onChange = renderSelector();

    fireEvent.change(
      screen.getByRole("searchbox", {
        name: "Поиск файлов для выбора",
      }),
      { target: { value: "несуществующий файл" } },
    );

    expect(screen.getByText("Файлы не найдены.")).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /Область поиска:/ }));

    fireEvent.click(screen.getByRole("button", { name: /Область поиска:/ }));

    expect(
      screen.getByRole("searchbox", {
        name: "Поиск файлов для выбора",
      }),
    ).toHaveValue("");

    expect(screen.getAllByRole("checkbox")).toHaveLength(2);
  });
});
