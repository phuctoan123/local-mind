import { Source } from '../api/client';

export function SourceCitation({ source }: { source: Source }) {
  return (
    <details className="source">
      <summary>
        <span className="source-title">{source.filename}</span>
        <span className="source-meta">
          {source.page_number ? `page ${source.page_number}` : 'page N/A'} · {Math.round(source.score * 100)}%
        </span>
      </summary>
      <p>{source.chunk_text_preview}</p>
    </details>
  );
}
