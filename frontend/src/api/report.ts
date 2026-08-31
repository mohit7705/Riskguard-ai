export type ReportSummary = {
  total_reviewed: number
  pending_review: number
  allowed: number
  blocked: number
  abuse_rate: number
}


export type RiskDistribution = {
  [key: string]: number
}


export type DecisionTrend = {
  date: string
  allow: number
  block: number
  review: number
}


export type RiskReason = {
  reason: string
  count: number
}


export type ModelPerformance = {
  model: string
  test_rows: number
  threshold: number
  precision: number
  recall: number
  f1_score: number
  pr_auc: number
  roc_auc: number
  false_positives: number
  false_negatives: number
  true_positives: number
  true_negatives: number
  business_cost?: number
}


export type FinancialImpact = {
  potential_refund_exposure_identified_inr: number
  observed_missed_refund_exposure_inr: number
  observed_fraud_exposure_reduction_inr: number
  false_positive_friction_cost: number
  false_positive_friction_cost_unit: string
  financial_interpretation: string
}


export type ThresholdPoint = {
  threshold: number
  false_positives: number
  false_negatives: number
  true_positives: number
  true_negatives: number
  precision: number
  recall: number
  f1_score: number
  business_cost: number
}

export type ThresholdCurve = {
  selected_threshold: number
  false_positive_cost: number
  false_negative_cost: number
  cost_formula: string
  selection_reason: string
  points: ThresholdPoint[]
}

export type ReportDashboardResponse = {
  summary: ReportSummary
  risk_distribution: RiskDistribution
  decision_trend: DecisionTrend[]
  top_risk_reasons: RiskReason[]
  model_performance?: ModelPerformance
  threshold_curve?: ThresholdCurve
  financial_impact?: FinancialImpact
}


const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"


export async function getReportDashboard()
: Promise<ReportDashboardResponse> {

  const response = await fetch(
    `${API_BASE}/api/v1/report/dashboard`
  )


  if (!response.ok) {
    throw new Error(
      "Failed to load report dashboard"
    )
  }


  return response.json()

}
