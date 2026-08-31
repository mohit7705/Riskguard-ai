import { useEffect, useState, type ChangeEvent } from 'react'

type ReturnInputProps = {
  mode: 'single' | 'batch'
  batchInputMode: 'csv' | 'json'
  jsonInput: string
  batchRows: Record<string, unknown>[]
  loading: boolean
  csvFileName: string
  error: string

  setJsonInput: (value: string) => void
  setBatchInputMode: (value: 'csv' | 'json') => void
  handleAnalyze: () => void
  handleCsvFile: (file: File) => void
}

type FieldDef =
  | {
      key: string
      label: string
      help: string
      type: 'number'
      step?: number
      min?: number
      max?: number
    }
  | {
      key: string
      label: string
      help: string
      type: 'select'
      options: string[]
    }
  | {
      key: string
      label: string
      help: string
      type: 'boolean'
    }

type FieldGroup = {
  title: string
  fields: FieldDef[]
}

const ORDER_CATEGORY_OPTIONS = [
  'Electronics',
  'Apparel',
  'Beauty',
  'Books',
  'Home',
  'Luxury',
  'Sports',
  'Other',
]

const RETURN_REASON_OPTIONS = [
  'Wrong size',
  'Changed mind',
  'Not as expected',
  'Defective',
  'Other',
]

const FIELD_GROUPS: FieldGroup[] = [
  {
    title: 'Order Details',
    fields: [
      {
        key: 'order_category',
        label: 'Order Category',
        help: 'Product category for this order.',
        type: 'select',
        options: ORDER_CATEGORY_OPTIONS,
      },
      {
        key: 'order_value',
        label: 'Order Value',
        help: 'Total value of the original order.',
        type: 'number',
        step: 0.01,
        min: 0,
      },
      {
        key: 'item_value',
        label: 'Item Value',
        help: 'Value of the specific item being returned.',
        type: 'number',
        step: 0.01,
        min: 0,
      },
      {
        key: 'quantity',
        label: 'Quantity',
        help: 'Number of units being returned.',
        type: 'number',
        step: 1,
        min: 0,
      },
    ],
  },
  {
    title: 'Return Details',
    fields: [
      {
        key: 'time_to_return_request_hours',
        label: 'Time to Return Request (hrs)',
        help: 'Hours between delivery and the return request.',
        type: 'number',
        step: 0.01,
        min: 0,
      },
      {
        key: 'refund_amount',
        label: 'Refund Amount',
        help: 'Amount to be refunded if approved.',
        type: 'number',
        step: 0.01,
        min: 0,
      },
      {
        key: 'return_reason',
        label: 'Return Reason',
        help: 'Reason given by the customer for the return.',
        type: 'select',
        options: RETURN_REASON_OPTIONS,
      },
      {
        key: 'returned_item_match',
        label: 'Returned Item Matches Order',
        help: 'Whether the returned item matches what was ordered.',
        type: 'boolean',
      },
      {
        key: 'item_condition_score',
        label: 'Item Condition Score',
        help: 'Assessed physical condition, 0 (poor) to 1 (like new).',
        type: 'number',
        step: 0.01,
        min: 0,
        max: 1,
      },
      {
        key: 'package_weight_delta_pct',
        label: 'Package Weight Delta (%)',
        help: 'Percent difference between expected and actual package weight.',
        type: 'number',
        step: 0.01,
      },
      {
        key: 'vision_confidence_score',
        label: 'Vision Confidence Score',
        help: 'Confidence that the returned item photo matches the product, 0 to 1.',
        type: 'number',
        step: 0.01,
        min: 0,
        max: 1,
      },
    ],
  },
  {
    title: 'Customer History',
    fields: [
      {
        key: 'account_age_days',
        label: 'Account Age (days)',
        help: 'Days since the customer account was created.',
        type: 'number',
        step: 1,
        min: 0,
      },
      {
        key: 'lifetime_order_count',
        label: 'Lifetime Orders',
        help: 'Total orders placed by this customer.',
        type: 'number',
        step: 1,
        min: 0,
      },
      {
        key: 'lifetime_return_count',
        label: 'Lifetime Returns',
        help: 'Total returns filed by this customer.',
        type: 'number',
        step: 1,
        min: 0,
      },
      {
        key: 'total_spent',
        label: 'Total Spent',
        help: 'Lifetime spend by this customer.',
        type: 'number',
        step: 0.01,
        min: 0,
      },
      {
        key: 'return_rate',
        label: 'Return Rate',
        help: 'Lifetime returns divided by lifetime orders.',
        type: 'number',
        step: 0.0001,
        min: 0,
        max: 1,
      },
      {
        key: 'return_velocity_30d',
        label: 'Returns in Last 30 Days',
        help: 'Number of returns filed in the past 30 days.',
        type: 'number',
        step: 1,
        min: 0,
      },
      {
        key: 'return_velocity_48h',
        label: 'Returns in Last 48 Hours',
        help: 'Number of returns filed in the past 48 hours.',
        type: 'number',
        step: 1,
        min: 0,
      },
    ],
  },
  {
    title: 'Network Signals',
    fields: [
      {
        key: 'shared_device_count',
        label: 'Shared Devices',
        help: 'Other accounts seen using the same device.',
        type: 'number',
        step: 1,
        min: 0,
      },
      {
        key: 'shared_address_count',
        label: 'Shared Addresses',
        help: 'Other accounts sharing this delivery address.',
        type: 'number',
        step: 1,
        min: 0,
      },
      {
        key: 'shared_payment_fingerprint_count',
        label: 'Shared Payment Fingerprints',
        help: 'Other accounts sharing this payment method.',
        type: 'number',
        step: 1,
        min: 0,
      },
      {
        key: 'device_return_velocity_7d',
        label: 'Device Return Velocity (7d)',
        help: 'Returns from this device across all accounts, last 7 days.',
        type: 'number',
        step: 1,
        min: 0,
      },
      {
        key: 'address_return_velocity_7d',
        label: 'Address Return Velocity (7d)',
        help: 'Returns from this address across all accounts, last 7 days.',
        type: 'number',
        step: 1,
        min: 0,
      },
      {
        key: 'payment_return_velocity_7d',
        label: 'Payment Return Velocity (7d)',
        help: 'Returns tied to this payment fingerprint, last 7 days.',
        type: 'number',
        step: 1,
        min: 0,
      },
      {
        key: 'cluster_return_velocity_7d',
        label: 'Cluster Return Velocity (7d)',
        help: 'Returns across the entire linked-account cluster, last 7 days.',
        type: 'number',
        step: 1,
        min: 0,
      },
    ],
  },
]

function tryParseJson(
  text: string,
): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(text)

    if (
      parsed &&
      typeof parsed === 'object' &&
      !Array.isArray(parsed)
    ) {
      return parsed as Record<string, unknown>
    }

    return null
  } catch {
    return null
  }
}

function ReturnInput({
  mode,
  batchInputMode,
  jsonInput,
  batchRows,
  loading,
  csvFileName,
  error,
  setJsonInput,
  setBatchInputMode,
  handleAnalyze,
  handleCsvFile,
}: ReturnInputProps) {
  const [singleInputMode, setSingleInputMode] = useState<'form' | 'json'>(
    'form',
  )

  const [fields, setFields] = useState<Record<string, unknown>>(
    () => tryParseJson(jsonInput) ?? {},
  )

  useEffect(() => {
    if (mode !== 'single') {
      return
    }

    const parsed = tryParseJson(jsonInput)

    if (parsed) {
      setFields(parsed)
    }
  }, [jsonInput, mode])

  const updateField = (key: string, value: unknown) => {
    const updated = { ...fields, [key]: value }
    setFields(updated)
    setJsonInput(JSON.stringify(updated, null, 2))
  }

  return (
    <div className="panel input-panel">
      <div className="panel-header">
        <div>
          <h3>
            {mode === 'single'
              ? 'Return Data'
              : 'Bulk Return Data'}
          </h3>

          <p>
            {mode === 'single'
              ? 'Enter one feature payload for assessment.'
              : 'Upload a CSV containing return records.'}
          </p>
        </div>
      </div>

      {mode === 'single' && (
        <>
          <div className="input-mode-switch">
            <button
              type="button"
              className={
                singleInputMode === 'form' ? 'active' : ''
              }
              onClick={() => setSingleInputMode('form')}
            >
              Guided Form
            </button>

            <button
              type="button"
              className={
                singleInputMode === 'json' ? 'active' : ''
              }
              onClick={() => setSingleInputMode('json')}
            >
              Developer JSON
            </button>
          </div>

          {singleInputMode === 'form' && (
            <div className="return-form">
              {FIELD_GROUPS.map((group) => (
                <div
                  className="return-form-group"
                  key={group.title}
                >
                  <h4>{group.title}</h4>

                  <div className="return-form-grid">
                    {group.fields.map((field) => (
                      <div className="field" key={field.key}>
                        <label htmlFor={field.key}>
                          {field.label}
                        </label>

                        {field.type === 'select' && (
                          <select
                            id={field.key}
                            className="field-input"
                            value={
                              (fields[field.key] as string) ??
                              field.options[0]
                            }
                            onChange={(event) =>
                              updateField(
                                field.key,
                                event.target.value,
                              )
                            }
                          >
                            {field.options.map((option) => (
                              <option
                                key={option}
                                value={option}
                              >
                                {option}
                              </option>
                            ))}
                          </select>
                        )}

                        {field.type === 'number' && (
                          <input
                            id={field.key}
                            className="field-input"
                            type="number"
                            step={field.step ?? 1}
                            min={field.min}
                            max={field.max}
                            value={
                              typeof fields[field.key] ===
                              'number'
                                ? (fields[field.key] as number)
                                : ''
                            }
                            onChange={(
                              event: ChangeEvent<HTMLInputElement>,
                            ) => {
                              const raw = event.target.value
                              updateField(
                                field.key,
                                raw === ''
                                  ? 0
                                  : Number(raw),
                              )
                            }}
                          />
                        )}

                        {field.type === 'boolean' && (
                          <label className="field-checkbox">
                            <input
                              id={field.key}
                              type="checkbox"
                              checked={Boolean(
                                fields[field.key],
                              )}
                              onChange={(event) =>
                                updateField(
                                  field.key,
                                  event.target.checked,
                                )
                              }
                            />
                            <span>
                              {fields[field.key]
                                ? 'Yes'
                                : 'No'}
                            </span>
                          </label>
                        )}

                        <span className="field-help">
                          {field.help}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {singleInputMode === 'json' && (
            <textarea
              value={jsonInput}
              onChange={(event) =>
                setJsonInput(event.target.value)
              }
              placeholder={jsonInput}
              spellCheck={false}
            />
          )}

          <button
            className="analyze-button"
            type="button"
            onClick={handleAnalyze}
            disabled={loading}
          >
            {loading
              ? 'Analyzing...'
              : 'Analyze Return Risk'}
          </button>
        </>
      )}

      {mode === 'batch' && (
        <div className="bulk-input">
          <div className="batch-input-switch">
            <button
              type="button"
              className={
                batchInputMode === 'csv' ? 'active' : ''
              }
              onClick={() => setBatchInputMode('csv')}
            >
              CSV Upload
            </button>

            <button
              type="button"
              className={
                batchInputMode === 'json' ? 'active' : ''
              }
              onClick={() => setBatchInputMode('json')}
            >
              Developer JSON
            </button>
          </div>

          {batchInputMode === 'csv' && (
            <>
              <label className="csv-dropzone">
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(
                    event: ChangeEvent<HTMLInputElement>,
                  ) => {
                    const file = event.target.files?.[0]

                    if (file) {
                      handleCsvFile(file)
                    }
                  }}
                />

                <div className="upload-icon">↑</div>

                <strong>
                  {csvFileName || 'Upload CSV file'}
                </strong>

                <span>
                  Select a CSV containing the 25 RiskGuard
                  features.
                </span>
              </label>

              {batchRows.length > 0 && (
                <div className="csv-info">
                  <strong>{batchRows.length}</strong>
                  <span>records ready for analysis</span>
                </div>
              )}

              <button
                className="analyze-button"
                type="button"
                onClick={handleAnalyze}
                disabled={
                  loading || batchRows.length === 0
                }
              >
                {loading
                  ? 'Analyzing...'
                  : `Analyze ${batchRows.length || ''} Returns`}
              </button>
            </>
          )}

          {batchInputMode === 'json' && (
            <>
              <textarea
                value={jsonInput}
                onChange={(event) =>
                  setJsonInput(event.target.value)
                }
                placeholder='[{"order_category":"Electronics",...}]'
                spellCheck={false}
              />

              <button
                className="analyze-button"
                type="button"
                onClick={handleAnalyze}
                disabled={loading}
              >
                {loading
                  ? 'Analyzing...'
                  : 'Analyze Batch JSON'}
              </button>
            </>
          )}
        </div>
      )}

      {error && (
        <div className="error-box">
          {error}
        </div>
      )}
    </div>
  )
}

export default ReturnInput