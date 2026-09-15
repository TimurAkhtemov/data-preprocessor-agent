import { useState } from 'react'
import { ArrowUpRight, Check, ChevronRight, Filter } from 'lucide-react'
import { Button } from './ui/button'
import { Sheet } from './ui/sheet'
import type { Finding, Investigation, Severity } from '@/types/api'
import { InvestigationResult } from './Investigator'

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={`severity ${severity}`}>
      <span className="status-dot" />
      {severity}
    </span>
  )
}
export function FindingList({
  findings,
  onSelect,
  onInvestigate,
  canInvestigate,
}: {
  findings: Finding[]
  onSelect: (f: Finding) => void
  onInvestigate: (f: Finding) => void
  canInvestigate: boolean
}) {
  if (!findings.length)
    return (
      <div className="empty-state">
        <Check size={22} />
        <h3>No findings in this view</h3>
        <p>Try a different filter, or explore individual columns.</p>
      </div>
    )
  return (
    <div className="finding-list">
      {findings.map((f) => (
        <div key={f.id} className="finding-row">
          <button className="finding-main" onClick={() => onSelect(f)}>
            <SeverityBadge severity={f.severity} />
            <div className="finding-text">
              <strong>{f.title}</strong>
              <p>{f.source === 'profiler' ? f.description : f.summary}</p>
              <div className="finding-meta">
                {(f.source === 'profiler' ? f.columns : f.related_columns).map((c) => (
                  <span key={c} className="column-tag">
                    {c}
                  </span>
                ))}
                <span className={`source-label ${f.source}`}>
                  {f.source === 'profiler' ? 'Profiler' : 'Agent finding'}
                </span>
              </div>
            </div>
          </button>
          <Button
            size="sm"
            variant="ghost"
            disabled={!canInvestigate}
            title={
              !canInvestigate
                ? 'Requires an available local model and no active investigation'
                : 'Investigate this finding'
            }
            onClick={() => onInvestigate(f)}
          >
            Investigate <ArrowUpRight />
          </Button>
          <button
            className="detail-chevron"
            aria-label={`Details: ${f.title}`}
            onClick={() => onSelect(f)}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      ))}
    </div>
  )
}
export function FindingsView(props: Parameters<typeof FindingList>[0]) {
  const [severity, setSeverity] = useState('all')
  const [source, setSource] = useState('all')
  const filtered = props.findings.filter(
    (f) =>
      (severity === 'all' || f.severity === severity) && (source === 'all' || f.source === source),
  )
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Findings</h2>
          <p>Signals worth a closer look. Unusual doesn’t always mean incorrect.</p>
        </div>
        <span className="muted">
          {filtered.length} of {props.findings.length} findings
        </span>
      </div>
      <div className="filter-row">
        <div className="filter-group" aria-label="Filter by severity">
          {['all', 'high', 'medium', 'low'].map((s) => (
            <button
              key={s}
              className={`filter-chip ${severity === s ? 'selected' : ''}`}
              aria-pressed={severity === s}
              onClick={() => setSeverity(s)}
            >
              {s[0].toUpperCase() + s.slice(1)}{' '}
              <span>
                {s === 'all'
                  ? props.findings.length
                  : props.findings.filter((f) => f.severity === s).length}
              </span>
            </button>
          ))}
        </div>
        <label className="source-filter">
          <Filter size={14} />
          <select
            aria-label="Filter by source"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          >
            <option value="all">All sources</option>
            <option value="profiler">Profiler</option>
            <option value="agent">Agent</option>
          </select>
        </label>
      </div>
      <FindingList {...props} findings={filtered} />
    </>
  )
}
export function FindingDetails({
  finding,
  close,
  onInvestigate,
  canInvestigate,
  investigations,
  dark,
}: {
  finding: Finding | null
  close: () => void
  onInvestigate: (f: Finding) => void
  canInvestigate: boolean
  investigations: Investigation[]
  dark: boolean
}) {
  return (
    <Sheet
      open={!!finding}
      onOpenChange={(open) => {
        if (!open) close()
      }}
      title="Finding details"
      description="Inspect the evidence behind this signal."
    >
      {finding && (
        <div className="finding-detail">
          <div className="row-between">
            <SeverityBadge severity={finding.severity} />
            <span className="source-label">
              {finding.source === 'profiler' ? 'Deterministic profiler' : 'Local agent'}
            </span>
          </div>
          {finding.source === 'profiler' ? (
            <>
              <h2>{finding.title}</h2>
              <p>{finding.description}</p>
              <div className="tags">
                {finding.columns.map((c) => (
                  <span className="column-tag" key={c}>
                    {c}
                  </span>
                ))}
              </div>
              <h3>Measured evidence</h3>
              <dl className="evidence-list">
                {Object.entries(finding.evidence).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key.replaceAll('_', ' ')}</dt>
                    <dd>
                      {typeof value === 'object' ? (
                        <pre>{JSON.stringify(value, null, 2)}</pre>
                      ) : (
                        String(value)
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
              <h3>Recommended investigation</h3>
              <p>
                Examine the affected observations and compare related columns to test whether this
                pattern is concentrated in a particular source or group.
              </p>
            </>
          ) : (
            <InvestigationResult
              investigation={investigations.find(
                (i) => i.investigation_id === finding.investigation_id,
              )}
              dark={dark}
            />
          )}
          <Button disabled={!canInvestigate} onClick={() => onInvestigate(finding)}>
            Investigate finding <ArrowUpRight />
          </Button>
        </div>
      )}
    </Sheet>
  )
}
