import type { NewsQuery, PipelineResponse } from '../types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

function apiUrl(path: string): string {
  if (!API_BASE) {
    return path
  }
  return `${API_BASE}${path}`
}

export async function analyzeNews(payload: NewsQuery): Promise<PipelineResponse> {
  const response = await fetch(apiUrl('/api/analyze'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }

  return response.json()
}
