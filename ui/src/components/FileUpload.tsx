import { UploadCloud } from 'lucide-react';
import { ChangeEvent, useRef, useState } from 'react';

export function FileUpload({ onUpload }: { onUpload: (file: File) => Promise<void> }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  async function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      await onUpload(file);
    } finally {
      setBusy(false);
      event.target.value = '';
    }
  }

  return (
    <div className="upload">
      <input ref={inputRef} type="file" accept=".pdf,.txt,.docx" onChange={handleChange} />
      <button className="primary-button" onClick={() => inputRef.current?.click()} disabled={busy}>
        <UploadCloud size={18} />
        <span>{busy ? 'Uploading' : 'Upload'}</span>
      </button>
    </div>
  );
}
