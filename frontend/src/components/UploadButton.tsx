import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Icon } from "./Icon";

interface UploadButtonProps {
  // Контракт API не меняется: один файл на один POST /documents.
  onUpload: (file: File) => Promise<void>;
  // Внешний флаг общей загрузки из App.
  disabled?: boolean;
  // Одна очередь и один диалог для кнопки документов и скрепки чата.
  iconOnly?: boolean;
}

type UploadState = "pending" | "uploading" | "accepted" | "invalid" | "failed";

interface UploadItem {
  id: number;
  file: File;
  state: UploadState;
  error: string | null;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024;

const stateLabels: Record<UploadState, string> = {
  pending: "Ожидает отправки",
  uploading: "Отправляется…",
  accepted: "Передан на обработку",
  invalid: "Файл не подходит",
  failed: "Не удалось отправить",
};

// Проверяем каждый файл отдельно. Сервер повторяет проверки и проверяет
// содержимое TXT. Лимит библиотеки (по умолчанию 100) также контролирует сервер;
// отдельного ограничения количества файлов в одном выборе контракт не задаёт.
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

function formatSize(bytes: number) {
  if (bytes === 0) return "0 Б";
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024)} КБ`;
  return `${(bytes / (1024 * 1024)).toLocaleString("ru-RU", {
    maximumFractionDigits: 1,
  })} МБ`;
}

export function UploadButton({
  onUpload,
  disabled = false,
  iconOnly = false,
}: UploadButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [items, setItems] = useState<UploadItem[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const nextIdRef = useRef(0);
  // Ref блокирует повторный submit сразу, до следующего рендера.
  const submittingRef = useRef(false);

  const titleId = useId();
  const descriptionId = useId();

  // App переключает disabled для отдельного запроса. Локальный флаг
  // удерживает блокировку на протяжении всей последовательной отправки.
  const isBusy = disabled || isSubmitting;
  const acceptedCount = items.filter(
    (item) => item.state === "accepted",
  ).length;
  const failedCount = items.filter((item) => item.state === "failed").length;
  const hasInvalidFiles = items.some((item) => item.state === "invalid");
  const hasCandidates = items.some(
    (item) => item.state === "pending" || item.state === "failed",
  );

  useEffect(() => {
    if (isOpen && !dialogRef.current?.open) {
      dialogRef.current?.showModal();
    }
  }, [isOpen]);

  const openDialog = () => {
    if (disabled || submittingRef.current) return;
    setItems([]);
    setIsOpen(true);
  };

  const closeDialog = () => {
    if (disabled || submittingRef.current) return;
    dialogRef.current?.close();
    setIsOpen(false);
    buttonRef.current?.focus();
  };

  const addFiles = (files: File[]) => {
    if (disabled || submittingRef.current) return;

    const addedItems: UploadItem[] = files.map((file) => {
      const error = validateFile(file);
      nextIdRef.current += 1;
      return {
        id: nextIdRef.current,
        file,
        state: error ? "invalid" : "pending",
        error,
      };
    });

    // Повторное открытие выбора дополняет очередь. Имена не используются
    // как ключи: контракт допускает разные документы с одинаковым именем.
    setItems((previous) => [...previous, ...addedItems]);
  };

  const updateItem = (
    id: number,
    state: UploadState,
    error: string | null = null,
  ) => {
    setItems((previous) =>
      previous.map((item) =>
        item.id === id ? { ...item, state, error } : item,
      ),
    );
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    // Проверка действует и при прямом submit формы, а не только через disabled.
    // Один неподходящий файл блокирует всю очередь до его удаления из списка.
    if (disabled || submittingRef.current || hasInvalidFiles) return;

    // До отправки вся очередь должна пройти локальную проверку.
    // Уже принятые сервером файлы повторно не отправляем; при серверной ошибке
    // можно повторить только failed и новые pending.
    const queue = items.filter(
      (item) => item.state === "pending" || item.state === "failed",
    );
    if (queue.length === 0) return;

    submittingRef.current = true;
    setIsSubmitting(true);
    let requestFailed = false;

    try {
      // Каждый файл — отдельный запрос и отдельный результат. Отправляем
      // последовательно, не меняя API и существующий обработчик в App.
      for (const item of queue) {
        updateItem(item.id, "uploading");
        try {
          await onUpload(item.file);
          // Успех POST означает принятие файла, а не готовность его обработки.
          // Статусы обработки в библиотеке продолжает обновлять polling.
          updateItem(item.id, "accepted");
        } catch (error) {
          requestFailed = true;
          updateItem(
            item.id,
            "failed",
            error instanceof Error
              ? error.message
              : "Не удалось загрузить файл. Попробуйте ещё раз.",
          );
        }
      }
    } finally {
      submittingRef.current = false;
      setIsSubmitting(false);
    }

    // Локально неподходящие файлы были отсеяны до начала очереди.
    // Серверные ошибки всё ещё возможны (например, лимит библиотеки):
    // при них сохраняем результаты. При полном успехе окно закрывается.
    if (!requestFailed) {
      closeDialog();
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
        disabled={isBusy}
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
            if (!isBusy) closeDialog();
          }}
        >
          <form
            className="upload-form"
            onSubmit={handleSubmit}
            aria-busy={isBusy}
          >
            <div className="upload-dialog-header">
              <h2 id={titleId}>Загрузить документы</h2>
              <button
                type="button"
                className="upload-close-button"
                aria-label="Закрыть окно загрузки"
                onClick={closeDialog}
                disabled={isBusy}
              >
                <Icon name="x" size={24} />
              </button>
            </div>

            <p id={descriptionId} className="upload-description">
              Выберите один или несколько файлов TXT. До 10 МБ на каждый файл.
              Повторный выбор добавляет файлы к списку.
            </p>

            <input
              ref={inputRef}
              type="file"
              accept=".txt,text/plain"
              multiple
              hidden
              disabled={isBusy}
              onChange={(event) => {
                const files = Array.from(event.target.files ?? []);
                // Сбрасываем input после чтения FileList: тот же файл можно
                // выбрать повторно, а уже добавленные элементы остаются в state.
                event.target.value = "";
                if (files.length > 0) addFiles(files);
              }}
            />

            <button
              type="button"
              className="upload-picker"
              onClick={() => inputRef.current?.click()}
              disabled={isBusy}
            >
              <Icon name="upload" size={32} />
              <span className="upload-picker-title">
                {items.length > 0
                  ? "Добавить файлы"
                  : "Выбрать файлы на компьютере"}
              </span>
              <span>TXT · до 10 МБ на файл</span>
            </button>

            {items.length > 0 && (
              <ul className="upload-file-list" aria-label="Выбранные файлы">
                {items.map((item) => (
                  <li className="upload-selected-file" key={item.id}>
                    <div className="upload-file-details">
                      <span className="upload-file-name" title={item.file.name}>
                        {item.file.name}
                      </span>
                      <span className="upload-file-size">
                        {formatSize(item.file.size)}
                      </span>
                      {item.state !== "invalid" && (
                        <span
                          className={`upload-item-status upload-item-status--${item.state}`}
                        >
                          {stateLabels[item.state]}
                        </span>
                      )}
                      {item.error && (
                        <p className="upload-file-error" role="alert">
                          {item.state === "invalid"
                            ? `Файл не подходит. ${item.error}`
                            : item.error}
                        </p>
                      )}
                    </div>

                    {/* Удаляем только из очереди. Принятые файлы удаляются
                        с сервера отдельно, через библиотеку документов. */}
                    {item.state !== "accepted" && (
                      <button
                        type="button"
                        className="upload-close-button"
                        aria-label={`Убрать файл «${item.file.name}»`}
                        disabled={isBusy}
                        onClick={() =>
                          setItems((previous) =>
                            previous.filter((entry) => entry.id !== item.id),
                          )
                        }
                      >
                        <Icon name="x" size={18} />
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {(isSubmitting || acceptedCount > 0 || failedCount > 0) && (
              <p className="upload-progress" role="status">
                Принято сервером: {acceptedCount}. Ошибок отправки:{" "}
                {failedCount}.
              </p>
            )}

            {hasInvalidFiles && (
              <p className="upload-file-error">
                Уберите файлы с ошибками, чтобы загрузить список.
              </p>
            )}

            <div className="upload-dialog-actions">
              <button
                type="button"
                className="upload-cancel-button"
                onClick={closeDialog}
                disabled={isBusy}
              >
                {acceptedCount > 0 ? "Закрыть" : "Отмена"}
              </button>
              <button
                type="submit"
                className="upload-button"
                disabled={!hasCandidates || hasInvalidFiles || isBusy}
              >
                {isBusy ? "Загружаем…" : "Загрузить"}
              </button>
            </div>
          </form>
        </dialog>
      )}
    </>
  );
}
