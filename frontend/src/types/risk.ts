export type VisionAssessment = {
  available: boolean
  condition: string
  confidence: number
  claim_supported: boolean | null
  evidence: string[]
  message: string
}

export type UnifiedRiskEvidence = {
  model_risk_score: number
  decision_threshold: number
  model_prediction: 'LEGITIMATE' | 'ABUSIVE'
  top_risk_signals: {
    feature: string
    value: number | string | boolean | null
    importance: number
    description: string
  }[]
  vision: VisionAssessment | null
}

export type RiskResult = {
  assessment_id: string | null
  predicted_label: number
  prediction: 'LEGITIMATE' | 'ABUSIVE'
  abuse_probability: number
  legitimate_probability: number
  risk_score: number
  risk_level: 'MINIMAL' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  decision_threshold: number
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
  unified_evidence?: UnifiedRiskEvidence
}

export type RiskResponse = {
  status: string
  result: RiskResult
}

export type BatchResponse = {
  status: string
  results: RiskResult[]
}
