import { ArrowRight, Check, Info } from 'lucide-react'
import type { Finding, Profile } from '@/types/api'
import { number, percent } from '@/lib/utils'
import { Button } from './ui/button'
import { DatasetChart } from './ChartRenderer'
import { FindingList } from './Findings'

export function Overview({
  profile,
  findings,
  dark,
  onSelect,
  onInvestigate,
  canInvestigate,
  viewFindings,
}: {
  profile: Profile
  findings: Finding[]
  dark: boolean
  onSelect: (f: Finding) => void
  onInvestigate: (f: Finding) => void
  canInvestigate: boolean
  viewFindings: () => void
}) {
  const types = profile.columns.reduce<Record<string, number>>(
    (acc, c) => ({ ...acc, [c.inferred_type]: (acc[c.inferred_type] || 0) + 1 }),
    {},
  )
  const counts = {
    high: findings.filter((f) => f.severity === 'high').length,
    medium: findings.filter((f) => f.severity === 'medium').length,
    low: findings.filter((f) => f.severity === 'low').length,
  }
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Dataset overview</h2>
          <p>A first pass through structure, completeness, and unusual patterns.</p>
        </div>
        <span className="completion-label">
          <Check size={13} /> Profiled in {profile.duration_seconds.toFixed(2)}s
        </span>
      </div>
      <div className="metric-strip">
        {[
          [number(profile.row_count), 'Rows', 'Full dataset'],
          [number(profile.column_count), 'Columns', `${Object.keys(types).length} inferred types`],
          [
            percent(profile.missing_ratio),
            'Missing cells',
            `${number(profile.missing_cells)} empty values`,
          ],
          [
            number(profile.duplicate_rows),
            'Duplicate rows',
            `${percent(profile.duplicate_ratio)} of all rows`,
          ],
          [
            `${(profile.memory_bytes / 1024 / 1024).toFixed(1)} MB`,
            'In-memory size',
            'Read-only snapshot',
          ],
        ].map(([value, label, note]) => (
          <div key={label}>
            <span className="metric-label">{label}</span>
            <strong>{value}</strong>
            <small>{note}</small>
          </div>
        ))}
      </div>
      {profile.sampled && (
        <div className="sample-notice">
          <Info size={16} />
          Distribution statistics estimated from a {number(profile.sample_size)}-row sample. Counts,
          missingness, and duplicates use the full dataset.
        </div>
      )}
      <div className="overview-grid">
        <section className="analytical-panel">
          <div className="panel-heading">
            <h3>Missingness by column</h3>
            <span className="muted">Percent of rows</span>
          </div>
          <DatasetChart
            spec={{ type: 'missingness', title: 'Missingness by column' }}
            dark={dark}
            compact
          />
        </section>
        <aside className="structure-panel">
          <h3>Column structure</h3>
          <div className="type-list">
            {Object.entries(types).map(([type, count]) => (
              <div key={type}>
                <span>
                  <i className={`type-dot type-${type}`} />
                  {type === 'identifier-like'
                    ? 'Identifier-like'
                    : type[0].toUpperCase() + type.slice(1)}
                </span>
                <span>
                  {count}
                  <span className="type-track">
                    <i style={{ width: `${(count / profile.column_count) * 100}%` }} />
                  </span>
                </span>
              </div>
            ))}
          </div>
          <div className="health-heading">
            <h3>Attention signals</h3>
            <span className="muted">{findings.length} total</span>
          </div>
          <div className="severity-track">
            {Object.entries(counts).map(([severity, count]) => (
              <i key={severity} className={severity} style={{ flex: count || 0.05 }} />
            ))}
          </div>
          <div className="severity-counts">
            {Object.entries(counts).map(([severity, count]) => (
              <span className={severity} key={severity}>
                <i className="status-dot" />
                {count} {severity}
              </span>
            ))}
          </div>
        </aside>
      </div>
      <section className="attention-section">
        <div className="panel-heading">
          <div>
            <h3>Needs attention</h3>
            <p className="muted">Start with the most significant signals.</p>
          </div>
          <Button variant="ghost" size="sm" onClick={viewFindings}>
            All findings <ArrowRight />
          </Button>
        </div>
        <FindingList
          findings={findings.slice(0, 5)}
          onSelect={onSelect}
          onInvestigate={onInvestigate}
          canInvestigate={canInvestigate}
        />
      </section>
    </>
  )
}
