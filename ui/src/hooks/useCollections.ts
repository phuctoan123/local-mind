import { useCallback, useEffect, useState } from 'react';
import {
  addDocumentToCollection,
  CollectionItem,
  createCollection,
  deleteCollection,
  getCollectionReadyDocumentIds,
  listCollections,
  removeDocumentFromCollection
} from '../api/client';

export function useCollections() {
  const [collections, setCollections] = useState<CollectionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setCollections(await listCollections());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load collections');
    } finally {
      setLoading(false);
    }
  }, []);

  const create = useCallback(
    async (name: string) => {
      setError(null);
      await createCollection(name);
      await refresh();
    },
    [refresh]
  );

  const remove = useCallback(
    async (collectionId: string) => {
      setError(null);
      await deleteCollection(collectionId);
      await refresh();
    },
    [refresh]
  );

  const addDocument = useCallback(
    async (collectionId: string, documentId: string) => {
      setError(null);
      await addDocumentToCollection(collectionId, documentId);
      await refresh();
    },
    [refresh]
  );

  const removeDocument = useCallback(
    async (collectionId: string, documentId: string) => {
      setError(null);
      await removeDocumentFromCollection(collectionId, documentId);
      await refresh();
    },
    [refresh]
  );

  const readyDocumentIds = useCallback((collectionId: string) => {
    return getCollectionReadyDocumentIds(collectionId);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return {
    collections,
    loading,
    error,
    refresh,
    create,
    remove,
    addDocument,
    removeDocument,
    readyDocumentIds
  };
}
