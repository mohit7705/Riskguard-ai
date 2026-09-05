import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react'
import type { RiskResult } from '../types/risk'

type BatchResultProps = {
  results: RiskResult[]
  summary: {
    total: number
    legitimate: number
    abusive: number
    allow: number
    review: number
    block: number
  }
}

export default function BatchResult({
  results,
  summary,
}: BatchResultProps) {
  const abusiveRate =
    summary.total > 0
      ? (summary.abusive / summary.total) * 100
      : 0

  return (
    <div className="batch-result bulk-result-content">
      <div className="bulk-result-intro">
        <div>
          <span className="bulk-result-kicker">
            BATCH OUTCOME
          </span>

          <h3>Assessment completed</h3>

          <p>
            RiskGuard analyzed {summary.total} return{' '}
            {summary.total === 1 ? 'request' : 'requests'} and
            generated an individual decision for each record.
          </p>
        </div>

        <div className="bulk-completion-badge">
          <CheckCircle2
            size={16}
            strokeWidth={2.2}
          />
          <span>Analysis complete</span>
        </div>
      </div>

      <div className="batch-summary">
        <div className="batch-summary-card total">
          <div className="batch-card-icon">
            <Activity size={16} />
          </div>

          <span>Total analyzed</span>
          <strong>{summary.total}</strong>
        </div>

        <div className="batch-summary-card legitimate">
          <div className="batch-card-icon">
            <ShieldCheck size={16} />
          </div>

          <span>Legitimate</span>
          <strong>{summary.legitimate}</strong>
        </div>

        <div className="batch-summary-card abusive">
          <div className="batch-card-icon">
            <ShieldAlert size={16} />
          </div>

          <span>Abusive</span>
          <strong>{summary.abusive}</strong>
        </div>

        <div className="batch-summary-card allow">
          <span>Allow</span>
          <strong>{summary.allow}</strong>
        </div>

        <div className="batch-summary-card review">
          <span>Review</span>
          <strong>{summary.review}</strong>
        </div>

        <div className="batch-summary-card block">
          <span>Block</span>
          <strong>{summary.block}</strong>
        </div>
      </div>

      <div className="bulk-risk-overview">
        <div className="bulk-overview-heading">
          <div>
            <span>RISK DISTRIBUTION</span>
            <strong>Batch risk overview</strong>
          </div>

          <strong>{abusiveRate.toFixed(1)}% abusive</strong>
        </div>

        <div className="bulk-distribution">
          <div
            className="bulk-distribution-abusive"
            style={{
              width: `${abusiveRate}%`,
            }}
          />

          <div
            className="bulk-distribution-legitimate"
            style={{
              width: `${100 - abusiveRate}%`,
            }}
          />
        </div>

        <div className="bulk-distribution-labels">
          <span>
            <i className="distribution-dot abusive" />
            Abusive {summary.abusive}
          </span>

          <span>
            <i className="distribution-dot legitimate" />
            Legitimate {summary.legitimate}
          </span>
        </div>
      </div>

      <div className="bulk-table-heading">
        <div>
          <span>INDIVIDUAL RESULTS</span>
          <h3>Return decisions</h3>
        </div>

        <span className="bulk-table-count">
          {Math.min(results.length, 100)} of {results.length}
        </span>
      </div>

      <div className="batch-table-wrapper">
        <table className="batch-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Prediction</th>
              <th>Risk Level</th>
              <th>Risk Score</th>
              <th>Decision</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {results.slice(0, 100).map((item, index) => {
              const isAbusive =
                item.prediction === 'ABUSIVE'

              return (
                <tr
                  key={`${item.prediction}-${index}`}
                >
                  <td className="batch-index">
                    {String(index + 1).padStart(2, '0')}
                  </td>

                  <td>
                    <span
                      className={`batch-prediction ${
                        isAbusive
                          ? 'abusive'
                          : 'legitimate'
                      }`}
                    >
                      {isAbusive ? (
                        <AlertTriangle size={13} />
                      ) : (
                        <CheckCircle2 size={13} />
                      )}

                      {item.prediction}
                    </span>
                  </td>

                  <td>
                    <span
                      className={`risk-pill ${item.risk_level.toLowerCase()}`}
                    >
                      {item.risk_level}
                    </span>
                  </td>

                  <td>
                    <strong className="batch-score">
                      {item.risk_score}
                    </strong>
                  </td>

                  <td>
                    <span className="batch-decision">
                      {item.decision}
                    </span>
                  </td>

                  <td className="batch-action">
                    {item.action}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {results.length > 100 && (
        <div className="table-note">
          Showing the first 100 results. All {results.length}{' '}
          records were analyzed.
        </div>
      )}
    </div>
  )
}