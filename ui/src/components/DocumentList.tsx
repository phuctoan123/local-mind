import { RefreshCw, Trash2 } from 'lucide-react';
import { DocumentItem } from '../api/client';
import { StatusBadge } from './StatusBadge';

export function DocumentList({
  documents,
  loading,
  onRefresh,
  onDelete
}: {
  documents: DocumentItem[];
  loading: boolean;
  onRefresh: () => void;
  onDelete: (id: string) => Promise<void>;
}) {
  return (
    <section className="panel document-panel">
      <div className="panel-header">
        <h2>Documents</h2>
        <button className="icon-button" aria-label="Refresh documents" onClick={onRefresh}>
          <RefreshCw size={17} className={loading ? 'spin' : ''} />
        </button>
      </div>
      <div className="document-list">
        {documents.length === 0 ? (
          <p className="muted">No documents indexed yet.</p>
        ) : (
          documents.map((doc) => (
            <article key={doc.id} className="document-row">
              <div className="document-main">
                <strong title={doc.original_name}>{doc.original_name}</strong>
                <span>{formatBytes(doc.file_size)} · {doc.chunk_count} chunks</span>
                {doc.error_message ? <small>{doc.error_message}</small> : null}
              </div>
              <div className="document-actions">
                <StatusBadge status={doc.status} />
                <button
                  className="icon-button danger"
                  aria-label={`Delete ${doc.original_name}`}
                  onClick={() => onDelete(doc.id)}
                  disabled={doc.status === 'PROCESSING'}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
