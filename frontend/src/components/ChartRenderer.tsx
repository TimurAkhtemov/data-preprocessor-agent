import { lazy, Suspense, useEffect, useState } from 'react'
import type { Data, Layout } from 'plotly.js'
import { api } from '@/api/client'
import type { ChartData, ChartSpec } from '@/types/api'
const Plot = lazy(() => import('./Plot'))
const colors = [
  '#337d78',
  '#7090b0',
  '#c99958',
  '#987faa',
  '#83955e',
  '#b67b78',
  '#688c9c',
  '#aaa075',
]
const escape = (value: string | number) =>
  typeof value === 'number'
    ? value
    : value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')

export function ChartRenderer({
  chart,
  dark,
  compact = false,
}: {
  chart: ChartData
  dark: boolean
  compact?: boolean
}) {
  const { spec } = chart
  const data: Data[] = chart.series.map((s, i) => {
    const base = {
      name: escape(s.name) as string,
      marker: { color: colors[i % colors.length] },
      x: s.x.map(escape),
      y: s.y.map(escape),
    }
    if (spec.type === 'box')
      return { ...base, y: undefined, type: 'box', boxpoints: false, orientation: 'h' } as Data
    if (spec.type === 'scatter')
      return {
        ...base,
        type: 'scatter',
        mode: 'markers',
        marker: { color: colors[i % colors.length], size: 5, opacity: 0.6 },
      } as Data
    if (spec.type === 'line')
      return {
        ...base,
        type: 'scatter',
        mode: 'lines',
        line: { color: colors[i % colors.length], width: 2 },
      } as Data
    return {
      ...base,
      type: 'bar',
      orientation: spec.type === 'missingness' ? 'h' : 'v',
      ...(s.width ? { width: s.width } : {}),
    } as Data
  })
  const axis = {
    gridcolor: dark ? '#2b3337' : '#eef0f1',
    zeroline: false,
    tickfont: { size: 11 },
    automargin: true,
  }
  const layout: Partial<Layout> = {
    autosize: true,
    height: compact ? 220 : 290,
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: {
      family: '-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif',
      color: dark ? '#abb7bd' : '#68757c',
      size: 12,
    },
    margin: {
      t: 15,
      r: 15,
      b: spec.type === 'bar' ? 65 : 42,
      l: spec.type === 'missingness' ? 110 : 50,
    },
    xaxis: {
      ...axis,
      title: {
        text: spec.type === 'missingness' ? 'Missing (%)' : (escape(spec.x || '') as string),
        font: { size: 11 },
      },
      ...(spec.type === 'missingness'
        ? { range: [0, Math.max(10, ...chart.series.flatMap((s) => s.x.map(Number))) * 1.15] }
        : {}),
    },
    yaxis: {
      ...axis,
      ...(spec.type === 'missingness'
        ? { autorange: 'reversed' as const, showgrid: false }
        : {
            title: {
              text:
                spec.type === 'box'
                  ? ''
                  : (escape(
                      spec.y ? `${spec.y}${chart.aggregation === 'mean' ? ' (mean)' : ''}` : 'Rows',
                    ) as string),
              font: { size: 11 },
            },
          }),
    },
    showlegend: chart.series.length > 1,
    legend: { orientation: 'h', y: 1.15, x: 0 },
    barmode: spec.type === 'histogram' ? 'stack' : 'group',
    bargap: 0.25,
    hovermode: 'closest',
  }
  const empty = chart.series.every((s) => !s.x.length)
  if (empty)
    return (
      <div className="empty-chart">
        No values to plot{spec.type === 'missingness' ? ' — every column is complete.' : '.'}
      </div>
    )
  return (
    <div className="chart-wrap" aria-label={spec.title}>
      <Suspense fallback={<div className="chart-skeleton skeleton" />}>
        <Plot
          data={data}
          layout={layout}
          config={{
            responsive: true,
            displaylogo: false,
            displayModeBar: false,
            scrollZoom: false,
          }}
          useResizeHandler
          style={{ width: '100%', height: layout.height }}
        />
      </Suspense>
      {chart.note && <p className="chart-note">{chart.note}</p>}
    </div>
  )
}

export function DatasetChart({
  spec,
  dark,
  compact = false,
}: {
  spec: ChartSpec
  dark: boolean
  compact?: boolean
}) {
  const [chart, setChart] = useState<ChartData | null>(null)
  const [error, setError] = useState('')
  const specKey = JSON.stringify(spec)
  useEffect(() => {
    let alive = true
    setChart(null)
    setError('')
    api
      .chart(JSON.parse(specKey))
      .then((value) => {
        if (alive) setChart(value)
      })
      .catch((e) => {
        if (alive) setError(e.message)
      })
    return () => {
      alive = false
    }
  }, [specKey])
  if (error)
    return (
      <p role="alert" className="inline-error">
        Chart unavailable: {error}
      </p>
    )
  return chart ? (
    <ChartRenderer chart={chart} dark={dark} compact={compact} />
  ) : (
    <div className="chart-skeleton skeleton" aria-label="Loading chart" />
  )
}
