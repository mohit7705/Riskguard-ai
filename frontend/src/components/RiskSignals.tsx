import {
  AlertTriangle,
  ArrowUpRight,
  ShieldCheck,
} from 'lucide-react'
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
          <span className="signals-kicker">
            RISK EVIDENCE
          </span>

          <h3>Key Risk Signals</h3>

          <p>
            The strongest factors influencing this assessment.
          </p>
        </div>
      </div>

      <div className="signals-list">
        {signals.map((signal, index) => {
          const isPositive = signal.importance < 0

          return (
            <div
              className={`signal signal-${isPositive ? 'positive' : 'negative'}`}
              key={signal.feature}
            >
              <div className="signal-indicator">
                {isPositive ? (
                  <ShieldCheck
                    size={15}
                    strokeWidth={2.2}
                  />
                ) : (
                  <AlertTriangle
                    size={15}
                    strokeWidth={2.2}
                  />
                )}
              </div>

              <div className="signal-body">
                <div className="signal-main">
                  <strong>
                    {signal.feature}
                  </strong>

                  <span>
                    {String(signal.value)}
                  </span>
                </div>

                <div className="signal-description">
                  {signal.description}
                </div>

                <div className="importance">
                  <div className="importance-track">
                    <div
                      className="importance-bar"
                      style={{
                        width: `${Math.min(
                          Math.abs(signal.importance) *
                            100 *
                            4,
                          100,
                        )}%`,
                      }}
                    />
                  </div>

                  <span className="importance-label">
                    {index === 0
                      ? 'Strongest signal'
                      : 'Risk contribution'}
                  </span>
                </div>
              </div>

              <ArrowUpRight
                className="signal-arrow"
                size={14}
                strokeWidth={2}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default RiskSignals