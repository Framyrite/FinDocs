import { render, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { UploadButton } from "./UploadButton";

window.alert = vi.fn();

describe("UploadButton", () => {
  it("не вызывает onUpload, если файл не .txt", () => {
    const handleUpload = vi.fn();
    const { container } = render(<UploadButton onUpload={handleUpload} />);

    const input = container.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    const file = new File(["test"], "test.pdf", { type: "application/pdf" });

    fireEvent.change(input, { target: { files: [file] } });

    expect(window.alert).toHaveBeenCalledWith(
      "Поддерживаются только файлы .txt",
    );
    expect(handleUpload).not.toHaveBeenCalled();
  });

  it("вызывает onUpload, если файл .txt и подходит по размеру", () => {
    const handleUpload = vi.fn();
    const { container } = render(<UploadButton onUpload={handleUpload} />);

    const input = container.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    const file = new File(["test"], "test.txt", { type: "text/plain" });

    fireEvent.change(input, { target: { files: [file] } });

    expect(handleUpload).toHaveBeenCalledWith(file);
  });
});
