export type Severity = 'high' | 'medium' | 'low'
export type ChartSpec = {
  type: 'histogram' | 'box' | 'bar' | 'scatter' | 'line' | 'missingness'
  title: string
  x?: string | null
  y?: string | null
  color?: string | null
  top_n?: number | null
}
export type ChartData = {
  spec: ChartSpec
  series: { name: string; x: (string | number)[]; y: (string | number)[]; width?: number }[]
  sampled: boolean
  sample_size: number
  note: string
  aggregation: string
}
export type NumericStats = Record<
  | 'count'
  | 'min'
  | 'max'
  | 'mean'
  | 'median'
  | 'std'
  | 'q1'
  | 'q3'
  | 'iqr'
  | 'p01'
  | 'p99'
  | 'skewness'
  | 'zero_count'
  | 'negative_count'
  | 'non_finite_count'
  | 'outlier_count'
  | 'outlier_ratio'
  | 'extreme_outlier_count'
  | 'extreme_outlier_ratio'
  | 'lower'
  | 'upper'
  | 'lower_extreme'
  | 'upper_extreme',
  number | null
>
export type ColumnProfile = {
  name: string
  inferred_type: string
  pandas_dtype: string
  non_null_count: number
  missing_count: number
  missing_ratio: number
  unique_count: number
  unique_ratio: number
  sample_values: unknown[]
  distribution_count: number
  numeric_stats: NumericStats | null
  categorical_stats: {
    top_values: { value: string; count: number }[]
    blank_string_count: number
    average_length: number
    max_length: number
    most_common_ratio: number
    normalized_unique_count: number
    raw_unique_count: number
    normalization_collisions: unknown[]
  } | null
  datetime_stats: {
    earliest: string | null
    latest: string | null
    span_days: number | null
    parsed_count: number
  } | null
}
export type ProfilerFinding = {
  id: string
  severity: Severity
  category: string
  title: string
  description: string
  columns: string[]
  evidence: Record<string, unknown>
  source: 'profiler'
}
export type AgentFinding = {
  id: string
  severity: Severity
  title: string
  summary: string
  evidence: string[]
  recommended_action: string
  confidence: number
  related_columns: string[]
  source: 'agent'
  investigation_id: string
}
export type Finding = ProfilerFinding | AgentFinding
export type Profile = {
  file_name: string
  row_count: number
  column_count: number
  memory_bytes: number
  duplicate_rows: number
  duplicate_ratio: number
  missing_cells: number
  missing_ratio: number
  sampled: boolean
  sample_size: number | null
  duration_seconds: number
  columns: ColumnProfile[]
  findings: ProfilerFinding[]
}
export type Investigation = {
  investigation_id: string
  question: string
  status: 'running' | 'completed' | 'failed'
  max_steps: number
  steps_remaining: number
  current_activity: string
  trace: {
    number: number
    action: string
    reason: string
    code?: string
    result_summary?: string
    error?: string
  }[]
  charts: (ChartData & { reason: string })[]
  final_finding: AgentFinding | null
  error: { code: string; message: string; details?: string } | null
}
export type Dataset = {
  dataset_id: string
  file_name: string
  rows: number
  columns: number
  profile: Profile
  investigations: Investigation[]
  active_investigation_id: string | null
}
export type OllamaStatus = {
  connected: boolean
  model_available: boolean
  model: string
  message: string
  code: string
}
