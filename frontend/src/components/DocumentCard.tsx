import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";
import type { Document } from "../types/api";

interface DocumentCardProps {
  doc: Document;
  onDelete: (id: string) => void;
  hasPollingError: boolean;
  onRetryPolling: (id: string) => void;
}

// Все четыре статуса API сохраняются.
// uploaded пока визуально относится к обработке;
// отдельное отображение «Загружен» согласуется с архитектором.
const statusLabels: Record<Document["status"], string> = {
  uploaded: "Обработка",
  processing: "Обработка",
  ready: "Готов",
  error: "Ошибка",
};

const statusClasses: Record<Document["status"], string> = {
  uploaded: "document-status--processing",
  processing: "document-status--processing",
  ready: "document-status--ready",
  error: "document-status--error",
};

const statusIcons: Record<
  Document["status"],
  "loader-2" | "check" | "alert-triangle"
> = {
  uploaded: "loader-2",
  processing: "loader-2",
  ready: "check",
  error: "alert-triangle",
};

// API передаёт размер в байтах; для интерфейса переводим в КБ или МБ.
function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.ceil(bytes / 1024))} КБ`;
  }

  const megabytes = (bytes / (1024 * 1024)).toLocaleString("ru-RU", {
    maximumFractionDigits: 1,
  });

  return `${megabytes} МБ`;
}

export function DocumentCard({
  doc,
  onDelete,
  hasPollingError,
  onRetryPolling,
}: DocumentCardProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const menuRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  const createdAt = new Date(doc.created_at);
  const menuId = `document-actions-${doc.id}`;

  useEffect(() => {
    if (!isMenuOpen) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (
        event.target instanceof Node &&
        !menuRef.current?.contains(event.target)
      ) {
        setIsMenuOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsMenuOpen(false);

        // После закрытия с клавиатуры возвращаем фокус на три точки.
        menuButtonRef.current?.focus();
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isMenuOpen]);

  return (
    <div className="document-row" role="row">
      <div className="document-name-cell" role="cell">
        <span className="document-file-icon" aria-hidden="true">
          <Icon name="file-description" size={21} />
        </span>

        <div className="document-name-content">
          <div className="document-name" title={doc.filename}>
            {doc.filename}
          </div>

          <div className="document-size">{formatSize(doc.size_bytes)}</div>
        </div>
      </div>

      <div className="document-status-cell" role="cell">
        <span
          className={`document-status ${statusClasses[doc.status]}`}
          title={
            doc.status === "uploaded"
              ? "Файл принят и ожидает обработки"
              : undefined
          }
        >
          <Icon
            name={statusIcons[doc.status]}
            size={16}
            className={
              doc.status === "processing"
                ? "document-status-icon--spinning"
                : ""
            }
          />

          {statusLabels[doc.status]}
        </span>

        {/* Ошибка обработки приходит в составе самого документа. */}
        {doc.status === "error" && doc.error_message && (
          <p className="document-error">{doc.error_message}</p>
        )}

        {/* Сбой опроса не меняет статус документа:
            показываем его отдельно и разрешаем повторить проверку. */}
        {hasPollingError && (
          <div className="document-polling-error" role="status">
            <span>Не удалось обновить статус.</span>

            <button type="button" onClick={() => onRetryPolling(doc.id)}>
              Повторить
            </button>
          </div>
        )}
      </div>

      <div className="document-date" role="cell">
        {/* В API время хранится в UTC.
            Для пользователя отображаем его в часовом поясе браузера. */}
        <time dateTime={doc.created_at}>
          {createdAt.toLocaleDateString("ru-RU", {
            day: "numeric",
            month: "long",
          })}
        </time>

        <span>
          {createdAt.toLocaleTimeString("ru-RU", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>

      <div className="document-actions" role="cell">
        <div className="document-menu-wrapper" ref={menuRef}>
          <button
            ref={menuButtonRef}
            type="button"
            className="document-menu-button"
            aria-label={`Действия с файлом «${doc.filename}»`}
            aria-expanded={isMenuOpen}
            aria-controls={isMenuOpen ? menuId : undefined}
            onClick={() => setIsMenuOpen((previous) => !previous)}
          >
            <Icon name="dots-vertical" size={21} />
          </button>

          {isMenuOpen && (
            <div
              id={menuId}
              className="document-menu"
              role="group"
              aria-label="Действия с документом"
            >
              <button
                type="button"
                className="document-delete-button"
                onClick={() => {
                  // Запрос удаления и обновление списка выполняются в App.
                  setIsMenuOpen(false);
                  onDelete(doc.id);
                }}
              >
                <Icon name="trash" size={18} />
                Удалить
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
