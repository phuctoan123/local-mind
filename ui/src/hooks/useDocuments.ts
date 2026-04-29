import { useCallback, useEffect, useState } from 'react';
import { deleteDocument, DocumentItem, listDocuments, uploadDocument } from '../api/client';

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDocuments(await listDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load documents');
    } finally {
      setLoading(false);
    }
  }, []);

  const upload = useCallback(
    async (file: File) => {
      setError(null);
      await uploadDocument(file);
      await refresh();
    },
    [refresh]
  );

  const remove = useCallback(
    async (documentId: string) => {
      setError(null);
      await deleteDocument(documentId);
      await refresh();
    },
    [refresh]
  );

  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, 4000);
    return () => window.clearInterval(id);
  }, [refresh]);

  return { documents, loading, error, refresh, upload, remove };
}
