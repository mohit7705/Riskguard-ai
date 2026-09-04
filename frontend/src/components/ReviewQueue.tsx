import { useEffect, useState } from 'react'
import { RefreshCw, Search, Clock, CheckCircle2, XCircle, ChevronLeft, ChevronRight } from 'lucide-react'
import {
  decideReviewCase,
  getReviewCase,
  getReviewQueue,
  type ReviewCase,
} from '../api/risk'

type ReviewQueueProps = {
  assignmentNumber: string
  onResolved?: () => void
}

type DetailTab = 'signals' | 'transaction' | 'customer' | 'history'

type DataFieldDef = {
  key: string
  label: string
  format: 'currency' | 'percent' | 'number' | 'hours' | 'days' | 'boolean' | 'text'
}

const PAGE_SIZE = 10

const TRANSACTION_FIELDS: DataFieldDef[] = [
  { key: 'order_category', label: 'Order Category', format: 'text' },
  { key: 'order_value', label: 'Order Value', format: 'currency' },
  { key: 'item_value', label: 'Item Value', format: 'currency' },
  { key: 'quantity', label: 'Quantity', format: 'number' },
  { key: 'refund_amount', label: 'Refund Amount', format: 'currency' },
  { key: 'return_reason', label: 'Return Reason', format: 'text' },
  { key: 'returned_item_match', label: 'Item Matches Order', format: 'boolean' },
  { key: 'time_to_return_request_hours', label: 'Time to Return Request', format: 'hours' },
  { key: 'item_condition_score', label: 'Item Condition Score', format: 'number' },
  { key: 'package_weight_delta_pct', label: 'Package Weight Delta', format: 'percent' },
  { key: 'vision_confidence_score', label: 'Vision Confidence Score', format: 'number' },
]

const CUSTOMER_FIELDS: DataFieldDef[] = [
  { key: 'account_age_days', label: 'Account Age', format: 'days' },
  { key: 'lifetime_order_count', label: 'Lifetime Orders', format: 'number' },
  { key: 'lifetime_return_count', label: 'Lifetime Returns', format: 'number' },
  { key: 'total_spent', label: 'Total Spent', format: 'currency' },
  { key: 'return_rate', label: 'Return Rate', format: 'percent' },
  { key: 'return_velocity_30d', label: 'Returns (Last 30 Days)', format: 'number' },
  { key: 'return_velocity_48h', label: 'Returns (Last 48 Hours)', format: 'number' },
  { key: 'shared_device_count', label: 'Shared Devices', format: 'number' },
  { key: 'shared_address_count', label: 'Shared Addresses', format: 'number' },
  { key: 'shared_payment_fingerprint_count', label: 'Shared Payment Methods', format: 'number' },
  { key: 'device_return_velocity_7d', label: 'Device Return Velocity (7d)', format: 'number' },
  { key: 'address_return_velocity_7d', label: 'Address Return Velocity (7d)', format: 'number' },
  { key: 'payment_return_velocity_7d', label: 'Payment Return Velocity (7d)', format: 'number' },
  { key: 'cluster_return_velocity_7d', label: 'Cluster Return Velocity (7d)', format: 'number' },
]

function formatFieldValue(
  value: unknown,
  format: DataFieldDef['format'],
): string {
  if (value === null || value === undefined) {
    return '—'
  }

  switch (format) {
    case 'currency':
      return typeof value === 'number'
        ? `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
        : String(value)

    case 'percent':
      return typeof value === 'number'
        ? `${(value <= 1 ? value * 100 : value).toFixed(2)}%`
        : String(value)

    case 'hours':
      return typeof value === 'number'
        ? `${value.toFixed(2)} hrs`
        : String(value)

    case 'days':
      return typeof value === 'number'
        ? `${value} days`
        : String(value)

    case 'boolean':
      return value ? 'Yes' : 'No'

    case 'number':
      return typeof value === 'number'
        ? value.toLocaleString('en-IN', { maximumFractionDigits: 4 })
        : String(value)

    default:
      return String(value)
  }
}

function formatDateTime(iso: string | null): string {
  if (!iso) {
    return '—'
  }

  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function ReviewQueue({
  assignmentNumber,
  onResolved,
}: ReviewQueueProps) {
  const [cases, setCases] = useState<ReviewCase[]>([])
  const [selectedCase, setSelectedCase] =
    useState<ReviewCase | null>(null)

  const [activeTab, setActiveTab] = useState<DetailTab>('signals')

  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] =
    useState(false)
  const [decisionLoading, setDecisionLoading] =
    useState(false)

  const [error, setError] = useState('')
  const [reason, setReason] = useState('')

  // Search box value (updates on every keystroke) vs. the debounced
  // value actually sent to the API, so we don't fire a request on
  // every single character typed.
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')

  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrev, setHasPrev] = useState(false)

  const loadQueue = async (
    targetPage: number = page,
    targetSearch: string = search,
  ) => {
    setLoading(true)
    setError('')

    try {
      const response = await getReviewQueue({
        assignmentNumber,
        page: targetPage,
        pageSize: PAGE_SIZE,
        search: targetSearch || undefined,
      })

      setCases(response.cases)
      setPage(response.page)
      setTotal(response.total)
      setTotalPages(response.total_pages)
      setHasNext(response.has_next)
      setHasPrev(response.has_prev)
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

  // Debounce the search box — wait 400ms after the user stops typing
  // before updating the actual search term used for the request.
  useEffect(() => {
    const timeout = setTimeout(() => {
      setSearch(searchInput.trim())
    }, 400)

    return () => clearTimeout(timeout)
  }, [searchInput])

  // Reload from page 1 whenever the (debounced) search term changes,
  // including on initial mount (search starts as '').
  useEffect(() => {
    void loadQueue(1, search)
    setSelectedCase(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, assignmentNumber])

  const goToPage = (nextPage: number) => {
    if (nextPage < 1 || nextPage > totalPages) {
      return
    }

    void loadQueue(nextPage, search)
  }

  const handleSelectCase = async (caseId: string) => {
    setDetailLoading(true)
    setError('')
    setActiveTab('signals')

    try {
      const reviewCase = await getReviewCase(
        caseId,
        assignmentNumber,
      )

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
        assignmentNumber,
        decision,
        trimmedReason,
      )

      setSelectedCase(null)
      setReason('')

      await loadQueue(page, search)

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
          onClick={() => void loadQueue(page, search)}
          disabled={loading}
        >
          <RefreshCw
            size={15}
            className={loading ? 'spin-icon' : ''}
          />
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          margin: '4px 0 16px',
          padding: '8px 12px',
          border: '1px solid #e2e5ea',
          borderRadius: '8px',
          maxWidth: '360px',
        }}
      >
        <Search size={16} strokeWidth={2} color="#8a94a6" />

        <input
          type="text"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Search by case ID (e.g. F7D3)..."
          style={{
            border: 'none',
            outline: 'none',
            width: '100%',
            fontSize: '14px',
            background: 'transparent',
          }}
        />
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

          <h3>
            {search
              ? 'No matching cases'
              : 'No pending reviews'}
          </h3>

          <p>
            {search
              ? `No open cases match "${search}".`
              : 'There are currently no open cases requiring analyst action.'}
          </p>
        </div>
      )}

      {!loading && cases.length > 0 && (
        <div className="review-layout">
          <div>
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

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginTop: '12px',
                padding: '8px 4px',
                fontSize: '13px',
                color: '#5b6472',
              }}
            >
              <span>
                {total === 0
                  ? '0 cases'
                  : `Showing ${(page - 1) * PAGE_SIZE + 1}–${Math.min(
                      page * PAGE_SIZE,
                      total,
                    )} of ${total}`}
              </span>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => goToPage(page - 1)}
                  disabled={!hasPrev || loading}
                  style={{ padding: '4px 8px' }}
                >
                  <ChevronLeft size={14} />
                </button>

                <span>
                  Page {page} of {totalPages}
                </span>

                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => goToPage(page + 1)}
                  disabled={!hasNext || loading}
                  style={{ padding: '4px 8px' }}
                >
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
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

                    <span className="review-detail-created">
                      Created:{' '}
                      {formatDateTime(selectedCase.created_at)}
                    </span>
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

                <div className="detail-tabs">
                  <button
                    type="button"
                    className={activeTab === 'signals' ? 'active' : ''}
                    onClick={() => setActiveTab('signals')}
                  >
                    Risk Signals
                  </button>

                  <button
                    type="button"
                    className={activeTab === 'transaction' ? 'active' : ''}
                    onClick={() => setActiveTab('transaction')}
                  >
                    Transaction Info
                  </button>

                  <button
                    type="button"
                    className={activeTab === 'customer' ? 'active' : ''}
                    onClick={() => setActiveTab('customer')}
                  >
                    Customer Info
                  </button>

                  <button
                    type="button"
                    className={activeTab === 'history' ? 'active' : ''}
                    onClick={() => setActiveTab('history')}
                  >
                    History
                  </button>
                </div>

                {activeTab === 'signals' && (
                  <div className="signals">
                    <div className="signals-heading">
                      <div>
                        <h3>Top Contributing Factors</h3>

                        <p>
                          The features that most influenced this
                          case's risk assessment.
                        </p>
                      </div>
                    </div>

                    {selectedCase.prediction.top_risk_signals.length === 0 && (
                      <p className="network-empty-note">
                        No significant risk-increasing signals were
                        found for this case.
                      </p>
                    )}

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
                )}

                {activeTab === 'transaction' && (
                  <div className="info-grid">
                    {TRANSACTION_FIELDS.map((field) => (
                      <div className="info-row" key={field.key}>
                        <span>{field.label}</span>
                        <strong>
                          {formatFieldValue(
                            selectedCase.data[field.key],
                            field.format,
                          )}
                        </strong>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'customer' && (
                  <div className="info-grid">
                    {CUSTOMER_FIELDS.map((field) => (
                      <div className="info-row" key={field.key}>
                        <span>{field.label}</span>
                        <strong>
                          {formatFieldValue(
                            selectedCase.data[field.key],
                            field.format,
                          )}
                        </strong>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'history' && (
                  <div className="case-timeline">
                    <div className="timeline-item">
                      <div className="timeline-icon opened">
                        <Clock size={15} strokeWidth={2.2} />
                      </div>

                      <div>
                        <strong>Case Opened</strong>
                        <span>
                          {formatDateTime(selectedCase.created_at)}
                        </span>
                        <p>
                          Routed to manual review — model decision
                          was {selectedCase.prediction.decision}.
                        </p>
                      </div>
                    </div>

                    {selectedCase.status === 'RESOLVED' ? (
                      <div className="timeline-item">
                        <div
                          className={`timeline-icon ${
                            selectedCase.analyst_decision === 'ALLOW'
                              ? 'allowed'
                              : 'blocked'
                          }`}
                        >
                          {selectedCase.analyst_decision === 'ALLOW' ? (
                            <CheckCircle2 size={15} strokeWidth={2.2} />
                          ) : (
                            <XCircle size={15} strokeWidth={2.2} />
                          )}
                        </div>

                        <div>
                          <strong>
                            Analyst Decision:{' '}
                            {selectedCase.analyst_decision}
                          </strong>
                          <span>
                            {formatDateTime(selectedCase.resolved_at)}
                          </span>
                          <p>
                            {selectedCase.analyst_reason ||
                              'No reason provided.'}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="timeline-item">
                        <div className="timeline-icon pending">
                          <Clock size={15} strokeWidth={2.2} />
                        </div>

                        <div>
                          <strong>Awaiting Analyst Decision</strong>
                          <span>Currently open</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

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