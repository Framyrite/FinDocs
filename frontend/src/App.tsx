// frontend/src/App.tsx
import { useEffect, useState, useCallback, useMemo } from "react";
import type { Document, Answer } from "./types/api";
import { api } from "./api";
import { ApiRequestError, getApiErrorMessage } from "./api/client";
import { DocumentList } from "./components/DocumentList";
import { UploadButton } from "./components/UploadButton";
import { Chat } from "./components/Chat";
import { Navbar } from "./components/Navbar";
import type { Tab } from "./components/Navbar";
import "./App.css";
import { usePolling } from "./hooks/usePolling";

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [documentsLoadError, setDocumentsLoadError] = useState<string | null>(
    null,
  );
  const [documentsLoadAttempt, setDocumentsLoadAttempt] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  // null = все готовые документы; [] = явный пустой выбор; массив ID = выбранные
  const [selectedDocIds, setSelectedDocIds] = useState<string[] | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("chat"); // По умолчанию открыт чат

  // Состояние для ошибок polling (сетевая ошибка)
  const [pollingErrors, setPollingErrors] = useState<Record<string, boolean>>(
    {},
  );

  useEffect(() => {
    // Ошибка загрузки — отдельное состояние, а не пустая библиотека.
    // Повтор запускается счётчиком; старый запрос не обновляет состояние
    // после cleanup (включая повторный запуск эффекта в StrictMode).
    let cancelled = false;
    api
      .getDocuments()
      .then((data) => {
        if (cancelled) return;
        setDocuments(data.items);
        setDocumentsLoadError(null);
        setIsLoading(false);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setDocumentsLoadError(
          getApiErrorMessage(
            error,
            "Проверьте подключение и попробуйте ещё раз.",
          ),
        );
        setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [documentsLoadAttempt]);

  const handleRetryDocumentsLoad = () => {
    if (isLoading) return;
    // Во время повтора показываем загрузку и блокируем повторный запрос.
    setIsLoading(true);
    setDocumentsLoadError(null);
    setDocumentsLoadAttempt((previous) => previous + 1);
  };

  // Вычисляем ID документов, которые нужно опрашивать (uploaded или processing)
  const pollingIds = useMemo(() => {
    return documents
      .filter((d) => d.status === "uploaded" || d.status === "processing")
      .map((d) => d.id);
  }, [documents]);

  const checkDocStatus = useCallback(async (id: string) => {
    const doc = await api.getDocumentById(id);

    // Обновляем документ в списке
    setDocuments((prev) =>
      prev.map((d) => (d.id === id ? { ...d, ...doc } : d)),
    );

    // Успешный запрос — сбрасываем ошибку polling для этого документа
    setPollingErrors((prev) => {
      if (!prev[id]) return prev;
      const next = { ...prev };
      delete next[id];
      return next;
    });

    return doc.status;
  }, []);

  const handlePollingError = useCallback((id: string) => {
    setPollingErrors((prev) => ({ ...prev, [id]: true }));
  }, []);

  const handleRetryPolling = (id: string) => {
    // Убираем ошибку, чтобы usePolling снова запустил опрос для этого ID
    setPollingErrors((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  // Ошибку отправки не перехватываем здесь: её покажет окно UploadButton.
  // finally снимает общий флаг загрузки и при успехе, и при ошибке.
  const handleUpload = async (file: File): Promise<void> => {
    setIsUploading(true);

    try {
      const newDocument = await api.uploadDocument(file);

      // API возвращает созданный документ: добавляем его первым без повторного
      // запроса списка. Его промежуточный статус автоматически включит polling.
      setDocuments((previous) => [
        newDocument,
        ...previous.filter((document) => document.id !== newDocument.id),
      ]);
    } finally {
      setIsUploading(false);
    }
  };

  // Удаляем известный отсутствующий документ и из библиотеки, и из выбора.
  // Пустой явный выбор не переключается на «Все».
  const removeDocumentFromState = (id: string) => {
    setDocuments((previous) =>
      previous.filter((document) => document.id !== id),
    );
    setSelectedDocIds((previous) =>
      previous === null
        ? null
        : previous.filter((documentId) => documentId !== id),
    );
    setPollingErrors((previous) => {
      const next = { ...previous };
      delete next[id];
      return next;
    });
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Удалить документ?")) return;

    try {
      await api.deleteDocument(id);
      removeDocumentFromState(id);
    } catch (error) {
      if (!(error instanceof ApiRequestError) || error.status !== 404) {
        // При сети, 403 или 5xx отсутствие документа не подтверждено:
        // не удаляем строку и не меняем выбор пользователя.
        alert(getApiErrorMessage(error, "Ошибка удаления"));
        return;
      }

      // 404 подтверждает, что документа уже нет. Это не успешный DELETE.
      // Убираем устаревшую строку сразу, даже если обновление списка даст сбой.
      removeDocumentFromState(id);

      try {
        const data = await api.getDocuments();
        const existingIds = new Set(data.items.map((document) => document.id));
        setDocuments(data.items);

        // В другой вкладке могли удалить несколько документов. Сверяем весь
        // явный выбор с ответом сервера, не расширяя его до всей библиотеки.
        setSelectedDocIds((previous) =>
          previous === null
            ? null
            : previous.filter((documentId) => existingIds.has(documentId)),
        );
        setPollingErrors((previous) =>
          Object.fromEntries(
            Object.entries(previous).filter(([documentId]) =>
              existingIds.has(documentId),
            ),
          ),
        );
      } catch {
        alert(
          "Документ уже отсутствует на сервере. Не удалось обновить список остальных документов. Обновите страницу, чтобы повторить загрузку списка.",
        );
        return;
      }

      alert("Документ уже отсутствует на сервере. Список документов обновлён.");
    }
  };

  // Функция для отправки вопроса
  const handleAskQuestion = async (
    question: string,
    docIds: string[] | null,
  ): Promise<Answer> => {
    // Пустой выбор допустим в UI, но запрещён контрактом запроса.
    // Защита остаётся и на границе API, независимо от disabled в форме.
    if (docIds !== null && docIds.length === 0) {
      throw new Error("Выберите документы для поиска");
    }
    return api.askQuestion({ question, document_ids: docIds });
  };

  // Хук для отслеживания статусов
  usePolling(
    pollingIds,
    checkDocStatus,
    () => {}, // onStatusChange
    handlePollingError,
    pollingErrors,
  );

  // Этот фильтр влияет только на список документов, не на область поиска чата.
  const filteredDocs = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  // Отправка доступна, только если готовый документ есть в выбранной области.
  const hasReadyDocuments = documents.some(
    (document) =>
      document.status === "ready" &&
      (selectedDocIds === null || selectedDocIds.includes(document.id)),
  );

  return (
    <div className="app-shell">
      <Navbar activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="app-workspace">
        {activeTab === "documents" && (
          <section className="documents-workspace" aria-label="Мои документы">
            <DocumentList
              documents={filteredDocs}
              isLoading={isLoading}
              loadError={documentsLoadError}
              onRetryLoad={handleRetryDocumentsLoad}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              onDelete={handleDelete}
              pollingErrors={pollingErrors}
              onRetryPolling={handleRetryPolling}
              uploadControl={
                <UploadButton onUpload={handleUpload} disabled={isUploading} />
              }
            />
          </section>
        )}

        {activeTab === "chat" && (
          <Chat
            isLoadingDocuments={isLoading}
            documentsLoadError={documentsLoadError}
            onRetryDocumentsLoad={handleRetryDocumentsLoad}
            onAsk={handleAskQuestion}
            hasReadyDocuments={hasReadyDocuments}
            documents={documents}
            selectedIds={selectedDocIds}
            onSelectionChange={setSelectedDocIds}
            onUpload={handleUpload}
            isUploading={isUploading}
          />
        )}
      </main>
    </div>
  );
}

export default App;
