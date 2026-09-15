import { useState } from 'react'
import { Search, Hash, CalendarDays, CaseSensitive, Fingerprint } from 'lucide-react'
import type { ColumnProfile, Finding, Profile } from '@/types/api'
import { number, percent } from '@/lib/utils'
import { DatasetChart } from './ChartRenderer'
import { FindingList } from './Findings'

function ColumnIcon({ column }: { column: ColumnProfile }) {
  const Icon =
    column.inferred_type === 'numeric'
      ? Hash
      : column.inferred_type === 'datetime'
        ? CalendarDays
        : column.inferred_type === 'identifier-like'
          ? Fingerprint
          : CaseSensitive
  return <Icon size={15} />
}
export function Columns({
  profile,
  findings,
  dark,
  onSelect,
  onInvestigate,
  canInvestigate,
}: {
  profile: Profile
  findings: Finding[]
  dark: boolean
  onSelect: (f: Finding) => void
  onInvestigate: (f: Finding) => void
  canInvestigate: boolean
}) {
  const [selected, setSelected] = useState(profile.columns[0].name)
  const [search, setSearch] = useState('')
  const [numericChart, setNumericChart] = useState<'histogram' | 'box'>('histogram')
  const columns = profile.columns.filter((c) =>
    `${c.name} ${c.inferred_type}`.toLowerCase().includes(search.toLowerCase()),
  )
  const c = profile.columns.find((c) => c.name === selected)!
  const n = c.numeric_stats,
    cat = c.categorical_stats,
    date = c.datetime_stats
  const related = findings.filter((f) =>
    (f.source === 'profiler' ? f.columns : f.related_columns).includes(c.name),
  )
  return (
    <div className="columns-layout">
      <aside className="column-picker">
        <div className="row-between">
          <h3>Columns</h3>
          <span className="count-badge">{profile.column_count}</span>
        </div>
        <label className="search-field">
          <Search size={15} />
          <input
            aria-label="Search columns"
            placeholder="Find a column…"
            value={search}
            onChange={(e) => {
              const query = e.target.value
              setSearch(query)
              const matches = profile.columns.filter((col) =>
                `${col.name} ${col.inferred_type}`.toLowerCase().includes(query.toLowerCase()),
              )
              if (matches.length && !matches.some((col) => col.name === selected))
                setSelected(matches[0].name)
            }}
          />
        </label>
        <select
          className="mobile-column-select"
          aria-label="Select column"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          {columns.map((col) => (
            <option key={col.name} value={col.name}>
              {col.name}
            </option>
          ))}
        </select>
        <div className="column-options">
          {columns.slice(0, 100).map((col) => (
            <button
              key={col.name}
              className={selected === col.name ? 'active' : ''}
              onClick={() => setSelected(col.name)}
            >
              <ColumnIcon column={col} />
              <span>{col.name}</span>
              {col.missing_count > 0 && (
                <i className="missing-dot" title="Contains missing values" />
              )}
            </button>
          ))}
          {columns.length > 100 && (
            <p className="muted">Search to narrow {columns.length} columns.</p>
          )}
          {!columns.length && <p className="muted">No matching columns.</p>}
        </div>
      </aside>
      <section className="column-content">
        <div className="section-heading">
          <div>
            <div className="column-title">
              <ColumnIcon column={c} />
              <h2>{c.name}</h2>
              <code>{c.pandas_dtype}</code>
            </div>
            <p className="column-subtitle">
              <span className="type-label">{c.inferred_type}</span>
              {number(c.non_null_count)} non-null<span>{number(c.missing_count)} missing</span>
              <span>{number(c.unique_count)} unique</span>
            </p>
          </div>
        </div>
        {profile.sampled && (
          <p className="sample-notice">
            Distribution statistics use {number(profile.sample_size)} sampled rows.
          </p>
        )}
        {n && (
          <dl className="column-stat-grid">
            {[
              ['Min', n.min],
              ['Q1', n.q1],
              ['Median', n.median],
              ['Mean', n.mean],
              ['Q3', n.q3],
              ['Max', n.max],
              ['Std. deviation', n.std],
              ['Skewness', n.skewness],
              ['P01', n.p01],
              ['P99', n.p99],
              ['Extreme observations', n.extreme_outlier_count],
              ['Zero values', n.zero_count],
            ].map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{number(value as number | null)}</dd>
              </div>
            ))}
          </dl>
        )}
        {!n && cat && (
          <dl className="column-stat-grid">
            {[
              ['Unique values', number(c.unique_count)],
              ['Missing', percent(c.missing_ratio)],
              ['Most common', cat.top_values[0]?.value || '—'],
              ['Most common frequency', percent(cat.most_common_ratio)],
              ['Blank strings', number(cat.blank_string_count)],
              ['Average length', number(cat.average_length)],
              ['Maximum length', number(cat.max_length)],
            ].map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd title={String(value)}>{value}</dd>
              </div>
            ))}
          </dl>
        )}
        {date && (
          <dl className="date-stat-grid">
            <div>
              <dt>Earliest date</dt>
              <dd>{date.earliest?.slice(0, 10)}</dd>
            </div>
            <div>
              <dt>Latest date</dt>
              <dd>{date.latest?.slice(0, 10)}</dd>
            </div>
            <div>
              <dt>Date span</dt>
              <dd>{number(date.span_days)} days</dd>
            </div>
          </dl>
        )}
        {c.inferred_type === 'identifier-like' ? (
          <div className="identifier-note">
            <Fingerprint size={22} />
            <div>
              <h3>{percent(c.unique_ratio)} of non-null values are unique</h3>
              <p>
                This column likely identifies records. A distribution plot would add little context.
              </p>
            </div>
          </div>
        ) : c.inferred_type === 'unknown' ? (
          <div className="empty-chart">No observed values in this column.</div>
        ) : (
          <div className="column-chart">
            <div className="panel-heading">
              <h3>
                {n ? 'Value distribution' : date ? 'Records over time' : 'Most frequent values'}
              </h3>
              {n && (
                <div className="filter-group">
                  {(['histogram', 'box'] as const).map((type) => (
                    <button
                      key={type}
                      className={`filter-chip ${numericChart === type ? 'selected' : ''}`}
                      onClick={() => setNumericChart(type)}
                    >
                      {type === 'histogram' ? 'Histogram' : 'Box plot'}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <DatasetChart
              spec={{
                type: n ? numericChart : date ? 'line' : 'bar',
                x: c.name,
                title: `${c.name} distribution`,
                top_n: 10,
              }}
              dark={dark}
            />
          </div>
        )}
        <div className="panel-heading">
          <h3>Related findings</h3>
          <span className="muted">{related.length} signals</span>
        </div>
        <FindingList
          findings={related}
          onSelect={onSelect}
          onInvestigate={onInvestigate}
          canInvestigate={canInvestigate}
        />
      </section>
    </div>
  )
}
