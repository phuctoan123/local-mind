import { ShieldCheck, ShieldQuestion, ShieldX } from 'lucide-react';
import { CitationValidation } from '../api/client';

const LABELS: Record<string, string> = {
  supported: 'Supported',
  partially_supported: 'Partial',
  unsupported: 'Unsupported',
  not_applicable: 'N/A'
};

export function CitationValidationBadge({
  validation
}: {
  validation: CitationValidation;
}) {
  const Icon =
    validation.status === 'supported'
      ? ShieldCheck
      : validation.status === 'unsupported'
        ? ShieldX
        : ShieldQuestion;

  return (
    <details className={`citation-validation validation-${validation.status}`}>
      <summary>
        <Icon size={16} />
        <span>{LABELS[validation.status] || validation.status}</span>
        <strong>{Math.round(validation.coverage_score * 100)}%</strong>
      </summary>
      <div>
        <span>{validation.cited_sources} cited</span>
        {validation.supporting_sources.length ? (
          <span>{validation.supporting_sources.join(', ')}</span>
        ) : null}
        {validation.warnings.length ? <span>{validation.warnings.join(', ')}</span> : null}
      </div>
    </details>
  );
}
