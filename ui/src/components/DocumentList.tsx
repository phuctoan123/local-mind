import { FolderMinus, FolderPlus, RefreshCw, Trash2 } from 'lucide-react';
import { CollectionItem, DocumentItem } from '../api/client';
import { StatusBadge } from './StatusBadge';

export function DocumentList({
  documents,
  collections,
  loading,
  selectedDocumentIds,
  activeCollection,
  onSelectionChange,
  onRefresh,
  onDelete,
  onAddToCollection,
  onRemoveFromCollection
}: {
  documents: DocumentItem[];
  collections: CollectionItem[];
  loading: boolean;
  selectedDocumentIds: string[];
  activeCollection: CollectionItem | null;
  onSelectionChange: (ids: string[]) => void;
  onRefresh: () => void;
  onDelete: (id: string) => Promise<void>;
  onAddToCollection: (documentId: string) => Promise<void>;
  onRemoveFromCollection: (documentId: string) => Promise<void>;
}) {
  const selectedSet = new Set(selectedDocumentIds);
  const readyDocuments = documents.filter((doc) => doc.status === 'READY');

  function toggleDocument(documentId: string) {
    if (selectedSet.has(documentId)) {
      onSelectionChange(selectedDocumentIds.filter((id) => id !== documentId));
      return;
    }
    onSelectionChange([...selectedDocumentIds, documentId]);
  }

  function toggleAllReady() {
    if (readyDocuments.length > 0 && readyDocuments.every((doc) => selectedSet.has(doc.id))) {
      onSelectionChange([]);
      return;
    }
    onSelectionChange(readyDocuments.map((doc) => doc.id));
  }

  return (
    <section className="panel document-panel">
      <div className="panel-header">
        <h2>Documents</h2>
        <div className="panel-actions">
          <button
            className="text-button"
            onClick={toggleAllReady}
            disabled={readyDocuments.length === 0}
          >
            {readyDocuments.length > 0 && readyDocuments.every((doc) => selectedSet.has(doc.id))
              ? 'Clear'
              : 'All'}
          </button>
          <button className="icon-button" aria-label="Refresh documents" onClick={onRefresh}>
            <RefreshCw size={17} className={loading ? 'spin' : ''} />
          </button>
        </div>
      </div>
      <div className="document-list">
        {documents.length === 0 ? (
          <p className="muted">No documents indexed yet.</p>
        ) : (
          documents.map((doc) => (
            <article key={doc.id} className="document-row">
              <label className="document-select">
                <input
                  type="checkbox"
                  checked={selectedSet.has(doc.id)}
                  disabled={doc.status !== 'READY'}
                  onChange={() => toggleDocument(doc.id)}
                  aria-label={`Use ${doc.original_name} for chat`}
                />
              </label>
              <div className="document-main">
                <strong title={doc.original_name}>{doc.original_name}</strong>
                <span>
                  {formatBytes(doc.file_size)} / {doc.chunk_count} chunks
                </span>
                {doc.collection_ids.length ? (
                  <div className="document-collections">
                    {doc.collection_ids.map((collectionId) => {
                      const collection = collections.find((item) => item.id === collectionId);
                      return collection ? <mark key={collectionId}>{collection.name}</mark> : null;
                    })}
                  </div>
                ) : null}
                {doc.error_message ? <small>{doc.error_message}</small> : null}
              </div>
              <div className="document-actions">
                <StatusBadge status={doc.status} />
                {activeCollection ? (
                  doc.collection_ids.includes(activeCollection.id) ? (
                    <button
                      className="icon-button"
                      aria-label={`Remove ${doc.original_name} from ${activeCollection.name}`}
                      onClick={() => onRemoveFromCollection(doc.id)}
                    >
                      <FolderMinus size={16} />
                    </button>
                  ) : (
                    <button
                      className="icon-button"
                      aria-label={`Add ${doc.original_name} to ${activeCollection.name}`}
                      onClick={() => onAddToCollection(doc.id)}
                    >
                      <FolderPlus size={16} />
                    </button>
                  )
                ) : null}
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
