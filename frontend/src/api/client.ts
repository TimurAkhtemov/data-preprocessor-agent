import type { ChartData, ChartSpec, Dataset, Investigation, OllamaStatus } from '@/types/api'
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message)
  }
}
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, init)
  } catch {
    throw new ApiError(
      'BACKEND_UNAVAILABLE',
      'Backend disconnected. Start the local server, then try again.',
    )
  }
  const payload = await response.json().catch(() => null)
  if (!response.ok)
    throw new ApiError(
      payload?.code || 'REQUEST_FAILED',
      payload?.message || 'The local server could not complete this request.',
      payload?.details,
    )
  return payload
}
export const api = {
  current: () => request<Dataset | null>('/datasets/current'),
  status: () => request<OllamaStatus>('/ollama/status'),
  health: () => request<{ max_upload_mb: number; agent_max_steps: number }>('/health'),
  upload: (file: File) => {
    const body = new FormData()
    body.append('file', file)
    return request<Dataset>('/datasets', { method: 'POST', body })
  },
  demo: () => request<Dataset>('/datasets/demo', { method: 'POST' }),
  progress: () => request<{ phase: string; loading: boolean }>('/datasets/progress'),
  chart: (spec: ChartSpec) =>
    request<ChartData>('/datasets/chart', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(spec),
    }),
  investigate: (question: string, finding_id?: string) =>
    request<Investigation>('/investigations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, finding_id }),
    }),
  investigation: (id: string) => request<Investigation>(`/investigations/${id}`),
}
