import { DocumentStatus } from '../api/client';

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return <span className={`status status-${status.toLowerCase()}`}>{status}</span>;
}
