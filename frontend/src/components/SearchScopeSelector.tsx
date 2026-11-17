import { useEffect, useId, useRef, useState } from "react";
import type { Document } from "../types/api";

interface SearchScopeSelectorProps {
  documents: Document[];
  selectedIds: string[] | null;
  onChange: (ids: string[] | null) => void;
}

export function SearchScopeSelector({
  documents,
  selectedIds,
  onChange,
}: SearchScopeSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const containerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownId = useId();

  const readyDocuments = documents.filter(
    (document) => document.status === "ready",
  );

  const selectedReadyIds = readyDocuments
    .filter(
      (document) => selectedIds !== null && selectedIds.includes(document.id),
    )
    .map((document) => document.id);

  const normalizedQuery = searchQuery.trim().toLocaleLowerCase("ru");

  const filteredDocuments = readyDocuments.filter((document) =>
    document.filename.toLocaleLowerCase("ru").includes(normalizedQuery),
  );

  const isAllSelected = selectedIds === null;

  const selectionLabel = isAllSelected
    ? "Все документы"
    : `Выбрано файлов: ${selectedReadyIds.length}`;

  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (
        event.target instanceof Node &&
        !containerRef.current?.contains(event.target)
      ) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsOpen(false);
        buttonRef.current?.focus();
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const toggleDocument = (id: string) => {
    const nextIds = selectedReadyIds.includes(id)
      ? selectedReadyIds.filter((selectedId) => selectedId !== id)
      : [...selectedReadyIds, id];

    onChange(nextIds.length > 0 ? nextIds : null);
  };

  return (
    <div className="search-scope" ref={containerRef}>
      <button
        ref={buttonRef}
        type="button"
        className="search-scope-button"
        aria-label={`Область поиска: ${selectionLabel}`}
        aria-expanded={isOpen}
        aria-controls={isOpen ? dropdownId : undefined}
        onClick={() => {
          if (!isOpen) {
            setSearchQuery("");
          }

          setIsOpen((previous) => !previous);
        }}
      >
        <span>{selectionLabel}</span>

        <svg
          className={`search-scope-chevron ${
            isOpen ? "search-scope-chevron--open" : ""
          }`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {isOpen && (
        <div
          id={dropdownId}
          className="search-scope-dropdown"
          role="group"
          aria-label="Документы для поиска"
        >
          <button
            type="button"
            className="search-scope-all"
            aria-pressed={isAllSelected}
            onClick={() => onChange(null)}
          >
            <span className="search-scope-all-mark" aria-hidden="true">
              {isAllSelected ? "✓" : ""}
            </span>
            Все готовые документы
          </button>

          <div className="search-scope-divider" role="separator" />

          <label className="search-scope-search">
            <span className="visually-hidden">Поиск файлов для выбора</span>

            <input
              type="search"
              placeholder="Найти файл"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </label>

          {readyDocuments.length === 0 ? (
            <p className="search-scope-empty">Готовых документов пока нет.</p>
          ) : filteredDocuments.length === 0 ? (
            <p className="search-scope-empty">Файлы не найдены.</p>
          ) : (
            <div className="search-scope-files">
              {filteredDocuments.map((document) => (
                <label key={document.id} className="search-scope-file">
                  <input
                    type="checkbox"
                    checked={selectedReadyIds.includes(document.id)}
                    onChange={() => toggleDocument(document.id)}
                  />

                  <span title={document.filename}>{document.filename}</span>
                </label>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
