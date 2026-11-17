import { useEffect, useId, useRef, useState } from "react";
import { Icon } from "./Icon";
import type { Document } from "../types/api";

interface SearchScopeSelectorProps {
  documents: Document[];

  // null — поиск по всем готовым документам.
  // Массив — только явно выбранные пользователем документы.
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

  // В область поиска можно включать только обработанные документы.
  const readyDocuments = documents.filter(
    (document) => document.status === "ready",
  );

  // Режим «Все» не ставит галочки у отдельных файлов:
  // галочки отражают исключительно явный выбор пользователя.
  const selectedReadyIds = readyDocuments
    .filter(
      (document) => selectedIds !== null && selectedIds.includes(document.id),
    )
    .map((document) => document.id);

  // Поиск меняет только видимый список, сохраняя выбранные файлы.
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

        // При закрытии с клавиатуры возвращаем фокус на кнопку.
        buttonRef.current?.focus();
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    // Убираем обработчики при закрытии списка и размонтировании.
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const toggleDocument = (id: string) => {
    const nextIds = selectedReadyIds.includes(id)
      ? selectedReadyIds.filter((selectedId) => selectedId !== id)
      : [...selectedReadyIds, id];

    // Снятие последней галочки возвращает режим «Все».
    // Галочки у остальных файлов при этом не появляются.
    onChange(nextIds.length > 0 ? nextIds : null);
  };

  const toggleDropdown = () => {
    // При новом открытии показываем полный список.
    // Сам выбор документов при этом сохраняется.
    if (!isOpen) {
      setSearchQuery("");
    }

    setIsOpen((previous) => !previous);
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
        onClick={toggleDropdown}
      >
        <span>{selectionLabel}</span>

        <Icon
          name="chevron-down"
          size={16}
          className={`search-scope-chevron ${
            isOpen ? "search-scope-chevron--open" : ""
          }`}
        />
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
              {isAllSelected && <Icon name="check" size={16} />}
            </span>
            Все готовые документы
          </button>

          <div className="search-scope-divider" role="separator" />

          <label className="search-scope-search">
            <span className="visually-hidden">Поиск файлов для выбора</span>

            <Icon
              name="search"
              size={16}
              className="search-scope-search-icon"
            />

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
