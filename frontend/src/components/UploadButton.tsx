import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent } from "react";

interface UploadButtonProps {
  onUpload: (file: File) => Promise<void>;
  disabled?: boolean;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024;

function validateFile(file: File): string | null {
  if (!file.name.toLowerCase().endsWith(".txt")) {
    return "Поддерживаются только файлы TXT.";
  }

  if (file.size === 0) {
    return "Файл пустой. Выберите файл с текстом.";
  }

  if (file.size > MAX_FILE_SIZE) {
    return "Размер файла превышает 10 МБ.";
  }

  return null;
}

export function UploadButton({
  onUpload,
  disabled = false,
}: UploadButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    if (isOpen && !dialogRef.current?.open) {
      dialogRef.current?.showModal();
    }
  }, [isOpen]);

  const openDialog = () => {
    setFile(null);
    setError(null);
    setIsOpen(true);
  };

  const closeDialog = () => {
    dialogRef.current?.close();
    setIsOpen(false);
    buttonRef.current?.focus();
  };

  const selectFile = (selectedFile: File) => {
    const validationError = validateFile(selectedFile);

    setError(validationError);
    setFile(validationError ? null : selectedFile);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!file || disabled) return;

    setError(null);

    try {
      await onUpload(file);
      closeDialog();
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "Не удалось загрузить файл. Попробуйте ещё раз.",
      );
    }
  };

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className="upload-button"
        onClick={openDialog}
        disabled={disabled}
      >
        <span aria-hidden="true">+</span>
        Загрузить документ
      </button>

      {isOpen && (
        <dialog
          ref={dialogRef}
          className="upload-dialog"
          aria-labelledby={titleId}
          aria-describedby={descriptionId}
          onCancel={(event) => {
            event.preventDefault();

            if (!disabled) {
              closeDialog();
            }
          }}
        >
          <form
            className="upload-form"
            onSubmit={handleSubmit}
            aria-busy={disabled}
          >
            <div className="upload-dialog-header">
              <h2 id={titleId}>Загрузить документ</h2>

              <button
                type="button"
                className="upload-close-button"
                aria-label="Закрыть окно загрузки"
                onClick={closeDialog}
                disabled={disabled}
              >
                ×
              </button>
            </div>

            <p id={descriptionId} className="upload-description">
              Выберите учебный материал в формате TXT, до 10 МБ.
            </p>

            <input
              ref={inputRef}
              type="file"
              accept=".txt,text/plain"
              hidden
              disabled={disabled}
              onChange={(event) => {
                const selectedFile = event.target.files?.[0];

                // Позволяет повторно выбрать тот же файл.
                event.target.value = "";

                if (selectedFile) {
                  selectFile(selectedFile);
                }
              }}
            />

            <button
              type="button"
              className="upload-picker"
              onClick={() => inputRef.current?.click()}
              disabled={disabled}
            >
              <span className="upload-picker-title">
                Выбрать файл на компьютере
              </span>

              <span>TXT · до 10 МБ</span>
            </button>

            {file && (
              <div className="upload-selected-file">
                <div className="upload-file-details">
                  <span className="upload-file-name" title={file.name}>
                    {file.name}
                  </span>

                  <span className="upload-file-size">
                    {file.size < 1024 * 1024
                      ? `${Math.ceil(file.size / 1024)} КБ`
                      : `${(file.size / (1024 * 1024)).toLocaleString("ru-RU", {
                          maximumFractionDigits: 1,
                        })} МБ`}
                  </span>
                </div>

                <button
                  type="button"
                  className="upload-close-button"
                  aria-label="Убрать выбранный файл"
                  disabled={disabled}
                  onClick={() => {
                    setFile(null);
                    setError(null);
                  }}
                >
                  ×
                </button>
              </div>
            )}

            {error && (
              <p className="upload-error" role="alert">
                {error}
              </p>
            )}

            <p className="upload-description">
              После загрузки документ пройдёт обработку. Когда он будет готов,
              вы сможете искать в нём ответы.
            </p>

            <div className="upload-dialog-actions">
              <button
                type="button"
                className="upload-cancel-button"
                onClick={closeDialog}
                disabled={disabled}
              >
                Отмена
              </button>

              <button
                type="submit"
                className="upload-button"
                disabled={!file || disabled}
              >
                {disabled ? "Загружаем…" : "Загрузить"}
              </button>
            </div>
          </form>
        </dialog>
      )}
    </>
  );
}
