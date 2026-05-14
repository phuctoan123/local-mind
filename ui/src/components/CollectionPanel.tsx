import { FolderPlus, Trash2 } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { CollectionItem } from '../api/client';

export function CollectionPanel({
  collections,
  activeCollectionId,
  loading,
  onActiveChange,
  onCreate,
  onDelete,
  onUseCollection
}: {
  collections: CollectionItem[];
  activeCollectionId: string | null;
  loading: boolean;
  onActiveChange: (collectionId: string | null) => void;
  onCreate: (name: string) => Promise<void>;
  onDelete: (collectionId: string) => Promise<void>;
  onUseCollection: (collectionId: string) => Promise<void>;
}) {
  const [name, setName] = useState('');
  const activeCollection = collections.find((collection) => collection.id === activeCollectionId);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    await onCreate(trimmed);
    setName('');
  }

  return (
    <section className="panel collection-panel">
      <div className="panel-header">
        <h2>Collections</h2>
        {activeCollection ? (
          <button
            className="icon-button danger"
            aria-label={`Delete ${activeCollection.name}`}
            onClick={() => onDelete(activeCollection.id)}
          >
            <Trash2 size={16} />
          </button>
        ) : null}
      </div>
      <form className="collection-form" onSubmit={handleSubmit}>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="New collection"
        />
        <button className="icon-button" aria-label="Create collection" disabled={!name.trim()}>
          <FolderPlus size={17} />
        </button>
      </form>
      <div className="collection-list" aria-busy={loading}>
        <button
          className={`collection-row ${activeCollectionId ? '' : 'active'}`}
          onClick={() => onActiveChange(null)}
        >
          <span>All documents</span>
          <strong>All</strong>
        </button>
        {collections.map((collection) => (
          <button
            key={collection.id}
            className={`collection-row ${collection.id === activeCollectionId ? 'active' : ''}`}
            onClick={() => onActiveChange(collection.id)}
          >
            <span>{collection.name}</span>
            <strong>{collection.document_count}</strong>
          </button>
        ))}
      </div>
      {activeCollection ? (
        <button className="text-button collection-use" onClick={() => onUseCollection(activeCollection.id)}>
          Use ready documents
        </button>
      ) : null}
    </section>
  );
}
