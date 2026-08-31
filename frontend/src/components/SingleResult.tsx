import {
  ShieldAlert,
  ShieldCheck,
  Gauge,
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

  return (
    <div className="result-content">
      <div className={`risk-banner ${riskClass}`}>
        <div className="risk-banner-main">
          {isAbusive ? (
            <ShieldAlert size={22} strokeWidth={2.2} />
          ) : (
            <ShieldCheck size={22} strokeWidth={2.2} />
          )}

          <div>
            <span className="risk-label">RISK LEVEL</span>
            <strong>{result.risk_level}</strong>
          </div>
        </div>

        <div className="risk-score">
          <Gauge size={16} strokeWidth={2.2} />
          <span>Risk Score</span>
          <strong>{result.risk_score}</strong>
        </div>
      </div>

      <div className="metrics">
        <div className="metric">
          <span>Prediction</span>
          <strong
            className={
              isAbusive ? 'value-negative' : 'value-positive'
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

      <div className="decision-card">
        <div className="decision-card-row">
          <span>DECISION</span>
          <strong>{result.decision}</strong>
        </div>

        <div className="decision-card-row">
          <span>ACTION</span>
          <strong>{result.action}</strong>
        </div>

        <p>{result.reason}</p>
      </div>

      <RiskSignals result={result} />

      <div className="model-footer">
        Model: <strong>{result.model_type}</strong>
      </div>
    </div>
  )
}

export default SingleResult
