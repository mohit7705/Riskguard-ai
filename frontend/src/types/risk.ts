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
  top_risk_signals: {
    feature: string
    value: number | string | boolean | null
    importance: number
    description: string
  }[]
  model_type: string
  review_case_id?: string | null
}

export type RiskResponse = {
  status: string
  result: RiskResult
}

export type BatchResponse = {
  status: string
  results: RiskResult[]
}
