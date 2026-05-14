import { FileSearch } from 'lucide-react';
import { FormEvent, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { ResearchResponse, runResearch } from '../api/client';
import { CitationValidationBadge } from './CitationValidationBadge';
import { SourceCitation } from './SourceCitation';

export function ResearchPanel({
  selectedDocumentIds
}: {
  selectedDocumentIds: string[];
}) {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await runResearch(trimmed, selectedDocumentIds));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to run research');
    } finally {
      setLoading(false);
    }
  }

  return (
    <details className="research-panel">
      <summary>Research assistant</summary>
      <form className="research-form" onSubmit={handleSubmit}>
        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask for a comparison, report, or multi-step analysis..."
          rows={2}
        />
        <button className="research-button" disabled={loading || !query.trim()}>
          <FileSearch size={17} />
          {loading ? 'Running' : 'Run'}
        </button>
      </form>
      {error ? <div className="debug-error">{error}</div> : null}
      {result ? (
        <section className="research-result">
          <div className="research-answer">
            <ReactMarkdown>{result.answer}</ReactMarkdown>
          </div>
          {result.citation_validation ? (
            <CitationValidationBadge validation={result.citation_validation} />
          ) : null}
          <details className="research-steps">
            <summary>
              <span>Steps</span>
              <strong>{result.steps.length}</strong>
            </summary>
            {result.steps.map((step) => (
              <article key={`${step.step}-${step.query}`}>
                <header>
                  <span>Step {step.step}</span>
                  <strong>{step.query}</strong>
                </header>
                <div className="sources compact">
                  {step.sources.slice(0, 3).map((source, index) => (
                    <SourceCitation
                      key={`${step.step}-${source.document_id}-${source.page_number}-${index}`}
                      source={source}
                    />
                  ))}
                </div>
              </article>
            ))}
          </details>
        </section>
      ) : null}
    </details>
  );
}
