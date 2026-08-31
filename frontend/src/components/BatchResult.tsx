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
  return (
    <div className="batch-result">
      <div className="batch-summary">
        <div className="batch-summary-card">
          <span>Total</span>
          <strong>{summary.total}</strong>
        </div>

        <div className="batch-summary-card">
          <span>Legitimate</span>
          <strong className="value-positive">
            {summary.legitimate}
          </strong>
        </div>

        <div className="batch-summary-card">
          <span>Abusive</span>
          <strong className="value-negative">
            {summary.abusive}
          </strong>
        </div>

        <div className="batch-summary-card">
          <span>Allow</span>
          <strong className="value-positive">
            {summary.allow}
          </strong>
        </div>

        <div className="batch-summary-card">
          <span>Review</span>
          <strong className="value-warning">
            {summary.review}
          </strong>
        </div>

        <div className="batch-summary-card">
          <span>Block</span>
          <strong className="value-negative">
            {summary.block}
          </strong>
        </div>
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
            {results.slice(0, 100).map((item, index) => (
              <tr key={`${item.prediction}-${index}`}>
                <td>{index + 1}</td>
                <td>{item.prediction}</td>
                <td>
                  <span
                    className={`risk-pill ${item.risk_level.toLowerCase()}`}
                  >
                    {item.risk_level}
                  </span>
                </td>
                <td>{item.risk_score}</td>
                <td>{item.decision}</td>
                <td>{item.action}</td>
              </tr>
            ))}
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
