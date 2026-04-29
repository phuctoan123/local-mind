import { ChatWindow } from './components/ChatWindow';
import { DocumentList } from './components/DocumentList';
import { FileUpload } from './components/FileUpload';
import { useChat } from './hooks/useChat';
import { useDocuments } from './hooks/useDocuments';

export default function App() {
  const docs = useDocuments();
  const chat = useChat();

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
        <DocumentList
          documents={docs.documents}
          loading={docs.loading}
          onRefresh={docs.refresh}
          onDelete={docs.remove}
        />
      </aside>
      <ChatWindow
        messages={chat.messages}
        loading={chat.loading}
        error={chat.error}
        onAsk={chat.ask}
        onReset={chat.reset}
      />
    </main>
  );
}
