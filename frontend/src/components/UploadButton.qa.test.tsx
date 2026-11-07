import { render, fireEvent, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { UploadButton } from "./UploadButton";

window.alert = vi.fn();

describe("UploadButton QA Edge Cases", () => {
  it("блокирует загрузку файла, превышающего 10 МиБ", () => {
    const handleUpload = vi.fn();
    const { container } = render(<UploadButton onUpload={handleUpload} />);
    
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    
    const largeFile = new File(["a".repeat(10485761)], "huge.txt", { type: "text/plain" });
    
    fireEvent.change(input, { target: { files: [largeFile] } });
    
    expect(window.alert).toHaveBeenCalled();
    expect(handleUpload).not.toHaveBeenCalled();
  });

  it("кнопка disabled во время загрузки", () => {
    render(<UploadButton onUpload={vi.fn()} isUploading={true} />);
    
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
  });
});