import type { Source } from "../types/api";

interface SourceCardProps {
  source: Source;
  index: number;
}

export function SourceCard({ source, index }: SourceCardProps) {
  return (
    <article className="source-card">
      <p className="source-card-number">Источник {index + 1}</p>

      <h3 className="source-card-filename">{source.filename}</h3>

      <blockquote className="source-card-quote">«{source.quote}»</blockquote>
    </article>
  );
}
