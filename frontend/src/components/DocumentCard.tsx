import { useEffect, useRef, useState } from "react";
import type { Document } from "../types/api";

interface DocumentCardProps {
  doc: Document;
  onDelete: (id: string) => void;
  hasPollingError: boolean;
  onRetryPolling: (id: string) => void;
}

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
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z" />
            <path d="M14 3v6h6M8 13h8M8 17h5" />
          </svg>
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
          {statusLabels[doc.status]}
        </span>

        {doc.status === "error" && doc.error_message && (
          <p className="document-error">{doc.error_message}</p>
        )}

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
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <circle cx="5" cy="12" r="1.7" />
              <circle cx="12" cy="12" r="1.7" />
              <circle cx="19" cy="12" r="1.7" />
            </svg>
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
                  setIsMenuOpen(false);
                  onDelete(doc.id);
                }}
              >
                Удалить
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
