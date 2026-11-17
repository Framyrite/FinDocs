import { useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { SourceCard } from "./SourceCard";
import { SearchScopeSelector } from "./SearchScopeSelector";
import type { Document, Answer } from "../types/api";
import { UploadButton } from "./UploadButton";

interface ChatProps {
  onAsk: (question: string, documentIds: string[] | null) => Promise<Answer>;
  hasReadyDocuments: boolean;
  documents: Document[];
  selectedIds: string[] | null;
  onSelectionChange: (ids: string[] | null) => void;
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
}

interface QuestionRequest {
  question: string;
  documentIds: string[] | null;
}

export function Chat({
  onAsk,
  hasReadyDocuments,
  documents,
  selectedIds,
  onSelectionChange,
  onUpload,
  isUploading,
}: ChatProps) {
  const [question, setQuestion] = useState("");
  const [sentQuestion, setSentQuestion] = useState("");
  const [chatTitle, setChatTitle] = useState("Новый чат");
  const [isWaiting, setIsWaiting] = useState(false);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSourcesOpen, setIsSourcesOpen] = useState(false);
  const [lastRequest, setLastRequest] = useState<QuestionRequest | null>(null);

  const sendQuestion = async (request: QuestionRequest) => {
    if (isWaiting) return;

    setIsWaiting(true);
    setAnswer(null);
    setError(null);
    setIsSourcesOpen(false);
    setLastRequest(request);
    setSentQuestion(request.question);

    setChatTitle((previous) =>
      previous === "Новый чат" ? request.question.slice(0, 60) : previous,
    );

    try {
      const result = await onAsk(request.question, request.documentIds);

      setAnswer(result);
      setQuestion("");
    } catch {
      setError(
        "Произошла техническая ошибка при получении ответа. Попробуйте еще раз.",
      );
    } finally {
      setIsWaiting(false);
    }
  };

  const submitQuestion = () => {
    const text = question.trim();

    if (!text || isWaiting || !hasReadyDocuments) return;

    void sendQuestion({
      question: text,
      documentIds: selectedIds === null ? null : [...selectedIds],
    });
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submitQuestion();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      submitQuestion();
    }
  };

  return (
    <div className="chat-layout">
      <section className="chat-panel" aria-label="Чат по документам">
        <header className="chat-header">
          <h1 className="chat-title" title={chatTitle}>
            {chatTitle}
          </h1>

          <fieldset className="chat-scope-controls" disabled={isWaiting}>
            <legend className="visually-hidden">Область поиска</legend>

            <SearchScopeSelector
              documents={documents}
              selectedIds={selectedIds}
              onChange={onSelectionChange}
            />
          </fieldset>
        </header>

        <div className="chat-thread" tabIndex={0} aria-label="Сообщения чата">
          {!sentQuestion ? (
            <div className="chat-welcome">
              <h2>
                {hasReadyDocuments
                  ? "Задайте вопрос вашим документам"
                  : "Начнём с ваших материалов"}
              </h2>

              <p>
                {hasReadyDocuments
                  ? "Находите нужное в лекциях и конспектах и проверяйте ответы по источникам."
                  : "Загрузите документ и дождитесь обработки, чтобы начать поиск ответов."}
              </p>
            </div>
          ) : (
            <div className="chat-messages">
              <div className="chat-user-message">{sentQuestion}</div>

              {isWaiting && (
                <p className="chat-waiting" role="status">
                  Ищем ответ в выбранных материалах…
                </p>
              )}

              {error && (
                <div className="chat-notice chat-notice--error" role="alert">
                  <p>{error}</p>

                  <button
                    type="button"
                    className="chat-retry-button"
                    disabled={isWaiting || !hasReadyDocuments}
                    onClick={() => {
                      if (lastRequest) {
                        void sendQuestion(lastRequest);
                      }
                    }}
                  >
                    Повторить запрос
                  </button>
                </div>
              )}

              {answer && (
                <article className="chat-answer" aria-label="Ответ">
                  {answer.status === "partial" && (
                    <p className="chat-notice chat-notice--warning">
                      Ответ неполный: система нашла информацию только по части
                      вопроса.
                    </p>
                  )}

                  <p
                    className={
                      answer.status === "insufficient_info"
                        ? "chat-answer-text chat-notice chat-notice--warning"
                        : "chat-answer-text"
                    }
                  >
                    {answer.answer}
                  </p>

                  {answer.sources.length > 0 && (
                    <div className="chat-answer-actions">
                      <button
                        type="button"
                        className="chat-sources-button"
                        aria-expanded={isSourcesOpen}
                        aria-controls={
                          isSourcesOpen ? "chat-sources-panel" : undefined
                        }
                        onClick={() => setIsSourcesOpen(true)}
                      >
                        Источники
                        <span>{answer.sources.length}</span>
                      </button>
                    </div>
                  )}
                </article>
              )}
            </div>
          )}
        </div>

        <div className="chat-composer-area">
          <div className="chat-composer">
            <UploadButton
              iconOnly
              onUpload={onUpload}
              disabled={isUploading || isWaiting}
            />

            <form className="chat-question-form" onSubmit={handleSubmit}>
              <textarea
                aria-label="Ваш вопрос"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  hasReadyDocuments
                    ? "Введите свой вопрос..."
                    : "Сначала загрузите и дождитесь обработки документа"
                }
                disabled={isWaiting || !hasReadyDocuments}
                maxLength={2000}
                rows={2}
              />

              <button
                type="submit"
                className="chat-send-button"
                aria-label="Отправить"
                disabled={!question.trim() || isWaiting || !hasReadyDocuments}
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="m5 12 7-7 7 7M12 5v14" />
                </svg>
              </button>
            </form>
          </div>

          <p className="chat-composer-note">
            Ответы могут быть неточными. Проверяйте источники.
          </p>
        </div>
      </section>

      {isSourcesOpen && answer && answer.sources.length > 0 && (
        <aside
          id="chat-sources-panel"
          className="chat-sources-panel"
          aria-label="Источники ответа"
        >
          <div className="chat-sources-header">
            <h2>Источники</h2>

            <button
              type="button"
              className="chat-close-sources"
              aria-label="Закрыть источники"
              onClick={() => setIsSourcesOpen(false)}
            >
              ×
            </button>
          </div>

          <div className="chat-sources-content">
            {answer.sources.map((source, index) => (
              <SourceCard
                key={`${source.document_id}-${source.chunk_id}-${index}`}
                source={source}
                index={index}
              />
            ))}
          </div>
        </aside>
      )}
    </div>
  );
}
