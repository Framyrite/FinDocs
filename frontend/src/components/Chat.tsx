// frontend/src/components/Chat.tsx
import React, { useState } from 'react';
import type { Answer } from '../types/api';
import { SourceCard } from './SourceCard';

interface ChatProps {
  onAsk: (question: string) => Promise<Answer>;
  hasReadyDocuments: boolean; // Новый пропс
}

export const Chat: React.FC<ChatProps> = ({ onAsk, hasReadyDocuments }) => {
  const [question, setQuestion] = useState('');
  const [isWaiting, setIsWaiting] = useState(false);
  const [answer, setAnswer] = useState<Answer | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isWaiting) return;

    setIsWaiting(true);
    setAnswer(null);

    try {
      const result = await onAsk(question);
      setAnswer(result);
      setQuestion(''); // Очищаем поле после ответа
    } catch (error) {
      alert('Ошибка при получении ответа');
    } finally {
      setIsWaiting(false);
    }
  };

  return (
    <div style={{ marginTop: '40px' }}>
      <h2>Задать вопрос</h2>
      
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '8px' }}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={
            hasReadyDocuments 
              ? "Введите свой вопрос..." 
              : "Сначала загрузите и дождитесь обработки документа"
          }
          disabled={isWaiting}
          maxLength={2000}
          style={{
            flex: 1,
            padding: '10px',
            border: '1px solid #ccc',
            borderRadius: '6px',
            fontSize: '14px'
          }}
        />
        <button
          type="submit"
          disabled={!question.trim() || isWaiting || !hasReadyDocuments}
          style={{
            padding: '10px 20px',
            backgroundColor: (!question.trim() || isWaiting) ? '#ccc' : '#0b5c6b',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: (!question.trim() || isWaiting) ? 'not-allowed' : 'pointer',
            fontWeight: 'bold'
          }}
        >
          {isWaiting ? 'Думаю...' : 'Отправить'}
        </button>
      </form>

      {/* Состояние ожидания */}
      {isWaiting && (
        <div style={{ marginTop: '20px', color: '#666' }}>
          ⏳ Система ищет ответ в документах...
        </div>
      )}

      {/* Блок ответа */}
      {answer && (
        <div style={{ marginTop: '20px' }}>
          {/* Внешний контейнер с цветом */}
          <div style={{
            padding: '16px',
            backgroundColor: 
              answer.status === 'insufficient_info' ? '#fff3cd' : 
              answer.status === 'partial' ? '#fff3cd' : 
              '#e8f5e9',
            borderLeft: `4px solid ${
              answer.status === 'insufficient_info' ? '#ffc107' : 
              answer.status === 'partial' ? '#ffc107' : 
              '#4caf50'
            }`,
            borderRadius: '4px',
            whiteSpace: 'pre-wrap',
            marginBottom: '16px'
          }}>
            {answer.answer}

            {/* Пометка для частичного ответа */}
            {answer.status === 'partial' && (
              <div style={{ marginTop: '8px', fontWeight: 'bold', color: '#856404' }}>
                ⚠️ Ответ неполный: система нашла информацию только по части вопроса.
              </div>
            )}
          </div>

          {/* Источники */}
          {answer.sources.length > 0 && (
            <div>
              <h4 style={{ marginBottom: '8px' }}>Источники:</h4>
              {answer.sources.map((source, idx) => (
                <SourceCard key={idx} source={source} index={idx} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
