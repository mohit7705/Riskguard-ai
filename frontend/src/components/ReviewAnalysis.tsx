import { useEffect, useState } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Search,
  CheckCircle2,
  Clock,
  XCircle,
} from 'lucide-react'
import {
  decideReviewCase,
  getReviewAnalysis,
  getReviewCase,
  type FeedbackRecord,
  type ReviewCase,
} from '../api/risk'
import './ReportDashboard.css'

type ReviewAnalysisProps = {
  assignmentNumber: string
  filter: 'all' | 'pending' | 'allowed' | 'blocked'
  onInvestigateNetwork: (caseId: string, userId: string) => void
}
type DetailTab =
  | 'signals'
  | 'transaction'
  | 'customer'
  | 'history'

type DataFieldDef = {
  key: string
  label: string
  format:
    | 'currency'
    | 'percent'
    | 'number'
    | 'hours'
    | 'days'
    | 'boolean'
    | 'text'
}

const PAGE_SIZE = 10

const RING_COLOR_BY_LEVEL: Record<string, string> = {
  CRITICAL: '#c74646',
  HIGH: '#e07856',
  MEDIUM: '#c8963e',
  LOW: '#3f9c6d',
  MINIMAL: '#3d6fb4',
}

const TRANSACTION_FIELDS: DataFieldDef[] = [
  { key: 'order_category', label: 'Order Category', format: 'text' },
  { key: 'order_value', label: 'Order Value', format: 'currency' },
  { key: 'item_value', label: 'Item Value', format: 'currency' },
  { key: 'quantity', label: 'Quantity', format: 'number' },
  { key: 'refund_amount', label: 'Refund Amount', format: 'currency' },
  { key: 'return_reason', label: 'Return Reason', format: 'text' },
  {
    key: 'returned_item_match',
    label: 'Item Matches Order',
    format: 'boolean',
  },
  {
    key: 'time_to_return_request_hours',
    label: 'Time to Return Request',
    format: 'hours',
  },
  {
    key: 'item_condition_score',
    label: 'Item Condition Score',
    format: 'number',
  },
  {
    key: 'package_weight_delta_pct',
    label: 'Package Weight Delta',
    format: 'percent',
  },
  {
    key: 'vision_confidence_score',
    label: 'Vision Confidence Score',
    format: 'number',
  },
]

const CUSTOMER_FIELDS: DataFieldDef[] = [
  {
    key: 'account_age_days',
    label: 'Account Age',
    format: 'days',
  },
  {
    key: 'lifetime_order_count',
    label: 'Lifetime Orders',
    format: 'number',
  },
  {
    key: 'lifetime_return_count',
    label: 'Lifetime Returns',
    format: 'number',
  },
  {
    key: 'total_spent',
    label: 'Total Spent',
    format: 'currency',
  },
  {
    key: 'return_rate',
    label: 'Return Rate',
    format: 'percent',
  },
  {
    key: 'return_velocity_30d',
    label: 'Returns (Last 30 Days)',
    format: 'number',
  },
  {
    key: 'return_velocity_48h',
    label: 'Returns (Last 48 Hours)',
    format: 'number',
  },
  {
    key: 'shared_device_count',
    label: 'Shared Devices',
    format: 'number',
  },
  {
    key: 'shared_address_count',
    label: 'Shared Addresses',
    format: 'number',
  },
  {
    key: 'shared_payment_fingerprint_count',
    label: 'Shared Payment Methods',
    format: 'number',
  },
  {
    key: 'device_return_velocity_7d',
    label: 'Device Return Velocity (7d)',
    format: 'number',
  },
  {
    key: 'address_return_velocity_7d',
    label: 'Address Return Velocity (7d)',
    format: 'number',
  },
  {
    key: 'payment_return_velocity_7d',
    label: 'Payment Return Velocity (7d)',
    format: 'number',
  },
  {
    key: 'cluster_return_velocity_7d',
    label: 'Cluster Return Velocity (7d)',
    format: 'number',
  },
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
        ? `₹${value.toLocaleString('en-IN', {
            maximumFractionDigits: 2,
          })}`
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
        ? value.toLocaleString('en-IN', {
            maximumFractionDigits: 4,
          })
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

function ReviewAnalysis({
  assignmentNumber,
  filter,
  onInvestigateNetwork,
}: ReviewAnalysisProps) {
  const [records, setRecords] = useState<FeedbackRecord[]>([])
  const [selectedRecord, setSelectedRecord] =
    useState<FeedbackRecord | null>(null)
  const [selectedCase, setSelectedCase] =
    useState<ReviewCase | null>(null)

  const [activeTab, setActiveTab] =
    useState<DetailTab>('signals')

  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')

  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrev, setHasPrev] = useState(false)

  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [decisionLoading, setDecisionLoading] =
    useState(false)

  const [error, setError] = useState('')
  const [reason, setReason] = useState('')

  const loadAnalysis = async (
    targetPage: number = page,
    targetSearch: string = search,
  ) => {
    setLoading(true)
    setError('')

    try {
      const response = await getReviewAnalysis({
        assignmentNumber,
        filter,
        page: targetPage,
        pageSize: PAGE_SIZE,
        search: targetSearch || undefined,
      })

      setRecords(response.records)
      setPage(response.page)
      setTotal(response.total)
      setTotalPages(response.total_pages)
      setHasNext(response.has_next)
      setHasPrev(response.has_prev)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to load review analysis.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timeout = setTimeout(() => {
      setSearch(searchInput.trim())
    }, 400)

    return () => clearTimeout(timeout)
  }, [searchInput])

  useEffect(() => {
    setPage(1)
    setSelectedRecord(null)
    setSelectedCase(null)
    void loadAnalysis(1, search)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, search, assignmentNumber])

  const goToPage = (nextPage: number) => {
    if (
      nextPage < 1 ||
      nextPage > totalPages ||
      loading
    ) {
      return
    }

    setSelectedRecord(null)
    setSelectedCase(null)
    void loadAnalysis(nextPage, search)
  }

  const handleSelectRecord = async (
    record: FeedbackRecord,
  ) => {
    setSelectedRecord(record)
    setSelectedCase(null)
    setReason(record.analyst_reason ?? '')
    setActiveTab('signals')
    setDetailLoading(true)
    setError('')

    if (!record.case_id) {
      setSelectedCase(null)
      setDetailLoading(false)
      return
    }

    try {
      const reviewCase = await getReviewCase(
        record.case_id,
        assignmentNumber,
      )

      setSelectedCase(reviewCase)
      setReason(
        reviewCase.analyst_reason ??
          record.analyst_reason ??
          '',
      )
    } catch {
      // The feedback record itself remains usable even if
      // its historical review case is unavailable.
      setSelectedCase(null)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleDecision = async (
    decision: 'ALLOW' | 'BLOCK',
  ) => {
    if (
      !selectedRecord ||
      !selectedRecord.case_id
    ) {
      setError(
        'This feedback record has no linked review case, so an analyst decision cannot be changed here.',
      )
      return
    }

    const trimmedReason = reason.trim()

    if (!trimmedReason) {
      setError(
        'Please provide a reason for the decision.',
      )
      return
    }

    setDecisionLoading(true)
    setError('')

    try {
      await decideReviewCase(
        selectedRecord.case_id,
        assignmentNumber,
        decision,
        trimmedReason,
      )

      await loadAnalysis(page, search)

      const updatedRecord =
        records.find(
          (record) =>
            record.id === selectedRecord.id,
        ) ?? null

      setSelectedRecord(updatedRecord)
      setSelectedCase(null)
      setReason('')
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

  const filterLabel =
    filter === 'all'
      ? 'All Reviewed Records'
      : filter === 'pending'
        ? 'Pending Review'
        : filter === 'allowed'
          ? 'Allowed Returns'
          : 'Blocked Returns'

  const selectedPrediction =
    selectedCase?.prediction ??
    (selectedRecord
      ? {
          predicted_label: selectedRecord.predicted_label,
          prediction:
            selectedRecord.prediction === 'ABUSIVE'
              ? 'ABUSIVE'
              : 'LEGITIMATE',
          abuse_probability:
            selectedRecord.abuse_probability,
          legitimate_probability:
            1 - selectedRecord.abuse_probability,
          risk_score: selectedRecord.risk_score,
          risk_level:
            selectedRecord.risk_level as ReviewCase['prediction']['risk_level'],
          decision: selectedRecord.model_decision,
          action:
            selectedRecord.model_decision === 'ALLOW'
              ? 'ALLOW_RETURN'
              : selectedRecord.model_decision === 'BLOCK'
                ? 'BLOCK_RETURN'
                : 'MANUAL_REVIEW',
          reason:
            selectedRecord.model_decision === 'ALLOW'
              ? `RiskGuard classified this return with an abuse probability of ${(selectedRecord.abuse_probability * 100).toFixed(2)}%. The model decision was ALLOW.`
              : selectedRecord.model_decision === 'BLOCK'
                ? `RiskGuard classified this return with an abuse probability of ${(selectedRecord.abuse_probability * 100).toFixed(2)}%. The model decision was BLOCK.`
                : `RiskGuard classified this return with an abuse probability of ${(selectedRecord.abuse_probability * 100).toFixed(2)}%. The model decision was REVIEW, so the return requires analyst review.`,
          top_risk_signals: [],
          model_type: 'RiskGuard XGBoost',
          review_case_id: selectedRecord.case_id,
        }
      : null)

  const selectedData =
    selectedCase?.data ??
    selectedRecord?.input_data ??
    {}

  const isLinkedCase =
    Boolean(selectedRecord?.case_id)

  const hasSelectedRecord =
    Boolean(selectedRecord)

  const ringColor = selectedPrediction
    ? RING_COLOR_BY_LEVEL[
        selectedPrediction.risk_level?.toUpperCase() ?? ''
      ] ?? 'var(--red)'
    : 'var(--red)'

  return (
    <section className="review-queue">
      <div className="panel-header">
        <div>
          <h3>{filterLabel}</h3>
          <p>
            Search and inspect the underlying RiskGuard
            review records.
          </p>
        </div>

        <button
          className="secondary-button"
          type="button"
          onClick={() =>
            void loadAnalysis(page, search)
          }
          disabled={loading}
        >
          <RefreshCw
            size={15}
            className={
              loading ? 'spin-icon' : ''
            }
          />
          {loading
            ? 'Refreshing...'
            : 'Refresh'}
        </button>
      </div>

      <div className="ra-search-bar">
        <Search
          size={16}
          strokeWidth={2}
          className="ra-search-icon"
        />

        <input
          type="text"
          value={searchInput}
          onChange={(event) =>
            setSearchInput(event.target.value)
          }
          placeholder="Search by case ID..."
          className="ra-search-input"
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
          <h3>Loading review analysis</h3>
          <p>
            RiskGuard is loading review records.
          </p>
        </div>
      )}

      {!loading && records.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">✓</div>

          <h3>
            {search
              ? 'No matching records'
              : 'No records found'}
          </h3>

          <p>
            {search
              ? `No records with case ID matching "${search}".`
              : 'There are no records for this filter.'}
          </p>
        </div>
      )}

      {!loading && records.length > 0 && (
        <div className="review-layout">
          <div>
            <div className="review-case-list">
              {records.map((record) => {
                const decision =
                  record.analyst_decision ??
                  record.model_decision

                return (
                  <button
                    className={`review-case-card ${
                      selectedRecord?.id === record.id
                        ? 'selected'
                        : ''
                    }`}
                    key={record.id}
                    type="button"
                    onClick={() =>
                      void handleSelectRecord(record)
                    }
                  >
                    <div className="review-case-top">
                      <strong>
                        {record.case_id ??
                          `Feedback #${record.id}`}
                      </strong>

                      <span
                        className={`risk-pill ${record.risk_level.toLowerCase()}`}
                      >
                        {record.risk_level}
                      </span>
                    </div>

                    <div className="review-case-summary">
                      <span>{decision}</span>

                      <strong>
                        {record.risk_score.toFixed(2)}
                      </strong>
                    </div>

                    <small>
                      {record.prediction} ·{' '}
                      {(
                        record.abuse_probability *
                        100
                      ).toFixed(2)}
                      % abuse probability
                    </small>
                  </button>
                )
              })}
            </div>

            <div className="ra-pagination">
              <span className="ra-pagination-count">
                {total === 0
                  ? '0 records'
                  : `Showing ${
                      (page - 1) * PAGE_SIZE + 1
                    }–${Math.min(
                      page * PAGE_SIZE,
                      total,
                    )} of ${total}`}
              </span>

              <div className="ra-pagination-controls">
                <button
                  type="button"
                  className="ra-page-button"
                  onClick={() =>
                    goToPage(page - 1)
                  }
                  disabled={!hasPrev || loading}
                >
                  <ChevronLeft size={14} />
                </button>

                <span className="ra-page-indicator">
                  Page {page} of {totalPages}
                </span>

                <button
                  type="button"
                  className="ra-page-button"
                  onClick={() =>
                    goToPage(page + 1)
                  }
                  disabled={!hasNext || loading}
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
                <p>
                  RiskGuard is loading the complete
                  review information.
                </p>
              </div>
            )}

            {!detailLoading &&
              !hasSelectedRecord && (
                <div className="empty-state">
                  <div className="empty-icon">
                    <Search
                      size={26}
                      strokeWidth={1.8}
                    />
                  </div>

                  <h3>Select a record</h3>

                  <p>
                    Select a record to inspect its
                    complete RiskGuard analysis.
                  </p>
                </div>
              )}

            {!detailLoading &&
              hasSelectedRecord &&
              selectedPrediction && (
                <>
                  <div className="review-detail-header">
                    <div>
                      <span>REVIEW RECORD</span>

                      <h3>
                        {selectedRecord?.case_id ??
                          `Feedback #${selectedRecord?.id}`}
                      </h3>

                      <span className="review-detail-created">
                        Created:{' '}
                        {formatDateTime(
                          selectedRecord?.created_at ??
                            null,
                        )}
                      </span>
                    </div>

                    <span
                      className={`risk-pill ${selectedPrediction.risk_level.toLowerCase()}`}
                    >
                      {
                        selectedPrediction.risk_level
                      }
                    </span>
                  </div>

                  <div className="metrics">
                    <div className="metric">
                      <span>Prediction</span>

                      <strong
                        className={
                          selectedPrediction.prediction ===
                          'ABUSIVE'
                            ? 'value-negative'
                            : 'value-positive'
                        }
                      >
                        {
                          selectedPrediction.prediction
                        }
                      </strong>
                    </div>

                    <div className="metric metric-ring">
                      <span>Risk Score</span>

                      <div className="ring-row">
                        <strong>
                          {
                            selectedPrediction.risk_score
                          }
                        </strong>

                        <div
                          className="score-ring"
                          style={{
                            background: `conic-gradient(${ringColor} ${selectedPrediction.risk_score}%, #eef1f5 0)`,
                          }}
                        >
                          <div className="score-ring-hole" />
                        </div>
                      </div>
                    </div>

                    <div className="metric">
                      <span>
                        Abuse Probability
                      </span>

                      <strong>
                        {(
                          selectedPrediction.abuse_probability *
                          100
                        ).toFixed(2)}
                        %
                      </strong>
                    </div>

                    <div className="metric">
                      <span>Model Decision</span>

                      <strong>
                        {
                          selectedPrediction.decision
                        }
                      </strong>
                    </div>
                  </div>

                  <div className="decision-card">
                    <div className="decision-card-row">
                      <div>
                        <span>
                          MODEL DECISION
                        </span>

                        <strong>
                          {
                            selectedPrediction.decision
                          }
                        </strong>
                      </div>
                    </div>

                    <p>
                      {selectedPrediction.reason}
                    </p>
                  </div>

                  {selectedRecord?.case_id &&
                    typeof selectedData.user_id === 'string' &&
                    selectedData.user_id.trim() && (
                      <div className="ra-investigate-row">
                        <button
                          type="button"
                          className="secondary-button"
                          onClick={() => {
                            const userId =
                              String(
                                selectedData.user_id,
                              ).trim()

                            if (
                              !selectedRecord.case_id ||
                              !userId
                            ) {
                              return
                            }

                            onInvestigateNetwork(
                              selectedRecord.case_id,
                              userId,
                            )
                          }}
                        >
                          Investigate Network
                        </button>
                      </div>
                    )}

                  {!isLinkedCase && (
                    <div className="decision-card ra-record-type-card">
                      <div className="decision-card-row">
                        <div>
                          <span>
                            RECORD TYPE
                          </span>

                          <strong>
                            Feedback Record
                          </strong>
                        </div>
                      </div>

                      <p>
                        This record has no linked review
                        case. The model decision is shown
                        from the stored production
                        feedback record; no analyst decision
                        is being inferred.
                      </p>
                    </div>
                  )}

                  <div className="detail-tabs">
                    <button
                      type="button"
                      className={
                        activeTab === 'signals'
                          ? 'active'
                          : ''
                      }
                      onClick={() =>
                        setActiveTab('signals')
                      }
                    >
                      Risk Signals
                    </button>

                    <button
                      type="button"
                      className={
                        activeTab === 'transaction'
                          ? 'active'
                          : ''
                      }
                      onClick={() =>
                        setActiveTab(
                          'transaction',
                        )
                      }
                    >
                      Transaction Info
                    </button>

                    <button
                      type="button"
                      className={
                        activeTab === 'customer'
                          ? 'active'
                          : ''
                      }
                      onClick={() =>
                        setActiveTab('customer')
                      }
                    >
                      Customer Info
                    </button>

                    <button
                      type="button"
                      className={
                        activeTab === 'history'
                          ? 'active'
                          : ''
                      }
                      onClick={() =>
                        setActiveTab('history')
                      }
                    >
                      History
                    </button>
                  </div>

                  {activeTab === 'signals' && (
                    <div className="signals">
                      <div className="signals-heading">
                        <div>
                          <h3>
                            Top Contributing
                            Factors
                          </h3>

                          <p>
                            The features that most
                            influenced this case's
                            risk assessment.
                          </p>
                        </div>
                      </div>

                      {selectedPrediction
                        .top_risk_signals
                        .length === 0 && (
                        <p className="network-empty-note">
                          No stored risk signals are
                          available for this feedback
                          record.
                        </p>
                      )}

                      {selectedPrediction.top_risk_signals.map(
                        (signal) => (
                          <div
                            className="signal"
                            key={
                              signal.feature
                            }
                          >
                            <div className="signal-main">
                              <strong>
                                {
                                  signal.feature
                                }
                              </strong>

                              <span>
                                {String(
                                  signal.value,
                                )}
                              </span>
                            </div>

                            <div className="signal-description">
                              {
                                signal.description
                              }
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

                  {activeTab ===
                    'transaction' && (
                    <div className="info-grid">
                      {TRANSACTION_FIELDS.map(
                        (field) => (
                          <div
                            className="info-row"
                            key={field.key}
                          >
                            <span>
                              {field.label}
                            </span>

                            <strong>
                              {formatFieldValue(
                                selectedData[
                                  field.key
                                ],
                                field.format,
                              )}
                            </strong>
                          </div>
                        ),
                      )}
                    </div>
                  )}

                  {activeTab === 'customer' && (
                    <div className="info-grid">
                      {CUSTOMER_FIELDS.map(
                        (field) => (
                          <div
                            className="info-row"
                            key={field.key}
                          >
                            <span>
                              {field.label}
                            </span>

                            <strong>
                              {formatFieldValue(
                                selectedData[
                                  field.key
                                ],
                                field.format,
                              )}
                            </strong>
                          </div>
                        ),
                      )}
                    </div>
                  )}

                  {activeTab === 'history' && (
                    <div className="case-timeline">
                      <div className="timeline-item">
                        <div className="timeline-icon opened">
                          <Clock
                            size={15}
                            strokeWidth={2.2}
                          />
                        </div>

                        <div>
                          <strong>
                            Record Created
                          </strong>

                          <span>
                            {formatDateTime(
                              selectedRecord?.created_at ??
                                null,
                            )}
                          </span>

                          <p>
                            RiskGuard stored this
                            production assessment
                            in the feedback record.
                          </p>
                        </div>
                      </div>

                      {selectedRecord
                        ?.actual_outcome && (
                        <div className="timeline-item">
                          <div className="timeline-icon allowed">
                            <CheckCircle2
                              size={15}
                              strokeWidth={2.2}
                            />
                          </div>

                          <div>
                            <strong>
                              Actual Outcome:{' '}
                              {
                                selectedRecord.actual_outcome
                              }
                            </strong>

                            <span>
                              {formatDateTime(
                                selectedRecord.outcome_recorded_at,
                              )}
                            </span>
                          </div>
                        </div>
                      )}

                      {selectedRecord
                        ?.analyst_decision ? (
                        <div className="timeline-item">
                          <div
                            className={`timeline-icon ${
                              selectedRecord.analyst_decision ===
                              'ALLOW'
                                ? 'allowed'
                                : 'blocked'
                            }`}
                          >
                            {selectedRecord.analyst_decision ===
                            'ALLOW' ? (
                              <CheckCircle2
                                size={15}
                                strokeWidth={2.2}
                              />
                            ) : (
                              <XCircle
                                size={15}
                                strokeWidth={2.2}
                              />
                            )}
                          </div>

                          <div>
                            <strong>
                              Analyst Decision:{' '}
                              {
                                selectedRecord.analyst_decision
                              }
                            </strong>

                            <span>
                              {formatDateTime(
                                selectedRecord.outcome_recorded_at,
                              )}
                            </span>

                            <p>
                              {selectedRecord.analyst_reason ||
                                'No reason provided.'}
                            </p>
                          </div>
                        </div>
                      ) : (
                        <div className="timeline-item">
                          <div className="timeline-icon pending">
                            <Clock
                              size={15}
                              strokeWidth={2.2}
                            />
                          </div>

                          <div>
                            <strong>
                              No Analyst Decision
                            </strong>

                            <span>
                              Not recorded
                            </span>

                            <p>
                              The model decision is
                              displayed separately from
                              analyst action.
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="review-decision">
                    <h3>Analyst Decision</h3>

                    {selectedRecord?.analyst_decision ? (
                      <div className="decision-card">
                        <div className="decision-card-row">
                          <div>
                            <span>
                              RECORDED DECISION
                            </span>

                            <strong>
                              {
                                selectedRecord.analyst_decision
                              }
                            </strong>
                          </div>
                        </div>

                        <p>
                          {selectedRecord.analyst_reason ||
                            'No reason provided.'}
                        </p>
                      </div>
                    ) : (
                      <>
                        <textarea
                          value={reason}
                          onChange={(event) =>
                            setReason(
                              event.target.value,
                            )
                          }
                          placeholder={
                            isLinkedCase
                              ? 'Enter the reason for your decision...'
                              : 'No linked review case — analyst decision is unavailable for this record.'
                          }
                          disabled={
                            decisionLoading ||
                            !isLinkedCase
                          }
                        />

                        <div className="review-actions">
                          <button
                            className="allow-button"
                            type="button"
                            onClick={() =>
                              void handleDecision(
                                'ALLOW',
                              )
                            }
                            disabled={
                              decisionLoading ||
                              !isLinkedCase
                            }
                          >
                            {decisionLoading
                              ? 'Saving...'
                              : 'ALLOW'}
                          </button>

                          <button
                            className="block-button"
                            type="button"
                            onClick={() =>
                              void handleDecision(
                                'BLOCK',
                              )
                            }
                            disabled={
                              decisionLoading ||
                              !isLinkedCase
                            }
                          >
                            {decisionLoading
                              ? 'Saving...'
                              : 'BLOCK'}
                          </button>
                        </div>
                      </>
                    )}

                    <div className="decision-guidelines">
                      <strong>
                        Decision Guidelines
                      </strong>

                      <ul>
                        <li>
                          <span className="dot allow" />
                          ALLOW: Legitimate return
                          request
                        </li>

                        <li>
                          <span className="dot block" />
                          BLOCK: Abuse or policy
                          violation
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

export default ReviewAnalysis