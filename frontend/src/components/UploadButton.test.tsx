import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { UploadButton } from "./UploadButton";

function openUpload(onUpload: (file: File) => Promise<void>) {
  const { container } = render(<UploadButton onUpload={onUpload} />);

  fireEvent.click(screen.getByRole("button", { name: /Загрузить документ/i }));

  const input = container.querySelector<HTMLInputElement>('input[type="file"]');

  if (!input) {
    throw new Error("Поле выбора файла не найдено");
  }

  return input;
}

describe("UploadButton", () => {
  it("показывает ошибку для неподдерживаемого формата", () => {
    const handleUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(handleUpload);
    const file = new File(["test"], "test.pdf", {
      type: "application/pdf",
    });

    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Поддерживаются только файлы TXT.",
    );

    expect(
      screen.getByRole("button", { name: "Загрузить", exact: true }),
    ).toBeDisabled();

    expect(handleUpload).not.toHaveBeenCalled();
  });

  it("отправляет подходящий файл только после подтверждения", async () => {
    const handleUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(handleUpload);
    const file = new File(["test"], "test.txt", {
      type: "text/plain",
    });

    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByText("test.txt")).toBeInTheDocument();
    expect(handleUpload).not.toHaveBeenCalled();

    fireEvent.click(
      screen.getByRole("button", { name: "Загрузить", exact: true }),
    );

    await waitFor(() => {
      expect(handleUpload).toHaveBeenCalledExactlyOnceWith(file);
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("не допускает загрузку пустого файла", () => {
    const handleUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(handleUpload);
    const file = new File([], "empty.txt", {
      type: "text/plain",
    });

    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Файл пустой. Выберите файл с текстом.",
    );

    expect(
      screen.getByRole("button", { name: "Загрузить", exact: true }),
    ).toBeDisabled();

    expect(handleUpload).not.toHaveBeenCalled();
  });

  it("не допускает загрузку файла больше 10 МБ", () => {
    const handleUpload = vi.fn().mockResolvedValue(undefined);
    const input = openUpload(handleUpload);
    const file = new File([new Uint8Array(10 * 1024 * 1024 + 1)], "large.txt", {
      type: "text/plain",
    });

    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Размер файла превышает 10 МБ.",
    );

    expect(
      screen.getByRole("button", { name: "Загрузить", exact: true }),
    ).toBeDisabled();

    expect(handleUpload).not.toHaveBeenCalled();
  });

  it("сохраняет окно и выбранный файл при ошибке отправки", async () => {
    const handleUpload = vi
      .fn()
      .mockRejectedValue(new Error("Сервер недоступен"));

    const input = openUpload(handleUpload);
    const file = new File(["test"], "test.txt", {
      type: "text/plain",
    });

    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(
      screen.getByRole("button", { name: "Загрузить", exact: true }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Сервер недоступен",
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("test.txt")).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: "Загрузить", exact: true }),
    ).toBeEnabled();
  });
});
