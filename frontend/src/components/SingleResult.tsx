import {
  ShieldAlert,
  ShieldCheck,
  Gauge,
  ArrowRight,
  CircleCheck,
} from 'lucide-react'
import type { RiskResult } from '../types/risk'
import RiskSignals from './RiskSignals'

function SingleResult({
  result,
}: {
  result: RiskResult
}) {
  const riskClass = result.risk_level.toLowerCase()
  const isAbusive = result.prediction === 'ABUSIVE'
  const evidence = result.unified_evidence

  const riskScore =
    evidence?.model_risk_score ?? result.risk_score

  const decisionThreshold =
    evidence?.decision_threshold ??
    result.decision_threshold

  return (
    <div className="result-content single-result-content">
      {/* Main risk status */}
      <div className={`risk-banner ${riskClass}`}>
        <div className="risk-banner-main">
          <div className="risk-status-icon">
            {isAbusive ? (
              <ShieldAlert
                size={23}
                strokeWidth={2.1}
              />
            ) : (
              <ShieldCheck
                size={23}
                strokeWidth={2.1}
              />
            )}
          </div>

          <div>
            <span className="risk-label">
              CURRENT RISK LEVEL
            </span>

            <strong>{result.risk_level}</strong>

            <span className="risk-status-subtitle">
              {isAbusive
                ? 'Potential return abuse detected'
                : 'Return appears consistent with legitimate activity'}
            </span>
          </div>
        </div>

        <div className="risk-score">
          <Gauge
            size={16}
            strokeWidth={2.1}
          />

          <div>
            <span>RISK SCORE</span>
            <strong>{riskScore}</strong>
          </div>
        </div>
      </div>

      {/* Prediction overview */}
      <div className="result-section-label">
        <span>MODEL OUTCOME</span>
      </div>

      <div className="metrics">
        <div className="metric">
          <span>Prediction</span>

          <strong
            className={
              isAbusive
                ? 'value-negative'
                : 'value-positive'
            }
          >
            {result.prediction}
          </strong>
        </div>

        <div className="metric">
          <span>Abuse Probability</span>

          <strong>
            {(result.abuse_probability * 100).toFixed(2)}%
          </strong>
        </div>

        <div className="metric">
          <span>Legitimate Probability</span>

          <strong>
            {(result.legitimate_probability * 100).toFixed(2)}%
          </strong>
        </div>
      </div>

      {/* Business decision */}
      <div className="decision-heading">
        <div>
          <span>BUSINESS DECISION</span>
          <h3>Recommended handling</h3>
        </div>

        <CircleCheck
          size={19}
          strokeWidth={2}
        />
      </div>

      <div className="decision-card">
        <div className="decision-card-row">
          <div>
            <span>DECISION</span>
            <strong>{result.decision}</strong>
          </div>

          <ArrowRight
            size={16}
            strokeWidth={2}
          />
        </div>

        <div className="decision-card-row">
          <div>
            <span>ACTION</span>
            <strong>{result.action}</strong>
          </div>
        </div>

        <div className="decision-card-row">
          <div>
            <span>DECISION THRESHOLD</span>
            <strong>
              {(decisionThreshold * 100).toFixed(0)}%
            </strong>
          </div>
        </div>

        <div className="decision-reason">
          <span>WHY THIS DECISION?</span>
          <p>{result.reason}</p>
        </div>
      </div>

      {/* Risk signals */}
      <div className="signals-section">
        <RiskSignals result={result} />
      </div>

      <div className="model-footer">
        <span>Assessment model</span>
        <strong>{result.model_type}</strong>
      </div>
    </div>
  )
}

export default SingleResult