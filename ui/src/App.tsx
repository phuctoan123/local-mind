import { ChatWindow } from './components/ChatWindow';
import { CollectionPanel } from './components/CollectionPanel';
import { DocumentList } from './components/DocumentList';
import { FileUpload } from './components/FileUpload';
import { useChat } from './hooks/useChat';
import { useCollections } from './hooks/useCollections';
import { useDocuments } from './hooks/useDocuments';
import { useMemo, useState } from 'react';

export default function App() {
  const docs = useDocuments();
  const collections = useCollections();
  const chat = useChat();
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [activeCollectionId, setActiveCollectionId] = useState<string | null>(null);
  const activeCollection = useMemo(
    () => collections.collections.find((collection) => collection.id === activeCollectionId) || null,
    [collections.collections, activeCollectionId]
  );
  const selectedReadyDocumentIds = useMemo(() => {
    const readyIds = new Set(docs.documents.filter((doc) => doc.status === 'READY').map((doc) => doc.id));
    return selectedDocumentIds.filter((id) => readyIds.has(id));
  }, [docs.documents, selectedDocumentIds]);

  async function handleUseCollection(collectionId: string) {
    setSelectedDocumentIds(await collections.readyDocumentIds(collectionId));
  }

  async function handleAddToCollection(documentId: string) {
    if (!activeCollectionId) return;
    await collections.addDocument(activeCollectionId, documentId);
    await docs.refresh();
  }

  async function handleRemoveFromCollection(documentId: string) {
    if (!activeCollectionId) return;
    await collections.removeDocument(activeCollectionId, documentId);
    await docs.refresh();
  }

  return (
    <main className="app">
      <aside className="sidebar">
        <div className="brand">
          <span>LM</span>
          <div>
            <strong>LocalMind</strong>
            <small>localhost RAG</small>
          </div>
        </div>
        <FileUpload onUpload={docs.upload} />
        {docs.error ? <div className="error">{docs.error}</div> : null}
        {collections.error ? <div className="error">{collections.error}</div> : null}
        <CollectionPanel
          collections={collections.collections}
          activeCollectionId={activeCollectionId}
          loading={collections.loading}
          onActiveChange={setActiveCollectionId}
          onCreate={collections.create}
          onDelete={async (collectionId) => {
            const collection = collections.collections.find((item) => item.id === collectionId);
            if (!window.confirm(`Delete collection "${collection?.name || collectionId}"?`)) return;
            await collections.remove(collectionId);
            if (activeCollectionId === collectionId) {
              setActiveCollectionId(null);
            }
            await docs.refresh();
          }}
          onUseCollection={handleUseCollection}
        />
        <DocumentList
          documents={docs.documents}
          collections={collections.collections}
          loading={docs.loading}
          selectedDocumentIds={selectedReadyDocumentIds}
          activeCollection={activeCollection}
          onSelectionChange={setSelectedDocumentIds}
          onRefresh={docs.refresh}
          onDelete={async (documentId) => {
            const document = docs.documents.find((item) => item.id === documentId);
            const label = document?.original_name || documentId;
            if (!window.confirm(`Delete document "${label}"? This cannot be undone.`)) return;
            await docs.remove(documentId);
          }}
          onAddToCollection={handleAddToCollection}
          onRemoveFromCollection={handleRemoveFromCollection}
        />
      </aside>
      <ChatWindow
        messages={chat.messages}
        loading={chat.loading}
        error={chat.error}
        selectedDocumentCount={selectedReadyDocumentIds.length}
        selectedDocumentIds={selectedReadyDocumentIds}
        onAsk={(query) => chat.ask(query, selectedReadyDocumentIds)}
        onReset={chat.reset}
      />
    </main>
  );
}
