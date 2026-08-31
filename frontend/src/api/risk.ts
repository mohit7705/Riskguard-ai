export type ReviewCase = {
  case_id: string
  status: string
  created_at: string
  prediction: RiskResult
  data: Record<string, unknown>
  analyst_decision: string | null
  analyst_reason: string | null
  resolved_at: string | null
}

export type FeedbackRecord = {
  id: number
  case_id: string | null
  prediction: string
  predicted_label: number
  abuse_probability: number
  risk_score: number
  risk_level: string
  model_decision: string
  analyst_decision: string | null
  actual_outcome: string | null
  analyst_reason: string | null
  input_data: Record<string, unknown>
  created_at: string
  outcome_recorded_at: string | null
}

export type MonitoringMetrics = {
  status: string
  total_records: number
  labeled_records: number
  accuracy: number | null
  precision: number | null
  recall: number | null
  false_positive_count: number
  false_negative_count: number
  true_positive_count: number
  true_negative_count: number
}

export type NetworkNode = {
  id: string
  type: string
  label: string
  is_target: boolean
}

export type NetworkEdge = {
  source: string
  target: string
  type: string
}

export type NetworkSummary = {
  shared_device_count: number
  shared_address_count: number
  shared_payment_fingerprint_count: number
  device_return_velocity_7d: number
  address_return_velocity_7d: number
  payment_return_velocity_7d: number
  cluster_return_velocity_7d: number
}

export type UserNetwork = {
  user_id: string
  nodes: NetworkNode[]
  edges: NetworkEdge[]
  network_summary: NetworkSummary
}

export type ReviewCaseListResponse = {
  status: string
  cases: ReviewCase[]
}

export type FeedbackListResponse = {
  status: string
  records: FeedbackRecord[]
}

export type RiskSignal = {
  feature: string
  value: number | string | boolean | null
  importance: number
  description: string
}

export type RiskResult = {
  predicted_label: number
  prediction: 'LEGITIMATE' | 'ABUSIVE'
  abuse_probability: number
  legitimate_probability: number
  risk_score: number
  risk_level: 'MINIMAL' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  decision: 'ALLOW' | 'REVIEW' | 'BLOCK'
  action: 'ALLOW_RETURN' | 'MANUAL_REVIEW' | 'BLOCK_RETURN'
  reason: string
  top_risk_signals: RiskSignal[]
  model_type: string
  review_case_id?: string | null
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
    ...options,
  })

  const body = await response.json()

  if (!response.ok) {
    throw new Error(
      body.detail || `API request failed: ${response.status}`,
    )
  }

  return body as T
}

export function getReviewQueue(): Promise<ReviewCaseListResponse> {
  return request<ReviewCaseListResponse>(
    '/api/v1/risk/review-queue',
  )
}

export function getReviewCase(
  caseId: string,
): Promise<ReviewCase> {
  return request<ReviewCase>(
    `/api/v1/risk/review-queue/${encodeURIComponent(caseId)}`,
  )
}

export function decideReviewCase(
  caseId: string,
  decision: string,
  reason?: string,
): Promise<ReviewCase> {
  return request<ReviewCase>(
    `/api/v1/risk/review-queue/${encodeURIComponent(caseId)}/decision`,
    {
      method: 'POST',
      body: JSON.stringify({
        decision,
        reason: reason || null,
      }),
    },
  )
}

export function getFeedback(): Promise<FeedbackListResponse> {
  return request<FeedbackListResponse>(
    '/api/v1/risk/feedback',
  )
}

export function getFeedbackRecord(
  feedbackId: number,
): Promise<FeedbackRecord> {
  return request<FeedbackRecord>(
    `/api/v1/risk/feedback/${feedbackId}`,
  )
}

export function recordActualOutcome(
  feedbackId: number,
  actualOutcome: string,
): Promise<FeedbackRecord> {
  return request<FeedbackRecord>(
    `/api/v1/risk/feedback/${feedbackId}/outcome`,
    {
      method: 'POST',
      body: JSON.stringify({
        actual_outcome: actualOutcome,
      }),
    },
  )
}

export function getMonitoring(): Promise<MonitoringMetrics> {
  return request<MonitoringMetrics>(
    '/api/v1/risk/monitoring',
  )
}

export function getUserNetwork(
  userId: string,
): Promise<UserNetwork> {
  return request<UserNetwork>(
    `/api/v1/risk/network/${encodeURIComponent(userId)}`,
  )
}
