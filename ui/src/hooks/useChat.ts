import { useCallback, useEffect, useState } from 'react';
import { createSession, Source, streamChat } from '../api/client';

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  latencyMs?: number;
};

export function useChat() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    createSession()
      .then((session) => setSessionId(session.session_id))
      .catch(() => setSessionId(null));
  }, []);

  const ask = useCallback(
    async (query: string, documentIds?: string[]) => {
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: query
      };
      const assistantId = crypto.randomUUID();
      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: ''
      };
      setMessages((current) => [...current, userMessage, assistantMessage]);
      setLoading(true);
      setError(null);
      try {
        await streamChat(query, sessionId, documentIds, (event) => {
          if (event.type === 'sources') {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId ? { ...message, sources: event.sources } : message
              )
            );
          }
          if (event.type === 'token') {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? { ...message, content: `${message.content}${event.content}` }
                  : message
              )
            );
          }
          if (event.type === 'done') {
            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId ? { ...message, latencyMs: event.latency_ms } : message
              )
            );
          }
          if (event.type === 'error') {
            setError(event.message);
          }
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to send question');
      } finally {
        setLoading(false);
      }
    },
    [sessionId]
  );

  const reset = useCallback(() => {
    setMessages([]);
    createSession()
      .then((session) => setSessionId(session.session_id))
      .catch(() => setSessionId(null));
  }, []);

  return { messages, loading, error, ask, reset, sessionId };
}
