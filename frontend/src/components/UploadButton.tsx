import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Icon } from "./Icon";

interface UploadButtonProps {
  onUpload: (file: File) => Promise<void>;
  // Общий флаг передаётся из App, чтобы блокировать действия во время отправки.
  disabled?: boolean;
  // Одна логика загрузки для кнопки в документах и скрепки в чате.
  iconOnly?: boolean;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024;

// Отсекаем неподходящие файлы до запроса. Сервер повторяет проверки
// и дополнительно проверяет содержимое, включая кодировку и пустой текст.
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
  iconOnly = false,
}: UploadButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const titleId = useId();
  const descriptionId = useId();

  // showModal включает штатную модальность dialog и ограничение фокуса.
  // Проверка open защищает от повторного вызова для уже открытого окна.
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
    // После закрытия возвращаем пользователя к кнопке, открывшей окно.
    buttonRef.current?.focus();
  };

  const selectFile = (selectedFile: File) => {
    const validationError = validateFile(selectedFile);

    setError(validationError);
    // Невалидный файл не сохраняется для отправки: подтверждение недоступно.
    setFile(validationError ? null : selectedFile);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!file || disabled) return;

    setError(null);

    try {
      // Выбор файла сам по себе ничего не отправляет. Ждём подтверждённую
      // загрузку и закрываем окно только при успешном завершении запроса.
      await onUpload(file);
      closeDialog();
    } catch (uploadError) {
      // При сбое сохраняем окно и файл, чтобы пользователь мог повторить отправку.
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
        className={iconOnly ? "chat-attach-button" : "upload-button"}
        aria-label={iconOnly ? "Прикрепить документ" : undefined}
        onClick={openDialog}
        disabled={disabled}
      >
        <Icon name={iconOnly ? "paperclip" : "plus"} size={20} />

        {!iconOnly && "Загрузить документ"}
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
                <Icon name="x" size={24} />
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
              <Icon name="upload" size={32} />

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
                  <Icon name="x" size={18} />
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
