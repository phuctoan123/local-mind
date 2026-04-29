export type DocumentStatus = 'PENDING' | 'PROCESSING' | 'READY' | 'FAILED';

export type DocumentItem = {
  id: string;
  filename: string;
  original_name: string;
  file_size: number;
  mime_type: string;
  status: DocumentStatus;
  chunk_count: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};

export type Source = {
  document_id: string;
  filename: string;
  page_number?: number | null;
  chunk_text_preview: string;
  score: number;
};

export type ChatResponse = {
  answer: string;
  sources: Source[];
  session_id?: string | null;
  latency_ms: number;
};

const API_BASE = '/api/v1';

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const message = payload.detail?.message || payload.detail || payload.message || response.statusText;
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export async function uploadDocument(file: File) {
  const body = new FormData();
  body.append('file', file);
  return parseResponse(await fetch(`${API_BASE}/upload`, { method: 'POST', body }));
}

export async function listDocuments(status?: DocumentStatus) {
  const query = status ? `?status=${status}` : '';
  const data = await parseResponse<{ documents: DocumentItem[] }>(
    await fetch(`${API_BASE}/documents${query}`)
  );
  return data.documents;
}

export async function deleteDocument(documentId: string) {
  return parseResponse<void>(await fetch(`${API_BASE}/documents/${documentId}`, { method: 'DELETE' }));
}

export async function createSession() {
  return parseResponse<{ session_id: string }>(
    await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}'
    })
  );
}

export async function sendChat(query: string, sessionId?: string | null, documentIds?: string[]) {
  return parseResponse<ChatResponse>(
    await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        session_id: sessionId || undefined,
        document_ids: documentIds?.length ? documentIds : undefined,
        top_k: 5,
        stream: false
      })
    })
  );
}

export type ChatStreamEvent =
  | { type: 'sources'; sources: Source[] }
  | { type: 'token'; content: string }
  | { type: 'done'; latency_ms: number }
  | { type: 'error'; error: string; message: string };

export async function streamChat(
  query: string,
  sessionId: string | null | undefined,
  documentIds: string[] | undefined,
  onEvent: (event: ChatStreamEvent) => void
) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      session_id: sessionId || undefined,
      document_ids: documentIds?.length ? documentIds : undefined,
      top_k: 3,
      stream: true
    })
  });
  if (!response.ok || !response.body) {
    await parseResponse(response);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';
    for (const rawEvent of events) {
      const line = rawEvent
        .split('\n')
        .find((item) => item.startsWith('data:'));
      if (!line) continue;
      const data = line.slice(5).trim();
      if (!data || data === '[DONE]') continue;
      onEvent(JSON.parse(data) as ChatStreamEvent);
    }
  }
}
