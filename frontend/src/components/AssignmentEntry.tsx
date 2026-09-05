import { useState } from 'react'
import { Mail, Hash, ArrowLeft } from 'lucide-react'
import {
  getAssignment,
  createAssignment,
  type Assignment,
} from '../api/assignment'

type AssignmentEntryProps = {
  onAssignmentSelected: (assignment: Assignment) => void
}

function NetworkMotif() {
  // Purely decorative — a faint node graph echoing the Network
  // Analysis feature (connected accounts / shared signals).
  return (
    <svg
      className="entry-graph"
      viewBox="0 0 420 420"
      fill="none"
      aria-hidden="true"
    >
      <g stroke="rgba(255,255,255,0.14)" strokeWidth="1">
        <line x1="120" y1="150" x2="210" y2="90" />
        <line x1="210" y1="90" x2="300" y2="140" />
        <line x1="120" y1="150" x2="90" y2="250" />
        <line x1="120" y1="150" x2="210" y2="220" />
        <line x1="210" y1="220" x2="300" y2="140" />
        <line x1="210" y1="220" x2="180" y2="320" />
        <line x1="210" y1="220" x2="300" y2="290" />
        <line x1="300" y1="140" x2="340" y2="230" />
      </g>
      <circle cx="210" cy="220" r="7" fill="rgba(255,255,255,0.9)" />
      <circle cx="120" cy="150" r="4.5" fill="rgba(255,255,255,0.45)" />
      <circle cx="210" cy="90" r="4.5" fill="rgba(255,255,255,0.45)" />
      <circle cx="300" cy="140" r="4.5" fill="rgba(255,255,255,0.45)" />
      <circle cx="90" cy="250" r="4.5" fill="rgba(255,255,255,0.45)" />
      <circle cx="180" cy="320" r="4.5" fill="rgba(255,255,255,0.45)" />
      <circle cx="300" cy="290" r="4.5" fill="rgba(255,255,255,0.45)" />
      <circle cx="340" cy="230" r="4.5" fill="rgba(255,255,255,0.45)" />
    </svg>
  )
}

function AssignmentEntry({
  onAssignmentSelected,
}: AssignmentEntryProps) {
  const [emailInput, setEmailInput] = useState('')
  const [assignmentNumberInput, setAssignmentNumberInput] = useState('')
  const [assignmentNameInput, setAssignmentNameInput] = useState('')

  const [entryStep, setEntryStep] = useState<
    'email' | 'assignment'
  >('email')

  const [assignmentMode, setAssignmentMode] = useState<
    'lookup' | 'create'
  >('lookup')

  const [entryLoading, setEntryLoading] = useState(false)
  const [entryError, setEntryError] = useState('')

  const handleEmailContinue = async () => {
    const value = emailInput.trim()

    if (!value) {
      setEntryError(
        'Please enter your email or assignment number.',
      )
      return
    }

    const isEmail = /^\S+@\S+\.\S+$/.test(value)
    const isNumber = /^\d+$/.test(value)

    if (!isEmail && !isNumber) {
      setEntryError(
        'Enter a valid Gmail/email or assignment number.',
      )
      return
    }

    setEntryError('')

    if (isNumber) {
      setAssignmentNumberInput(value)
      setEntryLoading(true)

      try {
        const existing = await getAssignment(value)

        if (existing) {
          onAssignmentSelected(existing)
        } else {
          setAssignmentMode('create')
          setEntryStep('assignment')
        }
      } catch (err) {
        setEntryError(
          err instanceof Error
            ? err.message
            : 'Unable to check assignment.',
        )
      } finally {
        setEntryLoading(false)
      }

      return
    }

    setEntryStep('assignment')
  }

  const handleAssignmentLookup = async () => {
    const number = assignmentNumberInput.trim()

    if (!number) {
      setEntryError('Please enter an assignment number.')
      return
    }

    setEntryLoading(true)
    setEntryError('')

    try {
      const existing = await getAssignment(number)

      if (existing) {
        onAssignmentSelected(existing)
      } else {
        setAssignmentMode('create')
        setEntryError('')
      }
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : 'Unable to find assignment.'

      setEntryError(message)
    } finally {
      setEntryLoading(false)
    }
  }

  const handleAssignmentCreate = async () => {
    const number = assignmentNumberInput.trim()
    const name = assignmentNameInput.trim()

    if (!number) {
      setEntryError('Please enter an assignment number.')
      return
    }

    if (!name) {
      setEntryError('Please enter an assignment name.')
      return
    }

    setEntryLoading(true)
    setEntryError('')

    try {
      const created = await createAssignment(number, name)

      onAssignmentSelected(created)
    } catch (err) {
      setEntryError(
        err instanceof Error
          ? err.message
          : 'Unable to create assignment.',
      )
    } finally {
      setEntryLoading(false)
    }
  }

  return (
    <div className="entry-shell">
      <div className="entry-frame">
        <div className="entry-brand-panel">
          <NetworkMotif />

          <div className="entry-brand-panel-top">
            <div className="entry-brand-mark">R</div>

            <div>
              <h1>RiskGuard AI</h1>
              <span>Return Abuse Intelligence</span>
            </div>
          </div>

          <p className="entry-brand-tagline">
            Stop the merchant losing money to return fraud —
            scored, explained, and reviewed in one workspace.
          </p>

          <div className="entry-steps">
            <span
              className={
                entryStep === 'email' ? 'active' : 'done'
              }
            />
            <span
              className={
                entryStep === 'assignment' ? 'active' : ''
              }
            />
          </div>
        </div>

        <div className="entry-form-panel">
          {entryStep === 'email' && (
            <>
              <div className="entry-heading">
                <h2>Welcome back</h2>

                <p>
                  Enter your email or assignment number to open
                  your risk intelligence workspace.
                </p>
              </div>

              <div className="entry-form">
                <label htmlFor="email">
                  Email or assignment number
                </label>

                <div className="entry-field">
                  <Mail size={17} strokeWidth={2} />

                  <input
                    id="email"
                    type="text"
                    value={emailInput}
                    onChange={(event) => {
                      setEmailInput(event.target.value)
                      setEntryError('')
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        handleEmailContinue()
                      }
                    }}
                    placeholder="you@example.com or 98765"
                    autoFocus
                  />
                </div>

                {entryError && (
                  <div className="entry-error">
                    {entryError}
                  </div>
                )}

                <button
                  type="button"
                  className="entry-primary"
                  onClick={handleEmailContinue}
                  disabled={entryLoading}
                >
                  {entryLoading ? 'Checking...' : 'Continue'}
                </button>
              </div>
            </>
          )}

          {entryStep === 'assignment' && (
            <>
              <div className="entry-heading">
                <h2>Open your assignment</h2>

                <p>
                  Enter the assignment number to open an existing
                  workspace, or create a new one.
                </p>
              </div>

              <div className="entry-form">
                <label htmlFor="assignment-number">
                  Assignment number
                </label>

                <div className="entry-field">
                  <Hash size={17} strokeWidth={2} />

                  <input
                    id="assignment-number"
                    type="text"
                    value={assignmentNumberInput}
                    onChange={(event) => {
                      setAssignmentNumberInput(event.target.value)
                      setEntryError('')
                      setAssignmentMode('lookup')
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        handleAssignmentLookup()
                      }
                    }}
                    placeholder="e.g. 98765"
                    autoFocus
                  />
                </div>

                {assignmentMode === 'create' && (
                  <>
                    <label htmlFor="assignment-name">
                      Assignment name
                    </label>

                    <div className="entry-field">
                      <input
                        id="assignment-name"
                        type="text"
                        value={assignmentNameInput}
                        onChange={(event) => {
                          setAssignmentNameInput(event.target.value)
                          setEntryError('')
                        }}
                        placeholder="e.g. Return Abuse Analysis"
                      />
                    </div>
                  </>
                )}

                {entryError && (
                  <div className="entry-error">
                    {entryError}
                  </div>
                )}

                {assignmentMode === 'lookup' ? (
                  <button
                    type="button"
                    className="entry-primary"
                    onClick={handleAssignmentLookup}
                    disabled={entryLoading}
                  >
                    {entryLoading
                      ? 'Checking...'
                      : 'Open assignment'}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="entry-primary"
                    onClick={handleAssignmentCreate}
                    disabled={entryLoading}
                  >
                    {entryLoading
                      ? 'Creating...'
                      : 'Create assignment'}
                  </button>
                )}

                <button
                  type="button"
                  className="entry-secondary"
                  onClick={() => {
                    setEntryStep('email')
                    setEntryError('')
                  }}
                >
                  <ArrowLeft size={15} strokeWidth={2.2} />
                  Back
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default AssignmentEntry