import { useEffect, useState } from 'react'
import { RefreshCw, Search } from 'lucide-react'
import {
  decideReviewCase,
  getReviewCase,
  getReviewQueue,
  type ReviewCase,
} from '../api/risk'

type ReviewQueueProps = {
  onResolved?: () => void
}

function ReviewQueue({
  onResolved,
}: ReviewQueueProps) {
  const [cases, setCases] = useState<ReviewCase[]>([])
  const [selectedCase, setSelectedCase] =
    useState<ReviewCase | null>(null)

  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] =
    useState(false)
  const [decisionLoading, setDecisionLoading] =
    useState(false)

  const [error, setError] = useState('')
  const [reason, setReason] = useState('')

  const loadQueue = async () => {
    setLoading(true)
    setError('')

    try {
      const response = await getReviewQueue()

      setCases(
        response.cases.filter(
          (item) => item.status === 'OPEN',
        ),
      )
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load review queue.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadQueue()
  }, [])

  const handleSelectCase = async (caseId: string) => {
    setDetailLoading(true)
    setError('')

    try {
      const reviewCase = await getReviewCase(caseId)

      setSelectedCase(reviewCase)
      setReason(reviewCase.analyst_reason ?? '')
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load review case.',
      )
    } finally {
      setDetailLoading(false)
    }
  }

  const handleDecision = async (
    decision: 'ALLOW' | 'BLOCK',
  ) => {
    if (!selectedCase) {
      return
    }

    const trimmedReason = reason.trim()

    if (!trimmedReason) {
      setError('Please provide a reason for the decision.')
      return
    }

    setDecisionLoading(true)
    setError('')

    try {
      await decideReviewCase(
        selectedCase.case_id,
        decision,
        trimmedReason,
      )

      setSelectedCase(null)
      setReason('')

      await loadQueue()

      onResolved?.()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to save review decision.',
      )
    } finally {
      setDecisionLoading(false)
    }
  }

  return (
    <section className="review-queue">
      <div className="panel-header">
        <div>
          <h3>Review Queue</h3>
          <p>
            Review high-risk returns requiring analyst
            action.
          </p>
        </div>

        <button
          className="secondary-button"
          type="button"
          onClick={() => void loadQueue()}
          disabled={loading}
        >
          <RefreshCw
            size={15}
            className={loading ? 'spin-icon' : ''}
          />
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="error-box">
          {error}
        </div>
      )}

      {loading && (
        <div className="empty-state">
          <div className="loader" />

          <h3>Loading review queue</h3>

          <p>
            RiskGuard is loading pending review cases.
          </p>
        </div>
      )}

      {!loading && cases.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">✓</div>

          <h3>No pending reviews</h3>

          <p>
            There are currently no open cases requiring
            analyst action.
          </p>
        </div>
      )}

      {!loading && cases.length > 0 && (
        <div className="review-layout">
          <div className="review-case-list">
            {cases.map((reviewCase) => (
              <button
                className={`review-case-card ${
                  selectedCase?.case_id ===
                  reviewCase.case_id
                    ? 'selected'
                    : ''
                }`}
                key={reviewCase.case_id}
                type="button"
                onClick={() =>
                  void handleSelectCase(
                    reviewCase.case_id,
                  )
                }
              >
                <div className="review-case-top">
                  <strong>
                    {reviewCase.case_id}
                  </strong>

                  <span
                    className={`risk-pill ${reviewCase.prediction.risk_level.toLowerCase()}`}
                  >
                    {reviewCase.prediction.risk_level}
                  </span>
                </div>

                <div className="review-case-summary">
                  <span>
                    {reviewCase.prediction.prediction}
                  </span>

                  <strong>
                    {reviewCase.prediction.risk_score}
                  </strong>
                </div>

                <small>
                  {reviewCase.prediction.action}
                </small>
              </button>
            ))}
          </div>

          <div className="review-detail">
            {detailLoading && (
              <div className="empty-state">
                <div className="loader" />

                <h3>Loading case</h3>
              </div>
            )}

            {!detailLoading && !selectedCase && (
              <div className="empty-state">
                <div className="empty-icon">
                  <Search size={26} strokeWidth={1.8} />
                </div>

                <h3>Select a case</h3>

                <p>
                  Select a case from the queue to review
                  its risk assessment.
                </p>
              </div>
            )}

            {!detailLoading && selectedCase && (
              <>
                <div className="review-detail-header">
                  <div>
                    <span>REVIEW CASE</span>

                    <h3>
                      {selectedCase.case_id}
                    </h3>
                  </div>

                  <span
                    className={`risk-pill ${selectedCase.prediction.risk_level.toLowerCase()}`}
                  >
                    {selectedCase.prediction.risk_level}
                  </span>
                </div>

                <div className="metrics">
                  <div className="metric">
                    <span>Prediction</span>

                    <strong
                      className={
                        selectedCase.prediction.prediction ===
                        'ABUSIVE'
                          ? 'value-negative'
                          : 'value-positive'
                      }
                    >
                      {
                        selectedCase.prediction
                          .prediction
                      }
                    </strong>
                  </div>

                  <div className="metric metric-ring">
                    <span>Risk Score</span>

                    <div className="ring-row">
                      <strong>
                        {
                          selectedCase.prediction
                            .risk_score
                        }
                      </strong>

                      <div
                        className="score-ring"
                        style={{
                          background: `conic-gradient(var(--red) ${selectedCase.prediction.risk_score}%, #eef1f5 0)`,
                        }}
                      >
                        <div className="score-ring-hole" />
                      </div>
                    </div>
                  </div>

                  <div className="metric">
                    <span>Abuse Probability</span>

                    <strong>
                      {(
                        selectedCase.prediction
                          .abuse_probability * 100
                      ).toFixed(2)}
                      %
                    </strong>
                  </div>

                  <div className="metric">
                    <span>Action</span>

                    <strong>
                      {
                        selectedCase.prediction
                          .action
                      }
                    </strong>
                  </div>
                </div>

                <div className="decision-card">
                  <div className="decision-card-row">
                    <div>
                      <span>MODEL DECISION</span>

                      <strong>
                        {
                          selectedCase.prediction
                            .decision
                        }
                      </strong>
                    </div>
                  </div>

                  <p>
                    {
                      selectedCase.prediction
                        .reason
                    }
                  </p>
                </div>

                <div className="signals">
                  <div className="signals-heading">
                    <div>
                      <h3>Top Contributing Factors</h3>

                      <p>
                        Model-wide feature importance ranking, applied to this
                        case's values.
                      </p>
                    </div>
                  </div>

                  {selectedCase.prediction.top_risk_signals.map(
                    (signal) => (
                      <div
                        className="signal"
                        key={signal.feature}
                      >
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
                          <div
                            className="importance-bar"
                            style={{
                              width: `${Math.min(
                                signal.importance *
                                  100 *
                                  4,
                                100,
                              )}%`,
                            }}
                          />
                        </div>
                      </div>
                    ),
                  )}
                </div>

                <div className="review-decision">
                  <h3>Analyst Decision</h3>

                  <textarea
                    value={reason}
                    onChange={(event) =>
                      setReason(event.target.value)
                    }
                    placeholder="Enter the reason for your decision..."
                    disabled={decisionLoading}
                  />

                  <div className="review-actions">
                    <button
                      className="allow-button"
                      type="button"
                      onClick={() =>
                        void handleDecision('ALLOW')
                      }
                      disabled={decisionLoading}
                    >
                      {decisionLoading
                        ? 'Saving...'
                        : 'ALLOW'}
                    </button>

                    <button
                      className="block-button"
                      type="button"
                      onClick={() =>
                        void handleDecision('BLOCK')
                      }
                      disabled={decisionLoading}
                    >
                      {decisionLoading
                        ? 'Saving...'
                        : 'BLOCK'}
                    </button>
                  </div>

                  <div className="decision-guidelines">
                    <strong>Decision Guidelines</strong>

                    <ul>
                      <li>
                        <span className="dot allow" />
                        ALLOW: Legitimate return request
                      </li>
                      <li>
                        <span className="dot block" />
                        BLOCK: Abuse or policy violation
                      </li>
                    </ul>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

export default ReviewQueue