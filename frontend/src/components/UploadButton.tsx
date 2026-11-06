// frontend/src/components/UploadButton.tsx
import React, { useRef } from "react";

interface UploadButtonProps {
  onUpload: (file: File) => void;
  disabled?: boolean;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 МБ
const ALLOWED_EXTENSIONS = [".txt"];

export const UploadButton: React.FC<UploadButtonProps> = ({
  onUpload,
  disabled,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 1. Проверка расширения
    const hasValidExtension = ALLOWED_EXTENSIONS.some((ext) =>
      file.name.toLowerCase().endsWith(ext),
    );

    if (!hasValidExtension) {
      alert(`Поддерживаются только файлы: ${ALLOWED_EXTENSIONS.join(", ")}`);
      return;
    }

    // 2. Проверка размера
    if (file.size > MAX_FILE_SIZE) {
      alert("Файл больше 10 МБ");
      return;
    }

    onUpload(file);

    // Очищаем input, чтобы можно было загрузить тот же файл снова
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <>
      <input
        type="file"
        accept={ALLOWED_EXTENSIONS.join(",")}
        ref={fileInputRef}
        onChange={handleFileChange}
        style={{ display: "none" }}
      />
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={disabled}
        style={{
          padding: "8px 16px",
          backgroundColor: disabled ? "#ccc" : "#0b5c6b",
          color: "white",
          border: "none",
          borderRadius: "6px",
          cursor: disabled ? "not-allowed" : "pointer",
          fontWeight: "bold",
        }}
      >
        + Загрузить документ
      </button>
    </>
  );
};
