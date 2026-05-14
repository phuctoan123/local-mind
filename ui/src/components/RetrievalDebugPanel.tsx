import { Search } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { debugRetrieval, RetrievalDebugResponse } from '../api/client';

const STAGES: Array<keyof Pick<
  RetrievalDebugResponse,
  'vector' | 'bm25' | 'fused' | 'reranked' | 'fallback' | 'data'
>> = ['data', 'reranked', 'fused', 'vector', 'bm25', 'fallback'];

export function RetrievalDebugPanel({
  selectedDocumentIds
}: {
  selectedDocumentIds: string[];
}) {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<RetrievalDebugResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await debugRetrieval(trimmed, selectedDocumentIds));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to debug retrieval');
    } finally {
      setLoading(false);
    }
  }

  return (
    <details className="retrieval-debug">
      <summary>Retrieval debug</summary>
      <form className="debug-form" onSubmit={handleSubmit}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Inspect retrieval..."
        />
        <button className="icon-button" aria-label="Inspect retrieval" disabled={loading || !query.trim()}>
          <Search size={17} />
        </button>
      </form>
      {error ? <div className="debug-error">{error}</div> : null}
      {result ? (
        <div className="debug-result">
          <div className="debug-meta">
            <span>{result.mode}</span>
            <span>{result.effective_query}</span>
          </div>
          {STAGES.map((stage) => (
            <details key={stage} className="debug-stage" open={stage === 'data'}>
              <summary>
                <span>{stage}</span>
                <strong>{result[stage].length}</strong>
              </summary>
              <div className="debug-stage-list">
                {result[stage].map((source) => (
                  <article key={`${stage}-${source.document_id}-${source.chunk_index}`}>
                    <header>
                      <span>#{source.rank}</span>
                      <strong>{source.filename}</strong>
                      <small>{Math.round(source.score * 100)}%</small>
                    </header>
                    <p>{source.chunk_text_preview}</p>
                  </article>
                ))}
              </div>
            </details>
          ))}
        </div>
      ) : null}
    </details>
  );
}
