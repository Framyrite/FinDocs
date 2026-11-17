import type { ReactNode } from "react";
import type { Document } from "../types/api";
import { DocumentCard } from "./DocumentCard";

interface DocumentListProps {
  documents: Document[];
  isLoading: boolean;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onDelete: (id: string) => void;
  pollingErrors: Record<string, boolean>;
  onRetryPolling: (id: string) => void;
  uploadControl: ReactNode;
}

export function DocumentList({
  documents,
  isLoading,
  searchQuery,
  onSearchChange,
  onDelete,
  pollingErrors,
  onRetryPolling,
  uploadControl,
}: DocumentListProps) {
  const hasSearchQuery = searchQuery.trim().length > 0;

  return (
    <section className="documents-panel" aria-label="Список документов">
      <div className="documents-toolbar">
        <label className="documents-search">
          <svg
            className="documents-search-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <circle cx="10.5" cy="10.5" r="6.5" />
            <path d="m16 16 4 4" />
          </svg>

          <input
            type="search"
            aria-label="Поиск документов по названию"
            placeholder="Поиск по названию документа"
            value={searchQuery}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </label>

        <div className="documents-upload">{uploadControl}</div>
      </div>

      {isLoading ? (
        <div className="documents-empty" role="status">
          <p>Загружаем документы…</p>
        </div>
      ) : documents.length === 0 ? (
        <div className="documents-empty">
          <h2>
            {hasSearchQuery
              ? "Документы не найдены"
              : "Здесь будут ваши документы"}
          </h2>

          <p>
            {hasSearchQuery
              ? "Попробуйте изменить название в строке поиска."
              : "Загрузите лекцию или конспект, чтобы задавать вопросы по материалам."}
          </p>
        </div>
      ) : (
        <div className="documents-table" role="table" aria-label="Документы">
          <div role="rowgroup">
            <div className="documents-columns" role="row">
              <div role="columnheader">Название документа</div>
              <div role="columnheader">Статус</div>
              <div role="columnheader">Дата загрузки</div>
              <div role="columnheader" className="documents-actions-heading">
                <span className="visually-hidden">Действия</span>
              </div>
            </div>
          </div>

          <div role="rowgroup">
            {documents.map((doc) => (
              <DocumentCard
                key={doc.id}
                doc={doc}
                onDelete={onDelete}
                hasPollingError={Boolean(pollingErrors[doc.id])}
                onRetryPolling={onRetryPolling}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
