import type { Source } from "../types/api";

interface SourceCardProps {
  source: Source;
  index: number;
}

// Цитату показываем из Source.quote без вырезания текста по start_char/end_char:
// позиции API считаются в Unicode-кодпоинтах, а индексы JS — в UTF-16.
export function SourceCard({ source, index }: SourceCardProps) {
  return (
    <article className="source-card">
      <p className="source-card-number">Источник {index + 1}</p>

      <h3 className="source-card-filename">{source.filename}</h3>

      <blockquote className="source-card-quote">«{source.quote}»</blockquote>
    </article>
  );
}
