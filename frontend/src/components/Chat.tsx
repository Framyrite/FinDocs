import { useLayoutEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { SourceCard } from "./SourceCard";
import { SearchScopeSelector } from "./SearchScopeSelector";
import type { Document, Answer } from "../types/api";
import { UploadButton } from "./UploadButton";
import { Icon } from "./Icon";

interface ChatProps {
  isLoadingDocuments?: boolean;
  onAsk: (question: string, documentIds: string[] | null) => Promise<Answer>;
  hasReadyDocuments: boolean;
  documents: Document[];
  selectedIds: string[] | null;
  onSelectionChange: (ids: string[] | null) => void;
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
}

// Снимок вопроса и области поиска для повторной отправки того же запроса.
interface QuestionRequest {
  question: string;
  documentIds: string[] | null;
}

export function Chat({
  isLoadingDocuments = false,
  onAsk,
  hasReadyDocuments,
  documents,
  selectedIds,
  onSelectionChange,
  onUpload,
  isUploading,
}: ChatProps) {
  // Черновик хранится отдельно от отправленного вопроса. В текущем MVP
  // показывается последняя пара «вопрос — ответ», без хранения истории бесед.
  const [question, setQuestion] = useState("");
  const [sentQuestion, setSentQuestion] = useState("");
  const [chatTitle, setChatTitle] = useState("Новый чат");
  const [isWaiting, setIsWaiting] = useState(false);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSourcesOpen, setIsSourcesOpen] = useState(false);
  const [lastRequest, setLastRequest] = useState<QuestionRequest | null>(null);

  const questionInputRef = useRef<HTMLTextAreaElement>(null);

  // [] — явный пустой выбор, а не режим «Все» (null).
  // Проверяем его отдельно, чтобы он не мог уйти в API даже при ошибке в props.
  const isScopeEmpty = selectedIds !== null && selectedIds.length === 0;
  const canAsk = !isLoadingDocuments && !isScopeEmpty && hasReadyDocuments;
  const emptyScopeHint =
    "Выберите хотя бы один документ или включите «Все готовые документы».";

  // Поле растёт по содержимому от одной до двух строк. Ввод остаётся
  // у нижнего края карточки, поэтому дополнительная строка занимает место сверху.
  // Повторный расчёт нужен и при открытии источников: меняется ширина чата.
  useLayoutEffect(() => {
    const textarea = questionInputRef.current;
    if (!textarea) return;

    const styles = window.getComputedStyle(textarea);
    const lineHeight = Number.parseFloat(styles.lineHeight) || 24;
    const verticalPadding =
      (Number.parseFloat(styles.paddingTop) || 0) +
      (Number.parseFloat(styles.paddingBottom) || 0);

    const minHeight = lineHeight + verticalPadding;
    const maxHeight = lineHeight * 2 + verticalPadding;

    // Сначала сбрасываем высоту: иначе поле не уменьшится при удалении текста.
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(
      Math.max(textarea.scrollHeight, minHeight),
      maxHeight,
    )}px`;
  }, [question, isSourcesOpen]);

  const sendQuestion = async (request: QuestionRequest) => {
    if (isWaiting || !canAsk || request.documentIds?.length === 0) return;

    // Новый запрос заменяет предыдущий ответ и закрывает его источники.
    setIsWaiting(true);
    setAnswer(null);
    setError(null);
    setIsSourcesOpen(false);
    setLastRequest(request);
    setSentQuestion(request.question);

    // Заголовок формируем по первому вопросу; это локальная подпись интерфейса.
    setChatTitle((previous) =>
      previous === "Новый чат" ? request.question.slice(0, 60) : previous,
    );

    try {
      const result = await onAsk(request.question, request.documentIds);

      setAnswer(result);
      // Очищаем черновик только после успешного ответа.
      setQuestion("");
    } catch {
      // Технический сбой показываем отдельно от ответа insufficient_info.
      // Черновик и снимок запроса остаются для исправления или повтора.
      setError(
        "Произошла техническая ошибка при получении ответа. Попробуйте еще раз.",
      );
    } finally {
      setIsWaiting(false);
    }
  };

  const submitQuestion = () => {
    const text = question.trim();

    if (!text || isWaiting || !canAsk) return;

    // null означает все готовые документы. Явный список копируем,
    // чтобы запрос и его повтор использовали один и тот же набор ID.
    void sendQuestion({
      question: text,
      documentIds: selectedIds === null ? null : [...selectedIds],
    });
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submitQuestion();
  };

  // Enter отправляет вопрос, Shift + Enter оставляет перенос строки.
  // Во время IME-ввода Enter не должен преждевременно отправлять текст.
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

  // Форма загрузки находится вне формы вопроса: вложенные form недопустимы.
  // Боковая панель показывает только источники, полученные вместе с ответом API.
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
                {isLoadingDocuments
                  ? "Загружаем документы…"
                  : isScopeEmpty
                    ? "Выберите документы для поиска"
                    : hasReadyDocuments
                      ? "Задайте вопрос вашим документам"
                      : "Начнём с ваших материалов"}
              </h2>

              {!isLoadingDocuments && !isScopeEmpty && (
                <p>
                  {hasReadyDocuments
                    ? "Находите нужное в лекциях и конспектах и проверяйте ответы по источникам."
                    : "Загрузите документ и дождитесь обработки, чтобы начать поиск ответов."}
                </p>
              )}
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
                    disabled={isWaiting || !canAsk}
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
          {/* Подсказка видна и после ответа, если пользователь очистил выбор. */}
          {!isLoadingDocuments && isScopeEmpty && (
            <p className="chat-composer-note" role="status">
              {emptyScopeHint}
            </p>
          )}
          <div className="chat-composer">
            <UploadButton
              iconOnly
              onUpload={onUpload}
              disabled={isUploading || isWaiting}
            />

            <form className="chat-question-form" onSubmit={handleSubmit}>
              <textarea
                ref={questionInputRef}
                aria-label="Ваш вопрос"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  isLoadingDocuments
                    ? "Загружаем документы…"
                    : isScopeEmpty
                      ? "Выберите документы для поиска"
                      : hasReadyDocuments
                        ? "Введите свой вопрос..."
                        : "Сначала загрузите и дождитесь обработки документа"
                }
                disabled={isWaiting || !canAsk}
                maxLength={2000}
                rows={1}
              />

              <button
                type="submit"
                className="chat-send-button"
                aria-label="Отправить"
                disabled={!question.trim() || isWaiting || !canAsk}
              >
                <Icon name="send" size={22} />
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
              <Icon name="x" size={18} />
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
