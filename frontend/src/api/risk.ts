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
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export type FeedbackListResponse = {
  status: string
  records: FeedbackRecord[]
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
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

export type ReviewQueueParams = {
  assignmentNumber: string
  page?: number
  pageSize?: number
  search?: string
}

export function getReviewQueue(
  params?: ReviewQueueParams,
): Promise<ReviewCaseListResponse> {
  const query = new URLSearchParams()

  if (params?.assignmentNumber) {
    query.set('assignment_number', params.assignmentNumber)
  }

  if (params?.page) {
    query.set('page', String(params.page))
  }

  if (params?.pageSize) {
    query.set('page_size', String(params.pageSize))
  }

  if (params?.search) {
    query.set('search', params.search)
  }

  const queryString = query.toString()

  return request<ReviewCaseListResponse>(
    `/api/v1/risk/review-queue${queryString ? `?${queryString}` : ''}`,
  )
}

export function getReviewCase(
  caseId: string,
  assignmentNumber: string,
): Promise<ReviewCase> {
  const query = new URLSearchParams({
    assignment_number: assignmentNumber,
  })

  return request<ReviewCase>(
    `/api/v1/risk/review-queue/${encodeURIComponent(caseId)}?${query.toString()}`,
  )
}

export function decideReviewCase(
  caseId: string,
  assignmentNumber: string,
  decision: string,
  reason?: string,
): Promise<ReviewCase> {
  const query = new URLSearchParams({
    assignment_number: assignmentNumber,
  })

  return request<ReviewCase>(
    `/api/v1/risk/review-queue/${encodeURIComponent(caseId)}/decision?${query.toString()}`,
    {
      method: 'POST',
      body: JSON.stringify({
        decision,
        reason: reason || null,
      }),
    },
  )
}

export function getFeedback(
  assignmentNumber: string,
): Promise<FeedbackListResponse> {
  const query = new URLSearchParams({
    assignment_number: assignmentNumber,
  })

  return request<FeedbackListResponse>(
    `/api/v1/risk/feedback?${query.toString()}`,
  )
}

export type ReviewAnalysisFilter =
  | 'all'
  | 'pending'
  | 'allowed'
  | 'blocked'

export type ReviewAnalysisParams = {
  assignmentNumber: string
  filter?: ReviewAnalysisFilter
  page?: number
  pageSize?: number
  search?: string
}

export function getReviewAnalysis(
  params?: ReviewAnalysisParams,
): Promise<FeedbackListResponse> {
  const query = new URLSearchParams()

  if (params?.assignmentNumber) {
    query.set('assignment_number', params.assignmentNumber)
  }

  if (params?.filter) {
    query.set('filter_type', params.filter)
  }

  if (params?.page) {
    query.set('page', String(params.page))
  }

  if (params?.pageSize) {
    query.set('page_size', String(params.pageSize))
  }

  if (params?.search) {
    query.set('search', params.search)
  }

  const queryString = query.toString()

  return request<FeedbackListResponse>(
    `/api/v1/risk/review-analysis${queryString ? `?${queryString}` : ''}`,
  )
}

export function getFeedbackRecord(
  feedbackId: number,
  assignmentNumber: string,
): Promise<FeedbackRecord> {
  const query = new URLSearchParams({
    assignment_number: assignmentNumber,
  })

  return request<FeedbackRecord>(
    `/api/v1/risk/feedback/${feedbackId}?${query.toString()}`,
  )
}

export function recordActualOutcome(
  feedbackId: number,
  assignmentNumber: string,
  actualOutcome: string,
): Promise<FeedbackRecord> {
  const query = new URLSearchParams({
    assignment_number: assignmentNumber,
  })

  return request<FeedbackRecord>(
    `/api/v1/risk/feedback/${feedbackId}/outcome?${query.toString()}`,
    {
      method: 'POST',
      body: JSON.stringify({
        actual_outcome: actualOutcome,
      }),
    },
  )
}

export function getMonitoring(
  assignmentNumber: string,
): Promise<MonitoringMetrics> {
  const query = new URLSearchParams({
    assignment_number: assignmentNumber,
  })

  return request<MonitoringMetrics>(
    `/api/v1/risk/monitoring?${query.toString()}`,
  )
}

export function getUserNetwork(
  userId: string,
  assignmentNumber: string,
): Promise<UserNetwork> {
  const query = new URLSearchParams({
    assignment_number: assignmentNumber,
  })

  return request<UserNetwork>(
    `/api/v1/risk/network/${encodeURIComponent(userId)}?${query.toString()}`,
  )
}
export type MonitoringResponse = {
  status: string
  total_records: number
  labeled_records: number
  accuracy: number | null
  precision: number | null
  recall: number | null
  f1_score: number | null
  false_positive_count: number
  false_negative_count: number
  true_positive_count: number
  true_negative_count: number
  business_cost: number
}

export async function getMonitoringMetrics(
  assignmentNumber: string,
): Promise<MonitoringResponse> {
  const query = new URLSearchParams({
    assignment_number: assignmentNumber,
  })

  const response = await fetch(
    `${API_BASE}/api/v1/risk/monitoring?${query.toString()}`,
  )

  if (!response.ok) {
    throw new Error("Failed to load monitoring metrics")
  }

  return response.json()
}