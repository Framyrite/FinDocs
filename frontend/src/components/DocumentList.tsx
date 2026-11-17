import type { ReactNode } from "react";
import type { Document } from "../types/api";
import { DocumentCard } from "./DocumentCard";
import { Icon } from "./Icon";

interface DocumentListProps {
  // Список уже отфильтрован по названию в App.
  documents: Document[];
  isLoading: boolean;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onDelete: (id: string) => void;
  pollingErrors: Record<string, boolean>;
  onRetryPolling: (id: string) => void;

  // Передаём готовую кнопку, сохраняя обработчик загрузки в App.
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
          <Icon name="search" size={18} className="documents-search-icon" />

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
          {/* Пустую библиотеку отличаем от отсутствия совпадений
              по введённому названию. */}
          <h2>
            {hasSearchQuery
              ? "Документы не найдены"
              : "Здесь будут ваши документы"}
          </h2>

          <p>
            {hasSearchQuery
              ? "Попробуйте изменить название в строке поиска."
              : "Загрузите лекцию или конспект, чтобы задавать вопросы по своим материалам."}
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
