import type {
  DemoSample,
  DetectionResponse,
  DetectionResult,
  EdgeLatestReport,
  EdgeSummary,
  NetworkAnalysisResult,
  TaskStatus,
} from '../types/api'

const API_BASE = '/api'

export async function uploadPcap(file: File): Promise<DetectionResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/detect`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(error.detail || 'Upload failed')
  }

  return response.json()
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await fetch(`${API_BASE}/status/${taskId}`)

  if (!response.ok) {
    throw new Error('Task not found')
  }

  return response.json()
}

export async function getTaskResult(taskId: string): Promise<DetectionResult> {
  const response = await fetch(`${API_BASE}/result/${taskId}`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Result not found' }))
    throw new Error(error.detail || 'Result not found')
  }

  return response.json()
}

export async function getDemoSamples(): Promise<DemoSample[]> {
  const response = await fetch(`${API_BASE}/demo-samples`)

  if (!response.ok) {
    throw new Error('Demo sample list unavailable')
  }

  return response.json()
}

export async function startDemoDetection(sampleId: string): Promise<DetectionResponse> {
  const response = await fetch(`${API_BASE}/detect-demo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sample_id: sampleId }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Demo detection failed' }))
    throw new Error(error.detail || 'Demo detection failed')
  }

  return response.json()
}

export async function getEdges(): Promise<EdgeSummary[]> {
  const response = await fetch(`${API_BASE}/edges`)

  if (!response.ok) {
    throw new Error('Edge list unavailable')
  }

  return response.json()
}

export async function getLatestEdgeReport(edgeId: string): Promise<EdgeLatestReport> {
  const response = await fetch(`${API_BASE}/edges/${edgeId}/reports/latest`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Edge report unavailable' }))
    throw new Error(error.detail || 'Edge report unavailable')
  }

  return response.json()
}

export async function startEdgeAnalysis(edgeId: string): Promise<EdgeLatestReport> {
  const response = await fetch(`${API_BASE}/edges/${edgeId}/analyze`, {
    method: 'POST',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Edge analysis failed' }))
    throw new Error(error.detail || 'Edge analysis failed')
  }

  return response.json()
}

export async function startNetworkAnalysis(): Promise<NetworkAnalysisResult> {
  const response = await fetch(`${API_BASE}/network/analyze`, {
    method: 'POST',
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Network analysis failed' }))
    throw new Error(error.detail || 'Network analysis failed')
  }

  return response.json()
}
