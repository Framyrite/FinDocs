// frontend/src/components/SearchScopeSelector.tsx
import React, { useState, useEffect, useRef } from "react";
import type { Document } from "../types/api";

interface SearchScopeSelectorProps {
  documents: Document[]; // Все документы (чтобы отфильтровать готовые)
  selectedIds: string[] | null; // null = все документы
  onChange: (ids: string[] | null) => void;
}

export const SearchScopeSelector: React.FC<SearchScopeSelectorProps> = ({
  documents,
  selectedIds,
  onChange,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Закрываем по клику вне компонента
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Только готовые документы можно выбирать
  const readyDocs = documents.filter((d) => d.status === "ready");

  const isAllSelected = selectedIds === null;

  const handleSelectAll = () => {
    onChange(null);
    setIsOpen(false);
  };

  const handleToggleDocument = (id: string) => {
    // Если сейчас "все", то начинаем с пустого массива
    const current = selectedIds || [];

    if (current.includes(id)) {
      // Убираем
      const next = current.filter((item) => item !== id);
      // Если ничего не осталось — возвращаем "все"
      onChange(next.length === 0 ? null : next);
    } else {
      // Добавляем
      onChange([...current, id]);
    }
  };

  return (
    <div
      ref={dropdownRef}
      style={{ position: "relative", display: "inline-block" }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          padding: "8px 12px",
          backgroundColor: "#fff",
          border: "1px solid #ccc",
          borderRadius: "6px",
          cursor: "pointer",
          fontSize: "14px",
          color: "#333",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}
      >
        {isAllSelected ? "Все документы" : `Выбрано: ${selectedIds?.length}`}
        <span>{isOpen ? "▲" : "▼"}</span>
      </button>

      {isOpen && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            marginTop: "4px",
            backgroundColor: "white",
            color: "#333",
            border: "1px solid #ccc",
            borderRadius: "6px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
            zIndex: 10,
            minWidth: "250px",
            padding: "8px 0",
          }}
        >
          <div
            onClick={handleSelectAll}
            style={{
              padding: "8px 12px",
              cursor: "pointer",
              backgroundColor: isAllSelected ? "#e8f5e9" : "transparent",
              fontWeight: isAllSelected ? "bold" : "normal",
            }}
          >
            Все готовые документы
          </div>

          <div style={{ borderTop: "1px solid #eee", margin: "4px 0" }} />

          {readyDocs.length === 0 ? (
            <div
              style={{ padding: "8px 12px", color: "#888", fontSize: "13px" }}
            >
              Нет готовых документов
            </div>
          ) : (
            readyDocs.map((doc) => (
              <div
                key={doc.id}
                onClick={() => handleToggleDocument(doc.id)}
                style={{
                  padding: "8px 12px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  fontSize: "13px",
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedIds?.includes(doc.id) || false}
                  readOnly
                />
                {doc.filename}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
