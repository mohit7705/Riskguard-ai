import type { RiskResult } from '../types/risk'

function RiskSignals({
  result,
}: {
  result: RiskResult
}) {
  const signals =
    result.unified_evidence?.top_risk_signals ??
    result.top_risk_signals

  return (
    <div className="signals">
      <div className="signals-heading">
        <div>
          <h3>Top Risk Signals</h3>
          <p>
            Features contributing to the model assessment.
          </p>
        </div>
      </div>

      {signals.map((signal) => (
        <div className="signal" key={signal.feature}>
          <div className="signal-main">
            <strong>{signal.feature}</strong>
            <span>{String(signal.value)}</span>
          </div>

          <div className="signal-description">
            {signal.description}
          </div>

          <div className="importance">
            <div
              className="importance-bar"
              style={{
                width: `${Math.min(
                  signal.importance * 100 * 4,
                  100,
                )}%`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

export default RiskSignals