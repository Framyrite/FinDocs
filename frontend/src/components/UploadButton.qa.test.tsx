import { render, fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { UploadButton } from "./UploadButton";

describe("UploadButton QA Edge Cases", () => {
  it("блокирует загрузку файла, превышающего 10 МиБ", async () => {
    const handleUpload = vi.fn().mockResolvedValue(undefined);
    const { container } = render(<UploadButton onUpload={handleUpload} />);

    await userEvent.click(
      screen.getByRole("button", { name: "Загрузить документ" }),
    );

    const input = container.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;
    const largeFile = new File(["a".repeat(10485761)], "huge.txt", {
      type: "text/plain",
    });

    fireEvent.change(input, { target: { files: [largeFile] } });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Размер файла превышает 10 МБ.",
    );
    expect(screen.getByRole("button", { name: "Загрузить" })).toBeDisabled();
    expect(handleUpload).not.toHaveBeenCalled();
  });

  it("кнопка disabled во время загрузки", () => {
    render(<UploadButton onUpload={vi.fn()} disabled={true} />);

    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });
});
