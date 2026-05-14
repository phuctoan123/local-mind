import { RotateCcw, Send } from 'lucide-react';
import { FormEvent, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { ChatMessage } from '../hooks/useChat';
import { CitationValidationBadge } from './CitationValidationBadge';
import { ResearchPanel } from './ResearchPanel';
import { RetrievalDebugPanel } from './RetrievalDebugPanel';
import { SourceCitation } from './SourceCitation';

export function ChatWindow({
  messages,
  loading,
  error,
  onAsk,
  onReset,
  selectedDocumentCount,
  selectedDocumentIds
}: {
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  onAsk: (query: string) => Promise<void>;
  onReset: () => void;
  selectedDocumentCount: number;
  selectedDocumentIds: string[];
}) {
  const [query, setQuery] = useState('');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const hasStreamingAssistant = loading && messages[messages.length - 1]?.role === 'assistant';

  useEffect(() => {
    if (!loading) {
      setElapsedSeconds(0);
      return;
    }
    const startedAt = Date.now();
    const id = window.setInterval(() => {
      setElapsedSeconds(Math.max(1, Math.floor((Date.now() - startedAt) / 1000)));
    }, 1000);
    return () => window.clearInterval(id);
  }, [loading]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    setQuery('');
    await onAsk(trimmed);
  }

  return (
    <section className="chat-shell">
      <div className="chat-toolbar">
        <div>
          <h1>LocalMind</h1>
          <p>
            {selectedDocumentCount > 0
              ? `Using ${selectedDocumentCount} selected document${selectedDocumentCount > 1 ? 's' : ''}.`
              : 'Using all ready documents.'}
          </p>
        </div>
        <button className="icon-button" aria-label="Start new session" onClick={onReset}>
          <RotateCcw size={18} />
        </button>
      </div>
      <ResearchPanel selectedDocumentIds={selectedDocumentIds} />
      <RetrievalDebugPanel selectedDocumentIds={selectedDocumentIds} />

      <div className="messages">
        {messages.length === 0 ? (
          <div className="empty-state">
            <strong>Ask a question after at least one document is READY.</strong>
            <span>Answers will include source snippets when retrieval finds matching context.</span>
          </div>
        ) : (
          messages.map((message) => (
            <article key={message.id} className={`message ${message.role}`}>
              {message.role === 'assistant' ? (
                <div className="markdown-body">
                  <ReactMarkdown>
                    {message.content ||
                      `Retrieving sources${elapsedSeconds ? ` · ${elapsedSeconds}s` : ''}`}
                  </ReactMarkdown>
                </div>
              ) : (
                <p>{message.content}</p>
              )}
              {message.latencyMs ? <span className="latency">{message.latencyMs} ms</span> : null}
              {message.citationValidation ? (
                <CitationValidationBadge validation={message.citationValidation} />
              ) : null}
              {message.sources?.length ? (
                <div className="sources">
                  {message.sources.map((source, index) => (
                    <SourceCitation key={`${source.document_id}-${source.page_number}-${index}`} source={source} />
                  ))}
                </div>
              ) : null}
            </article>
          ))
        )}
        {loading && !hasStreamingAssistant ? (
          <div className="message assistant pending">
            <span className="thinking-dot" />
            Thinking{elapsedSeconds ? ` · ${elapsedSeconds}s` : ''}
          </div>
        ) : null}
      </div>

      {error ? <div className="error">{error}</div> : null}

      <form className="composer" onSubmit={handleSubmit}>
        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ask about your documents..."
          rows={2}
        />
        <button className="send-button" aria-label="Send question" disabled={loading || !query.trim()}>
          <Send size={19} />
        </button>
      </form>
    </section>
  );
}
