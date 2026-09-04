import { useState } from 'react'
import './App.css'
import type {
  RiskResult,
  RiskResponse,
  BatchResponse,
} from './types/risk'
import { parseCsv } from './utils/csv'
import BatchResult from './components/BatchResult'
import SingleResult from './components/SingleResult'
import ReturnInput from './components/ReturnInput'
import NetworkResult from './components/NetworkResult'
import ReportDashboard from './components/ReportDashboard'
import ReviewAnalysis from './components/ReviewAnalysis'
import AssignmentEntry from './components/AssignmentEntry'
import {
  getUserNetwork,
  type UserNetwork,
} from './api/risk'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const REQUIRED_COLUMNS = [
  'order_category',
  'order_value',
  'item_value',
  'quantity',
  'time_to_return_request_hours',
  'refund_amount',
  'return_reason',
  'returned_item_match',
  'item_condition_score',
  'package_weight_delta_pct',
  'vision_confidence_score',
  'account_age_days',
  'lifetime_order_count',
  'lifetime_return_count',
  'total_spent',
  'return_rate',
  'return_velocity_30d',
  'return_velocity_48h',
  'shared_device_count',
  'shared_address_count',
  'shared_payment_fingerprint_count',
  'device_return_velocity_7d',
  'address_return_velocity_7d',
  'payment_return_velocity_7d',
  'cluster_return_velocity_7d',
]

const sampleSingleData = `{
  "order_category": "Electronics",
  "order_value": 509.83,
  "item_value": 55.82,
  "quantity": 1,
  "time_to_return_request_hours": 49.37,
  "refund_amount": 49.21,
  "return_reason": "Not as expected",
  "returned_item_match": true,
  "item_condition_score": 0.443,
  "package_weight_delta_pct": 1.89,
  "vision_confidence_score": 0.762,
  "account_age_days": 241,
  "lifetime_order_count": 64,
  "lifetime_return_count": 6,
  "total_spent": 218.44,
  "return_rate": 0.09375,
  "return_velocity_30d": 0,
  "return_velocity_48h": 0,
  "shared_device_count": 1,
  "shared_address_count": 2,
  "shared_payment_fingerprint_count": 2,
  "device_return_velocity_7d": 0,
  "address_return_velocity_7d": 0,
  "payment_return_velocity_7d": 0,
  "cluster_return_velocity_7d": 0
}`

function App() {
  const [activePage, setActivePage] = useState<
    'report' | 'review' | 'single' | 'bulk' | 'network'
  >('report')
  const [reviewFilter, setReviewFilter] = useState<
    'all' | 'pending' | 'allowed' | 'blocked'
  >('all')
  const [mode, setMode] = useState<'single' | 'batch'>('single')
  const [batchInputMode, setBatchInputMode] = useState<'csv' | 'json'>('csv')

  const [jsonInput, setJsonInput] = useState(sampleSingleData)
  const [batchRows, setBatchRows] = useState<Record<string, unknown>[]>([])

  const [result, setResult] = useState<RiskResult | null>(null)
  const [batchResults, setBatchResults] = useState<RiskResult[]>([])

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [csvFileName, setCsvFileName] = useState('')

  const [assignmentNumber, setAssignmentNumber] = useState('')
  const [networkUserId, setNetworkUserId] = useState('U000001')
  const [network, setNetwork] = useState<UserNetwork | null>(null)
  const [networkLoading, setNetworkLoading] = useState(false)
  const [networkError, setNetworkError] = useState('')

  const handleNetworkAnalysis = async () => {
    const userId = networkUserId.trim()

    if (!userId) {
      setNetworkError('Please enter a user ID.')
      setNetwork(null)
      return
    }

    setNetworkLoading(true)
    setNetworkError('')

    try {
      const response = await getUserNetwork(userId, assignmentNumber)
      setNetwork(response)
    } catch (err) {
      setNetwork(null)
      setNetworkError(
        err instanceof Error
          ? err.message
          : 'Unable to load user network.',
      )
    } finally {
      setNetworkLoading(false)
    }
  }

  const handleModeChange = (nextMode: 'single' | 'batch') => {
    setMode(nextMode)
    setResult(null)
    setBatchResults([])
    setError('')

    if (nextMode === 'single') {
      setJsonInput(sampleSingleData)
    }
  }

  const handleCsvFile = async (file: File) => {
    setError('')
    setBatchResults([])
    setCsvFileName(file.name)

    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Please upload a CSV file.')
      setCsvFileName('')
      setBatchRows([])
      return
    }

    try {
      const text = await file.text()
      const rows = parseCsv(text, REQUIRED_COLUMNS)

      if (rows.length === 0) {
        throw new Error('CSV does not contain any data rows.')
      }

      setBatchRows(rows)
    } catch (err) {
      setBatchRows([])
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to parse the CSV file.',
      )
    }
  }

  const handleAnalyze = async () => {
    setError('')
    setResult(null)
    setBatchResults([])

    if (mode === 'single') {
      await analyzeSingle()
    } else {
      await analyzeBatch()
    }
  }

  const analyzeSingle = async () => {
    if (!jsonInput.trim()) {
      setError('Please enter return feature data.')
      return
    }

    let data: Record<string, unknown>

    try {
      data = JSON.parse(jsonInput)
    } catch {
      setError('Invalid JSON. Please check the input format.')
      return
    }

    setLoading(true)

    try {
      const response = await fetch(`${API_BASE}/api/v1/risk/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          data,
          assignment_number: assignmentNumber,
        }),
      })

      const body = await response.json()

      if (!response.ok) {
        throw new Error(body.detail || 'Risk prediction failed.')
      }

      const payload = body as RiskResponse
      setResult(payload.result)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to connect to RiskGuard API.',
      )
    } finally {
      setLoading(false)
    }
  }

  const analyzeBatch = async () => {
    let rows = batchRows

    if (batchInputMode === 'json') {
      if (!jsonInput.trim()) {
        setError('Please enter a JSON array.')
        return
      }

      try {
        const parsed = JSON.parse(jsonInput)

        if (!Array.isArray(parsed)) {
          throw new Error('Batch JSON must be an array of records.')
        }

        rows = parsed
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : 'Invalid batch JSON.',
        )
        return
      }
    }

    if (rows.length === 0) {
      setError('Please upload a CSV file containing return records.')
      return
    }

    setLoading(true)

    try {
      const response = await fetch(
        `${API_BASE}/api/v1/risk/predict/batch`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            data: rows,
            assignment_number: assignmentNumber,
          }),
        },
      )

      const body = await response.json()

      if (!response.ok) {
        throw new Error(
          body.detail || 'Batch risk prediction failed.',
        )
      }

      const payload = body as BatchResponse

      setBatchResults(payload.results)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to connect to RiskGuard API.',
      )
    } finally {
      setLoading(false)
    }
  }

  const batchSummary = {
    total: batchResults.length,
    legitimate: batchResults.filter(
      (item) => item.prediction === 'LEGITIMATE',
    ).length,
    abusive: batchResults.filter(
      (item) => item.prediction === 'ABUSIVE',
    ).length,
    allow: batchResults.filter(
      (item) => item.decision === 'ALLOW',
    ).length,
    review: batchResults.filter(
      (item) => item.decision === 'REVIEW',
    ).length,
    block: batchResults.filter(
      (item) => item.decision === 'BLOCK',
    ).length,
  }

  if (!assignmentNumber) {
    return (
      <AssignmentEntry
        onAssignmentSelected={(selectedAssignment) => {
          setAssignmentNumber(
            selectedAssignment.assignment_number,
          )
        }}
      />
    )
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark">R</div>

          <div>
            <h1>RiskGuard AI</h1>
            <span>Return Abuse Intelligence</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button
            type="button"
            className={`nav-item ${
              activePage === 'report' ? 'active' : ''
            }`}
            onClick={() => setActivePage('report')}
          >
            <span className="nav-icon">▣</span>
            <span>
              <strong>Report</strong>
              <small>Summary &amp; charts</small>
            </span>
          </button>

          <button
            type="button"
            className={`nav-item ${
              activePage === 'review' ? 'active' : ''
            }`}
            onClick={() => setActivePage('review')}
          >
            <span className="nav-icon">☑</span>
            <span>
              <strong>Review Analysis</strong>
              <small>Model insights &amp; review queue</small>
            </span>
          </button>

          <button
            type="button"
            className={`nav-item ${
              activePage === 'single' ? 'active' : ''
            }`}
            onClick={() => {
              setActivePage('single')
              handleModeChange('single')
            }}
          >
            <span className="nav-icon">◉</span>
            <span>
              <strong>Single Assessment</strong>
              <small>Analyze one return</small>
            </span>
          </button>

          <button
            type="button"
            className={`nav-item ${
              activePage === 'bulk' ? 'active' : ''
            }`}
            onClick={() => {
              setActivePage('bulk')
              handleModeChange('batch')
            }}
          >
            <span className="nav-icon">▤</span>
            <span>
              <strong>Bulk Assessment</strong>
              <small>Analyze multiple returns</small>
            </span>
          </button>

          <button
            type="button"
            className={`nav-item ${
              activePage === 'network' ? 'active' : ''
            }`}
            onClick={() => setActivePage('network')}
          >
            <span className="nav-icon">⌁</span>
            <span>
              <strong>Network Analysis</strong>
              <small>Connected accounts</small>
            </span>
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="api-status">
            <span className="status-dot" />
            <span>
              <strong>API ONLINE</strong>
              <small>RiskGuard backend</small>
            </span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        {activePage === 'report' && (
          <ReportDashboard
            assignmentNumber={assignmentNumber}
            onReviewFilter={(filter) => {
              setReviewFilter(filter)
              setActivePage('review')
            }}
          />
        )}

        {activePage === 'review' && (
          <ReviewAnalysis assignmentNumber={assignmentNumber} filter={reviewFilter} />
        )}

        {activePage === 'single' && (
          <>
            <header className="page-header">
              <div className="page-header-row">
                <div className="page-header-icon blue">◉</div>
                <div>
                  <p className="eyebrow">RISK ASSESSMENT</p>
                  <h2>Single Return Assessment</h2>
                  <p>
                    Evaluate one return request using the RiskGuard
                    machine learning model.
                  </p>
                </div>
              </div>
            </header>

            <section className="workspace">
              <ReturnInput
                mode="single"
                batchInputMode={batchInputMode}
                jsonInput={jsonInput}
                batchRows={batchRows}
                loading={loading}
                csvFileName={csvFileName}
                error={error}
                setJsonInput={setJsonInput}
                setBatchInputMode={setBatchInputMode}
                handleAnalyze={handleAnalyze}
                handleCsvFile={handleCsvFile}
              />

              <div className="panel result-panel">
                <div className="panel-header">
                  <div>
                    <h3>Risk Assessment</h3>
                    <p>
                      Model prediction and business decision.
                    </p>
                  </div>
                </div>

                {!loading && !result && (
                  <div className="empty-state">
                    <div className="empty-icon">◎</div>
                    <h3>No assessment yet</h3>
                    <p>
                      Submit return data to generate a RiskGuard
                      risk assessment.
                    </p>
                  </div>
                )}

                {loading && (
                  <div className="empty-state">
                    <div className="loader" />
                    <h3>Analyzing return</h3>
                    <p>
                      RiskGuard is evaluating the submitted
                      record.
                    </p>
                  </div>
                )}

                {result && !loading && (
                  <SingleResult result={result} />
                )}
              </div>
            </section>
          </>
        )}

        {activePage === 'bulk' && (
          <>
            <header className="page-header">
              <div className="page-header-row">
                <div className="page-header-icon amber">▤</div>
                <div>
                  <p className="eyebrow">BULK PROCESSING</p>
                  <h2>Bulk Return Assessment</h2>
                  <p>
                    Upload a CSV or provide developer JSON to
                    analyze multiple return requests.
                  </p>
                </div>
              </div>
            </header>

            <section className="workspace">
              <ReturnInput
                mode="batch"
                batchInputMode={batchInputMode}
                jsonInput={jsonInput}
                batchRows={batchRows}
                loading={loading}
                csvFileName={csvFileName}
                error={error}
                setJsonInput={setJsonInput}
                setBatchInputMode={setBatchInputMode}
                handleAnalyze={handleAnalyze}
                handleCsvFile={handleCsvFile}
              />

              <div className="panel result-panel">
                <div className="panel-header">
                  <div>
                    <h3>Bulk Assessment</h3>
                    <p>
                      Batch prediction summary and individual
                      decisions.
                    </p>
                  </div>
                </div>

                {!loading && batchResults.length === 0 && (
                  <div className="empty-state">
                    <div className="empty-icon">▤</div>
                    <h3>No bulk assessment yet</h3>
                    <p>
                      Upload a CSV or provide JSON to generate
                      bulk RiskGuard assessments.
                    </p>
                  </div>
                )}

                {loading && (
                  <div className="empty-state">
                    <div className="loader" />
                    <h3>Analyzing bulk returns</h3>
                    <p>
                      RiskGuard is evaluating the submitted
                      records.
                    </p>
                  </div>
                )}

                {batchResults.length > 0 && !loading && (
                  <BatchResult
                    results={batchResults}
                    summary={batchSummary}
                  />
                )}
              </div>
            </section>
          </>
        )}

        {activePage === 'network' && (
          <>
            <header className="page-header">
              <div className="page-header-row">
                <div className="page-header-icon purple">⌁</div>
                <div>
                  <p className="eyebrow">INVESTIGATION</p>
                  <h2>Network Analysis</h2>
                  <p>
                    Investigate connected accounts through shared
                    devices, addresses and payments.
                  </p>
                </div>
              </div>
            </header>

            <section className="network-panel panel">
                <div className="panel-header">
                  <div>
                    <h3>Network Analysis</h3>
                    <p>
                      Inspect accounts connected through shared
                      devices, addresses, or payment fingerprints.
                    </p>
                  </div>
                </div>

                <div className="network-controls">
                  <input
                    type="text"
                    value={networkUserId}
                    onChange={(event) =>
                      setNetworkUserId(event.target.value)
                    }
                    placeholder="Enter user ID"
                  />

                  <button
                    type="button"
                    onClick={handleNetworkAnalysis}
                    disabled={networkLoading}
                  >
                    {networkLoading
                      ? 'Loading Network...'
                      : 'Analyze Network'}
                  </button>
                </div>

                {networkError && (
                  <div className="network-error">
                    {networkError}
                  </div>
                )}

                {networkLoading && (
                  <div className="empty-state">
                    <div className="loader" />
                    <h3>Analyzing network</h3>
                    <p>
                      RiskGuard is mapping connected accounts.
                    </p>
                  </div>
                )}

                {!network && !networkLoading && !networkError && (
                  <div className="empty-state">
                    <div className="empty-icon">⌁</div>
                    <h3>No network analyzed yet</h3>
                    <p>
                      Enter a user ID above to inspect its
                      connected accounts.
                    </p>
                  </div>
                )}

                {network && !networkLoading && (
                  <NetworkResult network={network}/>
                )}
            </section>
          </>
        )}
      </main>
    </div>
  )
}

export default App